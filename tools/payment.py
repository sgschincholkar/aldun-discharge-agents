from datetime import datetime, timezone

def confirm_patient_deductible_paid(case_id: str) -> dict:
    return {
        "paid": True,
        "amount_inr": 8500.0,
        "method": "UPI",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }

def update_payment_in_aldun_db(case_id: str, tpa_amount: float, patient_amount: float) -> dict:
    return {"updated": True}

def close_case(case_id: str) -> dict:
    return {"closed": True, "closed_at": datetime.now(timezone.utc).isoformat()}
