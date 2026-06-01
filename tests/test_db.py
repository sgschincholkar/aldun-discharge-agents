import pytest
import os
import json
from db import init_db, create_case, get_case, update_case, log_event

DB_PATH = "test_cases.db"

@pytest.fixture(autouse=True)
def fresh_db():
    init_db(DB_PATH)
    yield
    os.remove(DB_PATH)

def test_create_and_get_case():
    case_data = {
        "patient_name": "Rajesh Kumar",
        "patient_phone": "9876543210",
        "aadhaar_last4": "1234",
        "hospital_name": "Fortis Hospital Bangalore",
        "admission_date": "2026-05-27",
        "estimated_bill_inr": 85000.0,
        "insurance_policy_no": "HDFC-HLTH-2024-789",
        "tpa_name": "Medi Assist",
    }
    case_id = create_case(case_data, db_path=DB_PATH)
    assert case_id is not None

    row = get_case(case_id, db_path=DB_PATH)
    assert row["patient_name"] == "Rajesh Kumar"
    assert row["onboarding_status"] == "pending"
    assert row["case_status"] == "open"

def test_update_case():
    case_data = {
        "patient_name": "Test Patient",
        "patient_phone": "9999999999",
        "aadhaar_last4": "5678",
        "hospital_name": "Apollo",
        "admission_date": "2026-05-27",
        "estimated_bill_inr": 50000.0,
        "insurance_policy_no": "POL-001",
        "tpa_name": "TPA Corp",
    }
    case_id = create_case(case_data, db_path=DB_PATH)
    update_case(case_id, {"onboarding_status": "complete", "kyc_verified": 1}, db_path=DB_PATH)

    row = get_case(case_id, db_path=DB_PATH)
    assert row["onboarding_status"] == "complete"
    assert row["kyc_verified"] == 1

def test_log_event_strips_pii():
    case_data = {
        "patient_name": "Test",
        "patient_phone": "9999999999",
        "aadhaar_last4": "0000",
        "hospital_name": "H",
        "admission_date": "2026-05-27",
        "estimated_bill_inr": 1000.0,
        "insurance_policy_no": "P",
        "tpa_name": "T",
    }
    case_id = create_case(case_data, db_path=DB_PATH)
    payload = {"aadhaar": "1234-5678-9012-3456", "score": 742}
    log_event(case_id, "onboarding", "kyc_verified", payload, db_path=DB_PATH)

    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT payload FROM event_log WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    stored = json.loads(row[0])
    assert "aadhaar" not in stored
    assert stored["score"] == 742
