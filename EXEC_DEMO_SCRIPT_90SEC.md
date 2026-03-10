## Plant Co — 90-Second Demo Script

**Headline:** Revenue Capture Ratio is our north-star metric for value realization.

"We built this full-potential cockpit for Plant Co to answer one question fast: **where are we losing value, and what actions recover it?**

**Tab 1 — Data Mapping & Ontology:**
Here, AI-style fuzzy mapping turns messy plant language into a clean ontology. We connect assets, tags, events, and work orders into one graph. On the right, we inspect any node, see linked tags and recent events, and audit mapping quality with accuracy metrics and export.

**Tab 2 — Generation View:**
This chart compares dispatch target, available capacity, and net generation. The red shaded area is the dispatch gap. We overlay outages and 5-minute misses, then correlate historian signals like ID fan speed, damper position, and furnace draft with net generation. This explains *where and why* dispatch misses happen—especially draft-control saturation windows.

**Tab 3 — Revenue View:**
Now we translate operations into economics. At the top is **Revenue Capture Ratio**, plus actual, potential, and total loss. We trend RCR over time, then drill from loss category into system, subsystem, and component to isolate the biggest value leaks and linked events/work orders.

**Tab 4 — GenAI Chatbot:**
Finally, the chatbot synthesizes docs and live KPI context into action-oriented recommendations with evidence citations. In mock mode it is always available; with an API key, we can switch to LLM RAG mode.

In short: one workflow from messy data to root-cause diagnosis to prioritized actions—with RCR as the headline outcome." 
# 90-second Executive Demo Script — Plant Co (Synthetic)

**Context (5–10s)**
"Plant Co is a fictional 2×660 MW coal plant. This demo shows how an AI 'Full Potential' platform finds lost revenue and operational actions using synthetic, internally consistent data."

## Tab 1 — Data Mapping (15–25s)
“First, the ontology: Plant→Unit→System→Subsystem→Component→Sensor. Maintenance and operations text is messy—‘IDF-A’, ‘draft fan #1’, ‘APH’. The GenAI fuzzy mapper links these raw terms to canonical assets and sensors, with hidden ground truth for evaluation. From a work order or alarm, we can trace to the affected component and the event window.”

## Tab 2 — Generation View (20–25s)
“Here’s Unit 1 at 5-minute settlement: Available MW, Dispatch Target, Net Generation, and Delta. You can see two deviation types:
1) technical derates/outages where availability collapses,
2) short 5-minute misses where the unit was available but still under-delivered.”

“Recurring narrative: unstable furnace draft—draft variance rises, dampers saturate, ID fan speed hunts—sometimes a false alarm, sometimes triggering forced reductions.”

## Tab 3 — Revenue View (20–25s)
“This is the headline: Revenue Capture Ratio compares actual (energy + capacity minus penalties and non-recoverable fuel overburn) vs max potential. We then rank lost revenue drivers and attribute losses to systems. In the demo, Boiler + Cooling + Turbine drive ~two-thirds of total losses. Post-intervention in Sep 2024, draft-related misses and aux-drift losses visibly improve.”

## Tab 4 — Chatbot (15–20s)
“Finally, the chatbot answers ‘Why is RCR below 95%?’ and ‘What’s the best ROI intervention?’ grounded in evidence: sensor trends, event logs, and text artifacts, plus the fictional ops manual and troubleshooting cards. It returns an action plan with estimated recoverable value.”
