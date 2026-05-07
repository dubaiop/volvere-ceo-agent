"""
CEO Agent — FastAPI web dashboard.
"""

import uuid
import threading
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from config import PORT, COMPANY_NAME, CEO_NAME
from agent import run_skill, chat, clear_memory
from skills.prompts import SKILL_MAP

app = FastAPI(title=f"{COMPANY_NAME} CEO Agent", version="1.0.0")
_sessions: dict[str, list] = {}
_jobs: dict[str, dict] = {}

SKILL_ICONS = {
    "daily-briefing": "sunrise", "decision-support": "git-branch",
    "meeting-prep": "calendar", "investor-comms": "trending-up",
    "deal-maker": "handshake", "problem-solver": "zap",
}


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "web"


class SkillRequest(BaseModel):
    skill: str
    input: str
    context: Optional[str] = ""
    session_id: Optional[str] = "web"


@app.get("/", response_class=HTMLResponse)
def dashboard():
    try:
        from hubspot import get_pipeline_summary, get_recent_contacts
        pipeline = get_pipeline_summary()
        contacts = get_recent_contacts(limit=5)
        pipeline_html = f"""
        <div class="metric-card"><div class="metric-value">{pipeline['total_deals']}</div><div class="metric-label">Open Deals</div></div>
        <div class="metric-card"><div class="metric-value">${pipeline['total_value']:,.0f}</div><div class="metric-label">Pipeline Value</div></div>"""
        contact_rows = "".join(
            f"<tr><td>{c['properties'].get('firstname','') or ''} {c['properties'].get('lastname','') or ''}</td>"
            f"<td class='muted'>{c['properties'].get('email','—')}</td>"
            f"<td class='muted'>{c['properties'].get('company','—')}</td></tr>"
            for c in contacts
        )
    except Exception:
        pipeline_html = "<div class='metric-card'><div class='metric-value'>—</div><div class='metric-label'>HubSpot offline</div></div>"
        contact_rows = "<tr><td colspan='3' class='muted' style='text-align:center'>Connect HubSpot to see contacts</td></tr>"

    skill_cards = ""
    for sk_id, sk in SKILL_MAP.items():
        icon = SKILL_ICONS.get(sk_id, "zap")
        skill_cards += f"""
        <div class="skill-card" onclick="selectSkill('{sk_id}')">
          <div class="skill-icon"><i data-lucide="{icon}"></i></div>
          <div><div class="skill-name">{sk['name']}</div><div class="skill-desc">{sk['description']}</div></div>
        </div>"""

    today = datetime.now().strftime("%A, %B %d")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{COMPANY_NAME} CEO Agent</title>
  <script src="https://unpkg.com/lucide@latest/dist/umd/lucide.min.js"></script>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    :root{{
      --bg:#080810;--surface:#0f0f1a;--surface2:#161625;--border:#1a1a2e;--border2:#252540;
      --accent:#7c3aed;--accent2:#a78bfa;--gold:#f59e0b;
      --text:#f0f0ff;--muted:#5a5a7a;--muted2:#8888aa;--radius:12px;
    }}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:14px;line-height:1.6}}
    header{{border-bottom:1px solid var(--border);padding:0 40px;height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;background:rgba(8,8,16,0.95);backdrop-filter:blur(16px);z-index:100}}
    .logo{{display:flex;align-items:center;gap:12px;font-weight:700;font-size:16px;color:var(--text);text-decoration:none}}
    .logo-dot{{width:10px;height:10px;border-radius:50%;background:var(--accent);box-shadow:0 0 12px var(--accent)}}
    .header-right{{display:flex;align-items:center;gap:20px;color:var(--muted2);font-size:13px}}
    .date-badge{{background:var(--surface2);border:1px solid var(--border2);padding:4px 12px;border-radius:20px;font-size:12px}}
    main{{max-width:1200px;margin:0 auto;padding:40px 40px 80px;display:grid;grid-template-columns:1fr 380px;gap:32px}}
    .left-col{{display:flex;flex-direction:column;gap:32px}}
    .right-col{{display:flex;flex-direction:column;gap:24px}}
    .hero{{padding:32px 0 24px}}
    .hero-badge{{display:inline-flex;align-items:center;gap:6px;background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.3);color:var(--accent2);padding:4px 14px;border-radius:20px;font-size:12px;font-weight:500;margin-bottom:16px}}
    .hero h1{{font-size:32px;font-weight:700;letter-spacing:-.5px;line-height:1.2;margin-bottom:8px}}
    .hero p{{color:var(--muted2);font-size:15px}}
    .metrics-row{{display:flex;gap:16px;flex-wrap:wrap}}
    .metric-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;flex:1;min-width:140px}}
    .metric-value{{font-size:28px;font-weight:700;color:var(--text)}}
    .metric-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-top:4px}}
    .section-title{{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.8px;color:var(--muted);margin-bottom:16px}}
    .skill-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .skill-card{{display:flex;align-items:flex-start;gap:12px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:14px;cursor:pointer;transition:border-color .15s,background .15s}}
    .skill-card:hover,.skill-card.active{{border-color:var(--accent);background:rgba(124,58,237,.06)}}
    .skill-icon{{width:32px;height:32px;border-radius:8px;background:rgba(124,58,237,.12);border:1px solid rgba(124,58,237,.2);display:flex;align-items:center;justify-content:center;flex-shrink:0;color:var(--accent2)}}
    .skill-icon svg{{width:15px;height:15px}}
    .skill-name{{font-weight:600;font-size:13px;color:var(--text)}}
    .skill-desc{{font-size:11px;color:var(--muted2);margin-top:2px;line-height:1.4}}
    .chat-panel{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);display:flex;flex-direction:column;height:600px;position:sticky;top:80px}}
    .chat-header{{padding:16px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px;background:var(--surface2);border-radius:var(--radius) var(--radius) 0 0}}
    .chat-header-text{{font-weight:600;font-size:14px}}
    .chat-header-sub{{font-size:11px;color:var(--muted2)}}
    .online-dot{{width:8px;height:8px;border-radius:50%;background:#22c55e;box-shadow:0 0 6px #22c55e;flex-shrink:0}}
    .chat-messages{{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px}}
    .msg{{max-width:90%;padding:10px 14px;border-radius:10px;font-size:13px;line-height:1.6;white-space:pre-wrap;word-break:break-word}}
    .msg.user{{background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.3);color:var(--text);align-self:flex-end;border-radius:10px 10px 2px 10px}}
    .msg.assistant{{background:var(--surface2);border:1px solid var(--border2);color:var(--text);align-self:flex-start;border-radius:10px 10px 10px 2px}}
    .msg.system{{color:var(--muted);font-size:12px;text-align:center;align-self:center;background:none;border:none;padding:4px}}
    .chat-input-area{{padding:12px;border-top:1px solid var(--border);display:flex;gap:8px}}
    .chat-input{{flex:1;background:var(--bg);border:1px solid var(--border2);border-radius:8px;color:var(--text);padding:10px 12px;font-size:13px;font-family:inherit;outline:none;resize:none;max-height:120px;transition:border-color .15s}}
    .chat-input:focus{{border-color:var(--accent)}}
    .send-btn{{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:10px 16px;font-size:13px;font-weight:600;cursor:pointer;transition:opacity .15s;flex-shrink:0}}
    .send-btn:hover{{opacity:.85}}
    .send-btn:disabled{{opacity:.4;cursor:not-allowed}}
    .skill-runner{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
    .runner-header{{padding:14px 20px;border-bottom:1px solid var(--border);background:var(--surface2);display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px}}
    .runner-body{{padding:20px;display:flex;flex-direction:column;gap:12px}}
    .runner-body label{{font-size:12px;color:var(--muted2);font-weight:500;display:block;margin-bottom:4px}}
    .runner-body select,.runner-body textarea,.runner-body input{{width:100%;background:var(--bg);border:1px solid var(--border2);border-radius:8px;color:var(--text);padding:10px 12px;font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}}
    .runner-body select:focus,.runner-body textarea:focus,.runner-body input:focus{{border-color:var(--accent)}}
    .runner-body textarea{{resize:vertical;min-height:80px}}
    .run-btn{{background:var(--accent);color:#fff;border:none;border-radius:8px;padding:10px 24px;font-size:13px;font-weight:700;cursor:pointer;transition:opacity .15s;width:100%}}
    .run-btn:hover{{opacity:.85}}
    .run-btn:disabled{{opacity:.4;cursor:not-allowed}}
    .result-box{{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:16px;font-size:13px;line-height:1.7;white-space:pre-wrap;color:var(--text);display:none;max-height:400px;overflow-y:auto}}
    .result-box.visible{{display:block}}
    .table-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
    table{{width:100%;border-collapse:collapse}}
    th{{text-align:left;padding:10px 16px;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);background:var(--surface2);border-bottom:1px solid var(--border)}}
    td{{padding:10px 16px;border-bottom:1px solid var(--border);font-size:13px}}
    tr:last-child td{{border-bottom:none}}
    .muted{{color:var(--muted2)}}
    .spinner{{display:inline-block;width:13px;height:13px;border:2px solid rgba(167,139,250,.3);border-top-color:var(--accent2);border-radius:50%;animation:spin .7s linear infinite;margin-right:6px;vertical-align:middle}}
    @keyframes spin{{to{{transform:rotate(360deg)}}}}
    @media(max-width:900px){{main{{grid-template-columns:1fr}}.right-col{{order:-1}}.chat-panel{{height:400px;position:static}}.skill-grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <a class="logo" href="/"><span class="logo-dot"></span>{COMPANY_NAME} CEO Agent</a>
  <div class="header-right">
    <span class="date-badge">{today}</span>
    <a href="/docs" style="color:var(--muted2);text-decoration:none;font-size:13px">API Docs</a>
  </div>
</header>
<main>
  <div class="left-col">
    <div class="hero">
      <div class="hero-badge"><i data-lucide="sparkles" style="width:12px;height:12px"></i> AI-Powered CEO Assistant</div>
      <h1>Good morning, {CEO_NAME}.</h1>
      <p>Your AI advisor for decisions, deals, strategy, and execution.</p>
    </div>

    <div>
      <div class="section-title">Pipeline</div>
      <div class="metrics-row">{pipeline_html}</div>
    </div>

    <div>
      <div class="section-title">Skills</div>
      <div class="skill-grid">{skill_cards}</div>
    </div>

    <div class="skill-runner" id="runner">
      <div class="runner-header"><i data-lucide="zap" style="width:15px;height:15px;color:var(--accent2)"></i> Run a Skill</div>
      <div class="runner-body">
        <div>
          <label>Skill</label>
          <select id="skillSelect">
            {"".join(f'<option value="{sk_id}">{SKILL_MAP[sk_id]["name"]}</option>' for sk_id in SKILL_MAP)}
          </select>
        </div>
        <div>
          <label>Context (optional)</label>
          <input type="text" id="contextInput" placeholder="Company stage, industry, goals..."/>
        </div>
        <div>
          <label>Input</label>
          <textarea id="skillInput" placeholder="Describe your situation, paste data, or ask your question..."></textarea>
        </div>
        <button class="run-btn" id="runBtn" onclick="runSkill()">Run Skill</button>
        <div class="result-box" id="resultBox"></div>
      </div>
    </div>

    <div>
      <div class="section-title">Recent Contacts</div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Name</th><th>Email</th><th>Company</th></tr></thead>
          <tbody>{contact_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="right-col">
    <div class="chat-panel" id="chatPanel">
      <div class="chat-header">
        <span class="online-dot"></span>
        <div>
          <div class="chat-header-text">CEO Assistant</div>
          <div class="chat-header-sub">Ask me anything</div>
        </div>
      </div>
      <div class="chat-messages" id="chatMessages">
        <div class="msg system">Ask me anything about your business, strategy, deals, or operations.</div>
      </div>
      <div class="chat-input-area">
        <textarea class="chat-input" id="chatInput" rows="1" placeholder="Message your CEO assistant..." onkeydown="handleKey(event)"></textarea>
        <button class="send-btn" id="sendBtn" onclick="sendMessage()"><i data-lucide="send" style="width:15px;height:15px"></i></button>
      </div>
    </div>
  </div>
</main>

<script>
lucide.createIcons();
const sessionId = 'web-' + Math.random().toString(36).slice(2,9);

function selectSkill(skillId) {{
  document.getElementById('skillSelect').value = skillId;
  document.querySelectorAll('.skill-card').forEach(c => c.classList.remove('active'));
  event.currentTarget.classList.add('active');
  document.getElementById('runner').scrollIntoView({{behavior:'smooth',block:'center'}});
}}

async function runSkill() {{
  const skill = document.getElementById('skillSelect').value;
  const input = document.getElementById('skillInput').value.trim();
  const context = document.getElementById('contextInput').value.trim();
  if (!input) {{ alert('Please enter your input.'); return; }}
  const btn = document.getElementById('runBtn');
  const box = document.getElementById('resultBox');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>Analyzing...';
  box.className = 'result-box visible'; box.textContent = 'Thinking...';
  try {{
    const resp = await fetch('/skill/sync', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{skill,input,context,session_id:sessionId}})}});
    const data = await resp.json();
    box.textContent = data.result || data.detail || 'No result.';
  }} catch(e) {{ box.textContent = 'Error: ' + e.message; }}
  btn.disabled = false; btn.innerHTML = 'Run Skill';
}}

function handleKey(e) {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
}}

function appendMsg(role, text) {{
  const div = document.createElement('div');
  div.className = 'msg ' + role;
  div.textContent = text;
  const msgs = document.getElementById('chatMessages');
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}}

async function sendMessage() {{
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  appendMsg('user', msg);
  const btn = document.getElementById('sendBtn');
  btn.disabled = true;
  const placeholder = appendMsg('assistant', '...');
  try {{
    const resp = await fetch('/chat', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:msg,session_id:sessionId}})}});
    const data = await resp.json();
    placeholder.textContent = data.reply || data.detail || 'No response.';
  }} catch(e) {{ placeholder.textContent = 'Error: ' + e.message; }}
  btn.disabled = false;
  document.getElementById('chatMessages').scrollTop = 99999;
}}
</script>
</body>
</html>"""


@app.post("/chat")
def chat_endpoint(req: ChatRequest):
    try:
        reply = chat(req.message, session_id=req.session_id or "web")
        return {"reply": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/skill/sync")
def run_skill_sync(req: SkillRequest):
    if req.skill not in SKILL_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown skill '{req.skill}'")
    try:
        result = run_skill(req.skill, req.input, req.context or "", session_id=req.session_id or "web")
        return {"skill": req.skill, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{session_id}")
def clear_chat(session_id: str):
    clear_memory(session_id)
    return {"status": "cleared"}


@app.get("/health")
def health():
    return {"status": "ok", "company": COMPANY_NAME}


def start_telegram():
    try:
        from telegram_bot import run_bot
        run_bot()
    except Exception as e:
        print(f"Telegram bot error: {e}")


if __name__ == "__main__":
    import uvicorn
    t = threading.Thread(target=start_telegram, daemon=True)
    t.start()
    uvicorn.run("web:app", host="0.0.0.0", port=PORT, reload=False)
