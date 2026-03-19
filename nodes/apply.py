'''import asyncio
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

# ── Helper: safe fill ──────────────────────────────────────

async def safe_fill(page, selector: str, value: str):
    """Fills a field only if it exists on the page."""
    try:
        el = await page.query_selector(selector)
        if el and value:
            await el.fill(value)
    except Exception:
        pass

# ── Helper: detect apply type ──────────────────────────────

async def detect_apply_type(page, job_url: str) -> str:
    """
    Visits the job page and detects what apply method is available.
    Returns: easy_apply | email_apply | external_form | manual_required
    """
    try:
        await page.goto(job_url, timeout=15000)
        await page.wait_for_timeout(3000)

        # Check Easy Apply button
        easy = await page.query_selector('button[aria-label*="Easy Apply"]')
        if easy:
            return "easy_apply"

        # Check external apply button
        ext = await page.query_selector('button[aria-label*="Apply"]')
        if ext:
            href = await page.evaluate(
                "el => el.closest('a')?.href || ''", ext
            )
            if "mailto:" in href:
                return "email_apply"
            if href:
                return "external_form"

    except Exception as e:
        print(f"   ⚠️  Detection error: {e}")

    return "manual_required"

# ── Easy Apply handler ─────────────────────────────────────

async def handle_easy_apply(page, state: dict) -> str:
    """Handles LinkedIn Easy Apply multi-step form."""
    try:
        # Click Easy Apply button
        btn = await page.query_selector('button[aria-label*="Easy Apply"]')
        if not btn:
            return "easy_apply_button_not_found"
        await btn.click()
        await page.wait_for_timeout(2000)

        # Handle up to 5 form steps
        for step in range(5):
            print(f"   📝 Easy Apply step {step + 1}")

            # Fill phone if field exists
            await safe_fill(page,
                'input[id*="phoneNumber"]',
                state["resume_data"].get("phone", "")
            )

            # Upload resume if file input exists
            file_inputs = await page.query_selector_all('input[type="file"]')
            for inp in file_inputs:
                await inp.set_input_files(state["resume_pdf_path"])
                await page.wait_for_timeout(1000)

            # Check for Submit button
            submit = await page.query_selector('button[aria-label*="Submit application"]')
            if submit:
                await submit.click()
                await page.wait_for_timeout(2000)
                print("   ✅ Easy Apply submitted!")
                return "submitted"

            # Click Next if available
            next_btn = await page.query_selector('button[aria-label*="Continue"]')
            if not next_btn:
                next_btn = await page.query_selector('button[aria-label*="Next"]')
            if next_btn:
                await next_btn.click()
                await page.wait_for_timeout(2000)
            else:
                break

        return "easy_apply_incomplete"

    except Exception as e:
        print(f"   ❌ Easy Apply error: {e}")
        return "easy_apply_failed"

# ── External form handler ──────────────────────────────────

async def handle_external_form(page, state: dict, external_url: str) -> str:
    """Handles external company website application forms."""
    try:
        await page.goto(external_url, timeout=15000)
        await page.wait_for_timeout(3000)

        resume_data = state["resume_data"]

        # Fill common fields
        await safe_fill(page, '[name*="name"],[id*="name"]',
                        resume_data.get("name", ""))
        await safe_fill(page, '[name*="email"],[id*="email"]',
                        resume_data.get("email", ""))
        await safe_fill(page, '[name*="phone"],[id*="phone"]',
                        resume_data.get("phone", ""))

        # Fill cover letter field if exists
        if state.get("cover_letter"):
            await safe_fill(page,
                'textarea[name*="cover"],[id*="cover"],[name*="message"]',
                state["cover_letter"]
            )

        # Upload resume
        file_inputs = await page.query_selector_all('input[type="file"]')
        for inp in file_inputs:
            try:
                await inp.set_input_files(state["resume_pdf_path"])
                await page.wait_for_timeout(1000)
            except Exception:
                pass

        # Try to find and click submit
        submit = await page.query_selector(
            'button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Apply")'
        )
        if submit:
            await submit.click()
            await page.wait_for_timeout(3000)
            print("   ✅ External form submitted!")
            return "submitted"

        return "external_form_no_submit_found"

    except Exception as e:
        print(f"   ❌ External form error: {e}")
        return "external_form_failed"

# ── Email Apply handler ────────────────────────────────────

async def handle_email_apply(state: dict, email_address: str) -> str:
    """Sends application email with resume + cover letter attached."""
    try:
        msg = MIMEMultipart()
        msg["From"]     = os.getenv("MY_EMAIL")
        msg["To"]       = email_address
        msg["Subject"]  = (
            f"Application for {state['job_title']} "
            f"— {state['resume_data'].get('name', 'Candidate')}"
        )

        # Email body = cover letter or default message
        body = state.get("cover_letter") or (
            f"Dear Hiring Team,\n\n"
            f"Please find my resume attached for the "
            f"{state['job_title']} position at {state['company_name']}.\n\n"
            f"Best regards,\n"
            f"{state['resume_data'].get('name', '')}"
        )
        msg.attach(MIMEText(body, "plain"))

        # Attach resume PDF
        resume_path = state.get("resume_pdf_path", "data/resume.pdf")
        if os.path.exists(resume_path):
            with open(resume_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    'attachment; filename="Resume.pdf"'
                )
                msg.attach(part)

        # Send via Gmail SMTP
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(
                os.getenv("MY_EMAIL"),
                os.getenv("EMAIL_APP_PASSWORD")
            )
            server.send_message(msg)

        print(f"   ✅ Email sent to {email_address}!")
        return "email_sent"

    except Exception as e:
        print(f"   ❌ Email error: {e}")
        return "email_failed"

# ── Main Apply Node ────────────────────────────────────────

async def apply_node(state: dict) -> dict:
    """
    Master apply node — detects method and routes accordingly.
    Handles: Easy Apply, External Form, Email Apply.
    """

    job_url = state.get("job_url", "")
    print(f"\n🚀 Starting application for: {state['job_title']} @ {state['company_name']}")

    async with async_playwright() as p:
        # Launch browser (headless=False so you can watch it work)
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            # Step 1 — Detect apply type
            print("   🔍 Detecting apply method...")
            apply_type = await detect_apply_type(page, job_url)
            state["apply_method"] = apply_type
            print(f"   📌 Method detected: {apply_type}")

            # Step 2 — Route to correct handler
            if apply_type == "easy_apply":
                status = await handle_easy_apply(page, state)

            elif apply_type == "external_form":
                ext_url = state.get("external_url", job_url)
                status  = await handle_external_form(page, state, ext_url)

            elif apply_type == "email_apply":
                ext_url   = state.get("external_url", "")
                email_addr = ext_url.replace("mailto:", "").split("?")[0]
                status    = await handle_email_apply(state, email_addr)

            else:
                print("   ⚠️  No automated apply available — manual required")
                status = "manual_required"

        except Exception as e:
            print(f"   ❌ Apply node error: {e}")
            status = "failed"

        finally:
            await browser.close()

    state["application_status"] = status
    return state '''