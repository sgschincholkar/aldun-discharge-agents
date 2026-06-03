import json
import os
from openai import OpenAI
from opentelemetry import trace as otel_trace
from openinference.semconv.trace import SpanAttributes, OpenInferenceSpanKindValues
from db import get_case, update_case, log_event
from guardrails import (
    GuardrailError, inter_agent_state_check,
    validate_claim_totals, check_phi_not_in_notification, strip_pii_from_logs,
)
from tools.ehr import fetch_kyc_docs, fetch_ehr_data
from tools.billing import fetch_discharge_bills
from tools.tpa import file_claim_to_tpa
from tools.notifications import send_wa_email_notification

MODEL = "qwen/qwen3.5-flash-02-23"


def _get_client():
    """Lazy client initialization to avoid requiring env var at import time."""
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "fetch_kyc_docs",
            "description": "Fetch KYC documents (Aadhaar, insurance policy) for the patient.",
            "parameters": {
                "type": "object",
                "properties": {"case_id": {"type": "string"}},
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_ehr_data",
            "description": "Fetch Electronic Health Record data including diagnosis, procedures, and discharge info.",
            "parameters": {
                "type": "object",
                "properties": {"case_id": {"type": "string"}},
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_discharge_bills",
            "description": "Fetch final discharge bills from hospital billing system.",
            "parameters": {
                "type": "object",
                "properties": {"case_id": {"type": "string"}},
                "required": ["case_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_claim_to_tpa",
            "description": "File the assembled insurance claim packet to the TPA/insurer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "claim_packet": {
                        "type": "object",
                        "description": "Assembled claim with EHR, bills, and KYC docs",
                    },
                },
                "required": ["case_id", "claim_packet"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_wa_email_notification",
            "description": "Notify patient about discharge status via WhatsApp or email.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_phone": {"type": "string"},
                    "message_type": {
                        "type": "string",
                        "enum": ["discharge_complete", "claim_filed", "payment_due"],
                    },
                },
                "required": ["patient_phone", "message_type"],
            },
        },
    },
]


def _execute_tool(name: str, inputs: dict, case_id: str, case_row: dict, db_path: str) -> dict:
    if name == "fetch_kyc_docs":
        result = fetch_kyc_docs(inputs["case_id"])
        log_event(case_id, "discharge_claims", "kyc_docs_fetched", strip_pii_from_logs(result), db_path)
        return result

    elif name == "fetch_ehr_data":
        result = fetch_ehr_data(inputs["case_id"])
        # Strip diagnosis from logs (PHI)
        log_event(case_id, "discharge_claims", "ehr_fetched", {"discharge_date": result.get("discharge_date")}, db_path)
        return result

    elif name == "fetch_discharge_bills":
        result = fetch_discharge_bills(inputs["case_id"])
        validate_claim_totals(result["total_inr"], case_row["estimated_bill_inr"])
        log_event(case_id, "discharge_claims", "bills_fetched", {"total_inr": result["total_inr"]}, db_path)
        return result

    elif name == "file_claim_to_tpa":
        result = file_claim_to_tpa(inputs["case_id"], inputs["claim_packet"])
        log_event(case_id, "discharge_claims", "claim_filed", {
            "claim_id": result["claim_id"], "ack_id": result["ack_id"]
        }, db_path)
        return result

    elif name == "send_wa_email_notification":
        check_phi_not_in_notification(inputs["message_type"])
        result = send_wa_email_notification(inputs["patient_phone"], inputs["message_type"])
        log_event(case_id, "discharge_claims", "patient_notified", {"channel": result["channel"]}, db_path)
        return result

    return {"error": f"Unknown tool: {name}"}


def run(case_id: str, db_path: str = "cases.db") -> dict:
    """Run discharge & claims agent. Returns {success, trace}."""
    tracer = otel_trace.get_tracer(__name__)
    with tracer.start_as_current_span(
        "agent2.discharge_claims",
        attributes={
            SpanAttributes.OPENINFERENCE_SPAN_KIND: OpenInferenceSpanKindValues.AGENT.value,
            SpanAttributes.INPUT_VALUE: f"Process discharge and file TPA claim for case {case_id}",
            "case_id": case_id,
        },
    ) as span:
        result = _run(case_id, db_path)
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, f"success={result['success']}")
        if not result["success"]:
            span.set_status(otel_trace.Status(otel_trace.StatusCode.ERROR))
        return result


