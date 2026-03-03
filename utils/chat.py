"""Retrieval-based chatbot with mock and optional OpenAI modes."""

from __future__ import annotations

import os
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class RetrievedChunk:
    source: str
    section: str
    text: str
    score: float


def split_markdown_sections(text: str, source: str) -> list[dict[str, str]]:
    """Split markdown into heading-aware chunks."""
    lines = text.splitlines()
    chunks: list[dict[str, str]] = []
    current_heading = "Overview"
    current_lines: list[str] = []

    heading_pattern = re.compile(r"^#{1,4}\s+(.+)$")
    for line in lines:
        match = heading_pattern.match(line.strip())
        if match:
            if current_lines:
                chunks.append(
                    {
                        "source": source,
                        "section": current_heading,
                        "text": "\n".join(current_lines).strip(),
                    }
                )
            current_heading = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        chunks.append({"source": source, "section": current_heading, "text": "\n".join(current_lines).strip()})

    return [c for c in chunks if c["text"]]


def build_data_context_snippets(
    dispatch_df: pd.DataFrame,
    attribution_df: pd.DataFrame,
    revenue_monthly_df: pd.DataFrame,
) -> list[dict[str, str]]:
    """Create deterministic snippets from selected context."""
    snippets: list[dict[str, str]] = []

    if not dispatch_df.empty:
        d = dispatch_df.copy()
        if "delta_mw" in d.columns:
            d["delta_mw"] = pd.to_numeric(d["delta_mw"], errors="coerce").fillna(0)
            top = d.sort_values("delta_mw", ascending=False).head(5)
            text = "\n".join(
                [
                    f"{row.get('timestamp')}: delta_mw={row.get('delta_mw'):.2f}, root_cause={row.get('root_cause_category', 'n/a')}"
                    for _, row in top.iterrows()
                ]
            )
            snippets.append(
                {
                    "source": "generated_context",
                    "section": "Top dispatch deviation windows",
                    "text": text,
                }
            )

    if not attribution_df.empty:
        a = attribution_df.copy()
        a["loss_usd"] = pd.to_numeric(a.get("loss_usd", 0), errors="coerce").fillna(0)
        top_components = a.groupby("component")["loss_usd"].sum().sort_values(ascending=False).head(5)
        snippets.append(
            {
                "source": "generated_context",
                "section": "Top components by loss",
                "text": "\n".join([f"{comp}: ${val:,.0f}" for comp, val in top_components.items()]),
            }
        )

    if not revenue_monthly_df.empty and "revenue_capture_ratio" in revenue_monthly_df.columns:
        m = revenue_monthly_df.copy()
        m["month"] = pd.to_datetime(m.get("month"), errors="coerce", utc=True)
        latest = m.sort_values("month").tail(3)
        snippets.append(
            {
                "source": "generated_context",
                "section": "Recent RCR trend",
                "text": "\n".join([f"{row['month'].date()}: RCR={row['revenue_capture_ratio']:.2%}" for _, row in latest.iterrows()]),
            }
        )

    return snippets


class RetrievalIndex:
    """Supports TF-IDF retrieval with optional sentence-transformers fallback."""

    def __init__(self, chunks: list[dict[str, str]]) -> None:
        self.chunks = chunks
        self.texts = [c["text"] for c in chunks]
        self.meta = [(c["source"], c["section"]) for c in chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(self.texts) if self.texts else None

        self.embedder = None
        self.embeddings = None
        self._init_sentence_transformers_if_available()

    def _init_sentence_transformers_if_available(self) -> None:
        try:
            # Suppress PyTorch warnings during optional import
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=UserWarning)
                warnings.filterwarnings("ignore", message=".*torch.classes.*")
                from sentence_transformers import SentenceTransformer

                self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
                self.embeddings = self.embedder.encode(self.texts, normalize_embeddings=True)
        except Exception:
            # Fallback to TF-IDF retrieval
            self.embedder = None
            self.embeddings = None

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        if not query.strip() or not self.texts:
            return []

        scores: np.ndarray
        if self.embedder is not None and self.embeddings is not None:
            q = self.embedder.encode([query], normalize_embeddings=True)[0]
            scores = np.dot(self.embeddings, q)
        else:
            qv = self.vectorizer.transform([query])
            sims = cosine_similarity(qv, self.matrix).flatten()
            scores = sims

        idx = np.argsort(scores)[::-1][:top_k]
        out: list[RetrievedChunk] = []
        for i in idx:
            src, sec = self.meta[i]
            out.append(RetrievedChunk(source=src, section=sec, text=self.texts[i], score=float(scores[i])))
        return out


def build_retrieval_index(docs_dir: Path, extra_snippets: list[dict[str, str]]) -> RetrievalIndex:
    """Build retrieval index from docs and generated snippets."""
    chunks: list[dict[str, str]] = []

    for name in ["ops_manual.md", "troubleshooting_cards.md", "glossary.md"]:
        path = docs_dir / name
        if not path.exists():
            continue
        try:
            chunks.extend(split_markdown_sections(path.read_text(encoding="utf-8"), source=name))
        except OSError:
            continue

    chunks.extend(extra_snippets)
    if not chunks:
        chunks = [
            {
                "source": "fallback",
                "section": "General",
                "text": "No documentation found. Use data trends to estimate likely operational constraints.",
            }
        ]
    return RetrievalIndex(chunks)


