"""Test the enhanced chatbot mock responses."""
from utils.chat import build_mock_response, RetrievedChunk

# Mock context
context = [
    RetrievedChunk("ops_manual.md", "Draft Control", "Prioritize stability over aggressive chasing during draft instability.", 0.85),
    RetrievedChunk("troubleshooting_cards.md", "Draft Variance", "IF draft variance↑ AND damper>95% THEN reduce ramp", 0.78),
]

# Mock KPIs
kpis = {
    "dispatch_miss_mwh": 845.3,
    "rcr": 0.978,
    "top_loss_driver": "Efficiency",
    "top_component": "ID Fan / Dampers",
    "heat_rate_dev_pct": 2.3,
    "event_count": 12,
}

questions = [
    "Summarize the last 30 days of plant performance. What are the key trends in dispatch misses and revenue capture?",
    "What are the top 3 actions we should take to improve revenue capture ratio? Prioritize by expected financial impact.",
    "Explain why our net station heat rate is deviating from the PPA reference. What are the likely root causes and how do we address them?",
]

print("=" * 80)
for i, q in enumerate(questions, 1):
    print(f"\nQUESTION {i}: {q}\n")
    response = build_mock_response(q, context, kpis)
    print(response)
    print("\n" + "=" * 80)