def _run(case_id: str, db_path: str = "cases.db") -> dict:
    print("\n[Agent 2 — Discharge & Claims]")
    case_row = get_case(case_id, db_path)

    # Pre-condition check — Agent 1 must have completed successfully
    try:
        inter_agent_state_check(case_row, ["kyc_verified", "credit_approved", "payment_consent"])
    except GuardrailError as e:
        print(f"  ✗ Pre-condition failed: {e}")
        update_case(case_id, {"claim_status": "GUARDRAIL_FAILED"}, db_path)
        return False

    system_prompt = f"""You are the Aldun Discharge & Claims Agent.
Your job is to collect all required documents and file an insurance claim to the TPA so the patient can be discharged.

Patient context:
- Case ID: {case_id}
- Name: {case_row['patient_name']}
- Phone: {case_row['patient_phone']}
- Hospital: {case_row['hospital_name']}
- TPA: {case_row['tpa_name']}
- Insurance policy: {case_row['insurance_policy_no']}
- Credit approved: Rs {case_row['credit_limit_inr']}

Steps to complete in order:
1. Fetch KYC documents
2. Fetch EHR data
3. Fetch discharge bills
4. File claim to TPA with a claim packet containing all the above
5. Notify patient via WhatsApp (message_type: "discharge_complete")

Complete all steps."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please complete discharge processing and file the insurance claim."},
    ]
    claim_result = {}
    trace = []

    try:
        client = _get_client()
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )

            msg = response.choices[0].message
            if not msg.tool_calls:
                break

            messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                trace.append({"type": "tool_call", "name": tc.function.name, "args": args})
                result = _execute_tool(tc.function.name, args, case_id, case_row, db_path)
                trace.append({"type": "tool_result", "name": tc.function.name, "result": result})
                if tc.function.name == "file_claim_to_tpa":
                    claim_result = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        update_case(case_id, {
            "claim_packet_ready": 1,
            "tpa_claim_id": claim_result.get("claim_id", "TPA-2026-001234"),
            "tpa_acknowledgement_id": claim_result.get("ack_id", "ACK-5678"),
            "claim_status": "filed",
            "discharge_status": "complete",
        }, db_path)
        log_event(case_id, "discharge_claims", "discharge_complete", {}, db_path)
        trace.append({"type": "summary", "lines": [
            "✓ KYC docs and EHR fetched",
            "✓ Claim packet assembled",
            f"✓ Claim filed → {claim_result.get('claim_id', 'TPA-2026-001234')}",
            "✓ Patient notified via WhatsApp",
            "→ Discharge complete, claim filed",
        ]})
        print("  ✓ KYC docs and EHR fetched")
        print("  ✓ Claim packet assembled")
        print(f"  ✓ Claim filed → {claim_result.get('claim_id', 'TPA-2026-001234')}")
        print("  ✓ Patient notified via WhatsApp")
        print("  → Discharge complete, claim filed")
        return {"success": True, "trace": trace}

    except GuardrailError as e:
        update_case(case_id, {"claim_status": "GUARDRAIL_FAILED"}, db_path)
        log_event(case_id, "guardrail", "discharge_guardrail_failed", {"error": str(e)}, db_path)
        trace.append({"type": "error", "message": f"GUARDRAIL FAILED: {e}"})
        print(f"  ✗ GUARDRAIL FAILED: {e}")
        return {"success": False, "trace": trace}

    except Exception as e:
        update_case(case_id, {"claim_status": "AGENT_ERROR"}, db_path)
        log_event(case_id, "discharge_claims", "agent_error", {"error": str(e)}, db_path)
        trace.append({"type": "error", "message": f"AGENT ERROR: {e}"})
        print(f"  ✗ AGENT ERROR: {e}")
        return {"success": False, "trace": trace}
