"""Shakti Thermal Station — Full Potential Streamlit Demo."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from utils.chat import (
    build_data_context_snippets,
    build_mock_response,
    build_retrieval_index,
    call_openai_rag,
)
from utils.data import (
    DataCatalog,
    available_units,
    best_default_date_range,
    downsample_for_plotting,
    filter_by_unit_and_time,
    get_available_date_range,
    load_data_catalog,
)
from utils.matching import build_entity_catalog, compute_mapping_accuracy, fuzzy_match, map_work_orders
from utils.metrics import (
    cached_correlations,
    compute_revenue_kpis,
    correlation_explanation,
    standardize_dispatch_columns,
    top_loss_components,
)
from utils.ontology import build_pyvis_html, get_node_inspector, node_options
from utils.sanity import run_startup_checks
from utils.style import apply_bain_style, render_header, render_kpi_strip
from utils.viz import (
    dispatch_gap_attribution_chart,
    generation_main_chart,
    heat_rate_sync_chart,
    historian_overlay_chart,
    loss_treemap,
    lost_revenue_driver_chart,
    rcr_over_time_chart,
)


FALLBACK_GLOSSARY = {
    "Dispatch Target (5-min)": "The grid-required megawatt target every 5 minutes.",
    "Deviation / Dispatch Gap": "Difference between dispatch target and net generation.",
    "Net Station Heat Rate (NSHR)": "Fuel energy input per unit of net electricity generated.",
    "Auxiliary Load": "Power consumed internally by plant equipment.",
    "Revenue Capture Ratio": "Actual revenue divided by maximum potential revenue.",
    "Availability Factor (proxy)": "Approximate readiness to generate against dispatch needs.",
}


@st.cache_data(show_spinner=False)
def load_glossary_map(docs_dir: str) -> dict[str, str]:
    glossary_path = Path(docs_dir) / "glossary.md"
    if not glossary_path.exists():
        return FALLBACK_GLOSSARY

    out: dict[str, str] = {}
    try:
        for line in glossary_path.read_text(encoding="utf-8").splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                if key.strip() and val.strip():
                    out[key.strip()] = val.strip()
    except OSError:
        return FALLBACK_GLOSSARY

    return out if out else FALLBACK_GLOSSARY


def info_term(glossary: dict[str, str], term: str) -> None:
    with st.expander(f"ℹ {term}", expanded=False):
        st.write(glossary.get(term, FALLBACK_GLOSSARY.get(term, "Definition unavailable.")))


def fmt_usd(value: float) -> str:
    return f"${value:,.0f}" if pd.notna(value) else "-"


def _download_csv(df: pd.DataFrame, label: str, file_name: str) -> None:
    st.download_button(label=label, data=df.to_csv(index=False), file_name=file_name, mime="text/csv")


def _status_badge(status: str) -> str:
    klass = "status-pass" if status == "pass" else "status-warn" if status == "warn" else "status-fail"
    return f"<span class='{klass}'>{status.upper()}</span>"


def _filter_core(
    catalog: DataCatalog,
    unit: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> dict[str, pd.DataFrame]:
    return {
        key: filter_by_unit_and_time(df, unit, start_dt, end_dt)
        for key, df in catalog.tables.items()
    }


def render_sidebar(catalog: DataCatalog, checks: list) -> tuple[str, pd.Timestamp, pd.Timestamp, str]:
    st.sidebar.header("Global Controls")

    units = available_units(catalog)
    default_unit = units[0] if units else "STS-U1"
    unit = st.sidebar.selectbox("Plant / Unit", units if units else [default_unit], index=0)

    # Get available date range for slider bounds
    min_date, max_date = get_available_date_range(catalog)
    default_start, default_end = best_default_date_range(catalog)
    
    # Date range slider
    date_range = st.sidebar.slider(
        "Date range",
        min_value=min_date.to_pydatetime(),
        max_value=max_date.to_pydatetime(),
        value=(default_start.to_pydatetime(), default_end.to_pydatetime()),
        format="YYYY-MM-DD",
    )
    
    # Convert slider output to pandas Timestamps with UTC
    start_dt = pd.Timestamp(date_range[0])
    end_dt = pd.Timestamp(date_range[1])
    
    # Ensure UTC timezone
    if start_dt.tzinfo is None:
        start_dt = start_dt.tz_localize("UTC")
    else:
        start_dt = start_dt.tz_convert("UTC")
    
    if end_dt.tzinfo is None:
        end_dt = end_dt.tz_localize("UTC")
    else:
        end_dt = end_dt.tz_convert("UTC")
    
    # Extend end to end of day
    end_dt = end_dt + pd.Timedelta(days=1) - pd.Timedelta(minutes=1)

    resolution = st.sidebar.selectbox("Resolution", ["hourly", "5-min"], index=0)

    st.sidebar.subheader("Data Health")
    health = catalog.health.copy()
    if not health.empty:
        st.sidebar.dataframe(
            health[["dataset", "rows", "timestamp_min", "timestamp_max", "nulls_key_cols"]],
            use_container_width=True,
            hide_index=True,
            height=260,
        )

    missing = [s for s in catalog.statuses.values() if not s.loaded]
    warnings = [s for s in catalog.statuses.values() if s.warning]
    if missing:
        st.sidebar.warning("Some datasets are missing; app runs with degraded features.")
    if warnings:
        with st.sidebar.expander("Missing/Warning details"):
            for w in warnings:
                st.write(f"- {w.key}: {w.warning}")

    st.sidebar.markdown("---")
    with st.sidebar.expander("Sanity Check Status", expanded=False):
        for check in checks:
            st.markdown(f"- {_status_badge(check.status)} {check.name}: {check.message}", unsafe_allow_html=True)

    return unit, start_dt, end_dt, resolution


def render_tab_mapping(
    catalog: DataCatalog,
    filtered: dict[str, pd.DataFrame],
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> None:
    nodes_df = catalog.tables.get("ontology_nodes", pd.DataFrame())
    edges_df = catalog.tables.get("ontology_edges", pd.DataFrame())
    events_df = filtered.get("events", pd.DataFrame())
    wo_df = filtered.get("work_orders", pd.DataFrame())
    sensor_df = catalog.tables.get("sensor_registry", pd.DataFrame())
    asset_df = catalog.tables.get("asset_hierarchy", pd.DataFrame())

    left, right = st.columns([1.2, 1.0])
    with left:
        st.markdown("#### Interactive Ontology Graph")
        html = build_pyvis_html(nodes_df, edges_df, events_df, wo_df)
        components.html(html, height=640, scrolling=True)
        
        # Legend
        st.markdown("**Node Type Legend**")
        legend_html = """
        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 13px;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #CB2026; border-radius: 50%; display: inline-block;"></span>
                <span>Plant</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #EA6A6E; border-radius: 50%; display: inline-block;"></span>
                <span>Unit</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #F0A3A6; border-radius: 50%; display: inline-block;"></span>
                <span>System</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #BBD7EE; border-radius: 50%; display: inline-block;"></span>
                <span>Subsystem</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #92B7D5; border-radius: 50%; display: inline-block;"></span>
                <span>Component</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #6B7280; border-radius: 50%; display: inline-block;"></span>
                <span>Tag</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 14px; height: 14px; background: #9CA3AF; border-radius: 50%; display: inline-block;"></span>
                <span>Other</span>
            </div>
        </div>
        """
        st.markdown(legend_html, unsafe_allow_html=True)
        
        st.markdown("**Edge Mapping Legend**")
        edge_legend_html = """
        <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 8px; font-size: 13px;">
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 20px; height: 3px; background: #2563EB; display: inline-block;"></span>
                <span>Mapped by ID</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 20px; height: 3px; background: #F59E0B; display: inline-block;"></span>
                <span>Mapped by Fuzzy Logic</span>
            </div>
            <div style="display: flex; align-items: center; gap: 5px;">
                <span style="width: 20px; height: 3px; background: #10B981; display: inline-block;"></span>
                <span>Mapped by Timestamp</span>
            </div>
        </div>
        """
        st.markdown(edge_legend_html, unsafe_allow_html=True)

    with right:
        st.markdown("#### Node Inspector")
        opts = node_options(nodes_df)
        selected_node = st.selectbox("Selected Node", [""] + opts)
        if not selected_node:
            st.info("💡 **Try these examples**:\n- **ASSET::STS-U1-IDF-A**: ID Fan with linked tags + many draft events\n- **ASSET::STS-U1-TB-BRG2**: Turbine bearing with vibration tag + events\n- **ASSET::STS-U1**: Unit-level node with generation tags")
        if selected_node:
            details = get_node_inspector(selected_node, nodes_df, sensor_df, events_df, start_dt, end_dt)
            st.json(details.get("node", {}), expanded=False)
            aliases = details.get("aliases", [])
            if aliases:
                st.write("Aliases:", ", ".join([str(a) for a in aliases]))
            
            st.write("**Linked tags**")
            linked_tags_df = details.get("linked_tags", pd.DataFrame())
            if linked_tags_df.empty:
                st.caption("(No sensor tags measure this node)")
            else:
                st.dataframe(linked_tags_df.head(12), use_container_width=True)
            
            st.write("**Recent events**")
            recent_events_df = details.get("recent_events", pd.DataFrame())
            if recent_events_df.empty:
                st.caption("(No events affecting this node in selected date range)")
            else:
                st.dataframe(recent_events_df.head(8), use_container_width=True)

        st.markdown("#### GenAI-like Fuzzy Mapping")
        query = st.text_input("Messy string to map", placeholder="e.g., IDF A damper sat")
        entities = build_entity_catalog(asset_df, sensor_df)
        if query:
            out = fuzzy_match(query, entities, top_n=10)
            st.dataframe(out, use_container_width=True)

    st.markdown("#### Mapping Audit")
    mapped = map_work_orders(wo_df, entities=build_entity_catalog(asset_df, sensor_df), sample_size=50)
    if mapped.empty:
        st.info("Work orders unavailable for mapping audit.")
        return

    metrics = compute_mapping_accuracy(mapped)
    kpi = [
        ("Accuracy@1", f"{metrics['accuracy_at_1']:.1%}" if pd.notna(metrics["accuracy_at_1"]) else "n/a"),
        ("Accuracy@5", f"{metrics['accuracy_at_5']:.1%}" if pd.notna(metrics["accuracy_at_5"]) else "n/a"),
    ]
    render_kpi_strip(kpi)
    st.dataframe(mapped, use_container_width=True, height=260)
    _download_csv(mapped, "Export mapped work orders CSV", "mapped_work_orders.csv")


def render_tab_generation(
    catalog: DataCatalog,
    filtered: dict[str, pd.DataFrame],
    unit: str,
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
    resolution: str,
    glossary: dict[str, str],
) -> None:
    dispatch = standardize_dispatch_columns(filtered.get("dispatch", pd.DataFrame()))
    historian = filtered.get("historian", pd.DataFrame())
    heat_rate = filtered.get("heat_rate", pd.DataFrame())
    events = filtered.get("events", pd.DataFrame())

    ctrl = st.columns([1, 1])
    with ctrl[0]:
        show_outages = st.toggle("Show outages", value=True)
    with ctrl[1]:
        show_annotations = st.toggle("Show annotations", value=True)

    dispatch_plot = downsample_for_plotting(dispatch, resolution=resolution)
    
    # Auto-show 5-min misses only when resolution is 5-min
    show_misses = (resolution == "5-min")

    st.plotly_chart(
        generation_main_chart(dispatch_plot, events, show_outages=show_outages, show_misses=show_misses),
        use_container_width=True,
    )

    st.markdown("#### Dispatch Gap Attribution by Root Cause")
    st.plotly_chart(
        dispatch_gap_attribution_chart(dispatch, resolution=resolution),
        use_container_width=True,
    )

    st.markdown("#### Heat Rate Sync")
    heat_for_plot = heat_rate.copy()
    if resolution == "hourly" and not heat_for_plot.empty and "timestamp" in heat_for_plot.columns:
        heat_for_plot = heat_for_plot.set_index("timestamp").resample("1H").mean(numeric_only=True).reset_index()
    st.plotly_chart(heat_rate_sync_chart(heat_for_plot), use_container_width=True)

    st.markdown("#### Historian Correlation Panel")
    if dispatch.empty or "timestamp" not in dispatch.columns:
        st.info("Dispatch time series unavailable.")
        return

    # Use sidebar date range instead of separate slider
    corr_df = cached_correlations(historian, dispatch, unit, start_dt, end_dt, resolution)
    if corr_df.empty:
        st.info("Insufficient aligned historian signals in selected window.")
        return

    st.dataframe(corr_df, use_container_width=True, hide_index=True)

    merged = historian.copy()
    if "timestamp" in merged.columns:
        merged["timestamp"] = pd.to_datetime(merged["timestamp"], errors="coerce", utc=True)
        merged = merged[(merged["timestamp"] >= start_dt) & (merged["timestamp"] <= end_dt)]

    gen = dispatch[["timestamp", "net_generation_mw"]].copy() if {"timestamp", "net_generation_mw"}.issubset(dispatch.columns) else pd.DataFrame()
    if not gen.empty:
        gen["timestamp"] = pd.to_datetime(gen["timestamp"], errors="coerce", utc=True)
        merged = pd.merge_asof(
            merged.sort_values("timestamp"),
            gen.sort_values("timestamp"),
            on="timestamp",
            direction="nearest",
            tolerance=pd.Timedelta("10min"),
        )

    signals = [
        c
        for c in ["IDFanSpeed_pct", "draft_fan_speed", "DamperPosition_pct", "FurnaceDraftPressure_kPa", "FurnaceDraftPressure_Pa"]
        if c in merged.columns
    ]
    st.plotly_chart(historian_overlay_chart(merged, signals), use_container_width=True)
    if show_annotations:
        st.success(correlation_explanation(corr_df))


def render_tab_revenue(
    catalog: DataCatalog,
    filtered: dict[str, pd.DataFrame],
    glossary: dict[str, str],
) -> None:
    monthly = filtered.get("monthly_summary", pd.DataFrame())
    energy = filtered.get("energy_settlement", pd.DataFrame())
    capacity = filtered.get("capacity", pd.DataFrame())
    attr = filtered.get("attribution", pd.DataFrame())
    penalties = filtered.get("penalties", pd.DataFrame())
    fuel = filtered.get("fuel_cost", pd.DataFrame())
    events = filtered.get("events", pd.DataFrame())
    work_orders = filtered.get("work_orders", pd.DataFrame())

    if "month" in monthly.columns:
        monthly["month"] = pd.to_datetime(monthly["month"], errors="coerce", utc=True)

    if not monthly.empty and "month" in monthly.columns:
        current_month = monthly.sort_values("month").tail(1)
    else:
        current_month = monthly

    kpi_current = compute_revenue_kpis(current_month, energy, capacity, penalties, fuel)
    kpi_window = compute_revenue_kpis(monthly, energy, capacity, penalties, fuel)
    render_kpi_strip(
        [
            ("Revenue Capture Ratio", f"{kpi_current.revenue_capture_ratio:.2%}"),
            ("Total Actual Revenue", fmt_usd(kpi_window.actual_total_revenue)),
            ("Max Potential Revenue", fmt_usd(kpi_window.max_potential_revenue)),
            ("Total Loss", fmt_usd(kpi_window.total_loss)),
        ]
    )

    left, right = st.columns([1.1, 1.0])
    with left:
        show_ann = st.toggle("Show intervention annotations", value=True)
        st.plotly_chart(rcr_over_time_chart(monthly, show_annotations=show_ann), use_container_width=True)

    with right:
        st.plotly_chart(lost_revenue_driver_chart(attr), use_container_width=True)

    st.markdown("#### Lost Revenue Drilldown")
    cat_col, sys_col, sub_col = st.columns(3)
    category = cat_col.selectbox("Category", ["All"] + sorted(attr.get("loss_category", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr.empty else ["All"])

    attr_filtered = attr.copy()
    if category != "All" and "loss_category" in attr_filtered.columns:
        attr_filtered = attr_filtered[attr_filtered["loss_category"].astype(str) == category]

    systems = ["All"] + sorted(attr_filtered.get("system", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_filtered.empty else ["All"]
    system = sys_col.selectbox("System", systems)
    if system != "All" and "system" in attr_filtered.columns:
        attr_filtered = attr_filtered[attr_filtered["system"].astype(str) == system]

    subsystems = ["All"] + sorted(attr_filtered.get("subsystem", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_filtered.empty else ["All"]
    subsystem = sub_col.selectbox("Subsystem", subsystems)
    if subsystem != "All" and "subsystem" in attr_filtered.columns:
        attr_filtered = attr_filtered[attr_filtered["subsystem"].astype(str) == subsystem]

    st.plotly_chart(loss_treemap(attr_filtered), use_container_width=True)

    components = sorted(attr_filtered.get("component", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_filtered.empty else []
    selected_component = st.selectbox("Selected component (mirrors click fallback)", [""] + components)

    top_n = st.slider("Top N components", min_value=5, max_value=30, value=10)
    top_components_df = top_loss_components(attr_filtered, top_n=top_n)
    st.dataframe(top_components_df, use_container_width=True)
    _download_csv(top_components_df, "Export attribution table CSV", "attribution_top_components.csv")
    _download_csv(monthly, "Export monthly summary CSV", "monthly_summary_filtered.csv")

    if selected_component:
        st.markdown("#### Component Detail")
        detail = attr_filtered[attr_filtered.get("component", "").astype(str) == selected_component]
        linked_event_ids = detail.get("linked_event_id", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()

        related_events = events[events.get("event_id", "").astype(str).isin(linked_event_ids)] if not events.empty and "event_id" in events.columns else pd.DataFrame()
        related_wos = work_orders[work_orders.get("linked_event_id", "").astype(str).isin(linked_event_ids)] if not work_orders.empty and "linked_event_id" in work_orders.columns else pd.DataFrame()

        st.write("Related events")
        st.dataframe(related_events.head(20), use_container_width=True)
        st.write("Linked work orders")
        st.dataframe(related_wos.head(20), use_container_width=True)
        total_loss = pd.to_numeric(detail.get("loss_usd", 0), errors="coerce").sum()
        st.info(
            f"{selected_component} contributes ${total_loss:,.0f} in the selected context; reducing repeat event exposure should improve capture ratio."
        )


def render_tab_chatbot(
    filtered: dict[str, pd.DataFrame],
    docs_dir: Path,
    glossary: dict[str, str],
) -> None:
    dispatch = standardize_dispatch_columns(filtered.get("dispatch", pd.DataFrame()))
    attribution = filtered.get("attribution", pd.DataFrame())
    monthly = filtered.get("monthly_summary", pd.DataFrame())
    heat = filtered.get("heat_rate", pd.DataFrame())

    snippets = build_data_context_snippets(dispatch, attribution, monthly)
    index = build_retrieval_index(docs_dir, snippets)

    st.markdown("### 💬 Operations & Revenue Co-Pilot")
    
    # Settings in expander for cleaner UI
    with st.expander("⚙️ Settings", expanded=False):
        mode_cols = st.columns([1, 1, 2])
        with mode_cols[0]:
            mode = st.radio("Mode", ["Mock (AI-style)", "Real LLM"], key="chat_mode")
        
        api_key_input = None
        model = "gpt-4o"
        with mode_cols[1]:
            if mode == "Real LLM":
                model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-4o"))
        
        with mode_cols[2]:
            if mode == "Real LLM":
                api_key_input = st.text_input(
                    "OpenAI API Key", 
                    type="password",
                    value=os.getenv("OPENAI_API_KEY", ""),
                    help="Provide your OpenAI API key or set OPENAI_API_KEY env var"
                )
            else:
                st.caption("ℹ️ Mock mode uses retrieval + smart templates (no API needed)")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Helper function to process a question
    def process_question(question: str) -> str:
        """Process a user question and return response."""
        retrieved = index.search(question, top_k=5)

        # Compute comprehensive KPIs
        dispatch_miss_mwh = float(pd.to_numeric(dispatch.get("delta_mwh", 0), errors="coerce").clip(lower=0).sum()) if not dispatch.empty else 0.0
        rcr = float(pd.to_numeric(monthly.get("revenue_capture_ratio", 0), errors="coerce").mean()) if not monthly.empty else float("nan")
        
        top_driver = "Unknown"
        if not attribution.empty and "loss_category" in attribution.columns:
            cat_loss = attribution.groupby("loss_category")["loss_usd"].sum().sort_values(ascending=False)
            if not cat_loss.empty:
                top_driver = str(cat_loss.index[0])
        
        top_component = "ID Fan / Dampers"
        if not attribution.empty and "component" in attribution.columns:
            comp_loss = attribution.groupby("component")["loss_usd"].sum().sort_values(ascending=False)
            if not comp_loss.empty:
                top_component = str(comp_loss.index[0])
        
        heat_dev = float(pd.to_numeric(heat.get("heat_rate_deviation_percent", 0), errors="coerce").mean()) if not heat.empty else 0.0
        event_count = len(filtered.get("events", pd.DataFrame()))

        kpis: dict[str, Any] = {
            "dispatch_miss_mwh": dispatch_miss_mwh,
            "rcr": rcr,
            "top_loss_driver": top_driver,
            "top_component": top_component,
            "heat_rate_dev_pct": heat_dev,
            "event_count": event_count,
        }

        if mode == "Real LLM":
            return call_openai_rag(question, retrieved, kpis, model=model, api_key=api_key_input)
        else:
            return build_mock_response(question, retrieved, kpis)

    # Suggested questions as chips
    st.markdown("**💡 Suggested Questions**")
    quick = st.columns(3)
    if quick[0].button("📊 Summarize recent performance", use_container_width=True):
        question = "Summarize the last 30 days of plant performance. What are the key trends in dispatch misses and revenue capture?"
        st.session_state.chat_history.append({"role": "user", "content": question})
        if mode == "Mock (AI-style)":
            response = process_question(question)
        else:
            with st.spinner("Thinking..."):
                response = process_question(question)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()
    
    if quick[1].button("🎯 How can we improve RCR?", use_container_width=True):
        question = "What are the top 3 actions we should take to improve revenue capture ratio? Prioritize by expected financial impact."
        st.session_state.chat_history.append({"role": "user", "content": question})
        if mode == "Mock (AI-style)":
            response = process_question(question)
        else:
            with st.spinner("Thinking..."):
                response = process_question(question)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()
    
    if quick[2].button("🔍 Why is heat rate degraded?", use_container_width=True):
        question = "Explain why our net station heat rate is deviating from the PPA reference. What are the likely root causes and how do we address them?"
        st.session_state.chat_history.append({"role": "user", "content": question})
        if mode == "Mock (AI-style)":
            response = process_question(question)
        else:
            with st.spinner("Thinking..."):
                response = process_question(question)
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    # Action buttons
    if st.session_state.chat_history:
        action_cols = st.columns([1, 1, 3])
        with action_cols[0]:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()
        with action_cols[1]:
            transcript = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.chat_history])
            st.download_button(
                "📥 Export",
                data=io.StringIO(transcript).getvalue(),
                file_name="chat_transcript.md",
                mime="text/markdown",
                use_container_width=True,
            )

    st.markdown("---")

    # Display chat messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask about plant performance, operations, or troubleshooting..."):
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            if mode == "Mock (AI-style)":
                # Fast display for mock responses - no spinner
                response = process_question(prompt)
                st.markdown(response)
            else:
                # Show spinner for real LLM calls
                with st.spinner("Thinking..."):
                    response = process_question(prompt)
                st.markdown(response)
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="Shakti Thermal Station — Full Potential Demo", layout="wide")
    apply_bain_style()

    root = Path(__file__).resolve().parent
    catalog = load_data_catalog(str(root))
    glossary = load_glossary_map(str(root / "docs"))

    render_header(root / "assets")

    checks = run_startup_checks(catalog)
    unit, start_dt, end_dt, resolution = render_sidebar(catalog, checks)
    filtered = _filter_core(catalog, unit=unit, start_dt=start_dt, end_dt=end_dt)

    tabs = st.tabs([
        "Data Mapping & Ontology",
        "Generation View",
        "Revenue View",
        "GenAI Chatbot",
    ])

    with tabs[0]:
        render_tab_mapping(catalog, filtered, start_dt, end_dt)

    with tabs[1]:
        render_tab_generation(catalog, filtered, unit, start_dt, end_dt, resolution, glossary)

    with tabs[2]:
        render_tab_revenue(catalog, filtered, glossary)

    with tabs[3]:
        render_tab_chatbot(filtered, root / "docs", glossary)


if __name__ == "__main__":
    main()
