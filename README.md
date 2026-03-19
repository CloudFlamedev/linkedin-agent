# LinkedIn Job Agent 🤖

An autonomous AI-powered job application agent built with 
Python, LangGraph, and Gemini/Groq LLM.

## Features
- Scrapes LinkedIn for jobs matching your profile
- Scores resume vs job description using AI
- Filters by experience level and last 24 hours
- Generates tailored cover letters automatically
- Sends instant Telegram alerts for high matches
- Deduplication — never alerts same job twice
- Runs automatically every 6 hours

## Tech Stack
- Python 3.12
- LangGraph + LangChain
- Gemini / Groq (free LLM APIs)
- JobSpy (LinkedIn scraper)
- Playwright (browser automation)
- SQLite (logging)
- Telegram Bot API

## Project Structure
linkedin-agent/
├── data/           # Resume PDF (not uploaded)
├── logs/           # SQLite database (not uploaded)
├── nodes/          # LangGraph nodes
│   ├── evaluator.py
│   ├── cover_letter.py
│   ├── feedback.py
│   └── logger.py
├── tools/          # Helper utilities
│   ├── llm_client.py
│   ├── resume_parser.py
│   ├── telegram_notifier.py
│   └── job_tracker.py
├── graph.py        # LangGraph workflow
├── state.py        # Agent state schema
├── main.py         # Entry point + scheduler
└── .env.example    # Environment variables template

## Setup
1. Clone the repo
2. Create virtual environment: python3 -m venv venv
3. Activate: source venv/bin/activate
4. Install: pip install -r requirements.txt
5. Copy .env.example to .env and fill credentials
6. Add resume.pdf to data/ folder
7. Run: python3 main.py

## Environment Variables
See .env.example for required variables.
# linkedin-agent
