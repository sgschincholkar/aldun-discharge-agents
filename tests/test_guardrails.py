import pytest
from guardrails import (
    GuardrailError,
    mask_aadhaar,
    ocr_confidence_check,
    cross_check_aadhaar_name,
    credit_approval_check,
    payment_disbursement_check,
    recovery_check,
    tpa_sanity_check,
    validate_claim_totals,
    check_phi_not_in_notification,
    strip_pii_from_logs,
    inter_agent_state_check,
    reconciliation_audit,
)

def test_mask_aadhaar_returns_last4():
    assert mask_aadhaar("123456789012") == "9012"

def test_mask_aadhaar_already_last4():
    assert mask_aadhaar("9012") == "9012"

def test_ocr_passes_above_threshold():
    ocr_confidence_check(0.95)

def test_ocr_fails_below_threshold():
    with pytest.raises(GuardrailError, match="OCR confidence"):
        ocr_confidence_check(0.88)

def test_name_match_passes():
    cross_check_aadhaar_name("Rajesh Kumar", "Rajesh Kumar")

def test_name_match_passes_fuzzy():
    cross_check_aadhaar_name("Rajesh Kumar", "Rajesh Kumаr")

def test_name_match_fails():
    with pytest.raises(GuardrailError, match="Name mismatch"):
        cross_check_aadhaar_name("Rajesh Kumar", "Priya Sharma")

def test_credit_passes():
    credit_approval_check(cibil_score=742, amount_inr=85000)

def test_credit_fails_low_cibil():
    with pytest.raises(GuardrailError, match="CIBIL"):
        credit_approval_check(cibil_score=500, amount_inr=85000)

def test_disbursement_passes():
    payment_disbursement_check(bill_inr=85000, ehr_inr=84000, idempotency_key="KEY-001")

def test_disbursement_fails_mismatch():
    with pytest.raises(GuardrailError, match="Bill vs EHR mismatch"):
        payment_disbursement_check(bill_inr=85000, ehr_inr=60000, idempotency_key="KEY-002")

def test_recovery_passes():
    recovery_check(tpa_received=76500, approved_amount=85000, retry_count=1)

def test_recovery_fails_too_many_retries():
    with pytest.raises(GuardrailError, match="retry"):
        recovery_check(tpa_received=0, approved_amount=85000, retry_count=4)

def test_tpa_sanity_passes():
    tpa_sanity_check(tpa_amount=76500, original_billed=85000)

def test_tpa_sanity_fails_overpayment():
    with pytest.raises(GuardrailError, match="TPA amount exceeds"):
        tpa_sanity_check(tpa_amount=90000, original_billed=85000)

def test_claim_totals_pass():
    validate_claim_totals(llm_extracted_inr=85000, source_bill_inr=85000)

def test_claim_totals_fail():
    with pytest.raises(GuardrailError, match="Claim total mismatch"):
        validate_claim_totals(llm_extracted_inr=70000, source_bill_inr=85000)

def test_phi_check_passes():
    check_phi_not_in_notification("Your discharge is complete. Payment of Rs 8500 is due.")

def test_phi_check_fails():
    with pytest.raises(GuardrailError, match="PHI detected"):
        check_phi_not_in_notification("Your diagnosis of Type 2 Diabetes has been filed.")

def test_strip_pii():
    payload = {"aadhaar": "1234-5678-9012-3456", "score": 742, "phone": "9876543210"}
    result = strip_pii_from_logs(payload)
    assert "aadhaar" not in result
    assert "phone" not in result
    assert result["score"] == 742

def test_inter_agent_passes():
    case_row = {"kyc_verified": 1, "credit_approved": 1, "payment_consent": 1}
    inter_agent_state_check(case_row, ["kyc_verified", "credit_approved", "payment_consent"])

def test_inter_agent_fails_missing_field():
    case_row = {"kyc_verified": 1, "credit_approved": 0, "payment_consent": 1}
    with pytest.raises(GuardrailError, match="credit_approved"):
        inter_agent_state_check(case_row, ["kyc_verified", "credit_approved", "payment_consent"])

def test_reconciliation_passes():
    reconciliation_audit(tpa_amount=76500, patient_amount=8500, original_billed=85000)

def test_reconciliation_fails_shortfall():
    with pytest.raises(GuardrailError, match="[Rr]econciliation"):
        reconciliation_audit(tpa_amount=60000, patient_amount=8500, original_billed=85000)
