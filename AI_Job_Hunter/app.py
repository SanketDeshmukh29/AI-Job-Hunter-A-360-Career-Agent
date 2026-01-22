# app.py
import os
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import streamlit as st

# Local modules
from scraper import fetch_jobs, load_cache_or_demo
from resume_parser import extract_resume_features
from ai_assistant import analyze_job_fit, enhance_resume, generate_interview_questions

# ----------------- Page config -----------------
st.set_page_config(page_title="AI Job Hunter", layout="wide", page_icon="🤖")
st.title("🤖 AI Job Hunter — 360° Career Agent")
st.markdown(
    "Upload your resume, search live jobs, and use the AI assistant (local Ollama llama3.2) "
    "to analyze fit, enhance resume, and prepare for interviews."
)

# ----------------- Sidebar -----------------
with st.sidebar:
    st.header("🔎 Search & Inputs")

    job_role_input = st.text_input("💼 Job Role", value=st.session_state.get("job_role", ""))
    if job_role_input:
        st.session_state["job_role"] = job_role_input
    job_role = st.session_state.get("job_role", "")

    location = st.text_input("📍 Location", value=st.session_state.get("location", "Pune"))
    st.session_state["location"] = location

    remote = st.checkbox("🏠 Remote Only", value=st.session_state.get("remote", False))
    st.session_state["remote"] = remote

    date_posted = st.selectbox("🗓 Date Posted", ["day", "week", "month"], index=1)
    st.session_state["date_posted"] = date_posted

    resume_file = st.file_uploader("📄 Upload Resume (PDF / TXT)", type=["pdf", "txt"])
    use_cache = st.checkbox("🔁 Use cached jobs (avoid API calls)", value=True)
    results_limit = st.slider("Results per fetch", 1, 20, 8)

    st.markdown("---")
    refresh_jobs = st.button("🔄 Refresh Live Jobs")
    search_btn = st.button("🔎 Search & Match")

# ----------------- Utility -----------------
DATA_PATH = Path("data") / "scraped_jobs.json"


def get_cached_meta():
    """Returns cached job info for sidebar display."""
    if DATA_PATH.exists():
        mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
        return len(arr), mtime
    return 0, "N/A"


# ----------------- Resume Parsing -----------------
if resume_file:
    try:
        file_bytes = resume_file.read()
        resume_text = ""

        if resume_file.type == "application/pdf":
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(BytesIO(file_bytes))
                pages = [p.extract_text() or "" for p in reader.pages]
                resume_text = "\n".join(pages).strip()
                if resume_text:
                    st.sidebar.success("✅ PDF parsed successfully (PyPDF2).")
                else:
                    raise ValueError("No text extracted by PyPDF2")
            except Exception:
                from pdfminer.high_level import extract_text as pdfminer_extract_text
                resume_text = pdfminer_extract_text(BytesIO(file_bytes)).strip()
                st.sidebar.success("✅ PDF parsed successfully (pdfminer).")
        else:
            resume_text = file_bytes.decode("utf-8", errors="replace")
            st.sidebar.success("✅ TXT parsed successfully.")
    except Exception as e:
        st.sidebar.error(f"❌ Resume parsing error: {e}")
        resume_text = ""

    st.session_state["resume_text"] = resume_text
else:
    resume_text = st.session_state.get("resume_text", "")

# ----------------- Resume Summary -----------------
with st.sidebar.expander("📄 Resume Summary", expanded=False):
    if resume_text:
        features = extract_resume_features(resume_text)
        st.write(f"**Skills ({len(features['skills'])}):** {', '.join(features['skills']) or '—'}")
        st.write(f"**Experience (yrs):** {features['experience']}")
    else:
        st.info("Upload a resume to see parsed skills & experience.")

# ----------------- Job Fetching -----------------
jobs = st.session_state.get("jobs", [])

if refresh_jobs or (search_btn and not use_cache):
    with st.spinner("⏳ Fetching live jobs..."):
        try:
            q = st.session_state.get("job_role", "") or "Data Scientist"
            loc = st.session_state.get("location", "Pune")
            jobs = fetch_jobs(q, location=loc, remote=remote, date_posted=date_posted, limit=results_limit)
            if not jobs:
                st.warning("No live jobs found — loading cached/demo jobs.")
                jobs = load_cache_or_demo()
        except Exception as e:
            st.error(f"Error fetching jobs: {e}")
            jobs = load_cache_or_demo()
    st.session_state["jobs"] = jobs

elif use_cache and not jobs:
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                all_jobs = json.load(f)
            jobs = all_jobs[:results_limit]
        except Exception:
            jobs = load_cache_or_demo()
        st.session_state["jobs"] = jobs
    else:
        jobs = load_cache_or_demo()
        st.session_state["jobs"] = jobs

