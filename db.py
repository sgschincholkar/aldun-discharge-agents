import sqlite3
import uuid
import json
from datetime import datetime, timezone

PII_KEYS = {"aadhaar", "aadhaar_number", "phone", "pan", "bank_account", "ifsc"}

def _strip_pii(payload: dict) -> dict:
    return {k: v for k, v in payload.items() if k.lower() not in PII_KEYS}

def init_db(db_path: str = "cases.db") -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            case_id TEXT PRIMARY KEY,
            patient_name TEXT,
            patient_phone TEXT,
            aadhaar_last4 TEXT,
            hospital_name TEXT,
            admission_date TEXT,
            estimated_bill_inr REAL,
            insurance_policy_no TEXT,
            tpa_name TEXT,
            kyc_verified INTEGER DEFAULT 0,
            credit_approved INTEGER DEFAULT 0,
            credit_limit_inr REAL,
            payment_consent INTEGER DEFAULT 0,
            onboarding_status TEXT DEFAULT 'pending',
            claim_packet_ready INTEGER DEFAULT 0,
            tpa_claim_id TEXT,
            tpa_acknowledgement_id TEXT,
            claim_status TEXT DEFAULT 'pending',
            discharge_status TEXT DEFAULT 'pending',
            tpa_amount_received_inr REAL,
            patient_deductible_inr REAL,
            patient_paid INTEGER DEFAULT 0,
            case_status TEXT DEFAULT 'open',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT,
            agent TEXT,
            event TEXT,
            payload TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_case(data: dict, db_path: str = "cases.db") -> str:
    case_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute("""
        INSERT INTO cases (
            case_id, patient_name, patient_phone, aadhaar_last4,
            hospital_name, admission_date, estimated_bill_inr,
            insurance_policy_no, tpa_name, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        case_id, data["patient_name"], data["patient_phone"], data["aadhaar_last4"],
        data["hospital_name"], data["admission_date"], data["estimated_bill_inr"],
        data["insurance_policy_no"], data["tpa_name"], now, now
    ))
    conn.commit()
    conn.close()
    return case_id

def get_case(case_id: str, db_path: str = "cases.db") -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM cases WHERE case_id=?", (case_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

def update_case(case_id: str, fields: dict, db_path: str = "cases.db") -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [case_id]
    conn = sqlite3.connect(db_path)
    conn.execute(f"UPDATE cases SET {set_clause} WHERE case_id=?", values)
    conn.commit()
    conn.close()

def log_event(case_id: str, agent: str, event: str, payload: dict, db_path: str = "cases.db") -> None:
    clean = _strip_pii(payload)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO event_log (case_id, agent, event, payload, timestamp) VALUES (?,?,?,?,?)",
        (case_id, agent, event, json.dumps(clean), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
