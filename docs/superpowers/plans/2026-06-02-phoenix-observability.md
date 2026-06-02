# Phoenix Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Arize Phoenix cloud tracing to all 3 agents so every LLM call, tool call, and error is visible in the Phoenix UI at app.phoenix.arize.com.

**Architecture:** A single `observability.py` module initialises an OpenTelemetry tracer provider pointed at the Arize Phoenix cloud OTLP endpoint, then calls `OpenAIInstrumentor().instrument()` which monkey-patches the OpenAI SDK. From that point forward, every `chat.completions.create()` call across all 3 agents is automatically captured — no changes to agent code required. `app.py` calls `init_tracing()` once at startup before any agent import.

**Tech Stack:** `arize-phoenix-otel`, `openinference-instrumentation-openai`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `observability.py` | **Create** | OTel setup + `OpenAIInstrumentor` init |
| `app.py` | **Modify** | Call `init_tracing()` at startup |
| `.env` | **Modify** | Add `PHOENIX_API_KEY` and `PHOENIX_COLLECTOR_ENDPOINT` |
| `requirements.txt` | **Modify** | Add 4 new packages |
| `tests/test_observability.py` | **Create** | Verify tracing initialises without error |

---

## Task 1: Install packages

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add the 4 new packages to requirements.txt**

Open `requirements.txt` and replace its contents with:

```
openai>=1.30.0
flask>=3.0.0
pytest>=8.0.0
arize-phoenix-otel>=0.6.0
openinference-instrumentation-openai>=0.1.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-otlp-proto-http>=1.20.0
```

- [ ] **Step 2: Install the new packages**

```bash
pip install arize-phoenix-otel openinference-instrumentation-openai "opentelemetry-sdk>=1.20.0" "opentelemetry-exporter-otlp-proto-http>=1.20.0"
```

Expected: packages install without error. Verify with:

```bash
python -c "from openinference.instrumentation.openai import OpenAIInstrumentor; print('OK')"
```

Expected output: `OK`

- [ ] **Step 3: Commit**

```bash
cd /path/to/aldun-discharge-agents
git add requirements.txt
git commit -m "chore: add Phoenix observability dependencies"
```

---

## Task 2: Add env vars for Phoenix cloud

**Files:**
- Modify: `.env`

- [ ] **Step 1: Get your Phoenix API key**

