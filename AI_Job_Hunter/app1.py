# app.py — ChatGPT-style AI Job Hunter
import os
import json
from io import BytesIO
from datetime import datetime
from pathlib import Path
import streamlit as st

# Local imports
from scraper import fetch_jobs, load_cache_or_demo
from resume_parser import extract_resume_features
from ai_assistant import analyze_job_fit, enhance_resume, generate_interview_questions

# ----------------- Page Config -----------------
st.set_page_config(page_title="AI Job Hunter", layout="wide", page_icon="🤖")

# ----------------- Theme Styling -----------------
st.markdown("""
<style>
body, .stApp {
    background-color: #202123;
    color: #ECECEC;
}
h1,h2,h3,h4,h5 {
    color: #ECECEC;
}
.stButton>button {
    background-color: #2A2B32;
    color: #ECECEC;
    border: 1px solid #10A37F;
    border-radius: 8px;
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    background-color: #10A37F !important;
    color: white !important;
}
.stExpander {
    background-color: #2A2B32 !important;
    border: 1px solid #3A3B42;
    border-radius: 8px;
}
.ai-response-card {
    background-color: #2A2B32;
    color: #ECECEC;
    border-left: 4px solid #10A37F;
    padding: 1rem;
    border-radius: 8px;
}
.upload-box {
    border: 2px dashed #10A37F;
    border-radius: 10px;
    background-color: #2A2B32;
    padding: 1.5rem;
    text-align: center;
    color: #ECECEC;
}
.search-bar-container {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}
.search-input {
    width: 60%;
    background-color: #2A2B32;
    color: #ECECEC;
    border-radius: 8px;
    border: 1px solid #3A3B42;
    padding: 0.8rem;
}
.settings-icon {
    font-size: 22px;
    color: #10A37F;
    cursor: pointer;
}
</style>
""", unsafe_allow_html=True)

# ----------------- Header -----------------
st.title("🤖 AI Job Hunter — 360° Career Agent")

# ----------------- Data Path -----------------
DATA_PATH = Path("data") / "scraped_jobs.json"

# ----------------- Helper: Load Cache Metadata -----------------
def get_cached_meta():
    if DATA_PATH.exists():
        mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
        return len(arr), mtime
    return 0, "N/A"

# ----------------- Resume Upload Section -----------------
st.markdown("<div class='upload-box'>📄 **Upload your resume (PDF or TXT)**</div>", unsafe_allow_html=True)
resume_file = st.file_uploader("", type=["pdf", "txt"])

resume_text = st.session_state.get("resume_text", "")
if resume_file:
    try:
        file_bytes = resume_file.read()
        resume_text = ""
        if resume_file.type == "application/pdf":
            import PyPDF2
            reader = PyPDF2.PdfReader(BytesIO(file_bytes))
            pages = [p.extract_text() or "" for p in reader.pages]
            resume_text = "\n".join(pages).strip()
        else:
            resume_text = file_bytes.decode("utf-8", errors="replace")
        st.session_state["resume_text"] = resume_text
        st.success("✅ Resume uploaded successfully!")
    except Exception as e:
        st.error(f"Error reading resume: {e}")

# ----------------- Resume Insights -----------------
if resume_text:
    with st.expander("📊 Resume Insights", expanded=False):
        features = extract_resume_features(resume_text)
        st.write(f"**Skills ({len(features['skills'])}):** {', '.join(features['skills']) or '—'}")
        st.write(f"**Experience (yrs):** {features['experience']}")

# ----------------- Filter Popover (⚙️ Icon) -----------------
with st.popover("⚙️ Filters"):
    st.subheader("Job Filters")
    location = st.text_input("📍 Location", value=st.session_state.get("location", ""))
    st.session_state["location"] = location
    remote = st.checkbox("🏠 Remote Only", value=st.session_state.get("remote", False))
    st.session_state["remote"] = remote
    date_posted = st.selectbox("🗓 Posted Since", ["day", "week", "month"], index=1)
    st.session_state["date_posted"] = date_posted

# ----------------- Search Input -----------------
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("<h4>💬 Describe the kind of job you're looking for:</h4>", unsafe_allow_html=True)
col_input, col_button = st.columns([6, 1])
with col_input:
    user_prompt = st.chat_input("e.g., Remote Data Scientist role in Pune")
with col_button:
    search_clicked = st.button("🔍 Search Jobs", use_container_width=True)

# ----------------- Handle Search Logic -----------------
jobs = st.session_state.get("jobs", [])

