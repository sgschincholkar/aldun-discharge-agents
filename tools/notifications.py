from datetime import datetime, timezone

def send_wa_email_notification(patient_phone: str, message_type: str) -> dict:
    return {
        "delivered": True,
        "channel": "whatsapp",
        "message_type": message_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
