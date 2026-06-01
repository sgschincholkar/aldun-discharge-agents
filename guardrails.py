import difflib

PHI_KEYWORDS = [
    "diagnosis", "procedure", "diabetes", "hypertension", "cancer",
    "surgery", "fracture", "infection", "treatment", "prescription",
]
PII_KEYS = {"aadhaar", "aadhaar_number", "phone", "pan", "bank_account", "ifsc"}

class GuardrailError(Exception):
    pass

def mask_aadhaar(number: str) -> str:
    return number[-4:]

def ocr_confidence_check(score: float, threshold: float = 0.92) -> None:
    if score < threshold:
        raise GuardrailError(f"OCR confidence {score:.2f} below threshold {threshold}")

def cross_check_aadhaar_name(ocr_name: str, hospital_name: str, threshold: float = 0.85) -> None:
    ratio = difflib.SequenceMatcher(None, ocr_name.lower(), hospital_name.lower()).ratio()
    if ratio < threshold:
        raise GuardrailError(
            f"Name mismatch: OCR='{ocr_name}' vs Hospital='{hospital_name}' (similarity={ratio:.2f})"
        )

def credit_approval_check(cibil_score: int, amount_inr: float) -> None:
    # HITL: CIBIL between 600-650 — see CLAUDE.md
    if cibil_score < 650:
        raise GuardrailError(f"CIBIL score {cibil_score} below minimum 650. Block credit approval.")

def payment_disbursement_check(bill_inr: float, ehr_inr: float, idempotency_key: str) -> None:
    diff_pct = abs(bill_inr - ehr_inr) / bill_inr
    if diff_pct > 0.05:
        raise GuardrailError(
            f"Bill vs EHR mismatch: bill={bill_inr}, ehr={ehr_inr}, diff={diff_pct:.1%} > 5%"
        )

def recovery_check(tpa_received: float, approved_amount: float, retry_count: int) -> None:
    if retry_count > 3:
        raise GuardrailError(f"Max retry count exceeded ({retry_count}/3). Escalate to ops.")

def tpa_sanity_check(tpa_amount: float, original_billed: float) -> None:
    if tpa_amount > original_billed:
        raise GuardrailError(
            f"TPA amount exceeds original billed: tpa={tpa_amount}, billed={original_billed}"
        )

def validate_claim_totals(llm_extracted_inr: float, source_bill_inr: float) -> None:
    diff_pct = abs(llm_extracted_inr - source_bill_inr) / source_bill_inr
    if diff_pct > 0.01:
        raise GuardrailError(
            f"Claim total mismatch: llm={llm_extracted_inr}, source={source_bill_inr}, diff={diff_pct:.1%}"
        )

def check_phi_not_in_notification(message: str) -> None:
    lower = message.lower()
    for keyword in PHI_KEYWORDS:
        if keyword in lower:
            raise GuardrailError(f"PHI detected in notification message: '{keyword}'")

def strip_pii_from_logs(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k.lower() not in PII_KEYS}

def inter_agent_state_check(case_row: dict, required_fields: list) -> None:
    for field in required_fields:
        val = case_row.get(field)
        if not val:
            raise GuardrailError(
                f"Pre-condition failed: '{field}' is not set or falsy. Cannot proceed."
            )

def reconciliation_audit(tpa_amount: float, patient_amount: float, original_billed: float) -> None:
    total_recovered = tpa_amount + patient_amount
    diff = abs(total_recovered - original_billed)
    if diff > 1.0:
        raise GuardrailError(
            f"Reconciliation failed: tpa={tpa_amount} + patient={patient_amount} = {total_recovered}, "
            f"expected={original_billed}, shortfall={diff}"
        )
