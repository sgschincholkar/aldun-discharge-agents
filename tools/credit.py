from datetime import datetime, timezone

def check_credit_score_nbfc(patient_phone: str) -> dict:
    return {
        "cibil_score": 742,
        "bureau": "CIBIL",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

def get_credit_approval_nbfc(case_id: str, amount_inr: float) -> dict:
    return {"approved": True, "limit_inr": amount_inr, "approval_id": "NBFC-001"}
