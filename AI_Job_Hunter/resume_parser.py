import re
from typing import List, Dict

# A simple, extensible skill keyword list
SKILL_KEYWORDS = [
    'python', 'java', 'machine learning', 'ml', 'data science', 'sql',
    'react', 'javascript', 'node', 'c++', 'c#', 'aws', 'docker',
    'tensorflow', 'pytorch', 'nlp', 'excel', 'tableau',
]


def extract_resume_features(text: str) -> Dict:
    text_lower = text.lower()
    # --- Skill extraction ---
    detected_skills = sorted({
        skill for skill in SKILL_KEYWORDS
        if re.search(r'\b' + re.escape(skill) + r'\b', text_lower)
    })

    # --- Experience extraction (X years, e.g., "3 years", "7+ years") ---
    xp_matches = re.findall(r'(\d+)(\+)?\s*(?:years?|yrs?)', text_lower)
    experience = max((int(m[0]) for m in xp_matches), default=0)

    return {
        "skills": detected_skills,
        "experience": experience
    }


if __name__ == "__main__":
    # Example usage
    demo = """
    Experienced Data Scientist with 5+ years in Python, SQL, and ML. Also skilled in React and AWS.
    """
    print(extract_resume_features(demo))

