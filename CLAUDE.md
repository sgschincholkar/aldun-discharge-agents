# Aldun Agent — Project Instructions

## Overview
3-agent system for hospital discharge automation.
Agents chain directly: Onboarding → Discharge & Claims → Payment Collection.
State shared via SQLite (cases.db). All integrations mocked in v1.

## Model IDs
- Agent 1 (Onboarding): `openrouter/qwen/qwen3.5-flash-02-23`
- Agent 2 (Discharge & Claims): `openrouter/qwen/qwen3.5-flash-02-23`
- Agent 3 (Payment): `groq/llama-3.3-70b-versatile`

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

## Data Rules (DPDP · UIDAI · RBI)
- Never store full Aadhaar number — last 4 digits only
- Strip PII from all event_log payloads before writing
- No PHI (diagnosis, procedures) in WhatsApp/email message bodies
- Audit log (event_log table) is immutable — no UPDATE or DELETE
