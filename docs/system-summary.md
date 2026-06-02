# Aldun Discharge Agents — Stakeholder Summary

---

## 1. System Overview

A 3-agent LLM-powered system that automates the hospital discharge pipeline:
**Onboarding → Discharge & Claims → Payment Collection**

Agents chain directly with no orchestrator. Each agent completes its task, writes results to a shared SQLite database, and triggers the next agent. All external integrations are mocked in v1.

**Tech Stack:** Python 3.11+, OpenAI SDK (pointed at OpenRouter for all 3 agents), SQLite, pytest

---

## 2. Agent Architecture

| Agent | Model | Provider | Env var | Responsibility |
|---|---|---|---|---|
| Agent 1 — Onboarding | `qwen/qwen3.5-flash-02-23` | OpenRouter | `OPENROUTER_API_KEY` | KYC verification, CIBIL credit check, payment consent |
| Agent 2 — Discharge & Claims | `qwen/qwen3.5-flash-02-23` | OpenRouter | `OPENROUTER_API_KEY` | EHR + bill fetch, claim assembly, TPA filing |
| Agent 3 — Payment Collection | `qwen/qwen3.5-flash-02-23` | OpenRouter | `OPENROUTER_API_KEY` | TPA payment verification, deductible collection, case closure |

**Model rationale:**
- Qwen3.5-Flash for Agents 1 & 2 — 1M context, confirmed tool calling, strong multilingual reasoning for KYC and claim assembly
- Qwen3.5-Flash for Agent 3 — same model as Agents 1 & 2, single API key, consistent tool calling for structured payment reconciliation

---

## 3. Tool Calls per Agent

### Agent 1 — Onboarding
1. `verify_aadhaar_otp` — verifies patient identity via OTP
2. `check_credit_score_nbfc` — fetches CIBIL score
3. `fetch_discharge_bill_estimate` — gets estimated bill from hospital
4. `capture_payment_consent` — records patient consent
5. `get_credit_approval_nbfc` — requests NBFC credit approval
6. `store_kyc_info` — stores masked KYC data

### Agent 2 — Discharge & Claims
1. `fetch_kyc_docs` — retrieves Aadhaar and policy PDFs
2. `fetch_ehr_data` — fetches diagnosis, procedures, discharge info
3. `fetch_discharge_bills` — fetches itemized hospital bill
4. `file_claim_to_tpa` — files assembled claim packet to TPA
5. `send_wa_email_notification` — notifies patient via WhatsApp

### Agent 3 — Payment Collection
1. `verify_tpa_payment_received` — confirms TPA has transferred funds
2. `confirm_patient_deductible_paid` — confirms patient co-pay
3. `update_payment_in_aldun_db` — records payment amounts
4. `send_wa_email_notification` — notifies patient of case closure
5. `close_case` — closes the case after reconciliation

---

## 4. KYC Verification Flow

1. **Aadhaar OTP** — patient identity verified via OTP against last 4 digits
2. **OCR Confidence Guardrail** — confidence must be ≥ 0.92, else blocked
3. **Store KYC** — Aadhaar masked to last 4 digits before storage (UIDAI compliance)
4. **Audit log** — PII stripped before writing to event log (DPDP compliance)

**Production gaps in v1:**
- OTP hardcoded as `"000000"` — real UIDAI OTP flow not implemented
- Name cross-check guardrail (`cross_check_aadhaar_name`) exists but not called
- No real UIDAI API integration

---

## 5. Credit Check Flow

1. **Fetch CIBIL score** via NBFC using patient phone number
2. **Fetch bill estimate** to determine credit amount needed
3. **Guardrail check** — CIBIL < 650 blocks approval; 600–650 is a HITL trigger (stub in v1)
4. **NBFC credit approval** for bill amount
5. Results written to SQLite: `credit_approved=1`, `credit_limit_inr`

---

## 6. Document Flow (fetch_kyc_docs)

`fetch_kyc_docs` returns document references → Claude assembles all fetched data (KYC docs + EHR + bills) into a `claim_packet` → passed to `file_claim_to_tpa`.

