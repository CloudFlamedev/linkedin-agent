from tools.llm_client import llm

async def feedback_node(state: dict) -> dict:
    """Generates resume improvement suggestions for low match jobs."""

    prompt = f"""
You are a professional career coach. A candidate's resume scored {state['match_score']}/100 
for this job. Give specific, actionable advice to improve their resume for this role.

JOB TITLE: {state['job_title']}
COMPANY: {state['company_name']}
MISSING SKILLS: {state['gap_analysis']}

CURRENT RESUME:
{state['resume_text'][:2000]}

Provide feedback in this format:
1. TOP 3 SKILLS TO ADD: (specific skills missing from resume)
2. SECTIONS TO REWRITE: (which resume sections and exactly how)
3. KEYWORDS TO INCLUDE: (exact keywords from job description to add)
4. QUICK WINS: (small changes that immediately improve the score)

Be specific, not generic. Reference the actual job and resume content.
"""

    response = await llm.ainvoke(prompt)
    state["feedback"] = response.content
    state["application_status"] = "feedback_generated"

    print(f"\n💡 Feedback generated for: {state['job_title']}")
    print(state["feedback"][:500])

    return state