def build_mock_response(question: str, context: list[RetrievedChunk], kpis: dict[str, Any]) -> str:
    """Generate realistic mock response with citations and context-aware detail. Longer, more structured."""
    citations = [f"- {c.source} :: {c.section}" for c in context[:3]]
    dispatch_miss = float(kpis.get("dispatch_miss_mwh", 0.0))
    rcr = float(kpis.get("rcr", float("nan")))
    top_driver = str(kpis.get("top_loss_driver", "Unknown"))
    heat_dev = float(kpis.get("heat_rate_dev_pct", 0.0))
    top_component = str(kpis.get("top_component", "ID Fan / Dampers"))
    
    q_lower = question.lower()
    
    # Pattern-match question type for more natural responses
    if "summarize" in q_lower or "summary" in q_lower or "last" in q_lower:
        return (
            f"## Executive Summary: Recent Performance\n\n"
            f"### Key Metrics (Selected Period)\n"
            f"- **Revenue Capture Ratio**: {rcr:.1%}\n"
            f"- **Dispatch Gap**: {dispatch_miss:,.0f} MWh\n"
            f"- **Primary Loss Driver**: {top_driver}\n"
            f"- **Top Loss Component**: {top_component}\n"
            f"- **Heat Rate Deviation**: {heat_dev:.1f}% above PPA reference\n\n"
            f"### Performance Trends\n\n"
            f"Over the selected period, the plant achieved a **Revenue Capture Ratio of {rcr:.1%}**, "
            f"missing approximately **{dispatch_miss:,.0f} MWh** of dispatch targets. This translates to an estimated "
            f"**${dispatch_miss * 45:,.0f}** in forgone revenue at current market rates.\n\n"
            f"The primary loss driver is **{top_driver}**, accounting for the largest share of forgone revenue. "
            f"Within this category, **{top_component}** emerges as the top contributor, with recurring issues indicating "
            f"a systemic constraint rather than isolated operational errors.\n\n"
            f"**Heat Rate Performance**: Net station heat rate deviated **{heat_dev:.1f}% above PPA reference**, "
            f"indicating efficiency losses likely tied to {top_component.lower()} constraints and auxiliary load drift. "
            f"This inefficiency compounds revenue impact by increasing fuel costs per MWh generated.\n\n"
            f"### Root Cause Hypotheses\n\n"
            f"1. **Draft Control Instability** (High Confidence)\n"
            f"   - ID fan hunting and damper saturation (>98%) correlate strongly with 5-min dispatch misses\n"
            f"   - Unstable furnace pressure forces operators to cap load for boiler protection\n"
            f"   - Pattern repeats across multiple events, suggesting PID tuning or mechanical binding issues\n\n"
            f"2. **Auxiliary Load Creep** (Medium Confidence)\n"
            f"   - Elevated auxiliary consumption reduces net generation capacity\n"
            f"   - Likely culprits: condenser cooling tower performance degradation, circulating water pump inefficiency\n"
            f"   - Heat rate deviation supports this hypothesis\n\n"
            f"3. **Reactive Maintenance Cycle** (Medium Confidence)\n"
            f"   - Event clustering suggests chronic issues rather than random failures\n"
            f"   - Work order patterns show repeat interventions on same components\n"
            f"   - Transition to predictive maintenance could break this cycle\n\n"
            f"### Recommended Actions\n\n"
            f"**Immediate (Current Shift)**:\n"
            f"- Verify draft pressure transmitter calibration\n"
            f"- Inspect ID fan damper linkage for mechanical binding or wear\n"
            f"- Monitor furnace draft stability during ramp events\n\n"
            f"**Next Shift**:\n"
            f"- Retune ID fan PID loops to reduce hunting behavior\n"
            f"- Adjust damper response curves to avoid saturation region (98-100% open)\n"
            f"- Trend auxiliary load components to identify degraded equipment\n\n"
            f"**Next Planned Outage**:\n"
            f"- Deep inspection of {top_component} for wear, corrosion, or fouling\n"
            f"- Condenser tube cleaning and backpressure optimization\n"
            f"- Upgrade draft control instrumentation if transmitters are aged\n\n"
            f"### Expected Impact\n\n"
            f"- **RCR Improvement**: 0.5-0.8 percentage points (~${dispatch_miss * 18:,.0f} annually)\n"
            f"- **Heat Rate Recovery**: 80-120 Btu/kWh improvement (~${dispatch_miss * 8:,.0f} fuel savings)\n"
            f"- **Availability**: Reduced forced derates extend availability by 0.3-0.5% annually\n\n"
            f"---\n\n"
            f"**Evidence Sources**:\n" + "\n".join(citations)
        )
    
    elif "action" in q_lower or "improve" in q_lower or "recommend" in q_lower:
        return (
            f"## Prioritized Action Plan: Improve Revenue Capture\n\n"
            f"Based on analysis of the selected period (RCR: {rcr:.1%}, estimated revenue loss: ~${dispatch_miss * 45:,.0f}), "
            f"here are prioritized interventions ranked by expected financial impact:\n\n"
            f"---\n\n"
            f"### 1. **Optimize Draft Control System** 🔴 HIGHEST IMPACT\n\n"
            f"**What**: Retune ID fan PID loops and damper response curves to reduce hunting behavior and eliminate saturation conditions\n\n"
            f"**Why**: {top_component} is the top loss component across the selected period. Analysis shows:\n"
            f"- Damper saturation (>98% open) correlates strongly with dispatch misses\n"
            f"- ID fan speed variance exceeds normal operational bounds during ramp events\n"
            f"- Furnace draft instability forces operators to cap load for safety\n\n"
            f"**How** (Step-by-Step):\n"
            f"1. Verify DP transmitter calibration (zero and span checks)\n"
            f"2. Inspect damper linkage for mechanical binding, corrosion, or actuator wear\n"
            f"3. Retune PID loops: reduce integral gain to dampen hunting, adjust proportional band\n"
            f"4. Shift damper bias setpoint to operate in 60-85% range (avoid saturation)\n"
            f"5. Test during controlled ramp to verify stable response\n\n"
            f"**Expected Value**:\n"
            f"- Reducing draft-related misses by 30% could recover **0.5-0.8 RCR points**\n"
            f"- Financial impact: **~${dispatch_miss * 15:,.0f} annually** in recovered revenue\n"
            f"- Additional benefit: Reduced thermal stress on boiler extends equipment life\n\n"
            f"---\n\n"
            f"### 2. **Address Auxiliary Load Drift** 🟠 HIGH IMPACT\n\n"
            f"**What**: Inspect and optimize condenser cooling system and feedwater heater performance to reduce parasitic losses\n\n"
            f"**Why**: Heat rate deviation of **{heat_dev:.1f}%** suggests excess auxiliary consumption degrading net output. "
            f"Key indicators:\n"
            f"- Auxiliary load trending **{heat_dev * 2:.1f}% above baseline**\n"
            f"- Condenser backpressure likely elevated (trending data recommended)\n"
            f"- Cooling tower fan efficiency may be degraded\n\n"
            f"**How** (Step-by-Step):\n"
            f"1. Trend condenser backpressure and compare to design curves\n"
            f"2. Inspect cooling tower fill for fouling or physical damage\n"
            f"3. Measure circulating water pump flow and compare to nameplate\n"
            f"4. Check feedwater heater performance (terminal temperature difference)\n"
            f"5. Clean condenser tubes if backpressure is elevated\n\n"
            f"**Expected Value**:\n"
            f"- Returning aux load to baseline can improve heat rate by **80-120 Btu/kWh**\n"
            f"- Financial impact: **~${dispatch_miss * 8:,.0f} annually** in reduced fuel costs\n"
            f"- Net generation increase: **2-4 MW** additional capacity during peak demand\n\n"
            f"---\n\n"
            f"### 3. **Proactive Maintenance Scheduling** 🟡 MEDIUM IMPACT\n\n"
            f"**What**: Transition from reactive to predictive maintenance on chronic failure components\n\n"
            f"**Why**: Event clustering analysis shows:\n"
            f"- Work orders repeat on same components (ID fans, dampers, pumps)\n"
            f"- Forced derates occur more frequently than industry benchmarks\n"
            f"- Reactive repairs extend outage duration vs. planned interventions\n\n"
            f"**How** (Step-by-Step):\n"
            f"1. Identify top 5 repeat failure components from work order history\n"
            f"2. Schedule inspections during next planned outage window\n"
            f"3. Pre-procure critical spares to avoid expedited shipping costs\n"
            f"4. Implement vibration monitoring on rotating equipment (ID fans, pumps)\n"
            f"5. Shift maintenance schedule from time-based to condition-based\n\n"
            f"**Expected Value**:\n"
            f"- Preventing forced derates extends availability by **0.3-0.5% annually**\n"
            f"- Financial impact: **~${dispatch_miss * 5:,.0f} annually** in avoided forced outages\n"
            f"- Maintenance cost reduction: 15-20% lower spend by avoiding emergency repairs\n\n"
            f"---\n\n"
            f"### Summary of Total Impact\n\n"
            f"| Action | RCR Improvement | Annual Value | Effort |\n"
            f"|--------|----------------|--------------|--------|\n"
            f"| Draft Control Tuning | 0.5-0.8% | ${dispatch_miss * 15:,.0f} | Medium |\n"
            f"| Aux Load Optimization | 0.3-0.5% | ${dispatch_miss * 8:,.0f} | Medium |\n"
            f"| Proactive Maintenance | 0.2-0.3% | ${dispatch_miss * 5:,.0f} | Low |\n"
            f"| **TOTAL** | **1.0-1.6%** | **~${dispatch_miss * 28:,.0f}** | - |\n\n"
            f"**Critical Path**: Execute Actions 1 and 2 in parallel to maximize near-term impact. "
            f"Action 3 provides long-term reliability benefits.\n\n"
            f"---\n\n"
            f"**Supporting Evidence**:\n" + "\n".join(citations)
        )
    
    elif "outage" in q_lower or "event" in q_lower or "explain" in q_lower:
        return (
            f"## Event Analysis & Root Cause Investigation\n\n"
            f"### Event Pattern Overview\n\n"
            f"The referenced events appear to be part of a **recurring pattern** tied to {top_driver.lower()} constraints. "
            f"Based on historical data across the selected period:\n\n"
            f"**Typical Event Profile**:\n"
            f"- **Frequency**: Multiple occurrences per month\n"
            f"- **Duration**: 15-60 minutes per episode\n"
            f"- **Impact**: Average {dispatch_miss / max(1, kpis.get('event_count', 5)):.0f} MWh lost generation per event\n"
            f"- **Financial**: ~${(dispatch_miss / max(1, kpis.get('event_count', 5))) * 45:,.0f} per event at current rates\n\n"
            f"Over the selected period, draft-related events contributed approximately **{max(0.1, rcr * 100 - 96):.1f} RCR points** "
            f"of underperformance.\n\n"
            f"---\n\n"
            f"### Root Cause: Draft Control Instability\n\n"
            f"**Primary Failure Mode**: ID fan speed variance + damper saturation → unstable furnace pressure → operator load limiting\n\n"
            f"**Physical Mechanism**:\n"
            f"1. Grid dispatch request triggers load ramp (target MW increase)\n"
            f"2. Boiler master controller increases firing rate to meet steam demand\n"
            f"3. ID fan accelerates to maintain furnace draft setpoint (-0.5 to -1.5 inH2O)\n"
            f"4. ID fan damper opens to 98-100% (saturation)\n"
            f"5. Fan reaches speed limit but cannot maintain draft setpoint\n"
            f"6. Furnace pressure becomes unstable (oscillations or positive spikes)\n"
            f"7. Operators manually reduce firing rate to restore draft stability\n"
            f"8. Net generation falls below dispatch target → miss recorded\n"
            f"9. Cycle repeats until draft settles (often 20-40 minutes)\n\n"
            f"**Equipment-Level Indicators** (from event correlation):\n"
            f"- ID fan speed: 95-100% during events (mechanical limit)\n"
            f"- Damper position: 98-100% (control saturation)\n"
            f"- Draft pressure variance: 2-3x normal during events\n"
            f"- Furnace exit gas temp: Elevated 20-40°F (incomplete combustion signature)\n\n"
            f"---\n\n"
            f"### Contributing Factors\n\n"
            f"**1. Design Margin Erosion**\n"
            f"- Original ID fan sizing assumed cleaner coal (lower particulate loading)\n"
            f"- Current fuel quality may have higher ash content → increased fan duty\n"
            f"- Air heater fouling reduces available draft\n\n"
            f"**2. Control System Limitations**\n"
            f"- PID tuning optimized for steady-state, not ramp events\n"
            f"- Damper actuator response lag (~5-8 seconds) causes overshoot\n"
            f"- No feedforward compensation for rapid load changes\n\n"
            f"**3. Mechanical Degradation** (Possible)\n"
            f"- Damper linkage binding or corrosion reducing effective travel\n"
            f"- Fan blade erosion reducing efficiency at high speeds\n"
            f"- DP transmitter drift causing incorrect setpoint tracking\n\n"
            f"---\n\n"
            f"### Corrective Pathway (Short to Long Term)\n\n"
            f"**Phase 1: Immediate Stabilization** (0-2 weeks)\n"
            f"- Verify DP transmitter calibration\n"
            f"- Inspect damper linkage for mechanical issues\n"
            f"- Adjust draft setpoint bias to give more margin (e.g., -1.2 → -0.8 inH2O if safe)\n\n"
            f"**Phase 2: Control Optimization** (2-8 weeks)\n"
            f"- Retune ID fan PID loops (reduce integral gain, widen proportional band)\n"
            f"- Implement damper position limiting (prevent >95% saturation)\n"
            f"- Add feedforward control for load ramp events\n\n"
            f"**Phase 3: Equipment Upgrade** (Next outage)\n"
            f"- Replace degraded damper actuators if mechanical binding confirmed\n"
            f"- Clean air heater if fouling is significant\n"
            f"- Consider VFD upgrade for finer fan speed control (if fixed-speed currently)\n\n"
            f"---\n\n"
            f"### Validation Metrics\n\n"
            f"Track these KPIs to confirm corrective actions are effective:\n"
            f"- **Draft pressure variance**: Target <0.3 inH2O during ramps (currently 0.8-1.2)\n"
            f"- **Damper saturation events**: Target <2 per week (currently 8-12)\n"
            f"- **5-min dispatch misses**: Target 50% reduction month-over-month\n"
            f"- **RCR improvement**: Target +0.5% within 60 days\n\n"
            f"---\n\n"
            f"**Evidence Sources**:\n" + "\n".join(citations)
        )
    
    elif "heat rate" in q_lower or "efficiency" in q_lower or "nshr" in q_lower:
        return (
            f"## Heat Rate & Efficiency Deep Dive\n\n"
            f"### Current Performance\n\n"
            f"Net Station Heat Rate (NSHR) is deviating **{heat_dev:.1f}% above PPA reference**, "
            f"indicating the plant is consuming more fuel per MWh of net generation than contracted. "
            f"This inefficiency has direct financial consequences and compounds revenue losses.\n\n"
            f"**Baseline Comparison**:\n"
            f"- **Actual NSHR**: Trending {heat_dev:.1f}% above reference\n"
            f"- **Fuel Cost Impact**: ~${heat_dev * 12000:,.0f}/month in excess fuel expense\n"
            f"- **Efficiency Loss**: Equivalent to operating at {100 - heat_dev:.1f}% of design thermal efficiency\n\n"
            f"---\n\n"
            f"### Root Cause Analysis\n\n"
            f"**Primary Drivers** (ranked by contribution):\n\n"
            f"**1. Auxiliary Load Creep** (40-50% of deviation)\n"
            f"- Elevated auxiliary consumption reduces net output while maintaining fuel input\n"
            f"- Condenser circulating water pumps, cooling tower fans, and feedwater pumps are key culprits\n"
            f"- Typical signature: Gross generation stable, net generation declining\n\n"
            f"**2. {top_driver} Constraints** (30-40% of deviation)\n"
            f"- System inefficiencies force operational derates, pushing unit into less-efficient load ranges\n"
            f"- Part-load operation increases heat rate due to turbine curve characteristics\n"
            f"- {top_component} issues prevent operating at optimal efficiency point\n\n"
            f"**3. Cycling and Restart Penalties** (10-20% of deviation)\n"
            f"- Frequent restarts or deep load swings increase heat rate during stabilization\n"
            f"- Typical penalty: 200-400 Btu/kWh for 2-4 hours post-restart\n"
            f"- Thermal cycling reduces boiler efficiency until steady-state is reached\n\n"
            f"**4. Equipment Degradation** (5-10% of deviation)\n"
            f"- Condenser tube fouling elevates backpressure → turbine efficiency loss\n"
            f"- Air heater fouling reduces combustion air preheat → boiler efficiency loss\n"
            f"- Turbine blade erosion or deposits reduce stage efficiency\n\n"
            f"---\n\n"
            f"### Diagnostic Pathway\n\n"
            f"**Step 1: Auxiliary Load Analysis**\n"
            f"1. Compare actual vs design auxiliary load curves at multiple load points\n"
            f"2. Identify which components are consuming excess power:\n"
            f"   - Condenser circulating water pumps (check flow vs. design)\n"
            f"   - Cooling tower fans (verify VFD operation, blade pitch)\n"
            f"   - Feedwater pumps (check recirculation valve position)\n"
            f"   - Coal handling / pulverizers (verify mill loading distribution)\n"
            f"3. Trend auxiliary load over time to detect degradation patterns\n\n"
            f"**Step 2: Condenser Performance**\n"
            f"1. Trend condenser backpressure vs. cooling water temperature\n"
            f"2. Compare to design heat rejection curves\n"
            f"3. Calculate cleanliness factor (should be >85%)\n"
            f"4. If degraded, schedule condenser tube cleaning\n\n"
            f"**Step 3: Boiler Efficiency**\n"
            f"1. Audit mill performance: coal fineness (70-75% through 200 mesh)\n"
            f"2. Check primary air flow distribution across mills\n"
            f"3. Review soot blowing effectiveness (furnace exit gas temp pattern)\n"
            f"4. Inspect air heater leakage (measure O2 differential across AH)\n\n"
            f"**Step 4: Turbine Path Audit**\n"
            f"1. Review HP/IP/LP turbine stage efficiency (if instrumentation available)\n"
            f"2. Check for extraction steam flow abnormalities\n"
            f"3. Verify feedwater heater terminal temperature differences\n"
            f"4. Look for signs of blade deposits or erosion in vibration data\n\n"
            f"---\n\n"
            f"### Corrective Actions (Prioritized)\n\n"
            f"**High Priority** (0-4 weeks):\n"
            f"- Optimize auxiliary load: reduce condenser pump speed if allowed, verify cooling tower fan VFD operation\n"
            f"- Clean condenser tubes if backpressure is elevated (>2 inHg above design)\n"
            f"- Retune draft control to allow operating at optimal load point (addresses {top_driver} constraints)\n\n"
            f"**Medium Priority** (4-12 weeks):\n"
            f"- Inspect and clean air heater if O2 leakage >1.5%\n"
            f"- Audit mill performance and rebalance coal flow distribution\n"
            f"- Implement soot blowing optimization (automated vs. time-based)\n\n"
            f"**Low Priority** (Next outage):\n"
            f"- Turbine blade inspection and water wash if deposits suspected\n"
            f"- Feedwater heater tube inspection (look for plugging or bypassing)\n"
            f"- Upgrade cooling tower fill if severely fouled\n\n"
            f"---\n\n"
            f"### Expected Recovery\n\n"
            f"Based on typical performance improvements:\n\n"
            f"| Action | Heat Rate Improvement | Fuel Savings |\n"
            f"|--------|----------------------|-------------|\n"
            f"| Aux Load Optimization | 60-100 Btu/kWh | ${dispatch_miss * 5:,.0f}/year |\n"
            f"| Condenser Cleaning | 40-80 Btu/kWh | ${dispatch_miss * 3:,.0f}/year |\n"
            f"| Air Heater Cleaning | 30-60 Btu/kWh | ${dispatch_miss * 2:,.0f}/year |\n"
            f"| Mill Optimization | 20-40 Btu/kWh | ${dispatch_miss * 1.5:,.0f}/year |\n"
            f"| **TOTAL POTENTIAL** | **150-280 Btu/kWh** | **${dispatch_miss * 11:,.0f}/year** |\n\n"
            f"**Note**: Returning to PPA reference heat rate ({heat_dev:.1f}% improvement) would recover "
            f"**~${heat_dev * 12000:,.0f}/month** in excess fuel costs.\n\n"
            f"---\n\n"
            f"**Evidence Sources**:\n" + "\n".join(citations)
        )
    
    # Default broad response
    return (
        f"## Comprehensive Analysis\n\n"
        f"### Current Operating Context\n\n"
        f"Based on the selected operating period:\n"
        f"- **Revenue Capture Ratio**: {rcr:.2%}\n"
        f"- **Dispatch Gap**: {dispatch_miss:,.0f} MWh\n"
        f"- **Estimated Revenue Loss**: ~${dispatch_miss * 45:,.0f}\n"
        f"- **Heat Rate Deviation**: {heat_dev:.1f}% above reference\n\n"
        f"The primary performance constraint is **{top_driver}**, with **{top_component}** identified as the top loss component. "
        f"This pattern indicates a systemic issue rather than random operational variability.\n\n"
        f"---\n\n"
        f"### Key Observations\n\n"
        f"1. **Revenue Performance**:\n"
        f"   - Plant is capturing {rcr:.1%} of available revenue\n"
        f"   - Primary losses attributable to {top_driver}\n"
        f"   - Top component ({top_component}) shows recurring failure pattern\n\n"
        f"2. **Efficiency Trends**:\n"
        f"   - Heat rate deviation: {heat_dev:.1f}% above reference\n"
        f"   - Indicates elevated fuel consumption per MWh generated\n"
        f"   - Likely tied to auxiliary load creep and part-load operation\n\n"
        f"3. **Operational Patterns**:\n"
        f"   - Event clustering suggests chronic equipment limitations\n"
        f"   - Correlation analysis points to draft control and cooling system constraints\n"
        f"   - Reactive maintenance cycle perpetuates forced derates\n\n"
        f"---\n\n"
        f"### Recommended Focus Areas\n\n"
        f"**Immediate Actions**:\n"
        f"- Investigate {top_component} for mechanical or control system issues\n"
        f"- Verify instrumentation calibration (draft pressure, flow meters)\n"
        f"- Monitor furnace draft stability during load ramp events\n\n"
        f"**Near-Term Optimization**:\n"
        f"- Retune ID fan/damper control loops to reduce hunting and saturation\n"
        f"- Optimize auxiliary load (condenser pumps, cooling tower fans)\n"
        f"- Implement predictive maintenance on chronic failure components\n\n"
        f"**Long-Term Strategy**:\n"
        f"- Transition from reactive to condition-based maintenance\n"
        f"- Upgrade aging instrumentation and control systems\n"
        f"- Consider equipment upgrades during planned outages\n\n"
        f"---\n\n"
        f"### Expected Impact\n\n"
        f"Addressing these constraints should yield:\n"
        f"- **RCR Improvement**: 0.8-1.2 percentage points\n"
        f"- **Revenue Recovery**: ~${dispatch_miss * 20:,.0f} annually\n"
        f"- **Heat Rate Benefit**: 80-150 Btu/kWh improvement\n"
        f"- **Fuel Savings**: ~${dispatch_miss * 8:,.0f} annually\n"
        f"- **Availability**: 0.3-0.5% improvement (fewer forced derates)\n\n"
        f"---\n\n"
        f"**Evidence Sources**:\n" + "\n".join(citations)
    )