**Production gap:** v1 returns only filenames (`"aadhaar.pdf"`), not actual content. Production requires real document bytes or pre-signed URLs for TPA to access.

---

## 7. Memory Architecture

| Layer | Type | Contents |
|---|---|---|
| In-context | Ephemeral, per agent | Tool call/result history within one agent run |
| SQLite `cases` table | Shared, persistent | All case fields — read/written by all 3 agents |
| `_temp_` cache | Ephemeral, in-memory | CIBIL score, TPA/patient amounts within a single run |
| `event_log` table | Immutable, append-only | Audit trail — PII stripped before write |

**Inter-agent handoff via SQLite:**
```
Agent 1 writes → kyc_verified, credit_approved, onboarding_status
Agent 2 reads  → validates pre-conditions, writes tpa_claim_id, claim_status
Agent 3 reads  → validates tpa_claim_id, writes case_status=closed
```

---

## 8. Impact of Adding Simulated PDFs

Introducing real PDFs (Aadhaar, PAN, policy, discharge summary, hospital bill) requires:

1. **Document store** — `{case_id}/` folder structure on disk (S3 in production)
2. **PDF extraction layer** — new `tools/doc_processor.py` using Claude's vision to extract structured fields from PDFs
3. **Extraction cache** — results cached in SQLite to avoid re-running OCR
4. **Richer claim packet** — extracted fields from all documents assembled into IRDAI-compliant structure
5. **New guardrails** — PAN vs Aadhaar name cross-check, policy coverage vs bill amount, extraction confidence threshold

**Key constraint:** Raw PDFs must never appear in `event_log` or Claude's tool results — only extracted structured fields pass through (PHI and PII compliance).

---

## 9. Where RAG is Needed

RAG is **not needed** in the core pipeline (structured tool-call sequences). It adds value in 3 specific places:

| Use Case | What RAG Queries |
|---|---|
| TPA Policy Rules | Per-TPA mandatory fields, coverage exclusions, document requirements |
| Rejection Resolution | Historical rejection patterns → what to fix before re-filing |
| ICD-10 Code Lookup | Free-text diagnosis → standardised ICD-10/procedure codes |

All three are in **Agent 2** only. Agents 1 and 3 work entirely with structured data.

**Recommended stack:** ChromaDB (local/v2) → Pinecone (production), `bge-m3` embeddings (handles Hindi/English mixed text)

---

## 10. Model Swap Guide

The system uses the OpenAI SDK with a configurable `base_url` — swapping models is a 2-line change per agent (`model` string + `base_url`). Current stack already uses open-weight models:

| Agent | Current Model | Alternative |
|---|---|---|
| Agent 1 & 2 | `qwen/qwen3.5-flash-02-23` via OpenRouter | Any OpenRouter model with tool calling |
| Agent 3 | `qwen/qwen3.5-flash-02-23` via OpenRouter | Any OpenRouter model with tool calling |

**Key risk:** Tool-use reliability varies by model. Always test with the full tool sequence before swapping. Smaller models may skip steps or hallucinate tool names.

---

## 11. Production Data Requirements

### Core Patient Data
- Aadhaar last 4 + OTP, PAN, insurance policy number
- ABHA number (ABDM Health ID)
- CIBIL score, credit bureau report

### Medical Data
- ICD-10 primary/secondary diagnosis codes
- Procedure codes (ICD-10-PCS)
- Treating doctor NMC registration ID
- Hospital ROHINI ID
- Pre-authorisation number from TPA

### Financial Data
- Itemized hospital bills with GST/HSN codes
- TPA-approved amounts, coverage limits, exclusions
- UPI transaction IDs, NPCI reference numbers

### Historical Data (missing in v1 — critical for production)
- Past cases per patient (fraud detection)
- TPA rejection history by hospital (predict claim success)
- Agent success/failure rates (model evaluation)

---

## 12. Regulatory Framework

