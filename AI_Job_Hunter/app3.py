# app.py — AI Job Hunter (Glassmorphic UI + Salary Prediction)
import os
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path
import re

import streamlit as st

# Local modules
from scraper import fetch_jobs, load_cache_or_demo
from resume_parser import extract_resume_features
from ai_assistant import (
    analyze_job_fit,
    enhance_resume,
    generate_interview_questions,
    call_ollama,
)

# Salary predictor (optional but recommended)
try:
    from tech_salary_predictor import predict_salary, train_salary_model
    _HAS_SALARY_MODEL = True
except Exception:
    _HAS_SALARY_MODEL = False

# ----------------- Page Config -----------------
st.set_page_config(page_title="AI Job Hunter", layout="wide", page_icon="🤖")

# ----------------- Glassmorphic Theme -----------------
st.markdown("""
<style>
:root{
  --bg:#1E1F22;
  --card:#2A2B32C0; /* translucent */
  --card-solid:#2A2B32;
  --text:#ECECEC;
  --muted:#C9CDD2;
  --accent:#10A37F; /* ChatGPT green */
  --border:#3A3B42;
  --shadow:0 8px 24px rgba(0,0,0,0.25);
}

/* App base */
body, .stApp { background: radial-gradient(1200px 800px at 20% -10%, #23262b 0%, var(--bg) 40%), var(--bg); color: var(--text) !important; font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji","Segoe UI Emoji"; }

/* Top header bar */
.header-bar {
  display:flex; align-items:center; justify-content:space-between;
  padding: 12px 16px; margin-bottom: 12px;
  background: linear-gradient(135deg, #262830AA, #1f2227AA);
  border: 1px solid var(--border);
  border-radius: 14px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}

/* Upload box (glass) */
.upload-glass {
  width: 100%;
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 22px 18px;
  color: var(--text);
  background: linear-gradient(135deg, #2a2b32aa, #1f2227aa);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow);
}

/* Buttons */
.stButton>button {
  background: #262730;
  color: var(--text);
  border: 1px solid var(--accent);
  border-radius: 10px;
  transition: all .18s ease;
  font-weight: 600;
}
.stButton>button:hover{
  background: var(--accent) !important; color: white !important;
}

/* Popover trigger icon */
.pop-gear {
  display:inline-flex; align-items:center; justify-content:center;
  width:40px; height:40px; border-radius:10px;
  border:1px solid var(--border);
  background: #262730aa; cursor:pointer; user-select:none;
  transition: all .18s ease;
}
.pop-gear:hover{ border-color: var(--accent); color: var(--accent); }

/* Chat title & helper */
.section-title { margin: 6px 0 2px 2px; font-size: 0.95rem; color: var(--muted); }

/* Job card (glass) */
.job-card {
  width: 100%;
  border-radius: 16px;
  border: 1px solid var(--border);
  padding: 16px 16px 12px 16px;
  color: var(--text);
  background: linear-gradient(135deg, #2a2b32cc, #1f2227cc);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: var(--shadow);
}
.job-title { font-weight:800; font-size: 1.05rem; letter-spacing: .2px; }
.job-meta { color: var(--muted); font-size: .92rem; }
.job-desc { color: var(--text); opacity: .95; line-height: 1.55; }
.badge {
  display:inline-flex; align-items:center; gap:.4rem; padding:.25rem .55rem;
  border-radius:999px; border:1px solid var(--border); font-size:.82rem;
  background:#262730aa;
}
.badge.salary { border-color: var(--accent); color: var(--accent); background:#1b463b99; }

/* AI response card */
.ai-response {
  border-left: 4px solid var(--accent);
  background: #1f2227;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  color: var(--text);
  box-shadow: var(--shadow);
}

/* Expander restyle (subtle) */
.streamlit-expanderHeader{ font-weight:700!important; }

/* Fix form labels in dark */
label, .stTextInput label, .stSelectbox label { color: var(--muted) !important; }

/* Links */
a, .stMarkdown a { color: var(--accent) !important; text-decoration:none; }
a:hover { text-decoration:underline; }
</style>
""", unsafe_allow_html=True)

# ----------------- Header -----------------
st.markdown("""
<div class="header-bar">
  <div style="display:flex;align-items:center;gap:.6rem;">
    <span style="font-size:1.25rem;">🤖</span>
    <div>
      <div style="font-weight:800;letter-spacing:.3px;">AI Job Hunter — 360° Career Agent</div>
      <div style="font-size:.88rem;color:#C9CDD2;">Glass-style UI • Resume-aware search • Local LLM fit analysis</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:.5rem;">
      <!-- reserved for future toggles -->
  </div>
</div>
""", unsafe_allow_html=True)

# ----------------- Salary model (load once) -----------------
if _HAS_SALARY_MODEL:
    try:
        with st.spinner("⚙️ Loading Salary Prediction Model…"):
            _ = train_salary_model(force_retrain=False)
    except Exception as e:
        st.warning(f"Salary model not loaded: {e}")

