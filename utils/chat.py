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
    """Generate realistic mock response with citations and context-aware detail."""
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
            f"## Summary of Recent Performance\n\n"
            f"Over the selected period, the plant achieved a **Revenue Capture Ratio of {rcr:.1%}**, "
            f"missing approximately **{dispatch_miss:,.0f} MWh** of dispatch targets. "
            f"The primary loss driver is **{top_driver}**, accounting for the largest share of forgone revenue.\n\n"
            f"**Heat Rate Performance**: Net station heat rate deviated {heat_dev:.1f}% above PPA reference, "
            f"indicating efficiency losses likely tied to {top_component.lower()} constraints and auxiliary load drift.\n\n"
            f"**Key Pattern**: Draft control instability (ID fan hunting, damper saturation) appears in multiple "
            f"5-min miss windows, suggesting a recurring equipment limitation rather than operational error.\n\n"
            f"**Evidence Sources**:\n" + "\n".join(citations)
        )
    
    elif "action" in q_lower or "improve" in q_lower or "recommend" in q_lower:
        return (
            f"## Top 3 Actions to Improve Revenue Capture\n\n"
            f"Based on analysis of the selected period (RCR: {rcr:.1%}, loss: ~${dispatch_miss * 45:,.0f}), "
            f"here are prioritized interventions:\n\n"
            f"### 1. **Optimize Draft Control Tuning** (Highest Impact)\n"
            f"- **What**: Retune ID fan PID loops and damper response curves to reduce hunting behavior\n"
            f"- **Why**: {top_component} is the top loss component; damper saturation (>98%) correlates strongly with dispatch misses\n"
            f"- **Expected Value**: Reducing draft-related misses by 30% could recover ~0.5-0.8 RCR points (~${dispatch_miss * 15:,.0f})\n\n"
            f"### 2. **Address Auxiliary Load Drift**\n"
            f"- **What**: Inspect condenser cooling tower fans, circulating water pumps, and feedwater heater performance\n"
            f"- **Why**: Heat rate deviation of {heat_dev:.1f}% suggests excess auxiliary consumption degrading net output\n"
            f"- **Expected Value**: Returning aux load to baseline can improve heat rate by 80-120 Btu/kWh (~${dispatch_miss * 8:,.0f})\n\n"
            f"### 3. **Proactive Work Order Scheduling**\n"
            f"- **What**: Schedule maintenance on repeat failure components during planned outages\n"
            f"- **Why**: Event clustering suggests chronic issues rather than random failures\n"
            f"- **Expected Value**: Preventing forced derates extends availability by 0.3-0.5% annually\n\n"
            f"**Supporting Evidence**:\n" + "\n".join(citations)
        )
    
    elif "outage" in q_lower or "event" in q_lower or "explain" in q_lower:
        return (
            f"## Event Analysis\n\n"
            f"The referenced event appears to be part of a **recurring pattern** tied to {top_driver.lower()} constraints. "
            f"Based on historical data:\n\n"
            f"**Root Cause**: Draft control instability—ID fan speed variance + damper saturation near 98-100% "
            f"leads to unstable furnace pressure and temporary load caps to preserve boiler stability.\n\n"
            f"**Impact**: Each event window averages {dispatch_miss / max(1, kpis.get('event_count', 5)):.0f} MWh of lost generation. "
            f"Over the selected period, draft-related events contributed ~{rcr * 100 - 96:.1f} RCR points of underperformance.\n\n"
            f"**Typical Sequence**:\n"
            f"1. Rising grid demand triggers ramp request\n"
            f"2. ID fan accelerates to maintain furnace draft\n"
            f"3. Damper reaches saturation (98-100% open)\n"
            f"4. Draft pressure becomes unstable; operators cap load to stabilize\n"
            f"5. Dispatch target missed until draft settles\n\n"
            f"**Corrective Pathway**: Verify DP transmitter calibration, inspect damper linkage for mechanical binding, "
            f"and retune draft control bias to avoid saturation region during normal operation.\n\n"
            f"**Evidence**:\n" + "\n".join(citations)
        )
    
    elif "heat rate" in q_lower or "efficiency" in q_lower or "nshr" in q_lower:
        return (
            f"## Heat Rate & Efficiency Analysis\n\n"
            f"Net Station Heat Rate (NSHR) is deviating **{heat_dev:.1f}% above PPA reference**, "
            f"indicating the plant is consuming more fuel per MWh of net generation than contracted.\n\n"
            f"**Primary Drivers**:\n"
            f"- **Auxiliary Load**: Elevated aux consumption (condenser pumps, cooling tower fans) reduces net output while maintaining fuel input\n"
            f"- **{top_driver}**: System inefficiencies force operational derates, pushing the unit into less-efficient load ranges\n"
            f"- **Cycling Penalty**: Frequent restarts or deep load swings increase heat rate during stabilization periods\n\n"
            f"**Financial Impact**: Each 1% heat rate deviation at current coal costs translates to ~${heat_dev * 12000:,.0f}/month in excess fuel expense.\n\n"
            f"**Diagnostic Path**:\n"
            f"1. Compare actual vs design auxiliary load curves\n"
            f"2. Trend condenser backpressure and identify cooling-side bottlenecks\n"
            f"3. Audit mill performance (coal fineness, primary air flow)\n"
            f"4. Review soot blowing effectiveness and boiler tube cleanliness\n\n"
            f"**Evidence**:\n" + "\n".join(citations)
        )
    
    # Default broad response
    return (
        f"## Analysis Response\n\n"
        f"Based on the selected operating context (RCR: {rcr:.2%}, dispatch gap: {dispatch_miss:,.0f} MWh), "
        f"the primary performance constraint is **{top_driver}**, with {top_component} identified as the top loss component.\n\n"
        f"**Key Observations**:\n"
        f"- Heat rate deviation: {heat_dev:.1f}% above reference\n"
        f"- Recurring event pattern suggests chronic equipment limitation\n"
        f"- Correlation analysis points to draft control and auxiliary load as actionable levers\n\n"
        f"**Next Steps**: Focus corrective actions on ID fan/damper tuning and condenser performance to close the RCR gap.\n\n"
        f"**Evidence**:\n" + "\n".join(citations)
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
                "Structure responses with: Key Findings, Root Cause Analysis, Recommended Actions, Expected Impact. "
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
        resp = client.chat.completions.create(model=model, messages=messages, temperature=0.3, max_tokens=1200)
        return resp.choices[0].message.content or "No response generated."
    except Exception as exc:
        return f"❌ LLM request failed: {exc}\n\nFalling back to mock mode."
