from langgraph.graph import StateGraph, END
from state import AgentState
from nodes.evaluator import evaluator_node
from nodes.cover_letter import cover_letter_node
from nodes.feedback import feedback_node
from nodes.logger import logger_node

# ── Routing ────────────────────────────────────────────────

def score_router(state: dict) -> str:
    """Routes based on match score AND experience match."""
    
    # Skip if experience doesn't match
    if not state.get("experience_match", True):
        print(f"\n⛔ Experience mismatch — routing to logger only")
        return "skip"

    score = state.get("match_score", 0)
    if score >= 70:
        print(f"\n🟢 Score {score}/100 → Generating cover letter")
        return "high"
    else:
        print(f"\n🔴 Score {score}/100 → Generating feedback")
        return "low"

# ── Graph ──────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("evaluator",    evaluator_node)
    graph.add_node("cover_letter", cover_letter_node)
    graph.add_node("feedback",     feedback_node)
    graph.add_node("logger",       logger_node)

    graph.set_entry_point("evaluator")

    # Route based on score AND experience
    graph.add_conditional_edges("evaluator", score_router, {
        "high": "cover_letter",
        "low":  "feedback",
        "skip": "logger"       # ← experience mismatch goes straight to logger
    })

    graph.add_edge("cover_letter", "logger")
    graph.add_edge("feedback",     "logger")
    graph.add_edge("logger",       END)

    return graph.compile()

app = build_graph()