# ----------------- Data Path & cache meta -----------------
DATA_PATH = Path("data") / "scraped_jobs.json"

def _cache_meta():
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
        ts = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return len(arr), ts
    return 0, "N/A"

# ----------------- Upload + Filters + Search -----------------
with st.container():
    # Upload (glass)
    st.markdown('<div class="upload-glass">📄 <b>Upload your resume (PDF or TXT)</b></div>', unsafe_allow_html=True)
    resume_file = st.file_uploader("", type=["pdf", "txt"], label_visibility="collapsed")

    resume_text = st.session_state.get("resume_text", "")
    if resume_file:
        try:
            data = resume_file.read()
            if resume_file.type == "application/pdf":
                import PyPDF2
                reader = PyPDF2.PdfReader(BytesIO(data))
                resume_text = "\n".join([p.extract_text() or "" for p in reader.pages]).strip()
            else:
                resume_text = data.decode("utf-8", errors="replace")
            st.session_state["resume_text"] = resume_text
            st.success("✅ Resume uploaded successfully.")
        except Exception as e:
            st.error(f"Resume read error: {e}")

    if resume_text:
        with st.expander("📊 Resume Insights", expanded=False):
            feats = extract_resume_features(resume_text)
            st.write(f"**Skills ({len(feats['skills'])})**: {', '.join(feats['skills']) or '—'}")
            st.write(f"**Experience (yrs)**: {feats['experience']}")

    # Filters popover trigger
    cols = st.columns([0.08, 0.92])
    with cols[0]:
        with st.popover("⚙️", use_container_width=True):
            st.subheader("Job Filters")
            location = st.text_input("📍 Location", value=st.session_state.get("location", ""))
            remote = st.checkbox("🏠 Remote Only", value=st.session_state.get("remote", False))
            date_posted = st.selectbox("🗓 Posted Since", ["day", "week", "month"], index=1)
            st.session_state.update({"location": location, "remote": remote, "date_posted": date_posted})
    with cols[1]:
        st.markdown('<div class="section-title">Describe your ideal role (ChatGPT-like)</div>', unsafe_allow_html=True)
        user_prompt = st.chat_input("e.g., Senior Data Scientist in Bangalore, remote preferred, Python + ML")
        search_clicked = st.button("🔍 Search Jobs", use_container_width=True)

# ----------------- Search logic -----------------
jobs = st.session_state.get("jobs", [])

if user_prompt or search_clicked:
    # Parse natural language into filters via local LLM
    if user_prompt:
        with st.spinner("🧠 Understanding your search (Llama 3.2)…"):
            try:
                parsed = call_ollama(
                    "Extract job search filters from this user query and return JSON with keys: "
                    "job_role, location, remote (true/false).\n\n"
                    f"QUERY: {user_prompt}"
                )
                match = re.search(r"\{.*\}", str(parsed), re.DOTALL)
                if match:
                    parsed_json = json.loads(match.group(0))
                    job_role = parsed_json.get("job_role", "").strip()
                    loc = parsed_json.get("location", "").strip()
                    rem = bool(parsed_json.get("remote", False))
                else:
                    job_role, loc, rem = user_prompt, st.session_state.get("location", ""), st.session_state.get("remote", False)
                if job_role:
                    st.session_state["job_role"] = job_role
                if loc:
                    st.session_state["location"] = loc
                st.session_state["remote"] = rem
                st.success(f"✅ Searching: {st.session_state.get('job_role','jobs')} in {st.session_state.get('location','Anywhere')} (Remote={rem})")
            except Exception as e:
                st.warning(f"Parser fallback: {e}")
                st.session_state["job_role"] = user_prompt

    role = st.session_state.get("job_role", "")
    if not role:
        st.warning("Please describe a job role or skill.")
    else:
        with st.spinner("🔎 Fetching job listings…"):
            try:
                jobs = fetch_jobs(
                    role,
                    location=st.session_state.get("location", ""),
                    remote=st.session_state.get("remote", False),
                    date_posted=st.session_state.get("date_posted", "week"),
                    limit=12,
                )
                if not jobs:
                    st.warning("No live jobs found — showing cached/demo.")
                    jobs = load_cache_or_demo()
            except Exception as e:
                st.error(f"Fetch error: {e}")
                jobs = load_cache_or_demo()
        st.session_state["jobs"] = jobs

# ----------------- Results header -----------------
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("📋 Job Recommendations")
total_cached, last_updated = _cache_meta()
st.caption(f"Cache: {total_cached} jobs • Last updated: {last_updated}")

