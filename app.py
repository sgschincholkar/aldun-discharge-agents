"""
Aldun Agent Test UI — Flask web app for testing Agent 1 & Agent 2 live.
Run: python3 app.py
Open: http://localhost:5000
"""
import json
import sys
import os
from flask import Flask, request, jsonify, render_template_string

# Add project root to path so agents can import db, guardrails, tools
sys.path.insert(0, os.path.dirname(__file__))

from db import init_db, create_case, get_case

app = Flask(__name__)
DB_PATH = "cases.db"

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Aldun Agent Test UI</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: #020617;
      color: #e2e8f0;
      font-family: 'SF Mono', 'Fira Code', monospace;
      font-size: 13px;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: #0f172a;
      border-bottom: 1px solid #1e293b;
      padding: 12px 24px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    header h1 { font-size: 14px; color: #38bdf8; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; }
    header .tag { background: #1e293b; color: #64748b; font-size: 10px; padding: 2px 8px; border-radius: 4px; }
    .main {
      display: flex;
      flex: 1;
      overflow: hidden;
    }

    /* LEFT PANEL */
    .left {
      width: 320px;
      min-width: 320px;
      background: #0f172a;
      border-right: 1px solid #1e293b;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .panel-title {
      color: #38bdf8;
      font-size: 10px;
      font-weight: bold;
      text-transform: uppercase;
      letter-spacing: 1px;
      margin-bottom: 4px;
    }
    .field { display: flex; flex-direction: column; gap: 4px; }
    .field label { color: #64748b; font-size: 10px; }
    .field input {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 4px;
      padding: 7px 10px;
      color: #e2e8f0;
      font-family: inherit;
      font-size: 12px;
      outline: none;
      transition: border-color 0.15s;
    }
    .field input:focus { border-color: #38bdf8; }
    .btn-run {
      background: #0ea5e9;
      color: white;
      border: none;
      border-radius: 6px;
      padding: 10px;
      font-size: 13px;
      font-weight: bold;
      font-family: inherit;
      cursor: pointer;
      margin-top: 4px;
      transition: background 0.15s;
    }
    .btn-run:hover { background: #0284c7; }
    .btn-run:disabled { background: #1e293b; color: #475569; cursor: not-allowed; }
    .btn-reset {
      background: transparent;
      color: #64748b;
      border: 1px solid #1e293b;
      border-radius: 6px;
      padding: 8px;
      font-size: 11px;
      font-family: inherit;
      cursor: pointer;
      transition: color 0.15s;
    }
    .btn-reset:hover { color: #e2e8f0; }

    /* RIGHT PANEL */
    .right {
      flex: 1;
      background: #020617;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .idle-msg {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: #1e293b;
      gap: 8px;
    }
    .idle-msg .icon { font-size: 40px; }
    .idle-msg p { font-size: 12px; color: #334155; }

    /* Agent blocks */
    .agent-block {
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 8px;
      overflow: hidden;
    }
    .agent-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: #1e293b;
      border-bottom: 1px solid #334155;
    }
    .agent-name { color: #94a3b8; font-size: 11px; font-weight: bold; }
    .status-badge {
      font-size: 10px;
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: bold;
    }
    .status-complete { background: #052e16; color: #4ade80; }
    .status-failed { background: #2d1515; color: #f87171; }
    .status-running { background: #1e293b; color: #fbbf24; }
    .agent-body { padding: 14px; display: flex; flex-direction: column; gap: 5px; }
    .line-ok { color: #4ade80; }
    .line-done { color: #e2e8f0; font-weight: bold; }
    .line-err { color: #f87171; }
    .line-warn { color: #fbbf24; }

    /* Summary grid */
    .summary {
      background: #0f172a;
      border: 1px solid #1e293b;
      border-radius: 8px;
      padding: 14px;
    }
    .summary-title { color: #64748b; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
    .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .summary-item { background: #1e293b; border-radius: 4px; padding: 8px 10px; }
    .summary-item .key { color: #64748b; font-size: 9px; margin-bottom: 2px; }
    .summary-item .val { color: #e2e8f0; font-size: 11px; }
    .val-green { color: #4ade80 !important; }
    .val-red { color: #f87171 !important; }

    /* Tool calls */
    .tool-call {
      color: #7dd3fc;
      font-size: 11px;
      padding: 4px 0 2px 0;
      border-top: 1px solid #1e293b;
      margin-top: 4px;
    }
    .tool-call:first-child { border-top: none; margin-top: 0; }
    .tool-name { color: #38bdf8; font-weight: bold; }
    .tool-args { color: #94a3b8; }
    .tool-result {
      color: #475569;
      font-size: 10px;
      padding: 2px 0 6px 12px;
      border-left: 2px solid #1e293b;
      margin-left: 8px;
      word-break: break-all;
      white-space: pre-wrap;
    }

    /* Spinner */
    .spinner {
      display: inline-block;
      width: 12px; height: 12px;
      border: 2px solid #334155;
      border-top-color: #38bdf8;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;
      margin-right: 6px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <header>
    <h1>🏥 Aldun Agent Test UI</h1>
    <span class="tag">Agent 1 → Agent 2</span>
    <span class="tag">qwen/qwen3.5-flash-02-23</span>
  </header>

  <div class="main">
    <!-- LEFT: Form -->
    <div class="left">
      <div class="panel-title">📋 Patient Details</div>

      <div class="field">
        <label>Patient Name</label>
        <input id="patient_name" type="text" value="Rajesh Kumar">
      </div>
      <div class="field">
        <label>Phone</label>
        <input id="patient_phone" type="text" value="9876543210">
      </div>
      <div class="field">
        <label>Aadhaar Last 4</label>
        <input id="aadhaar_last4" type="text" value="1234">
      </div>
      <div class="field">
        <label>Hospital Name</label>
        <input id="hospital_name" type="text" value="Fortis Hospital Bangalore">
      </div>
      <div class="field">
        <label>Admission Date</label>
        <input id="admission_date" type="text" value="2026-05-27">
      </div>
      <div class="field">
        <label>Estimated Bill (INR)</label>
        <input id="estimated_bill_inr" type="number" value="85000">
      </div>
      <div class="field">
        <label>Insurance Policy No.</label>
        <input id="insurance_policy_no" type="text" value="HDFC-HLTH-2024-789">
      </div>
      <div class="field">
        <label>TPA Name</label>
        <input id="tpa_name" type="text" value="Medi Assist">
      </div>

      <button class="btn-run" id="runBtn" onclick="runAgents()">▶ Run Agent 1 → Agent 2</button>
      <button class="btn-reset" onclick="resetUI()">↺ Reset</button>
    </div>

    <!-- RIGHT: Output -->
    <div class="right" id="output">
      <div class="idle-msg" id="idleMsg">
        <div class="icon">⚡</div>
        <p>Fill in patient details and click Run</p>
      </div>
    </div>
  </div>

  <script>
    async function runAgents() {
      const btn = document.getElementById('runBtn');
      const out = document.getElementById('output');

      const data = {
        patient_name: document.getElementById('patient_name').value,
        patient_phone: document.getElementById('patient_phone').value,
        aadhaar_last4: document.getElementById('aadhaar_last4').value,
        hospital_name: document.getElementById('hospital_name').value,
        admission_date: document.getElementById('admission_date').value,
        estimated_bill_inr: parseFloat(document.getElementById('estimated_bill_inr').value),
        insurance_policy_no: document.getElementById('insurance_policy_no').value,
        tpa_name: document.getElementById('tpa_name').value,
      };

      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Running...';

      out.innerHTML = `
        <div class="agent-block">
          <div class="agent-header">
            <span class="agent-name">Agent 1 — Onboarding</span>
            <span class="status-badge status-running"><span class="spinner"></span>running</span>
          </div>
          <div class="agent-body"><div class="line-warn">Calling LLM...</div></div>
        </div>
      `;

      try {
        const resp = await fetch('/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });
        const result = await resp.json();
        renderResult(result);
      } catch (e) {
        out.innerHTML = `<div class="agent-block"><div class="agent-body"><div class="line-err">✗ Server error: ${e.message}</div></div></div>`;
      }

      btn.disabled = false;
      btn.innerHTML = '▶ Run Agent 1 → Agent 2';
    }

    function renderResult(r) {
      const out = document.getElementById('output');
      let html = '';

      if (r.agent1) html += renderAgentBlock('Agent 1 — Onboarding', r.agent1);
      if (r.agent2) html += renderAgentBlock('Agent 2 — Discharge & Claims', r.agent2);

      if (r.case_summary) {
        const s = r.case_summary;
        html += `
          <div class="summary">
            <div class="summary-title">Case Summary</div>
            <div class="summary-grid">
              <div class="summary-item"><div class="key">Case ID</div><div class="val">${s.case_id ? s.case_id.substring(0,16)+'...' : '—'}</div></div>
              <div class="summary-item"><div class="key">TPA Claim ID</div><div class="val">${s.tpa_claim_id || '—'}</div></div>
              <div class="summary-item"><div class="key">Onboarding</div><div class="val ${s.onboarding_status === 'complete' ? 'val-green' : 'val-red'}">${s.onboarding_status || '—'}</div></div>
              <div class="summary-item"><div class="key">Claim Status</div><div class="val ${s.claim_status === 'filed' ? 'val-green' : 'val-red'}">${s.claim_status || '—'}</div></div>
              <div class="summary-item"><div class="key">KYC Verified</div><div class="val ${s.kyc_verified ? 'val-green' : 'val-red'}">${s.kyc_verified ? 'yes' : 'no'}</div></div>
              <div class="summary-item"><div class="key">Credit Approved</div><div class="val ${s.credit_approved ? 'val-green' : 'val-red'}">${s.credit_approved ? 'yes' : 'no'}</div></div>
            </div>
          </div>`;
      }

      out.innerHTML = html;
    }

    function renderAgentBlock(name, agent) {
      const status = agent.success ? 'complete' : 'failed';
      let rows = '';
      for (const event of agent.trace) {
        if (event.type === 'tool_call') {
          const argsStr = Object.entries(event.args).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(', ');
          rows += `<div class="tool-call">→ <span class="tool-name">${escHtml(event.name)}</span>(<span class="tool-args">${escHtml(argsStr)}</span>)</div>`;
        } else if (event.type === 'tool_result') {
          rows += `<div class="tool-result">${escHtml(JSON.stringify(event.result, null, 0))}</div>`;
        } else if (event.type === 'summary') {
          rows += event.lines.map(l => `<div class="${lineClass(l)}">${escHtml(l)}</div>`).join('');
        } else if (event.type === 'error') {
          rows += `<div class="line-err">✗ ${escHtml(event.message)}</div>`;
        }
      }
      return `
        <div class="agent-block">
          <div class="agent-header">
            <span class="agent-name">${name}</span>
            <span class="status-badge status-${status}">● ${status}</span>
          </div>
          <div class="agent-body">${rows}</div>
        </div>`;
    }

    function lineClass(line) {
      if (line.includes('✓')) return 'line-ok';
      if (line.includes('→')) return 'line-done';
      if (line.includes('✗') || line.includes('FAILED') || line.includes('ERROR')) return 'line-err';
      return 'line-done';
    }

    function escHtml(str) {
      return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
    }

    function resetUI() {
      document.getElementById('output').innerHTML = `
        <div class="idle-msg" id="idleMsg">
          <div class="icon">⚡</div>
          <p>Fill in patient details and click Run</p>
        </div>`;
    }
  </script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/run", methods=["POST"])
def run_agents():
    data = request.get_json()

    init_db(DB_PATH)
    case_id = create_case(data, db_path=DB_PATH)

    from agents.onboarding import run as run_onboarding
    a1 = run_onboarding(case_id, db_path=DB_PATH)

    result = {
        "case_id": case_id,
        "agent1": {"success": a1["success"], "trace": a1["trace"]},
        "agent2": None,
        "case_summary": None,
    }

    if a1["success"]:
        from agents.discharge_claims import run as run_discharge
        a2 = run_discharge(case_id, db_path=DB_PATH)
        result["agent2"] = {"success": a2["success"], "trace": a2["trace"]}

    case_row = get_case(case_id, db_path=DB_PATH)
    result["case_summary"] = {
        "case_id": case_id,
        "tpa_claim_id": case_row.get("tpa_claim_id"),
        "onboarding_status": case_row.get("onboarding_status"),
        "claim_status": case_row.get("claim_status"),
        "kyc_verified": case_row.get("kyc_verified"),
        "credit_approved": case_row.get("credit_approved"),
    }

    return jsonify(result)


if __name__ == "__main__":
    init_db(DB_PATH)
    print("\n🏥 Aldun Agent Test UI")
    print("   Open: http://localhost:5000")
    print("   Set OPENROUTER_API_KEY before running\n")
    app.run(debug=False, port=5001)