def has_openai_key() -> bool:
    """Whether OpenAI mode is available."""
    key = os.getenv("OPENAI_API_KEY", "")
    return bool(key.strip())


def call_openai_rag(
    question: str,
    context: list[RetrievedChunk],
    kpis: dict[str, Any],
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> str:
    """Call OpenAI responses API in safe optional mode."""
    key = api_key or os.getenv("OPENAI_API_KEY", "")
    if not key or not key.strip():
        return "❌ LLM mode unavailable. Please provide an API key or set OPENAI_API_KEY environment variable."

    try:
        from openai import OpenAI
    except Exception:
        return "❌ OpenAI package is not installed. Run: pip install openai"

    client = OpenAI(api_key=key)
    context_blob = "\n\n".join([f"[{c.source}::{c.section}]\n{c.text}" for c in context])
    
    dispatch_miss = float(kpis.get("dispatch_miss_mwh", 0.0))
    rcr = float(kpis.get("rcr", float("nan")))
    top_driver = str(kpis.get("top_loss_driver", "Unknown"))
    heat_dev = float(kpis.get("heat_rate_dev_pct", 0.0))
    
    kpi_summary = (
        f"Revenue Capture Ratio: {rcr:.2%}\n"
        f"Dispatch Gap: {dispatch_miss:,.1f} MWh\n"
        f"Top Loss Driver: {top_driver}\n"
        f"Heat Rate Deviation: {heat_dev:.1f}%"
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert operations and revenue optimization advisor for thermal power plants. "
                "Provide actionable, data-driven insights based on plant performance metrics and operational context. "
                "Structure responses with: Executive Summary (5-7 bullets), Evidence (tables + dataset citations), "
                "Root Cause Hypotheses (ranked), Recommended Actions (immediate/next shift/next outage), "
                "Expected Impact ($ and/or MW estimates). "
                "Be thorough and detailed - aim for 400-800 words. "
                "Cite evidence from provided documentation."
            ),
        },
        {
            "role": "user",
            "content": (
                f"**Current Plant Performance KPIs:**\n{kpi_summary}\n\n"
                f"**Supporting Documentation:**\n{context_blob}\n\n"
                f"**Question:**\n{question}"
            ),
        },
    ]

    try:
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=2000)
        return resp.choices[0].message.content or "No response generated."
    except Exception as exc:
        return f"❌ LLM request failed: {exc}\n\nFalling back to mock mode."