1. Go to [app.phoenix.arize.com](https://app.phoenix.arize.com)
2. Sign in / create a free account
3. Navigate to **Settings → API Keys** and create a new key
4. Copy the key — you will need it in the next step

- [ ] **Step 2: Add vars to .env**

Open `.env` and add these two lines (keep your existing `OPENROUTER_API_KEY`):

```
PHOENIX_API_KEY=your-api-key-here
PHOENIX_COLLECTOR_ENDPOINT=https://app.phoenix.arize.com/v1/traces
```

Replace `your-api-key-here` with the key you copied in Step 1.

- [ ] **Step 3: Verify .env is gitignored**

```bash
grep "\.env" .gitignore
```

Expected output should include `.env` or `*.env`. The API key must never be committed.

---

## Task 3: Create observability.py

**Files:**
- Create: `observability.py`

- [ ] **Step 1: Write the failing test first**

Create `tests/test_observability.py`:

```python
import os
import pytest

def test_init_tracing_runs_without_error(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    # Import fresh — monkeypatch must be set before import resolves env vars
    import importlib
    import observability
    importlib.reload(observability)
    # Should not raise
    observability.init_tracing()

def test_init_tracing_missing_api_key(monkeypatch):
    monkeypatch.delenv("PHOENIX_API_KEY", raising=False)
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="PHOENIX_API_KEY"):
        observability.init_tracing()

def test_init_tracing_missing_endpoint(monkeypatch):
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    import importlib
    import observability
    importlib.reload(observability)
    with pytest.raises(EnvironmentError, match="PHOENIX_COLLECTOR_ENDPOINT"):
        observability.init_tracing()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd /path/to/aldun-discharge-agents
pytest tests/test_observability.py -v
```

Expected: `ModuleNotFoundError: No module named 'observability'` (file doesn't exist yet — that's correct)

- [ ] **Step 3: Create observability.py**

```python
import os
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

_instrumented = False


def init_tracing():
    """Initialise Phoenix cloud tracing. Call once at app startup."""
    global _instrumented

    api_key = os.environ.get("PHOENIX_API_KEY")
    if not api_key:
        raise EnvironmentError("PHOENIX_API_KEY is not set. Add it to your .env file.")

    endpoint = os.environ.get("PHOENIX_COLLECTOR_ENDPOINT")
    if not endpoint:
        raise EnvironmentError("PHOENIX_COLLECTOR_ENDPOINT is not set. Add it to your .env file.")

    tracer_provider = trace_sdk.TracerProvider()
    tracer_provider.add_span_processor(
        SimpleSpanProcessor(
            OTLPSpanExporter(
                endpoint=endpoint,
                headers={"api_key": api_key},
            )
        )
    )

    if not _instrumented:
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
        _instrumented = True
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
pytest tests/test_observability.py -v
```

Expected output:
```
tests/test_observability.py::test_init_tracing_runs_without_error PASSED
tests/test_observability.py::test_init_tracing_missing_api_key PASSED
tests/test_observability.py::test_init_tracing_missing_endpoint PASSED
3 passed
```

- [ ] **Step 5: Commit**

```bash
git add observability.py tests/test_observability.py
git commit -m "feat: add Phoenix observability module with OTel + OpenAI auto-instrumentation"
```

---

## Task 4: Wire init_tracing() into app.py

**Files:**
- Modify: `app.py` (top of file, before agent imports)

The `run_agents` route in `app.py` imports agents lazily (inside the function). `init_tracing()` must be called **before** the OpenAI client is created — i.e. at module load time, not inside the route handler. We call it right after the Flask `app` is created.

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_observability.py`:

```python
def test_app_calls_init_tracing(monkeypatch):
    """app.py must call init_tracing() at module load, not inside a route."""
    calls = []
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006/v1/traces")

    import importlib
    import observability
    importlib.reload(observability)

    original_init = observability.init_tracing
    def recording_init():
        calls.append(1)
        # don't actually instrument in tests
    monkeypatch.setattr(observability, "init_tracing", recording_init)

    import app as app_module
    importlib.reload(app_module)

    assert len(calls) >= 1, "init_tracing() was never called during app.py load"
```

- [ ] **Step 2: Run to verify it fails**

```bash
pytest tests/test_observability.py::test_app_calls_init_tracing -v
```

Expected: `AssertionError: init_tracing() was never called during app.py load`

- [ ] **Step 3: Modify app.py to call init_tracing() at startup**

Open `app.py`. Find this block near the top (around line 13):

```python
from db import init_db, create_case, get_case

app = Flask(__name__)
DB_PATH = "cases.db"
```

Replace it with:

```python
from db import init_db, create_case, get_case
from observability import init_tracing

app = Flask(__name__)
DB_PATH = "cases.db"

init_tracing()
```

- [ ] **Step 4: Run all tests to verify nothing broke**

```bash
pytest tests/ -v
```

Expected: all tests pass, including the new `test_app_calls_init_tracing`.

Note: the `init_tracing()` call will raise `EnvironmentError` if `PHOENIX_API_KEY` is not set. When running tests, `monkeypatch` handles this. When running the app for real, ensure `.env` is loaded first:

```bash
export $(cat .env | xargs) && python3 app.py
```

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_observability.py
git commit -m "feat: wire Phoenix init_tracing() into app startup"
```

---

## Task 5: Verify traces appear in Phoenix UI

This task is manual — no code changes.

- [ ] **Step 1: Start the app with env vars loaded**

```bash
cd /path/to/aldun-discharge-agents
export $(cat .env | xargs) && python3 app.py
```

Expected: app starts on `http://localhost:5001` with no errors.

- [ ] **Step 2: Run a test case through the Flask UI**

Open `http://localhost:5001` in your browser. Fill in the form and submit a case. The pipeline (Agent 1 → Agent 2 → Agent 3) will run.

- [ ] **Step 3: Check Phoenix**

Go to [app.phoenix.arize.com](https://app.phoenix.arize.com) → **Traces**.

You should see:
- One trace per LLM call (3 agents = 3+ traces)
- Each trace shows: model name (`qwen/qwen3.5-flash-02-23`), input messages, output, token counts, latency
- Tool calls appear as child spans under the LLM span (e.g. `verify_aadhaar_otp`, `check_credit_score_nbfc`, etc.)
- Any guardrail failures show as ERROR spans

If traces don't appear within 30 seconds, check:
```bash
# Verify env vars are set
echo $PHOENIX_API_KEY
echo $PHOENIX_COLLECTOR_ENDPOINT

# Check for errors in the app console output
```

- [ ] **Step 4: Commit the docs/superpowers/plans file and push everything**

```bash
git add docs/superpowers/plans/2026-06-02-phoenix-observability.md
git commit -m "docs: add Phoenix observability implementation plan"
git push
```

---

## Self-Review Notes

- **Spec coverage:** All 4 design points covered — `observability.py`, `app.py` wiring, `.env` vars, `requirements.txt` packages.
- **No placeholders:** All steps have exact code, exact commands, exact expected output.
- **Type consistency:** `init_tracing()` is defined in Task 3 and called in Task 4 — names match.
- **`_instrumented` guard:** Prevents double-instrumentation if `init_tracing()` is called more than once (e.g. test reloads).
- **Agent code:** Zero changes to `onboarding.py`, `discharge_claims.py`, `payment_collection.py` — auto-instrumentation handles everything.
