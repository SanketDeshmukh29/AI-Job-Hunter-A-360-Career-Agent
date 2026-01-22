# AI Job Hunter: A 360° Career Agent

AI Job Hunter is a career automation platform powered by AI, designed to guide users through every stage of their job search. It provides:

- **Resume-based Job Recommendation**
- **AI Fit Analysis (Resume vs. Job Description Matching)**
- **Resume Enhancer**
- **Interview Trainer**

## Tech Stack
- **Frontend:** Streamlit
- **Backend:** Python
- **AI Engine:** Ollama (local LLM: llama3)
- **Job Data:** JSearch API via RapidAPI
- **Storage:** JSON files (no database)

## Folder Structure

```
AI_Job_Hunter/
├── app.py
├── scraper.py
├── ai_assistant.py
├── resume_parser.py
├── data/
├── assets/
├── .env
├── requirements.txt
```

## Run Project

1. **Start Ollama (Required for AI features!)**
   ```bash
   ollama serve
   ```
   - If you see the error:  
     `ollama : The term 'ollama' is not recognized ...`  
     → Download and install Ollama: https://ollama.com/download  
     → Ensure Ollama's install directory is in your PATH  
     → Restart your terminal!*  
     → Try `ollama --help` to confirm it works

2. **Run the app**
   ```bash
   streamlit run app.py
   ```

3. **Upload your resume and search jobs.**

4. **Click “Analyze My Fit”** for instant AI-powered job fit feedback!

---

**Debug steps and clarity have been added to the README.md as well as a troubleshooting section for common issues (e.g., PATH and Ollama not recognized on Windows).**  
Both `ollama serve` and `streamlit run app.py` can be run as background jobs; if you set up Ollama as described and have your virtual environment activated, you should have a seamless local run experience.

Let me know if you need onboarding screenshots, want to automate Ollama–model pulls, or have further debugging issues!