def generate_llm_insight(
    data_context: str,
    kpis: dict[str, Any],
    mode: str = "mock",
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> str:
    """Generate a short LLM insight for tab callouts (200-400 words)."""
    dispatch_miss = float(kpis.get("dispatch_miss_mwh", 0.0))
    rcr = float(kpis.get("rcr", float("nan")))
    top_driver = str(kpis.get("top_loss_driver", "Unknown"))
    heat_dev = float(kpis.get("heat_rate_dev_pct", 0.0))
    
    if mode == "mock":
        # Deterministic mock insight
        return (
            f"**AI-Generated Insight**: Over the selected period, the plant captured **{rcr:.1%}** of available revenue, "
            f"with **{top_driver}** identified as the primary constraint. Analysis reveals a recurring pattern: "
            f"draft control instability during load ramps forces operators to cap generation, missing dispatch targets. "
            f"Heat rate deviation of **{heat_dev:.1f}%** above reference compounds losses through elevated fuel costs. "
            f"\n\n"
            f"**Key Recommendation**: Prioritize ID fan/damper control loop retuning to reduce saturation events (>98% open). "
            f"Expected impact: **0.5-0.8% RCR improvement** (~${dispatch_miss * 18:,.0f} annually) plus heat rate recovery "
            f"of 80-120 Btu/kWh. Near-term actions include verifying draft pressure transmitter calibration and inspecting "
            f"damper linkage for mechanical binding."
        )
    else:
        # Real LLM mode
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key or not key.strip():
            return "❌ LLM mode unavailable. Please provide an API key."
        
        try:
            from openai import OpenAI
        except Exception:
            return "❌ OpenAI package not installed."
        
        client = OpenAI(api_key=key)
        
        kpi_summary = (
            f"Revenue Capture Ratio: {rcr:.2%}\n"
            f"Dispatch Gap: {dispatch_miss:,.1f} MWh\n"
            f"Top Loss Driver: {top_driver}\n"
            f"Heat Rate Deviation: {heat_dev:.1f}%"
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert power plant operations advisor. Provide a concise insight (200-400 words) "
                    "summarizing key trends, root causes, and actionable recommendations for the selected time period. "
                    "Focus on financial impact and prioritized next steps."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"**Plant Performance KPIs:**\n{kpi_summary}\n\n"
                    f"**Context:**\n{data_context}\n\n"
                    f"Provide a brief AI-generated insight summarizing trends and recommendations."
                ),
            },
        ]
        
        try:
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=600)
            return resp.choices[0].message.content or "No insight generated."
        except Exception as exc:
            return f"❌ LLM request failed: {exc}"


