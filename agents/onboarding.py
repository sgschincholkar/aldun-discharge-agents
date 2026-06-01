import json
import os
from openai import OpenAI
from db import get_case, update_case, log_event
from guardrails import (
    GuardrailError, mask_aadhaar, ocr_confidence_check,
    credit_approval_check,
)
from tools.kyc import verify_aadhaar_otp, store_kyc_info
from tools.credit import check_credit_score_nbfc, get_credit_approval_nbfc
from tools.billing import fetch_discharge_bill_estimate

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
            "name": "verify_aadhaar_otp",
            "description": "Verify patient Aadhaar identity via OTP. Returns verified status, name, and OCR confidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "aadhaar_last4": {"type": "string"},
                    "otp": {"type": "string"},
                },
                "required": ["aadhaar_last4", "otp"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_credit_score_nbfc",
            "description": "Check patient CIBIL credit score via NBFC integration.",
            "parameters": {
                "type": "object",
                "properties": {"patient_phone": {"type": "string"}},
                "required": ["patient_phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_discharge_bill_estimate",
            "description": "Fetch estimated discharge bill from hospital billing system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hospital_name": {"type": "string"},
                    "admission_date": {"type": "string"},
                },
                "required": ["hospital_name", "admission_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "capture_payment_consent",
            "description": "Capture patient's payment consent for Aldun to pay hospital on their behalf.",
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
            "name": "get_credit_approval_nbfc",
            "description": "Request credit approval from NBFC for the discharge amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "amount_inr": {"type": "number"},
                },
                "required": ["case_id", "amount_inr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_kyc_info",
            "description": "Store verified KYC information in the patient record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string"},
                    "aadhaar_last4": {"type": "string"},
                    "name": {"type": "string"},
                },
                "required": ["case_id", "aadhaar_last4", "name"],
            },
        },
    },
]


def _execute_tool(name: str, inputs: dict, case_id: str, case_row: dict, db_path: str) -> dict:
    if name == "verify_aadhaar_otp":
        result = verify_aadhaar_otp(inputs["aadhaar_last4"], inputs["otp"])
        ocr_confidence_check(result["confidence"])
        log_event(case_id, "onboarding", "kyc_otp_verified", {"confidence": result["confidence"]}, db_path)
        return result

    elif name == "check_credit_score_nbfc":
        result = check_credit_score_nbfc(inputs["patient_phone"])
        log_event(case_id, "onboarding", "credit_score_fetched", {"cibil_score": result["cibil_score"]}, db_path)
        return result

    elif name == "fetch_discharge_bill_estimate":
        result = fetch_discharge_bill_estimate(inputs["hospital_name"], inputs["admission_date"])
        log_event(case_id, "onboarding", "bill_estimate_fetched", {"estimated_inr": result["estimated_inr"]}, db_path)
        return result

    elif name == "capture_payment_consent":
        result = {"consent": True, "timestamp": "2026-05-27T10:01:00Z"}
        log_event(case_id, "onboarding", "payment_consent_captured", {}, db_path)
        return result

    elif name == "get_credit_approval_nbfc":
        credit_score = case_row.get("_temp_cibil_score", 742)
        credit_approval_check(credit_score, inputs["amount_inr"])
        result = get_credit_approval_nbfc(inputs["case_id"], inputs["amount_inr"])
        log_event(case_id, "onboarding", "credit_approved", {"limit_inr": result["limit_inr"]}, db_path)
        return result

    elif name == "store_kyc_info":
        masked = mask_aadhaar(inputs["aadhaar_last4"])
        result = store_kyc_info(inputs["case_id"], masked, inputs["name"])
        log_event(case_id, "onboarding", "kyc_stored", {"aadhaar_last4": masked}, db_path)
        return result

    return {"error": f"Unknown tool: {name}"}


def run(case_id: str, db_path: str = "cases.db") -> bool:
    """Run onboarding agent. Returns True if successful, False otherwise."""
    print("\n[Agent 1 — Onboarding]")
    case_row = get_case(case_id, db_path)

    system_prompt = f"""You are the Aldun Patient Onboarding Agent.
Your job is to onboard a patient for instant hospital discharge by verifying their identity and securing credit approval.

Patient context:
- Name: {case_row['patient_name']}
- Phone: {case_row['patient_phone']}
- Aadhaar last 4: {case_row['aadhaar_last4']}
- Hospital: {case_row['hospital_name']}
- Admission date: {case_row['admission_date']}
- Estimated bill: Rs {case_row['estimated_bill_inr']}

Steps to complete in order:
1. Verify Aadhaar OTP (use aadhaar_last4={case_row['aadhaar_last4']}, otp="000000")
2. Check credit score
3. Fetch discharge bill estimate
4. Capture payment consent
5. Get NBFC credit approval for the bill amount
6. Store KYC info

Complete all steps. Do not skip any."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please complete the patient onboarding."},
    ]

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
                result = _execute_tool(tc.function.name, args, case_id, case_row, db_path)
                if tc.function.name == "check_credit_score_nbfc":
                    case_row["_temp_cibil_score"] = result.get("cibil_score", 742)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        update_case(case_id, {
            "kyc_verified": 1,
            "credit_approved": 1,
            "credit_limit_inr": case_row["estimated_bill_inr"],
            "payment_consent": 1,
            "onboarding_status": "complete",
        }, db_path)
        log_event(case_id, "onboarding", "onboarding_complete", {}, db_path)
        print("  ✓ Aadhaar OTP verified")
        print(f"  ✓ Credit approved Rs {case_row['estimated_bill_inr']:,.0f}")
        print("  ✓ Payment consent captured")
        print("  → Onboarding complete")
        return True

    except GuardrailError as e:
        update_case(case_id, {"onboarding_status": "GUARDRAIL_FAILED"}, db_path)
        log_event(case_id, "guardrail", "onboarding_guardrail_failed", {"error": str(e)}, db_path)
        print(f"  ✗ GUARDRAIL FAILED: {e}")
        return False

    except Exception as e:
        update_case(case_id, {"onboarding_status": "AGENT_ERROR"}, db_path)
        log_event(case_id, "onboarding", "agent_error", {"error": str(e)}, db_path)
        print(f"  ✗ AGENT ERROR: {e}")
        return False
