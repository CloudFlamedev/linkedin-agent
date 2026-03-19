from tools.llm_client import llm

async def cover_letter_node(state: dict) -> dict:
    """Generates tailored cover letter for high match jobs."""

    prompt = f"""
Write a professional cover letter for this job application.

Candidate Name: {state['resume_data'].get('name', 'Candidate')}
Job Title: {state['job_title']}
Company: {state['company_name']}
Required Skills: {state['required_skills']}
Resume Summary: {state['resume_text'][:2000]}

Rules:
- Exactly 3 paragraphs
- Max 250 words
- Professional but human tone
- Paragraph 1: strong opening mentioning the specific role
- Paragraph 2: map 2-3 resume achievements to job requirements
- Paragraph 3: confident closing with call to action
- Do NOT use generic filler phrases like "I am writing to express my interest"
"""

    response = await llm.ainvoke(prompt)
    state["cover_letter"]        = response.content
    state["application_status"]  = "cover_letter_ready"  # ← fixes None status

    print(f"\n📄 Cover letter generated ({len(response.content)} chars)")
    return state