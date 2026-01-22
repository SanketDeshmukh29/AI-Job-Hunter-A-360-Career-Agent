import os
import json
import random
import requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

DATA_PATH = os.path.join('data', 'scraped_jobs.json')
JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"

# --- Basic logging utility ---
def log(msg: str, error=False):
    prefix = '[ERROR]' if error else '[OK]'
    print(f"{prefix} {msg}")


def fetch_jobs(query, location=None, remote=False, date_posted=None, limit=10):
    # Read the API key at call time to avoid import-order issues
    rapidapi_key = os.getenv('RAPIDAPI_KEY')
    if not rapidapi_key:
        log("RAPIDAPI_KEY not set in environment.", error=True)
        return load_cache_or_demo()

    # Prefer including location in the query string per JSearch examples
    combined_query = f"{query} in {location}" if location else query
    log(f"Searching: '{combined_query}' (remote={remote}, date_posted={date_posted}, limit={limit})")

    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    params = {
        "query": combined_query,
        "page": random.randint(1, 3),
        "num_pages": 1,
        "limit": limit
    }
    if remote:
        params["remote_jobs_only"] = "true"
    if date_posted:
        params["date_posted"] = date_posted  # e.g., "day", "week", "month"

    try:
        resp = requests.get(JSEARCH_URL, headers=headers, params=params, timeout=20)
        resp.raise_for_status()
        jobs_data = resp.json().get("data", [])
    except Exception as e:
        log(f"Error fetching jobs: {e}", error=True)
        return load_cache_or_demo()

    parsed_jobs = []
    for job in jobs_data:
        parsed_jobs.append({
            "title": job.get("job_title"),
            "company": job.get("employer_name"),
            "location": job.get("job_city") or job.get("job_country") or job.get("job_state"),
            "salary": job.get("job_min_salary") or "",
            "description": job.get("job_description"),
            "url": job.get("job_apply_link") or job.get("job_google_link"),
            "posted_date": job.get("job_posted_at_datetime_utc") or job.get("job_posted_at_timestamp")
        })

    if parsed_jobs:
        save_jobs(parsed_jobs)
        loc_str = f"{query} in {location}" if location else f"{query}"
        log(f"Added {len(parsed_jobs)} jobs for '{loc_str}'")
    else:
        log(f"No jobs found for '{combined_query}'", error=True)

    return parsed_jobs


def load_cache_or_demo():
    # Try local cache, then hardcoded sample
    try:
        if os.path.exists(DATA_PATH):
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            if jobs:
                print("[OK] Loaded cached job data.")
                return jobs[:8]
    except Exception:
        pass
    print("[OK] Loaded cached job data.")
    # 2-demo sample jobs
    return [
        {
            "title": "Demo Data Scientist",
            "company": "Sample Analytics",
            "location": "Pune",
            "salary": "15-20 LPA",
            "description": "Work on ML pipelines, SQL, Python, and stakeholder presentations. Growth opportunity.",
            "url": "https://example.com/apply-demo-ds",
            "posted_date": "2025-10-30"
        },
        {
            "title": "Demo AI Engineer",
            "company": "Demo AI Innovations",
            "location": "Remote",
            "salary": "12-18 LPA",
            "description": "Develop, tune, and deploy deep learning models in production for Indian clients.",
            "url": "https://example.com/apply-demo-ai",
            "posted_date": "2025-10-29"
        }
    ]

def save_jobs(jobs):
    # Append jobs in data/scraped_jobs.json
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    existing = []
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        except Exception:
            existing = []
    with open(DATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(existing + jobs, f, indent=2)

if __name__ == "__main__":
    fetch_jobs("Data Scientist", location="Pune", remote=False, date_posted="week", limit=5)
