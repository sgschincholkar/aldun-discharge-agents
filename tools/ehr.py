from datetime import datetime, timezone

def fetch_kyc_docs(case_id: str) -> dict:
    return {
        "docs": ["aadhaar.pdf", "policy.pdf"],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

def fetch_ehr_data(case_id: str) -> dict:
    return {
        "diagnosis": "Acute Appendicitis",
        "procedures": ["Appendectomy"],
        "discharge_date": "2026-05-27",
        "total_inr": 84150.0,
    }