# ----------------- Sidebar metadata -----------------
total_cached, last_updated = get_cached_meta()
st.sidebar.markdown("---")
st.sidebar.write(f"📁 Cached jobs: **{total_cached}**")
st.sidebar.write(f"🕓 Last updated: **{last_updated}**")

# ----------------- Helper for AI Response -----------------
def show_ai_response(title, content):
    """Display AI-generated text with theme-aware styling."""
    theme = st.get_option("theme.base") or "light"
    bg_color = "#f9fafb" if theme == "light" else "#1e1e1e"
    text_color = "#111111" if theme == "light" else "#f5f5f5"
    border_color = "#2563eb"

    safe_text = content.replace("\n", "<br>").replace("**", "<b>").replace("__", "<u>")

    st.markdown(f"### 🤖 {title}", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='
            padding:16px;
            background-color: {bg_color};
            color: {text_color};
            border: 1px solid #d1d5db;
            border-left: 5px solid {border_color};
            border-radius: 10px;
            line-height: 1.6;
            font-size: 15px;
            font-family: "Segoe UI", sans-serif;
        '>
            {safe_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- Display job results -----------------
st.header("📋 Results")

if not jobs:
    st.info("No jobs to show. Use the sidebar to search or refresh live jobs.")
else:
    st.success(f"Showing {len(jobs)} job results")

    def display_job_card(job, idx):
        """Displays a single job card with interactive AI actions."""
        key_prefix = f"job_{idx}"
        resume_text = st.session_state.get("resume_text", "")
        job_role = st.session_state.get("job_role", "")

        header = f"**{job.get('title','Untitled')}** — {job.get('company','')} • {job.get('location','')}"
        with st.expander(header, expanded=False):
            st.markdown(
                f"**💸 Salary:** `{job.get('salary') or 'N/A'}` | **⏰ Posted:** `{job.get('posted_date') or 'N/A'}`"
            )
            st.markdown(f"🔗 [Apply Here]({job.get('url')})", unsafe_allow_html=True)

            # ✅ Improved description display
            desc = job.get("description") or "No description available."
            if len(desc) > 400:
                preview = desc[:400] + "..."
                with st.expander("📜 Read Full Description"):
                    st.markdown(desc)
                st.markdown(preview)
            else:
                st.markdown(desc)

            # --- Action buttons ---
            cols = st.columns([1, 1, 1])
            fit_btn = cols[0].button("🧩 Analyze My Fit", key=f"{key_prefix}_fit")
            enh_btn = cols[1].button("🚀 Resume Enhancer", key=f"{key_prefix}_enh")
            int_btn = cols[2].button("🎯 Interview Trainer", key=f"{key_prefix}_int")

            output_key = f"output_{idx}"
            if "card_outputs" not in st.session_state:
                st.session_state["card_outputs"] = {}

            # --- Button Handlers ---
            if fit_btn:
                if not resume_text:
                    st.error("⬇️ Please upload your resume first.")
                else:
                    with st.spinner("🔍 Analyzing job fit..."):
                        try:
                            ai_text = analyze_job_fit(resume_text, desc)
                        except Exception as e:
                            ai_text = f"❌ Error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Fit Analysis", ai_text)
                        st.rerun()

            if enh_btn:
                if not resume_text:
                    st.error("⬇️ Please upload your resume first.")
                else:
                    with st.spinner("✨ Enhancing your resume..."):
                        try:
                            ai_text = enhance_resume(resume_text, job.get("title") or job_role)
                        except Exception as e:
                            ai_text = f"❌ Error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Resume Enhancer", ai_text)
                        st.rerun()

            if int_btn:
                with st.spinner("🧠 Generating interview questions..."):
                    try:
                        job_title = job.get("title") or job_role or "Software Engineer"
                        job_skills = extract_resume_features(desc).get("skills", [])
                        ai_text = generate_interview_questions(job_title, job_skills)
                    except Exception as e:
                        ai_text = f"❌ Error: {e}"
                    st.session_state["card_outputs"][output_key] = ("Interview Trainer", ai_text)
                    st.rerun()

            # --- Show AI Output (Clean Layout) ---
            prev = st.session_state["card_outputs"].get(output_key)
            if prev:
                kind, text = prev
                st.markdown("---")
                show_ai_response(kind, text)

    # --- Render job cards ---
    for idx, job in enumerate(jobs):
        display_job_card(job, idx)

# ----------------- Footer -----------------
st.markdown("---")
st.caption("📄 **AI Job Hunter** — CDAC DBDA Project | Local LLM (Ollama llama3.2) integrated securely.")
