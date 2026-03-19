import asyncio
import os
import re
from datetime import datetime, timedelta
from jobspy import scrape_jobs
from tools.resume_parser import parse_resume
from tools.telegram_notifier import send_job_alert, send_daily_summary
from tools.job_tracker import is_already_processed, mark_job_processed
from graph import app
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────

MY_EXPERIENCE_YEARS = 2
MIN_MATCH_SCORE     = 75
LOCATION            = "India"
RESULTS_PER_SEARCH  = 20        # ← increased from 15 to 20
MAX_RETRIES         = 3

JOB_SEARCH_TERMS = [
    # DevOps focused
    "DevOps Engineer",
    "DevOps Engineer 2 years experience",
    "Junior DevOps Engineer",
    "Autonomy DevOps Engineer",
    "Entry Level DevOps Engineer",
    "DevOps Specialist",
    # SRE focused
    "Site Reliability Engineer",
    "SRE Engineer",
    # Cloud focused
    "Cloud Engineer",
    "AWS DevOps Engineer",
    "Azure DevOps Engineer",
    # CI/CD focused
    "CI CD Engineer",
    "Build Release Engineer",
    # Related roles
    "Platform Engineer",
    "Infrastructure Engineer",
    "Systems Engineer DevOps",
    "Build and Release Engineer",
]

# ── Experience filter ──────────────────────────────────────

def matches_experience(description: str, years: int) -> bool:
    """
    Returns True if job description matches candidate's
    experience level or doesn't mention experience at all.
    """
    if not description:
        return True

    desc_lower = description.lower()

    patterns = [
        r'(\d+)\s*\+\s*years?',
        r'(\d+)\s*-\s*(\d+)\s*years?',
        r'(\d+)\s*years?\s*of\s*exp',
        r'minimum\s*(\d+)\s*years?',
    ]

    for pattern in patterns:
        match = re.search(pattern, desc_lower)
        if match:
            req_years = int(match.group(1))
            max_years = int(match.group(2)) if len(match.groups()) > 1 \
                        and match.group(2) else req_years + 2

            if req_years <= years <= max_years + 1:
                return True
            if req_years > years + 1:
                return False

    return True


# ── Date filter ────────────────────────────────────────────

def is_posted_recently(job, hours: int = 24) -> bool:
    """Returns True if job was posted within the last X hours."""
    try:
        date_posted = job.get("date_posted")
        if date_posted is None:
            return True

        if hasattr(date_posted, 'hour'):
            posted_dt = date_posted
        else:
            posted_dt = datetime.combine(date_posted, datetime.min.time())

        cutoff = datetime.now() - timedelta(hours=hours)
        return posted_dt >= cutoff

    except Exception:
        return True


# ── Scraper with retry logic ───────────────────────────────

