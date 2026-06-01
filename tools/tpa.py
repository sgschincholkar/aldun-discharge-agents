from datetime import datetime, timezone

def file_claim_to_tpa(case_id: str, claim_packet: dict) -> dict:
    return {
        "claim_id": "TPA-2026-001234",
        "ack_id": "ACK-5678",
        "status": "submitted",
        "filed_at": datetime.now(timezone.utc).isoformat(),
    }

def verify_tpa_payment_received(tpa_claim_id: str) -> dict:
    return {
        "received": True,
        "amount_inr": 76500.0,
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