### Tier 1 — Cannot Ship Without
| Regulation | Governs |
|---|---|
| UIDAI Aadhaar Authentication API Spec | OTP flow, storage rules, error codes |
| DPDP Act 2023 + Rules 2025 | Consent, data minimisation, retention, breach notification |
| IRDAI Cashless Hospitalisation Guidelines 2024 | Claim packet mandatory fields, filing timelines |

### Tier 2 — Needed Before First Real Patient
| Regulation | Governs |
|---|---|
| RBI Digital Lending Guidelines 2022 | Credit check consent, NBFC digital norms |
| ABDM Health Data Management Policy 2022 | EHR access via HIE, PHI definition |
| TRAI TCCCPR 2018 + DLT Registration | WhatsApp/SMS template compliance |

### Tier 3 — Needed for Scale
- RBI KYC Master Direction 2016 — periodic KYC refresh, CKYC registry
- IRDAI TPA Regulations 2016 — settlement SLA (30 days), rejection escalation
- IT Act 2000 + SPDI Rules 2011 — minimum security standards, audit log retention

---

## 13. Publicly Available Data for Simulated System

### Schemas & Specifications
| Resource | Source | Use |
|---|---|---|
| NHCX Claim Spec | nhcx.pmjay.gov.in | Standard claim packet format |
| ABDM FHIR R4 India Profile | nrces.in | EHR data structure |
| UIDAI Aadhaar XML Schema | uidai.gov.in | KYC simulation |
| ICD-10 Code List | who.int | Diagnosis/procedure codes |
| RBI Key Fact Statement Template | rbi.org.in | Credit approval format |
| NPCI UPI Technical Spec | npci.org.in | Payment confirmation format |
| TRAI TCCCPR 2018 | trai.gov.in | Notification template structure |
| DPDP Act 2023 | meity.gov.in | Consent artifact format |

### Synthetic Patient Data
| Dataset | Source | Use |
|---|---|---|
| Synthea Synthetic EHR | synthea.mitre.org | Realistic patient records |
| Indian Name Dataset | github.com/datasets | Realistic Indian names |
| Indian Pincode Database | data.gov.in | Address simulation |
| Hospital Directory | NHA/ABDM public data | Real hospital names, ROHINI IDs |

### Simulated PDFs to Generate
| Document | Based On |
|---|---|
| Aadhaar | UIDAI XML schema |
| PAN Card | Income Tax Dept format |
| Insurance Policy | IRDAI standard policy wordings |
| Discharge Summary | ABDM FHIR R4 profile |
| Hospital Bill | Standard GST invoice + HSN codes |
| NBFC Loan Agreement | RBI KFS template |

---

## 14. 6 HITL Trigger Points (Stubs in v1)

Search for `# HITL:` in codebase to find all stubs. Must be implemented before production.

| Trigger | Action Required |
|---|---|
| CIBIL score 600–650 | Pause, alert ops, await manual approval |
| KYC name mismatch < 85% | Show both names to ops, await override |
| TPA claim rejected | Alert ops with rejection reason, allow re-file |
| TPA partial approval | Alert ops with gap amount, decide coverage strategy |
| Patient deductible unpaid after 7 days | Escalate to collections team |
| Short-payment on case closure | Ops to manually close or write off balance |

---

## 15. Recommended Build Sequence for Production-Ready Simulation

```
Week 1:  Download ICD-10, NHCX spec, UIDAI XML schema, Synthea dataset
         → Rebuild mock tools with realistic structured responses

Week 2:  Generate simulated PDFs (Aadhaar, PAN, policy, bill, discharge summary)
         → Add PDF extraction layer, update memory architecture

Week 3:  Ingest IRDAI, RBI, DPDP documents into RAG (ChromaDB)
         → Update guardrail thresholds with regulation-cited constants
         → Build NHCX-compliant claim packet validator

Week 4:  Implement HITL stubs with proper ops notification hooks
         → Add data retention policies to db.py
         → Swap models as needed (change model + base_url per agent)
```

---

*This document covers architecture, data flows, regulatory requirements, and build roadmap for the Aldun Discharge Agents system. All integrations are mocked in v1 for learning purposes.*