async def scrape_with_retry(search_term: str) -> object:
    """
    Scrapes LinkedIn jobs with simple retry logic.
    LinkedIn only — Indeed/Glassdoor unreliable for India.
    Waits 10s → 20s → 30s between retries.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"   🔄 Attempt {attempt}/{MAX_RETRIES}...")

            jobs = scrape_jobs(
                site_name=["linkedin"],   # ← LinkedIn only
                search_term=search_term,
                location=LOCATION,
                results_wanted=RESULTS_PER_SEARCH,
                hours_old=24
            )

            if jobs is not None and not jobs.empty:
                print(f"   ✅ Found {len(jobs)} jobs")
                return jobs
            else:
                print(f"   ⚠️  No results on attempt {attempt}")

        except Exception as e:
            print(f"   ❌ Attempt {attempt} failed: {str(e)[:80]}")

        # Wait before next retry (10s → 20s → 30s)
        if attempt < MAX_RETRIES:
            wait_time = attempt * 10
            print(f"   ⏳ Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)

    print(f"   ❌ All {MAX_RETRIES} attempts failed for: {search_term}")
    return None


# ── Main agent run ─────────────────────────────────────────

async def run_agent():
    """Runs the full job agent pipeline."""

    print(f"\n{'='*55}")
    print(f"🤖 LinkedIn Job Agent Started")
    print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"🎯 Experience filter: {MY_EXPERIENCE_YEARS} years")
    print(f"📊 Min match score:   {MIN_MATCH_SCORE}+")
    print(f"🔍 Search terms:      {len(JOB_SEARCH_TERMS)}")
    print(f"{'='*55}")

    # Parse resume once
    resume = parse_resume("data/resume.pdf")

    total_jobs     = 0
    filtered_jobs  = 0
    high_matches   = 0
    low_matches    = 0
    skipped_dupes  = 0
    failed_scrapes = 0

    for search_term in JOB_SEARCH_TERMS:
        print(f"\n🔍 Searching: {search_term} in {LOCATION}")

        # ── Scrape with retry ──────────────────────────────
        jobs = await scrape_with_retry(search_term)

        if jobs is None or jobs.empty:
            failed_scrapes += 1
            print(f"   ⚠️  Skipping — no results after {MAX_RETRIES} attempts")
            continue

        print(f"   ✅ Found {len(jobs)} jobs — applying filters...")

        for _, job in jobs.iterrows():
            total_jobs += 1

            title       = str(job.get("title", ""))
            company     = str(job.get("company", ""))
            description = str(job.get("description", ""))
            job_url     = str(job.get("job_url", ""))

            # ── Filter 1: Skip already processed jobs ──
            if is_already_processed(title, company):
                skipped_dupes += 1
                print(f"   ⏭️  Already processed: {title} @ {company}")
                continue

            # ── Filter 2: Posted in last 24 hours ──
            if not is_posted_recently(job, hours=24):
                print(f"   ⏭️  Skipping (too old): {title}")
                continue

            # ── Filter 3: Experience level match ──
            if not matches_experience(description, MY_EXPERIENCE_YEARS):
                print(f"   ⏭️  Skipping (exp mismatch): {title}")
                continue

            filtered_jobs += 1
            print(f"\n{'─'*50}")
            print(f"   📋 {title} @ {company}")

            # ── Build state ──
            state = {
                "job_url":            job_url,
                "job_title":          title,
                "company_name":       company,
                "job_description":    description,
                "required_skills":    [],
                "external_url":       job_url,
                "resume_text":        resume["full_text"],
                "resume_data":        resume,
                "resume_pdf_path":    "data/resume.pdf",
                "match_score":        0,
                "gap_analysis":       "",
                "missing_skills":     [],
                "matched_skills":     [],
                "cover_letter":       None,
                "apply_method":       None,
                "application_status": None,
                "feedback":           None,
            }

            # ── Run the graph ──
            try:
                result = await app.ainvoke(state)
                score  = result.get("match_score", 0)

                # Mark processed regardless of score
                mark_job_processed(title, company)

                if score >= MIN_MATCH_SCORE:
                    high_matches += 1
                    await send_job_alert(result)
                    print(f"   📱 Telegram alert sent!")
                else:
                    low_matches += 1
                    print(f"   🔴 Score too low ({score}) — skipping alert")

            except Exception as e:
                print(f"   ❌ Agent error: {e}")
                mark_job_processed(title, company)

            # Delay between jobs — keeps Groq rate limits happy
            await asyncio.sleep(20)

        # Delay between search terms
        await asyncio.sleep(10)

    # ── Final summary ──────────────────────────────────────
    print(f"\n{'='*55}")
    print(f"✅ Scan Complete!")
    print(f"   Total found:      {total_jobs}")
    print(f"   Skipped (dupes):  {skipped_dupes}")
    print(f"   Failed scrapes:   {failed_scrapes}")
    print(f"   After filters:    {filtered_jobs}")
    print(f"   High matches:     {high_matches}")
    print(f"   Low matches:      {low_matches}")
    print(f"{'='*55}")

    await send_daily_summary(filtered_jobs, high_matches, low_matches)


# ── Scheduler: runs every 6 hours ─────────────────────────

async def scheduler():
    """Runs the agent every 6 hours automatically."""
    while True:
        try:
            await run_agent()
        except Exception as e:
            print(f"❌ Scheduler error: {e}")

        next_run = datetime.now() + timedelta(hours=6)
        print(f"\n⏳ Next run at: {next_run.strftime('%H:%M')}")

        await asyncio.sleep(6 * 60 * 60)


# ── Entry point ────────────────────────────────────────────

if __name__ == "__main__":
    print("🚀 Starting LinkedIn Job Agent with scheduler...")
    print("   Press Ctrl+C to stop\n")
    asyncio.run(scheduler())