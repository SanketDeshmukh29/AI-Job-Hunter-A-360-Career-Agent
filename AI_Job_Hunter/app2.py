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



from scraper import fetch_jobs, load_cache_or_demo
from resume_parser import extract_resume_features
from ai_assistant import analyze_job_fit, enhance_resume, generate_interview_questions


st.set_page_config(page_title="AI Job Hunter", layout="wide", page_icon="🎯")
st.title("🚀 AI Job Hunter — Your 360° Career Agent")


PRIMARY_COLOR = "#1A98FF"
DARK_BG = "#0E1117"
DARK_CARD_BG = "#1F2430"
LIGHT_TEXT = "#FAFAFA"
SUBTLE_BORDER = "#333333"

st.markdown(
    f"""
    <style>
    /* 1. Global Background and Text Color Fix (DARK MODE) */
    .main, .css-1dp5ss0, .stApp {{
        background-color: {DARK_BG}; 
        color: {LIGHT_TEXT}; 
    }}
    /* Target common Streamlit content blocks to ensure light text */
    .stMarkdown, .stText, .stLabel, .stCheckbox > label, .stSelectbox > label, .stTextInput > label {{
        color: {LIGHT_TEXT} !important; 
    }}
    
    /* 2. Custom Button Style with primary color */
    .stButton>button {{
        font-weight: 700;
        border-radius: 6px; 
        transition: all 0.2s ease-in-out;
        border: 1px solid {PRIMARY_COLOR};
        background-color: {DARK_CARD_BG}; /* Dark background for unpressed buttons */
        color: {LIGHT_TEXT}; /* Light text color */
    }}
    .stButton>button:hover {{
        background-color: {PRIMARY_COLOR} !important;
        color: white !important;
    }}
    /* 3. Job Card Expander Style (Flat and minimal, using background contrast) */
    .stExpander {{
        border-radius: 8px; 
        border: 1px solid {SUBTLE_BORDER}; 
        box-shadow: none; 
        margin-bottom: 15px;
        background-color: {DARK_CARD_BG}; /* Lighter dark background for cards */
    }}
    .stExpander > div:first-child {{
        padding: 16px;
    }}
    .stExpander > div:last-child {{
        padding: 0 16px 16px 16px;
    }}
    /* 4. AI Response Card (Clean, high contrast output) */
    .ai-response-card {{
        box-shadow: none;
        border: 1px solid {SUBTLE_BORDER}; 
        border-left: 4px solid {PRIMARY_COLOR} !important; /* Accent border */
        background-color: {DARK_CARD_BG} !important; /* Matches job card background */
        color: {LIGHT_TEXT};
        border-radius: 8px;
    }}
    /* 5. Header and Subheader styling */
    h1, h2, h3, h4 {{
        color: {LIGHT_TEXT}; 
    }}
    /* Ensure the container border looks good for the I Love PDF style tool box */
    .stContainer {{
        border-radius: 12px;
        border: 2px solid {SUBTLE_BORDER};
        padding: 20px;
        background-color: {DARK_CARD_BG};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }}
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown(
    "Configure your search and upload your resume below. **Live data and AI features are ready.**",
    unsafe_allow_html=True
)

# ----------------- Utility -----------------
DATA_PATH = Path("data") / "scraped_jobs.json"
results_limit = 20  # Maximum number of jobs to display


def get_cached_meta():
    """Returns cached job info for display."""
    if DATA_PATH.exists():
        mtime = datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                arr = json.load(f)
        except Exception:
            arr = []
        return len(arr), mtime
    return 0, "N/A"

# --- Define resume file uploader outside the container for Streamlit functionality ---
resume_file = st.file_uploader("Upload PDF / TXT", type=["pdf", "txt"], help="Upload your resume to enable fit analysis and enhancement.")
# Note: The uploader component is defined here, but visually placed inside the container below using a placeholder/caption.

# ----------------- Resume Parsing Logic (Moved to top for session state update) -----------------
resume_text = st.session_state.get("resume_text", "")
current_file_name = resume_file.name if resume_file else None
parsed_file_name = st.session_state.get("parsed_file_name", None)

if resume_file and (current_file_name != parsed_file_name or not resume_text):
    
    st.session_state["resume_text"] = "" 
    st.session_state["parsed_file_name"] = None 

    # Status update happens globally before the main container
    with st.spinner("Parsing resume..."):
        try:
            file_bytes = resume_file.read()
            resume_text = ""

            if resume_file.type == "application/pdf":
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(BytesIO(file_bytes))
                    pages = [p.extract_text() or "" for p in reader.pages]
                    resume_text = "\n".join(pages).strip()
                    if not resume_text:
                        raise ValueError("No text extracted by PyPDF2")
                except Exception:
                    from pdfminer.high_level import extract_text as pdfminer_extract_text
                    resume_text = pdfminer_extract_text(BytesIO(file_bytes)).strip()
            else:
                resume_text = file_bytes.decode("utf-8", errors="replace")
                
            if resume_text:
                st.session_state["resume_text"] = resume_text
                st.session_state["parsed_file_name"] = current_file_name
                
            else:
                st.error("❌ Resume parsing failed: No text extracted.")

        except Exception as e:
            st.error(f"❌ Resume parsing error: {e}")
            st.session_state["resume_text"] = ""


# ----------------- Control Hub (Single Dashboard Card - I LOVE PDF Style) -----------------
st.markdown("<br>", unsafe_allow_html=True) 
with st.container(border=True): # Gives a prominent, distinct card look
    st.subheader("🛠️ Career Tools Configuration")
    st.markdown("---")

    # --- Row 1: Search Inputs ---
    st.markdown("##### 🔎 Job Search Criteria")
    col1, col2, col3, col4 = st.columns([3, 2, 1.5, 1])

    with col1:
        job_role_input = st.text_input("💼 Job Role (e.g., Data Scientist)", value=st.session_state.get("job_role", ""))
        if job_role_input:
            st.session_state["job_role"] = job_role_input
        job_role = st.session_state.get("job_role", "")

    with col2:
        location = st.text_input("📍 Location (e.g., Pune)", value=st.session_state.get("location", "Pune"))
        st.session_state["location"] = location
        
    with col3:
        date_posted = st.selectbox("🗓 Posted Since", ["day", "week", "month"], index=1, help="Filter jobs posted within this time frame.")
        st.session_state["date_posted"] = date_posted
        
    with col4:
        st.markdown("<br>", unsafe_allow_html=True) # Align checkbox vertically
        remote = st.checkbox("🏠 Remote Only", value=st.session_state.get("remote", False), help="Only search for fully remote positions.")
        st.session_state["remote"] = remote

    st.markdown("---")

    # --- Row 2: Resume Uploader & Summary/Metrics ---
    col_upload_placeholder, col_summary_metric = st.columns([2.5, 3.5])

    with col_upload_placeholder:
        st.markdown("##### 📄 Upload Resume")
        # Placeholder for the uploader which was defined globally
        st.caption("Resume file uploader is active above this block.")
        
        # Display the simple summary/status here
        resume_text = st.session_state.get("resume_text", "")
        if resume_text:
            features = extract_resume_features(resume_text)
            st.success(f"✅ Resume parsed! {len(features['skills'])} skills found.")
            st.caption(f"Experience: {features['experience'] or 'N/A'} yrs.")
        else:
            st.warning("Upload resume to unlock Fit Analysis & Enhancer.")
        
    with col_summary_metric:
        st.markdown("##### ⚙️ Settings & Cache")
        col_opt1, col_opt2 = st.columns([1.5, 2])
        
        with col_opt1:
            use_cache = st.checkbox("🔄 Use Cached Jobs", value=st.session_state.get("use_cache", True), help="Use local data to speed up loading.")
            st.session_state["use_cache"] = use_cache
        
        with col_opt2:
            total_cached, last_updated = get_cached_meta()
            st.metric(label="Cached Jobs in file", value=total_cached, help=f"Last updated: {last_updated}")


# ----------------- Action Buttons (Prominent placement) -----------------
st.markdown("<br>", unsafe_allow_html=True) 
col_action_1, col_action_2, col_spacer = st.columns([1.5, 1.5, 4])

with col_action_1:
    refresh_jobs = st.button("🔄 Refresh Live Jobs", use_container_width=True, help="Force a refresh of live jobs from the API.")

with col_action_2:
    search_btn = st.button("🚀 Search & Match", use_container_width=True, type="primary", help="Search using cache or live data based on the checkbox.")


# ----------------- Job Fetching -----------------
jobs = st.session_state.get("jobs", [])

if refresh_jobs or (search_btn and not use_cache):
    if not job_role:
        st.error("Please enter a **Job Role** before searching.")
    else:
        # Use st.status for a cleaner, modern look during loading
        with st.status("⏳ Fetching live jobs...", expanded=True) as status:
            try:
                q = st.session_state.get("job_role", "Software Engineer")
                loc = st.session_state.get("location", "Pune")
                st.write(f"Searching for '{q}' in '{loc}'...")
                jobs = fetch_jobs(q, location=loc, remote=remote, date_posted=date_posted, limit=results_limit)
                if not jobs:
                    st.warning("No live jobs found — loading cached/demo jobs.")
                    jobs = load_cache_or_demo()
                    status.update(label="⚠️ Loaded cached/demo jobs.", state="warning", expanded=False)
                else:
                    status.update(label=f"✅ Found {len(jobs)} live jobs.", state="complete", expanded=False)
            except Exception as e:
                st.error(f"Error fetching jobs: {e}")
                jobs = load_cache_or_demo()
                status.update(label="❌ Failed to fetch. Loaded demo jobs.", state="error", expanded=False)
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


# ----------------- Helper for AI Response -----------------
def show_ai_response(title, content):
    """Display AI-generated text with a modern, stylized card look."""
    
    # Use the defined dark mode colors
    bg_color = DARK_CARD_BG
    text_color = LIGHT_TEXT
    
    safe_text = content.replace("\n", "<br>")

    st.markdown(f"**🤖 {title}**", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='ai-response-card' style='
            padding: 16px;
            color: {text_color};
            background-color: {bg_color};
            border-radius: 8px;
            line-height: 1.6;
            font-size: 15px;
            margin-top: 5px;
        '>
            {safe_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- Display job results -----------------
st.markdown("<br><br>", unsafe_allow_html=True) 
st.header("📋 Matched Job Listings")
st.divider()

if not jobs:
    st.info("No jobs to show. Use the **Configuration Dashboard** above to set a role and search.")
else:
    st.success(f"Showing **{len(jobs)}** results for **{st.session_state.get('job_role', 'Jobs')}**")

    def display_job_card(job, idx):
        """Displays a single job card with interactive AI actions using an expanded layout."""
        key_prefix = f"job_{idx}"
        resume_text = st.session_state.get("resume_text", "")
        job_role = st.session_state.get("job_role", "")

        title = job.get('title','Untitled')
        company = job.get('company','')
        location = job.get('location','')
        salary = job.get('salary') or 'N/A'

        header_title = f"**{title}** — {company}"
        
        with st.expander(header_title, expanded=False):
            # Row for key metadata
            col_meta_1, col_meta_2, col_meta_3, col_meta_4 = st.columns([2, 2, 2, 1])
            col_meta_1.markdown(f"🏢 **Company:** {company}")
            col_meta_2.markdown(f"📍 **Location:** {location or 'N/A'}")
            col_meta_3.markdown(f"💰 **Salary:** `{salary}`")
            col_meta_4.markdown(f"🗓 **Posted:** `{job.get('posted_date') or 'N/A'}`")
            
            st.markdown(f"🔗 [**Apply Here**]({job.get('url')})", unsafe_allow_html=True)

            st.divider()
            
            # Job Description Area
            desc = job.get("description") or "No description available."
            st.markdown("##### 📜 Job Description Summary")
            if len(desc) > 300:
                preview = desc[:300] + "..."
                st.markdown(preview)
                with st.expander("Read Full Description"):
                    st.markdown(desc)
            else:
                st.markdown(desc)
            
            st.markdown("---")

            # --- Action buttons ---
            st.markdown("##### 🤖 Get AI Insight")
            cols = st.columns(3)
            # Buttons are disabled if no resume text is available
            fit_btn = cols[0].button("🧩 Analyze My Fit", key=f"{key_prefix}_fit", use_container_width=True, disabled=not resume_text)
            enh_btn = cols[1].button("✨ Resume Enhancer", key=f"{key_prefix}_enh", use_container_width=True, disabled=not resume_text)
            int_btn = cols[2].button("🎯 Interview Trainer", key=f"{key_prefix}_int", use_container_width=True)

            output_key = f"output_{idx}"
            if "card_outputs" not in st.session_state:
                st.session_state["card_outputs"] = {}

            # --- Button Handlers (Logic remains the same) ---
            if fit_btn:
                if not resume_text:
                    st.error("⬇️ Please upload your resume first to analyze fit.")
                else:
                    with st.spinner("🔍 Analyzing job fit..."):
                        try:
                            ai_text = analyze_job_fit(resume_text, desc)
                        except Exception as e:
                            ai_text = f"❌ Error: Could not analyze fit. LLM communication error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Fit Analysis", ai_text)
                        st.rerun()

            if enh_btn:
                if not resume_text:
                    st.error("⬇️ Please upload your resume first to enhance it.")
                else:
                    with st.spinner("✨ Enhancing your resume..."):
                        try:
                            ai_text = enhance_resume(resume_text, job.get("title") or job_role)
                        except Exception as e:
                            ai_text = f"❌ Error: Could not enhance resume. LLM communication error: {e}"
                        st.session_state["card_outputs"][output_key] = ("Resume Enhancement Suggestions", ai_text)
                        st.rerun()

            if int_btn:
                with st.spinner("🧠 Generating interview questions..."):
                    try:
                        job_title = job.get("title") or job_role or "Software Engineer"
                        job_skills = extract_resume_features(desc).get("skills", [])
                        ai_text = generate_interview_questions(job_title, job_skills)
                    except Exception as e:
                        ai_text = f"❌ Error: Could not generate questions. LLM communication error: {e}"
                    st.session_state["card_outputs"][output_key] = ("Interview Questions", ai_text)
                    st.rerun()

            # --- Show AI Output ---
            prev = st.session_state["card_outputs"].get(output_key)
            if prev:
                st.markdown("<br>", unsafe_allow_html=True)
                kind, text = prev
                show_ai_response(kind, text)
                st.markdown("<br>", unsafe_allow_html=True)

    # --- Render job cards ---
    for idx, job in enumerate(jobs):
        display_job_card(job, idx)

# ----------------- Footer -----------------
st.divider()
st.caption("© 2025 AI Job Hunter | Built with Streamlit and Local LLMs (Ollama llama3.2).")


