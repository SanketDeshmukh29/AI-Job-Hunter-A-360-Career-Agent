# ai_assistant.py
import os
import json
from difflib import SequenceMatcher
from resume_parser import extract_resume_features


try:
    import ollama
except ImportError:
    ollama = None
    print("⚠️ Ollama not found. Please install with: pip install ollama")


OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def call_ollama(prompt: str) -> str:
   
    if ollama is None:
        return "⚠️ Ollama not installed. Run: pip install ollama"

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        
        if hasattr(response, "message") and hasattr(response.message, "content"):
            return response.message.content.strip()
        elif isinstance(response, dict):
            if "message" in response and isinstance(response["message"], dict):
                return response["message"].get("content", "").strip()
            elif "messages" in response and isinstance(response["messages"], list):
                return response["messages"][-1].get("content", "").strip()
      
        return str(response)

    except Exception as e:
        return f"❌ Ollama error: {e}"



def analyze_job_fit(resume_text: str, job_description: str) -> str:
    
    res_features = extract_resume_features(resume_text)
    job_features = extract_resume_features(job_description)

    common_skills = set(res_features["skills"]) & set(job_features["skills"])
    missing_skills = set(job_features["skills"]) - set(res_features["skills"])
    xp_user = res_features["experience"]
    xp_job = job_features["experience"] if job_features["experience"] else 1

    fit_percent = int(
        (len(common_skills) / (len(job_features["skills"]) or 1)) * 70
        + min(xp_user / xp_job, 1) * 30
    )

    
    if ollama is None:
        ratio = SequenceMatcher(None, resume_text.lower(), job_description.lower()).ratio()
        return f"(Offline Fallback)\nFit Score: {int(ratio * 100)}%\nSkills Matched: {', '.join(common_skills)}\nMissing Skills: {', '.join(missing_skills)}"

    prompt = f"""
You are a technical recruiter AI. Compare a candidate's resume and a job description.

**Candidate Skills:** {res_features['skills']}
**Job Skills:** {job_features['skills']}
**Candidate Experience:** {xp_user} years
**Job Experience:** {xp_job} years

Compute an accurate and fair **Fit Score: {fit_percent}%** and provide a professional summary with:
- ✅ Skills Matched
- ⚠️ Missing Skills
- 📊 Fit Percentage ({fit_percent}%)
- 🧩 Short Recommendation (2–3 sentences)
"""
    return call_ollama(prompt)



def enhance_resume(resume_text: str, job_title: str) -> str:
    
    prompt = f"""
You are a professional resume writer.
Optimize this resume for a **{job_title}** role.

- Keep existing experience details but rewrite bullet points for stronger impact.
- Add relevant modern industry keywords.
- Improve structure and phrasing to ATS standards.
- Keep tone concise and professional.

Resume:
{resume_text[:4000]}
"""
    return call_ollama(prompt)



def generate_interview_questions(job_title: str, skills: list) -> str:

    skill_str = ", ".join(skills) or "general technical and behavioral skills"
    prompt = f"""
You are an experienced interviewer hiring for a **{job_title}**.

Generate:
- 5 technical questions focusing on these skills: {skill_str}
- 3 behavioral questions assessing teamwork, communication, and adaptability.

Format output clearly in Markdown:
### Technical Questions
1. ...
2. ...
### Behavioral Questions
1. ...
2. ...
"""
    return call_ollama(prompt)


# ---------------- Local testing ----------------
if __name__ == "__main__":
    demo_resume = "5 years of experience in Python, SQL, and React. Worked on ML projects."
    demo_job = "Looking for a Data Scientist with Python, ML, SQL, and 3+ years experience."

    print("\n--- Analyze Fit ---")
    print(analyze_job_fit(demo_resume, demo_job))

    print("\n--- Enhanced Resume ---")
    print(enhance_resume(demo_resume, "Data Scientist"))

    print("\n--- Interview Questions ---")
    print(generate_interview_questions("Data Scientist", ["Python", "ML", "SQL"]))