def generate_evidence_summary(
    events_df: pd.DataFrame,
    work_orders_df: pd.DataFrame,
    media_df: pd.DataFrame,
    mode: str = "mock",
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> str:
    """Generate a comprehensive evidence summary from multiple sources."""
    # Build evidence context
    evidence_parts = []
    
    if not events_df.empty:
        evidence_parts.append(f"**Events**: {len(events_df)} related events identified")
        if "type" in events_df.columns:
            event_types = events_df["type"].value_counts().to_dict()
            evidence_parts.append(f"Event types: {event_types}")
    
    if not work_orders_df.empty:
        evidence_parts.append(f"**Work Orders**: {len(work_orders_df)} linked work orders")
        if "status" in work_orders_df.columns:
            wo_status = work_orders_df["status"].value_counts().to_dict()
            evidence_parts.append(f"WO status: {wo_status}")
    
    if not media_df.empty:
        evidence_parts.append(f"**Media**: {len(media_df)} media items")
        if "media_type" in media_df.columns:
            media_types = media_df["media_type"].value_counts().to_dict()
            evidence_parts.append(f"Media types: {media_types}")
    
    evidence_context = "\n".join(evidence_parts)
    
    if mode == "mock":
        # Deterministic mock summary
        event_count = len(events_df) if not events_df.empty else 0
        wo_count = len(work_orders_df) if not work_orders_df.empty else 0
        media_count = len(media_df) if not media_df.empty else 0
        
        return (
            f"### Evidence Summary\n\n"
            f"Analysis of **{event_count} events**, **{wo_count} work orders**, and **{media_count} media items** "
            f"reveals a consistent pattern of draft control-related issues affecting the selected system/subsystem.\n\n"
            f"**Event Pattern**: Multiple forced derates and load limitations occurred during high-demand periods, "
            f"with operators citing 'furnace draft instability' and 'ID fan at limit' as primary constraints. "
            f"Events cluster around morning and evening peak ramps, indicating a control system limitation rather than "
            f"equipment failure.\n\n"
            f"**Maintenance History**: Work orders show repeat interventions on ID fan dampers and actuators, with "
            f"'damper binding' and 'linkage wear' noted in multiple completions. Replacement parts were installed but "
            f"root cause (control tuning) was not addressed, leading to continued issues.\n\n"
            f"**Field Evidence**: Voice recordings from shift handoffs mention 'fighting the draft' during ramps. "
            f"Operator notes indicate manual bias adjustments were required to maintain stable operation. "
            f"Images show damper position trending at 98-100% during peak load, confirming saturation.\n\n"
            f"**Root Cause Assessment**: Combined evidence points to inadequate ID fan/damper control authority during "
            f"rapid load changes. Current PID tuning is optimized for steady-state but lacks feedforward compensation "
            f"for ramp events. Mechanical condition of dampers is degraded but control deficiency is primary driver.\n\n"
            f"**Recommended Action**: Retune draft control loops as first priority, then address mechanical wear during "
            f"next planned outage. Expected impact: 40-60% reduction in draft-related derates within 30 days."
        )
    else:
        # Real LLM mode
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key or not key.strip():
            return "❌ LLM mode unavailable. Please provide an API key."
        
        try:
            from openai import OpenAI
        except Exception:
            return "❌ OpenAI package not installed."
        
        client = OpenAI(api_key=key)
        
        # Prepare detailed evidence for LLM
        evidence_details = []
        
        if not events_df.empty:
            events_sample = events_df.head(5).to_dict("records")
            evidence_details.append(f"**Events (sample of {len(events_df)})**:\n" + 
                                  "\n".join([f"- {e.get('type', 'N/A')}: {e.get('description', 'N/A')}" for e in events_sample]))
        
        if not work_orders_df.empty:
            wo_sample = work_orders_df.head(5).to_dict("records")
            evidence_details.append(f"**Work Orders (sample of {len(work_orders_df)})**:\n" + 
                                  "\n".join([f"- {w.get('title', 'N/A')}: {w.get('status', 'N/A')}" for w in wo_sample]))
        
        if not media_df.empty:
            media_sample = media_df.head(3).to_dict("records")
            evidence_details.append(f"**Media (sample of {len(media_df)})**:\n" + 
                                  "\n".join([f"- {m.get('media_type', 'N/A')}: {m.get('caption', 'N/A')}" for m in media_sample]))
        
        evidence_blob = "\n\n".join(evidence_details)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert power plant analyst. Synthesize evidence from events, work orders, and field media "
                    "to provide a comprehensive multi-paragraph summary with: Event Pattern, Maintenance History, "
                    "Field Evidence, Root Cause Assessment, Recommended Actions. Be detailed and specific."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"**Evidence Overview:**\n{evidence_context}\n\n"
                    f"**Detailed Evidence:**\n{evidence_blob}\n\n"
                    f"Provide a comprehensive evidence summary (300-500 words) with bullet points and analysis."
                ),
            },
        ]
        
        try:
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=1200)
            return resp.choices[0].message.content or "No summary generated."
        except Exception as exc:
            return f"❌ LLM request failed: {exc}"


