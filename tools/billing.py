def fetch_discharge_bill_estimate(hospital_name: str, admission_date: str) -> dict:
    return {
        "estimated_inr": 85000.0,
        "line_items": [
            {"description": "Room charges", "amount_inr": 30000.0},
            {"description": "Surgeon fee", "amount_inr": 25000.0},
            {"description": "Pharmacy", "amount_inr": 12000.0},
            {"description": "Lab reports", "amount_inr": 8000.0},
            {"description": "Miscellaneous", "amount_inr": 10000.0},
        ],
    }

def fetch_discharge_bills(case_id: str) -> dict:
    return {
        "total_inr": 85000.0,
        "pharmacy_inr": 12000.0,
        "lab_inr": 8000.0,
        "line_items": [
            {"description": "Room charges", "amount_inr": 30000.0},
            {"description": "Surgeon fee", "amount_inr": 25000.0},
            {"description": "Pharmacy", "amount_inr": 12000.0},
            {"description": "Lab reports", "amount_inr": 8000.0},
            {"description": "Miscellaneous", "amount_inr": 10000.0},
        ],
    }
