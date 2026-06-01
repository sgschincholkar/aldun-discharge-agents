from datetime import datetime, timezone

def verify_aadhaar_otp(aadhaar_last4: str, otp: str) -> dict:
    return {"verified": True, "name": "Rajesh Kumar", "confidence": 0.97}

def store_kyc_info(case_id: str, aadhaar_last4: str, name: str) -> dict:
    return {"stored": True}