def generate_maintenance_criticality_insight(
    asset_row: pd.Series | dict,
    event_impacts_df: pd.DataFrame,
    work_orders_df: pd.DataFrame,
    ai_insights_df: pd.DataFrame,
    mode: str = "mock",
    model: str = "gpt-4o",
    api_key: str | None = None,
) -> str:
    """Generate maintenance criticality insight for a selected asset.
    
    Args:
        asset_row: Row from maintenance_criticality_asset_summary with asset metrics
        event_impacts_df: Related events from maintenance_event_impacts.csv
        work_orders_df: Related work orders
        ai_insights_df: Pre-generated AI insights (for mock mode)
        mode: 'mock' or 'real'
        model: OpenAI model name
        api_key: OpenAI API key
    
    Returns:
        Formatted insight text (250-450 words)
    """
    # Extract asset info
    if isinstance(asset_row, dict):
        asset_path = str(asset_row.get("asset_path", "Unknown"))
        asset_id = str(asset_row.get("asset_id", ""))
        maint_cost = float(asset_row.get("maintenance_cost_usd", 0))
        rev_impact = float(asset_row.get("revenue_impact_usd", 0))
        event_count = int(asset_row.get("event_count", 0))
        mci = float(asset_row.get("maintenance_criticality_index", 0))
        quadrant = str(asset_row.get("criticality_quadrant", "Unknown"))
        top_cause = str(asset_row.get("top_root_cause_category", "Unknown"))
    else:
        asset_path = str(asset_row.get("asset_path", "Unknown"))
        asset_id = str(asset_row.get("asset_id", ""))
        maint_cost = float(asset_row.get("maintenance_cost_usd", 0))
        rev_impact = float(asset_row.get("revenue_impact_usd", 0))
        event_count = int(asset_row.get("event_count", 0))
        mci = float(asset_row.get("maintenance_criticality_index", 0))
        quadrant = str(asset_row.get("criticality_quadrant", "Unknown"))
        top_cause = str(asset_row.get("top_root_cause_category", "Unknown"))
    
    if mode == "mock":
        # Try to find pre-generated insight from CSV
        if not ai_insights_df.empty and "asset_id" in ai_insights_df.columns:
            matches = ai_insights_df[ai_insights_df["asset_id"].astype(str) == asset_id]
            if not matches.empty and "ai_insight_text" in matches.columns:
                insight_text = matches.iloc[0]["ai_insight_text"]
                if pd.notna(insight_text) and str(insight_text).strip():
                    return str(insight_text)
        
        # Fallback: Generate deterministic mock insight
        return (
            f"## Maintenance Criticality Analysis: {asset_path}\n\n"
            f"### Executive Summary\n\n"
            f"- **Criticality Index**: {mci:.2f} ({quadrant} quadrant)\n"
            f"- **Total Events**: {event_count} occurrences in analysis period\n"
            f"- **Maintenance Spend**: ${maint_cost:,.0f}\n"
            f"- **Revenue Impact**: ${rev_impact:,.0f}\n"
            f"- **Primary Driver**: {top_cause}\n\n"
            f"### Drivers of Criticality\n\n"
            f"**Frequency**: This asset experienced **{event_count} events**, placing it in the "
            f"{'high-frequency' if event_count > 5 else 'moderate-frequency'} category. "
            f"The recurring nature suggests a chronic issue rather than random failures.\n\n"
            f"**Consequence**: Each incident carries significant operational impact, with total revenue losses "
            f"of **${rev_impact:,.0f}**. This reflects both direct generation curtailment and secondary effects "
            f"(downstream equipment impacts, startup delays).\n\n"
            f"**Maintenance Spend**: Cumulative maintenance costs of **${maint_cost:,.0f}** indicate "
            f"{'reactive spending patterns' if maint_cost > rev_impact * 0.3 else 'controlled intervention costs'}. "
            f"The cost-to-impact ratio suggests opportunities for optimization.\n\n"
            f"### Recommended Actions\n\n"
            f"**Immediate (Current Shift)**:\n"
            f"- Review recent work order history for repeat failure patterns\n"
            f"- Verify current operating parameters are within design limits\n"
            f"- Schedule inspection during next available maintenance window\n\n"
            f"**Next Shift**:\n"
            f"- Implement enhanced monitoring on this asset (trend key parameters)\n"
            f"- Conduct root cause analysis with maintenance and ops teams\n"
            f"- Identify predictive indicators to enable early intervention\n\n"
            f"**Next Planned Outage**:\n"
            f"- Deep inspection and potential component upgrade/replacement\n"
            f"- Address design or operational constraints contributing to recurrence\n"
            f"- Consider condition-based maintenance strategy vs. current reactive approach\n\n"
            f"### Expected Impact\n\n"
            f"Reducing event recurrence by **30-50%** through proactive interventions could yield:\n"
            f"- **Revenue protection**: ${rev_impact * 0.4:,.0f} annually\n"
            f"- **Maintenance savings**: ${maint_cost * 0.25:,.0f} (fewer emergency repairs)\n"
            f"- **Availability improvement**: 0.2-0.4% increase in unit availability\n\n"
            f"Prioritize this asset in your reliability improvement roadmap based on its {quadrant.lower()} position."
        )
    else:
        # Real LLM mode
        key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not key or not key.strip():
            return "❌ LLM mode unavailable. Please provide an API key."
        
        try:
            from openai import OpenAI
        except Exception:
            return "❌ OpenAI package not installed."
        
        client = OpenAI(api_key=key)
        
        # Build evidence context
        evidence_parts = []
        
        if not event_impacts_df.empty:
            evidence_parts.append(
                f"**Event History**: {len(event_impacts_df)} events analyzed\n"
                + "\n".join([
                    f"- {row.get('event_date', 'N/A')}: {row.get('description', 'N/A')} "
                    f"(Cost: ${row.get('maintenance_cost_usd', 0):,.0f}, Impact: ${row.get('revenue_impact_usd', 0):,.0f})"
                    for _, row in event_impacts_df.head(5).iterrows()
                ])
            )
        
        if not work_orders_df.empty:
            evidence_parts.append(
                f"**Work Order Pattern**: {len(work_orders_df)} work orders\n"
                + "\n".join([
                    f"- {row.get('title', 'N/A')}: {row.get('status', 'N/A')}"
                    for _, row in work_orders_df.head(5).iterrows()
                ])
            )
        
        evidence_blob = "\n\n".join(evidence_parts) if evidence_parts else "Limited evidence available."
        
        # Build asset summary
        asset_summary = (
            f"Asset: {asset_path}\n"
            f"Criticality Index: {mci:.2f}\n"
            f"Quadrant: {quadrant}\n"
            f"Event Count: {event_count}\n"
            f"Maintenance Cost: ${maint_cost:,.0f}\n"
            f"Revenue Impact: ${rev_impact:,.0f}\n"
            f"Top Root Cause: {top_cause}"
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert reliability engineer analyzing maintenance criticality. "
                    "Provide a structured analysis (250-450 words) with: Executive Summary (5-7 bullets), "
                    "Drivers of Criticality (frequency vs consequence vs spend), "
                    "Recommended Actions (immediate/next shift/next outage), "
                    "Expected Impact ($ savings if recurrence reduced). "
                    "Use risk framing (likelihood vs consequence) and explain the asset's quadrant position."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"**Asset Summary:**\n{asset_summary}\n\n"
                    f"**Evidence:**\n{evidence_blob}\n\n"
                    f"Provide a maintenance criticality analysis for this asset."
                ),
            },
        ]
        
        try:
            resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=800)
            return resp.choices[0].message.content or "No insight generated."
        except Exception as exc:
            return f"❌ LLM request failed: {exc}"
