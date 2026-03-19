from tools.llm_client import llm
import json

async def evaluator_node(state: dict) -> dict:
    """Scores resume against job description using Groq/Gemini."""

    prompt = f"""
You are an expert hiring manager. Compare this resume and job description carefully.

RESUME:
{state['resume_text'][:3000]}

JOB TITLE: {state['job_title']}
COMPANY: {state['company_name']}
JOB DESCRIPTION:
{state['job_description'][:2000]}

Return ONLY a valid JSON object, no extra text, no markdown:
{{
    "score": <integer 0-100>,
    "matched_skills": ["skill1", "skill2"],
    "missing_skills": ["skill1", "skill2"],
    "experience_match": true or false,
    "summary": "<one sentence explaining the score>"
}}
"""

    response = await llm.ainvoke(prompt)
    
    raw = response.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    
    result = json.loads(raw)

    state["match_score"]     = result["score"]
    state["gap_analysis"]    = result["summary"]
    state["missing_skills"]  = result.get("missing_skills", [])
    state["matched_skills"]  = result.get("matched_skills", [])

    print(f"\n✅ Match Score: {result['score']}/100")
    print(f"✅ Matched: {result['matched_skills']}")
    print(f"⚠️  Missing: {result['missing_skills']}")
    print(f"📝 {result['summary']}")

    return state