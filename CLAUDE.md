# Aldun Agent — Project Instructions

## Overview
3-agent system for hospital discharge automation.
**No orchestrator** — agents chain directly: Agent 1 spawns Agent 2 on success, Agent 2 spawns Agent 3.
State shared via SQLite (cases.db). All integrations mocked in v1.

## LLM Stack
OpenAI Python SDK (`openai>=1.30.0`) pointed at OpenRouter — no LiteLLM, no Groq.

| Agent | Model | base_url | Env var |
|---|---|---|---|
| Agent 1 (Onboarding) | `qwen/qwen3.5-flash-02-23` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Agent 2 (Discharge & Claims) | `qwen/qwen3.5-flash-02-23` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Agent 3 (Payment) | `qwen/qwen3.5-flash-02-23` | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |

## HITL Trigger Points (NOT implemented in v1 — implement before production)

The following 6 scenarios require a human to approve before the agent proceeds.
Each is currently a pass-through in the code. Search for `# HITL:` to find stubs.

1. **Onboarding / Borderline CIBIL** — CIBIL between 600–650
   - Action: pause, alert ops via WhatsApp/dashboard, wait for approval
2. **Onboarding / ID mismatch on KYC** — OCR name vs hospital record fuzzy match < 85%
   - Action: pause, show both names to ops, wait for manual override
3. **Claims / TPA rejection** — TPA returns status = 'rejected'
   - Action: alert ops, provide rejection reason, allow re-file with corrections
4. **Claims / Partial TPA approval** — TPA approves less than claimed amount
   - Action: alert ops with gap amount, ops decides coverage strategy
5. **Payment / Patient deductible unpaid after 7 days**
   - Action: escalate to collections ops team
6. **Payment / Short-payment — cannot close case**
   - Action: ops to manually close or write off balance

## Agent Architecture Decisions

### Tool definition format
All tools use **OpenAI-style format** — not Anthropic format. Every tool must be:
```python
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "...",
        "parameters": { "type": "object", "properties": {...}, "required": [...] }
    }
}
```
⚠️ Never use `input_schema` — that is the Anthropic SDK format and will silently fail with OpenRouter.

### Lazy client init
All agents use `_get_client()` pattern — client is created inside `run()`, not at module level.
This allows tests to import agents without `OPENROUTER_API_KEY` being set.

### Agent return format
All agents return a **dict**, not a bool:
```python
{"success": True/False, "trace": [...]}
```
The `trace` is a list of events consumed by the UI and integration tests.

### Trace event structure
Each event in `trace` is one of:
```python
{"type": "tool_call",   "name": "verify_aadhaar_otp", "args": {...}}
{"type": "tool_result", "name": "verify_aadhaar_otp", "result": {...}}
{"type": "summary",     "lines": ["✓ ...", "→ ..."]}
{"type": "error",       "message": "GUARDRAIL FAILED: ..."}
```

### Mock tool limitations (v1)
- `fetch_discharge_bill_estimate` — always returns ₹85,000 hardcoded regardless of hospital/date input
- `fetch_discharge_bills` — same hardcoded breakdown (Room ₹30k, Surgeon ₹25k, Pharmacy ₹12k, Lab ₹8k, Misc ₹10k)
- All tools ignore their inputs and return fixed responses — production must replace with real API calls

## Test UI
- **File:** `app.py` — Flask app
- **Port:** 5001 (`http://localhost:5001`)
- **Run:** `export $(cat .env | xargs) && python3 app.py`
- **What it does:** Form → calls Agent 1 → Agent 2 → shows full tool call I/O + case summary
- `.env` file holds `OPENROUTER_API_KEY` — never commit this file (covered by `.gitignore`)

## Git / Secrets
- `.env` — ignored by git (holds API keys)
- `*.db` — ignored by git (SQLite databases)
- `secrets.md` — ignored by git
- Never commit real Aadhaar numbers or patient data — test data only

## Data Rules (DPDP · UIDAI · RBI)
- Never store full Aadhaar number — last 4 digits only
- Strip PII from all event_log payloads before writing
- No PHI (diagnosis, procedures) in WhatsApp/email message bodies
- Audit log (event_log table) is immutable — no UPDATE or DELETE
