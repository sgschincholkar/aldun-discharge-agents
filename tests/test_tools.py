from tools.kyc import verify_aadhaar_otp, store_kyc_info
from tools.credit import check_credit_score_nbfc, get_credit_approval_nbfc
from tools.ehr import fetch_ehr_data, fetch_kyc_docs
from tools.billing import fetch_discharge_bills, fetch_discharge_bill_estimate
from tools.tpa import file_claim_to_tpa, verify_tpa_payment_received
from tools.notifications import send_wa_email_notification
from tools.payment import confirm_patient_deductible_paid, update_payment_in_aldun_db, close_case

def test_verify_aadhaar_otp():
    result = verify_aadhaar_otp("1234", "000000")
    assert result["verified"] is True
    assert "name" in result
    assert result["confidence"] >= 0.9

def test_check_credit_score():
    result = check_credit_score_nbfc("9876543210")
    assert "cibil_score" in result
    assert isinstance(result["cibil_score"], int)

def test_get_credit_approval():
    result = get_credit_approval_nbfc("case-001", 85000)
    assert result["approved"] is True
    assert result["limit_inr"] == 85000

def test_fetch_discharge_bills():
    result = fetch_discharge_bills("case-001")
    assert "total_inr" in result
    assert isinstance(result["total_inr"], float)
    assert "line_items" in result

def test_file_claim_to_tpa():
    claim_packet = {"case_id": "case-001", "total_inr": 85000}
    result = file_claim_to_tpa("case-001", claim_packet)
    assert result["status"] == "submitted"
    assert "claim_id" in result
    assert "ack_id" in result

def test_verify_tpa_payment():
    result = verify_tpa_payment_received("TPA-2026-001234")
    assert result["received"] is True
    assert result["amount_inr"] > 0

def test_confirm_patient_deductible():
    result = confirm_patient_deductible_paid("case-001")
    assert result["paid"] is True
    assert result["amount_inr"] > 0

def test_send_notification():
    result = send_wa_email_notification("9876543210", "discharge_complete")
    assert result["delivered"] is True
    assert result["channel"] in ("whatsapp", "email")

def test_close_case():
    result = close_case("case-001")
    assert result["closed"] is True
    assert "closed_at" in result