if user_prompt or search_clicked:
    from ai_assistant import call_ollama

    if user_prompt:
        with st.spinner("🧠 Understanding your search..."):
            try:
                parse_prompt = (
                    f"Extract structured search parameters from this job query:\n\n'{user_prompt}'\n\n"
                    "Return JSON with keys: job_role, location, remote (true/false)."
                )
                parsed = call_ollama(parse_prompt)
                import re, json
                match = re.search(r"\{.*\}", parsed, re.DOTALL)
                if match:
                    parsed_json = json.loads(match.group(0))
                    job_role = parsed_json.get("job_role", "")
                    location = parsed_json.get("location", "")
                    remote = parsed_json.get("remote", False)
                else:
                    job_role = user_prompt
                    location = ""
                    remote = False
                st.session_state["job_role"] = job_role
                st.session_state["location"] = location
                st.session_state["remote"] = remote
                st.success(f"✅ Parsed: {job_role or 'N/A'} in {location or 'Anywhere'} (Remote={remote})")
            except Exception as e:
                st.error(f"Could not parse search: {e}")
                job_role = user_prompt
    else:
        job_role = st.session_state.get("job_role", "")

    if not job_role:
        st.warning("Please describe or specify a job role.")
    else:
        with st.spinner("🔍 Fetching job listings..."):
            try:
                jobs = fetch_jobs(job_role, location=st.session_state.get("location", ""), remote=remote,
                                  date_posted=st.session_state.get("date_posted", "week"), limit=10)
                if not jobs:
                    st.warning("No live jobs found — showing cached ones.")
                    jobs = load_cache_or_demo()
            except Exception as e:
                st.error(f"Error fetching jobs: {e}")
                jobs = load_cache_or_demo()
        st.session_state["jobs"] = jobs

# ----------------- Job Results -----------------
st.markdown("<br><br>", unsafe_allow_html=True)
st.header("📋 Job Recommendations")

if not jobs:
    st.info("No jobs to show. Upload your resume and describe what you're looking for.")
else:
    def display_job_card(job, idx):
        key_prefix = f"job_{idx}"
        resume_text = st.session_state.get("resume_text", "")
        job_role = st.session_state.get("job_role", "")

        title = job.get('title','Untitled')
        company = job.get('company','')
        location = job.get('location','')
        salary = job.get('salary') or 'N/A'

        header = f"**{title}** — {company}"
        with st.expander(header, expanded=False):
            st.markdown(f"📍 {location or 'N/A'} | 💰 {salary} | 🗓 {job.get('posted_date','N/A')}")
            st.markdown(f"🔗 [Apply Here]({job.get('url')})", unsafe_allow_html=True)

            desc = job.get("description") or "No description available."
            st.markdown("---")
            st.markdown(desc[:400] + ("..." if len(desc) > 400 else ""))

            cols = st.columns(3)
            fit = cols[0].button("🧩 Analyze My Fit", key=f"{key_prefix}_fit")
            enh = cols[1].button("✨ Resume Enhancer", key=f"{key_prefix}_enh")
            intr = cols[2].button("🎯 Interview Trainer", key=f"{key_prefix}_int")

            output_key = f"output_{idx}"
            if "card_outputs" not in st.session_state:
                st.session_state["card_outputs"] = {}

            if fit:
                if not resume_text:
                    st.error("Please upload your resume first.")
                else:
                    with st.spinner("Analyzing fit..."):
                        try:
                            text = analyze_job_fit(resume_text, desc)
                        except Exception as e:
                            text = f"❌ Error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Fit Analysis", text)
                        st.rerun()

            if enh:
                if not resume_text:
                    st.error("Please upload your resume first.")
                else:
                    with st.spinner("Enhancing resume..."):
                        try:
                            text = enhance_resume(resume_text, job.get("title") or job_role)
                        except Exception as e:
                            text = f"❌ Error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Resume Enhancement", text)
                        st.rerun()

            if intr:
                with st.spinner("Generating interview questions..."):
                    try:
                        skills = extract_resume_features(desc).get("skills", [])
                        text = generate_interview_questions(job.get("title") or job_role, skills)
                    except Exception as e:
                        text = f"❌ Error: {e}"
                    st.session_state["card_outputs"][output_key] = ("Interview Questions", text)
                    st.rerun()

            prev = st.session_state["card_outputs"].get(output_key)
            if prev:
                kind, text = prev
                st.markdown("---")
                st.markdown(f"### {kind}")
                st.markdown(f"<div class='ai-response-card'>{text.replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

    for idx, job in enumerate(jobs):
        display_job_card(job, idx)

# ----------------- Footer -----------------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("© 2025 AI Job Hunter — Powered by Ollama Llama 3.2")