# ----------------- Helpers -----------------
def _format_salary(title, company, location, desc, raw_salary):
    """Return HTML-ready salary line (uses model if needed)."""
    # If explicit salary present and not blank-like, show listed
    if raw_salary and str(raw_salary).strip().lower() not in ["n/a", "-", "none", ""]:
        return f"<span class='badge'>💰 Listed: {raw_salary}</span>"

    # Try predict if model available
    if not _HAS_SALARY_MODEL:
        return "<span class='badge'>💰 Salary: Not Available</span>"

    try:
        job_skills = extract_resume_features(desc or "").get("skills", [])
        pred = predict_salary(
            job_title=title or "",
            company=company or "",
            location=location or "",
            experience_level="Mid",
            employment_type="Full-Time",
            skills=", ".join(job_skills),
        )
        if pred and isinstance(pred, (int, float)) and pred > 0:
            return "<span class='badge salary'>💰 Predicted: ₹{} LPA</span>".format(int(round(pred)))
        return "<span class='badge'>💰 Salary: Not Available</span>"
    except Exception:
        return "<span class='badge'>💰 Salary: Not Available</span>"

def _render_ai_output(kind, text):
    st.markdown(f"**{kind}**")
    st.markdown(
        f"<div class='ai-response'>{text.replace(chr(10),'<br>')}</div>",
        unsafe_allow_html=True
    )

def _job_card(job, idx):
    """Glass-style job card with AI actions."""
    title = job.get("title", "Untitled")
    company = job.get("company", "Unknown Company")
    location = job.get("location", "N/A")
    posted = job.get("posted_date", "N/A")
    url = job.get("url", "#")
    desc = job.get("description", "") or "No description available."

    salary_html = _format_salary(title, company, location, desc, job.get("salary"))

    # Card
    st.markdown("<div class='job-card'>", unsafe_allow_html=True)
    st.markdown(f"<div class='job-title'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='job-meta'>🏢 {company} &nbsp;&nbsp;•&nbsp;&nbsp; 📍 {location} &nbsp;&nbsp;•&nbsp;&nbsp; 🗓 {posted}</div>", unsafe_allow_html=True)
    st.markdown(f"{salary_html} &nbsp;&nbsp; <a href='{url}' target='_blank' class='badge'>🔗 Apply</a>", unsafe_allow_html=True)
    st.markdown("<hr style='border:0;border-top:1px solid var(--border);margin:.8rem 0;'/>", unsafe_allow_html=True)

    # Description (short with expand)
    if len(desc) > 420:
        st.markdown(f"<div class='job-desc'>{desc[:420]}…</div>", unsafe_allow_html=True)
        with st.expander("Read full description"):
            st.markdown(f"<div class='job-desc'>{desc}</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='job-desc'>{desc}</div>", unsafe_allow_html=True)

    # Actions
    c1, c2, c3 = st.columns(3)
    do_fit = c1.button("🧩 Analyze My Fit", key=f"fit_{idx}")
    do_enh = c2.button("✨ Resume Enhancer", key=f"enh_{idx}")
    do_int = c3.button("🎯 Interview Trainer", key=f"int_{idx}")

    out_key = f"out_{idx}"
    st.session_state.setdefault("card_outputs", {})

    # Handlers
    if do_fit:
        if not st.session_state.get("resume_text"):
            st.error("Please upload your resume first.")
        else:
            with st.spinner("Analyzing fit…"):
                try:
                    text = analyze_job_fit(st.session_state["resume_text"], desc)
                except Exception as e:
                    text = f"❌ Error: {e}"
                st.session_state["card_outputs"][out_key] = ("🧩 Fit Analysis", text)
                st.rerun()

    if do_enh:
        if not st.session_state.get("resume_text"):
            st.error("Please upload your resume first.")
        else:
            with st.spinner("Enhancing resume…"):
                try:
                    text = enhance_resume(st.session_state["resume_text"], title)
                except Exception as e:
                    text = f"❌ Error: {e}"
                st.session_state["card_outputs"][out_key] = ("✨ Resume Enhancement", text)
                st.rerun()

    if do_int:
        with st.spinner("Generating interview questions…"):
            try:
                job_sk = extract_resume_features(desc).get("skills", [])
                text = generate_interview_questions(title, job_sk)
            except Exception as e:
                text = f"❌ Error: {e}"
            st.session_state["card_outputs"][out_key] = ("🎯 Interview Questions", text)
            st.rerun()

    prev = st.session_state["card_outputs"].get(out_key)
    if prev:
        kind, text = prev
        st.markdown("<div style='height:.4rem'></div>", unsafe_allow_html=True)
        _render_ai_output(kind, text)

    st.markdown("</div>", unsafe_allow_html=True)  # end card

# ----------------- Render results (grid) -----------------
if not jobs:
    st.info("No jobs to show. Upload your resume and describe what you're looking for.")
else:
    # 2-column grid (responsive-ish)
    for i in range(0, len(jobs), 2):
        cols = st.columns(2, gap="large")
        for j, col in enumerate(cols):
            idx = i + j
            if idx < len(jobs):
                with col:
                    _job_card(jobs[idx], idx)

# ----------------- Footer -----------------
st.markdown("<br>", unsafe_allow_html=True)
st.caption("© 2025 AI Job Hunter — Glass UI • Local LLM (Ollama Llama 3.2) • Salary Prediction")
