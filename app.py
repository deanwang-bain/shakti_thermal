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
    generate_evidence_summary,
    generate_llm_insight,
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
    heat_rate_anomaly_table,
    heat_rate_sync_chart,
    heat_rate_trend_chart,
    historian_overlay_chart,
    loss_treemap,
    lost_revenue_driver_chart,
    rcr_over_time_chart,
    revenue_absolute_chart,
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
        show_outages = st.toggle("Show outages", value=True, key="gen_outages")
    with ctrl[1]:
        show_annotations = st.toggle("Show annotations", value=True, key="gen_annotations")

    dispatch_plot = downsample_for_plotting(dispatch, resolution=resolution)
    
    # Auto-show 5-min misses only when resolution is 5-min
    show_misses = (resolution == "5-min")

    st.plotly_chart(
        generation_main_chart(dispatch_plot, events, show_outages=show_outages, show_misses=show_misses),
        use_container_width=True,
    )

    # LLM Insight Callout
    st.markdown("#### 💡 AI-Generated Insight")
    with st.expander("View Generation Performance Analysis", expanded=False):
        # Compute KPIs for LLM
        dispatch_miss_mwh = float(pd.to_numeric(dispatch.get("delta_mwh", 0), errors="coerce").clip(lower=0).sum()) if not dispatch.empty else 0.0
        
        attr = filtered.get("attribution", pd.DataFrame())
        top_driver = "Unknown"
        if not attr.empty and "loss_category" in attr.columns:
            cat_loss = attr.groupby("loss_category")["loss_usd"].sum().sort_values(ascending=False)
            if not cat_loss.empty:
                top_driver = str(cat_loss.index[0])
        
        kpis = {
            "dispatch_miss_mwh": dispatch_miss_mwh,
            "rcr": 0.0,  # Not primary focus for generation insight
            "top_loss_driver": top_driver,
            "heat_rate_dev_pct": 0.0,
            "event_count": len(events) if not events.empty else 0,
        }
        
        # Get mode from session state if exists
        mode = "mock"
        if "chat_mode" in st.session_state:
            mode = "mock" if st.session_state.chat_mode == "Mock (AI-style)" else "real"
        
        insight = generate_llm_insight(
            data_context=f"Dispatch performance and generation gaps over selected period at {resolution} resolution",
            kpis=kpis,
            mode=mode,
        )
        st.markdown(insight)

    st.markdown("#### Dispatch Gap Attribution by Root Cause")
    st.plotly_chart(
        dispatch_gap_attribution_chart(dispatch, resolution=resolution),
        use_container_width=True,
    )

    st.markdown("#### Historian Correlation Panel")
    if dispatch.empty or "timestamp" not in dispatch.columns:
        st.info("Dispatch time series unavailable.")
        return

    # Prepare merged historian data
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

    # Get available numeric signals (exclude timestamp, unit_id, net_generation_mw)
    available_signals = [
        c for c in merged.columns 
        if c not in ["timestamp", "unit_id", "net_generation_mw"] 
        and pd.api.types.is_numeric_dtype(merged[c])
    ]
    
    if not available_signals:
        st.info("No historian signals available in selected window.")
        return
    
    # Default signals for demo (ID Fan and Draft pressure for unstable draft story)
    default_signals = [s for s in ["IDFanSpeed_pct", "DamperPosition_pct", "FurnaceDraftPressure_Pa"] if s in available_signals]
    if not default_signals:
        default_signals = available_signals[:3]  # Fallback to first 3 if defaults not found
    
    selected_signals = st.multiselect(
        "Select signals to analyze",
        options=available_signals,
        default=default_signals,
        help="Choose SCADA tags to show in correlation table and overlay chart. Common demo signals: IDFanSpeed_pct, DamperPosition_pct, FurnaceDraftPressure_Pa",
        key="gen_signals"
    )
    
    if not selected_signals:
        st.info("Select one or more signals above to display correlation analysis and overlay chart.")
        return

    # Compute correlations for selected signals
    corr_rows = []
    for col in selected_signals:
        if col in merged.columns:
            x = pd.to_numeric(merged[col], errors="coerce")
            y = pd.to_numeric(merged["net_generation_mw"], errors="coerce")
            corr = x.corr(y)
            corr_rows.append({"signal": col, "correlation_to_net_generation": corr})
    
    corr_df = pd.DataFrame(corr_rows).sort_values("correlation_to_net_generation", key=lambda s: s.abs(), ascending=False)
    
    if corr_df.empty:
        st.info("Unable to compute correlations for selected signals.")
        return
    
    st.dataframe(corr_df, use_container_width=True, hide_index=True)
    
    st.plotly_chart(historian_overlay_chart(merged, selected_signals), use_container_width=True)
    if show_annotations:
        st.success(correlation_explanation(corr_df))


def render_tab_revenue(
    catalog: DataCatalog,
    filtered: dict[str, pd.DataFrame],
    glossary: dict[str, str],
) -> None:
    monthly = filtered.get("monthly_summary", pd.DataFrame())
    daily = filtered.get("daily_summary", pd.DataFrame())
    energy = filtered.get("energy_settlement", pd.DataFrame())
    capacity = filtered.get("capacity", pd.DataFrame())
    attr = filtered.get("attribution", pd.DataFrame())
    penalties = filtered.get("penalties", pd.DataFrame())
    fuel = filtered.get("fuel_cost", pd.DataFrame())
    events = filtered.get("events", pd.DataFrame())
    work_orders = filtered.get("work_orders", pd.DataFrame())
    media = filtered.get("media", pd.DataFrame())

    # Normalize time columns
    if "month" in monthly.columns:
        monthly["month"] = pd.to_datetime(monthly["month"], errors="coerce", utc=True)
    if "date" in daily.columns:
        daily["date"] = pd.to_datetime(daily["date"], errors="coerce", utc=True)

    # Granularity toggle
    st.markdown("#### Revenue Performance Controls")
    ctrl_cols = st.columns([1, 1, 2])
    with ctrl_cols[0]:
        granularity = st.radio("Granularity", ["Monthly", "Daily"], horizontal=True, key="rev_granularity")
    with ctrl_cols[1]:
        view_mode = st.radio("View Mode", ["% (RCR)", "Absolute ($)"], horizontal=True, key="rev_view_mode")
    with ctrl_cols[2]:
        show_ann = st.toggle("Show intervention annotations", value=True, key="rev_annotations")
    
    # Select appropriate dataset based on granularity
    revenue_df = monthly if granularity == "Monthly" else daily
    gran_str = "monthly" if granularity == "Monthly" else "daily"
    
    # Compute KPIs
    if not revenue_df.empty:
        time_col = "month" if granularity == "Monthly" else "date"
        if time_col in revenue_df.columns:
            current_period = revenue_df.sort_values(time_col).tail(1)
        else:
            current_period = revenue_df
    else:
        current_period = revenue_df

    kpi_current = compute_revenue_kpis(current_period, energy, capacity, penalties, fuel)
    kpi_window = compute_revenue_kpis(revenue_df, energy, capacity, penalties, fuel)
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
        if view_mode == "% (RCR)":
            st.plotly_chart(rcr_over_time_chart(revenue_df, show_annotations=show_ann), use_container_width=True)
        else:
            st.plotly_chart(revenue_absolute_chart(revenue_df, granularity=gran_str, show_annotations=show_ann), use_container_width=True)

    with right:
        # Only show Capacity, Energy, Penalty (no Efficiency)
        attr_filtered = attr.copy()
        if not attr_filtered.empty and "loss_category" in attr_filtered.columns:
            # Filter to only these categories
            valid_categories = ["Capacity", "Energy", "Penalty"]
            attr_filtered = attr_filtered[attr_filtered["loss_category"].isin(valid_categories)]
        st.plotly_chart(lost_revenue_driver_chart(attr_filtered), use_container_width=True)

    # LLM Insight Callout
    st.markdown("#### 💡 AI-Generated Insight")
    with st.expander("View Revenue Optimization Recommendations", expanded=False):
        # Compute KPIs for LLM
        dispatch = filtered.get("dispatch", pd.DataFrame())
        dispatch = standardize_dispatch_columns(dispatch)
        
        dispatch_miss_mwh = float(pd.to_numeric(dispatch.get("delta_mwh", 0), errors="coerce").clip(lower=0).sum()) if not dispatch.empty else 0.0
        rcr = float(pd.to_numeric(revenue_df.get("revenue_capture_ratio", 0), errors="coerce").mean()) if not revenue_df.empty else float("nan")
        
        top_driver = "Unknown"
        if not attr_filtered.empty and "loss_category" in attr_filtered.columns:
            cat_loss = attr_filtered.groupby("loss_category")["loss_usd"].sum().sort_values(ascending=False)
            if not cat_loss.empty:
                top_driver = str(cat_loss.index[0])
        
        kpis = {
            "dispatch_miss_mwh": dispatch_miss_mwh,
            "rcr": rcr,
            "top_loss_driver": top_driver,
            "heat_rate_dev_pct": 0.0,  # Not relevant for revenue insight
            "event_count": len(events) if not events.empty else 0,
        }
        
        # Get mode from session state if exists (for consistency with chatbot)
        mode = "mock"
        if "chat_mode" in st.session_state:
            mode = "mock" if st.session_state.chat_mode == "Mock (AI-style)" else "real"
        
        insight = generate_llm_insight(
            data_context=f"Revenue trends over selected {granularity.lower()} period",
            kpis=kpis,
            mode=mode,
        )
        st.markdown(insight)

    st.markdown("#### Lost Revenue Drilldown")
    
    # REMOVE Category filter, keep only System/Subsystem/Component
    sys_col, sub_col, comp_col = st.columns(3)

    attr_drilldown = attr_filtered.copy()
    
    systems = ["All"] + sorted(attr_drilldown.get("system", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_drilldown.empty else ["All"]
    system = sys_col.selectbox("System", systems, key="rev_system")
    if system != "All" and "system" in attr_drilldown.columns:
        attr_drilldown = attr_drilldown[attr_drilldown["system"].astype(str) == system]

    subsystems = ["All"] + sorted(attr_drilldown.get("subsystem", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_drilldown.empty else ["All"]
    subsystem = sub_col.selectbox("Subsystem", subsystems, key="rev_subsystem")
    if subsystem != "All" and "subsystem" in attr_drilldown.columns:
        attr_drilldown = attr_drilldown[attr_drilldown["subsystem"].astype(str) == subsystem]
    
    components = ["All"] + sorted(attr_drilldown.get("component", pd.Series(dtype=str)).dropna().unique().tolist()) if not attr_drilldown.empty else ["All"]
    component = comp_col.selectbox("Component", components, key="rev_component")
    if component != "All" and "component" in attr_drilldown.columns:
        attr_drilldown = attr_drilldown[attr_drilldown["component"].astype(str) == component]

    st.plotly_chart(loss_treemap(attr_drilldown), use_container_width=True)

    # Top N components table
    top_n = st.slider("Top N components", min_value=5, max_value=30, value=10, key="rev_top_n")
    top_components_df = top_loss_components(attr_drilldown, top_n=top_n)
    st.dataframe(top_components_df, use_container_width=True)
    _download_csv(top_components_df, "Export attribution table CSV", "attribution_top_components.csv")

    # Evidence Panel - Enhanced with Voice, Images, Events
    selected_component = st.selectbox(
        "Selected component for evidence drilldown", 
        [""] + [c for c in components if c != "All"],
        key="rev_selected_component"
    )

    if selected_component:
        st.markdown("---")
        st.markdown("#### 🔍 Evidence Panel: Detailed Analysis")
        
        detail = attr_drilldown[attr_drilldown.get("component", "").astype(str) == selected_component]
        linked_event_ids = detail.get("linked_event_id", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()
        
        # Get linked asset ID for component
        linked_asset_ids = []
        if not detail.empty and "component" in detail.columns:
            # Try to find asset_id from asset hierarchy
            asset_df = catalog.tables.get("asset_hierarchy", pd.DataFrame())
            if not asset_df.empty and "canonical_name" in asset_df.columns:
                matches = asset_df[asset_df["canonical_name"].astype(str).str.contains(selected_component, case=False, na=False)]
                if not matches.empty:
                    linked_asset_ids = matches["asset_id"].dropna().astype(str).unique().tolist()
        
        # Related Events
        related_events = events[events.get("event_id", "").astype(str).isin(linked_event_ids)] if not events.empty and "event_id" in events.columns else pd.DataFrame()
        
        # Also include events linked by asset_id (broader match)
        if linked_asset_ids and not events.empty and "linked_asset_id" in events.columns:
            asset_events = events[events.get("linked_asset_id", "").astype(str).isin(linked_asset_ids)]
            related_events = pd.concat([related_events, asset_events]).drop_duplicates()
        
        # Related Work Orders
        related_wos = work_orders[work_orders.get("linked_event_id", "").astype(str).isin(linked_event_ids)] if not work_orders.empty and "linked_event_id" in work_orders.columns else pd.DataFrame()
        
        # Also match work orders by asset_id
        if linked_asset_ids and not work_orders.empty and "standard_asset_id_truth" in work_orders.columns:
            asset_wos = work_orders[work_orders.get("standard_asset_id_truth", "").astype(str).isin(linked_asset_ids)]
            related_wos = pd.concat([related_wos, asset_wos]).drop_duplicates()
        
        # Related Media - Images and Voice
        related_media = pd.DataFrame()
        if not media.empty:
            # Match by linked_event_id
            if "linked_event_id" in media.columns:
                media_by_event = media[media.get("linked_event_id", "").astype(str).isin(linked_event_ids)]
                related_media = pd.concat([related_media, media_by_event])
            
            # Match by linked_asset_id
            if linked_asset_ids and "linked_asset_id" in media.columns:
                media_by_asset = media[media.get("linked_asset_id", "").astype(str).isin(linked_asset_ids)]
                related_media = pd.concat([related_media, media_by_asset])
            
            related_media = related_media.drop_duplicates()
        
        # Split media by type
        images = related_media[related_media.get("media_type", "") == "image"] if not related_media.empty else pd.DataFrame()
        voice = related_media[related_media.get("media_type", "") == "audio"] if not related_media.empty else pd.DataFrame()
        
        # Display evidence in tabs
        ev_tabs = st.tabs(["Events", "Work Orders", "Images", "Voice Recordings", "LLM Summary"])
        
        with ev_tabs[0]:
            st.write(f"**Related Events** ({len(related_events)})")
            if related_events.empty:
                st.caption("(No events affecting this component in selected date range)")
            else:
                # Show key columns
                cols_to_show = ["event_id", "type", "description", "start_time", "duration_hours", "severity"]
                cols_to_show = [c for c in cols_to_show if c in related_events.columns]
                st.dataframe(related_events[cols_to_show].head(20), use_container_width=True)
        
        with ev_tabs[1]:
            st.write(f"**Linked Work Orders** ({len(related_wos)})")
            if related_wos.empty:
                st.caption("(No work orders linked to this component)")
            else:
                cols_to_show = ["work_order_id", "title", "status", "priority", "created_at", "completed_at"]
                cols_to_show = [c for c in cols_to_show if c in related_wos.columns]
                st.dataframe(related_wos[cols_to_show].head(20), use_container_width=True)
        
        with ev_tabs[2]:
            st.write(f"**Images** ({len(images)})")
            if images.empty:
                st.caption("(No images available for this component)")
            else:
                for idx, row in images.head(10).iterrows():
                    st.markdown(f"**{row.get('media_id', 'N/A')}**: {row.get('caption', 'No caption')}")
                    st.caption(f"📁 {row.get('file_path_placeholder', 'N/A')} | 🕒 {row.get('timestamp', 'N/A')}")
                    if pd.notna(row.get("content_text")) and str(row.get("content_text")).strip():
                        st.text(f"Content: {row.get('content_text')}")
                    st.markdown("---")
        
        with ev_tabs[3]:
            st.write(f"**Voice Recordings** ({len(voice)})")
            if voice.empty:
                st.caption("(No voice recordings available for this component)")
            else:
                for idx, row in voice.head(10).iterrows():
                    st.markdown(f"**{row.get('media_id', 'N/A')}**: {row.get('caption', 'No caption')}")
                    st.caption(f"📁 {row.get('file_path_placeholder', 'N/A')} | 🕒 {row.get('timestamp', 'N/A')}")
                    if pd.notna(row.get("transcript_text")) and str(row.get("transcript_text")).strip():
                        st.info(f"**Transcript**: {row.get('transcript_text')}")
                    st.markdown("---")
        
        with ev_tabs[4]:
            st.write("**LLM-Generated Evidence Summary**")
            
            # Get mode from session state
            mode = "mock"
            if "chat_mode" in st.session_state:
                mode = "mock" if st.session_state.chat_mode == "Mock (AI-style)" else "real"
            
            summary = generate_evidence_summary(
                events_df=related_events,
                work_orders_df=related_wos,
                media_df=related_media,
                mode=mode,
            )
            st.markdown(summary)
        
        total_loss = pd.to_numeric(detail.get("loss_usd", 0), errors="coerce").sum()
        st.success(
            f"**{selected_component}** contributes **${total_loss:,.0f}** in revenue loss over the selected period. "
            f"Reducing repeat event exposure should improve capture ratio."
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


def render_tab_heat_rate(
    catalog: DataCatalog,
    filtered: dict[str, pd.DataFrame],
    start_dt: pd.Timestamp,
    end_dt: pd.Timestamp,
) -> None:
    """New Heat Rate analysis tab with daily/monthly views and anomaly detection."""
    heat_daily = filtered.get("heat_rate_daily", pd.DataFrame())
    heat_monthly = filtered.get("heat_rate_monthly", pd.DataFrame())
    events = filtered.get("events", pd.DataFrame())
    
    st.markdown("#### Heat Rate Analysis")
    
    # Granularity toggle
    ctrl_cols = st.columns([1, 1, 2])
    with ctrl_cols[0]:
        granularity = st.radio("Granularity", ["Daily", "Monthly"], horizontal=True, key="hr_granularity")
    with ctrl_cols[1]:
        highlight_anomalies = st.toggle("Highlight Anomalies", value=True, key="hr_anomalies")
    
    # Select appropriate dataset
    heat_df = heat_daily if granularity == "Daily" else heat_monthly
    gran_str = "daily" if granularity == "Daily" else "monthly"
    
    if heat_df.empty:
        st.warning(f"Heat rate {gran_str} data unavailable.")
        return
    
    # Normalize time columns
    time_col = "date" if granularity == "Daily" else "month"
    if time_col in heat_df.columns:
        heat_df[time_col] = pd.to_datetime(heat_df[time_col], errors="coerce", utc=True)
    
    # Compute summary KPIs
    avg_hr = heat_df.get("net_station_heat_rate", pd.Series(dtype=float)).mean()
    avg_ref = heat_df.get("ppa_reference_heat_rate", pd.Series(dtype=float)).mean()
    avg_dev = heat_df.get("heat_rate_deviation_percent", pd.Series(dtype=float)).mean()
    total_fuel_impact = heat_df.get("fuel_cost_impact_usd", pd.Series(dtype=float)).sum()
    
    kpi_cols = st.columns(4)
    kpi_cols[0].metric("Avg NSHR", f"{avg_hr:.0f} Btu/kWh" if pd.notna(avg_hr) else "N/A")
    kpi_cols[1].metric("Avg PPA Ref", f"{avg_ref:.0f} Btu/kWh" if pd.notna(avg_ref) else "N/A")
    kpi_cols[2].metric("Avg Deviation", f"{avg_dev:.2f}%" if pd.notna(avg_dev) else "N/A")
    kpi_cols[3].metric("Total Fuel Impact", fmt_usd(total_fuel_impact))
    
    # Trend chart
    st.plotly_chart(
        heat_rate_trend_chart(heat_df, granularity=gran_str, highlight_anomalies=highlight_anomalies),
        use_container_width=True,
    )
    
    # LLM Insight Callout
    st.markdown("#### 💡 AI-Generated Heat Rate Insight")
    with st.expander("View Heat Rate Optimization Analysis", expanded=False):
        # Compute KPIs for LLM
        attr = filtered.get("attribution", pd.DataFrame())
        dispatch = filtered.get("dispatch", pd.DataFrame())
        dispatch = standardize_dispatch_columns(dispatch)
        
        dispatch_miss_mwh = float(pd.to_numeric(dispatch.get("delta_mwh", 0), errors="coerce").clip(lower=0).sum()) if not dispatch.empty else 0.0
        
        kpis = {
            "dispatch_miss_mwh": dispatch_miss_mwh,
            "rcr": 0.0,
            "top_loss_driver": "Heat Rate",
            "heat_rate_dev_pct": avg_dev if pd.notna(avg_dev) else 0.0,
            "event_count": len(events) if not events.empty else 0,
        }
        
        # Get mode from session state if exists
        mode = "mock"
        if "chat_mode" in st.session_state:
            mode = "mock" if st.session_state.chat_mode == "Mock (AI-style)" else "real"
        
        insight = generate_llm_insight(
            data_context=f"Heat rate trends and efficiency analysis over selected {granularity.lower()} period",
            kpis=kpis,
            mode=mode,
        )
        st.markdown(insight)
    
    # Top anomalies table (only for daily view)
    if granularity == "Daily" and not heat_daily.empty:
        st.markdown("#### Top Heat Rate Anomalies")
        
        top_n = st.slider("Top N anomalies", min_value=5, max_value=30, value=10, key="hr_top_n")
        anomaly_table = heat_rate_anomaly_table(heat_daily, top_n=top_n)
        
        if anomaly_table.empty:
            st.info("No anomalies detected in selected period.")
        else:
            st.dataframe(anomaly_table, use_container_width=True, hide_index=True)
            _download_csv(anomaly_table, "Export anomalies CSV", "heat_rate_anomalies.csv")
            
            # Event correlation
            st.markdown("#### Event Correlation Analysis")
            st.caption("Events occurring within ±24 hours of heat rate anomalies")
            
            if not events.empty and "start_time" in events.columns and not anomaly_table.empty and "date" in anomaly_table.columns:
                # Normalize event timestamps
                events_corr = events.copy()
                events_corr["start_time"] = pd.to_datetime(events_corr["start_time"], errors="coerce", utc=True)
                
                # Find events near anomaly dates
                correlated_events = []
                for _, anomaly_row in anomaly_table.iterrows():
                    anomaly_date = pd.to_datetime(anomaly_row["date"])
                    if pd.isna(anomaly_date):
                        continue
                    
                    # Ensure timezone consistency (localize to UTC if naive)
                    if anomaly_date.tzinfo is None:
                        anomaly_date = anomaly_date.tz_localize("UTC")
                    
                    # Find events within ±24 hours
                    window_start = anomaly_date - pd.Timedelta(hours=24)
                    window_end = anomaly_date + pd.Timedelta(hours=24)
                    
                    nearby = events_corr[
                        (events_corr["start_time"] >= window_start) & 
                        (events_corr["start_time"] <= window_end)
                    ]
                    
                    for _, event_row in nearby.iterrows():
                        correlated_events.append({
                            "anomaly_date": anomaly_date.date(),
                            "event_id": event_row.get("event_id", "N/A"),
                            "event_type": event_row.get("type", "N/A"),
                            "event_time": event_row.get("start_time"),
                            "description": event_row.get("description", "N/A")[:80],
                            "linked_asset": event_row.get("linked_asset_id", "N/A"),
                        })
                
                if correlated_events:
                    corr_df = pd.DataFrame(correlated_events)
                    st.dataframe(corr_df.head(20), use_container_width=True, hide_index=True)
                    
                    # Try to map events to system/subsystem using asset hierarchy
                    st.markdown("##### System/Subsystem Breakdown")
                    asset_df = catalog.tables.get("asset_hierarchy", pd.DataFrame())
                    
                    if not asset_df.empty and "asset_id" in asset_df.columns:
                        # Determine which columns are available
                        merge_cols = ["asset_id"]
                        display_cols = []
                        
                        if "system" in asset_df.columns:
                            merge_cols.append("system")
                            display_cols.append("system")
                        if "subsystem" in asset_df.columns:
                            merge_cols.append("subsystem")
                            display_cols.append("subsystem")
                        
                        if display_cols:
                            # Merge to get system/subsystem info
                            merged = corr_df.merge(
                                asset_df[merge_cols],
                                left_on="linked_asset",
                                right_on="asset_id",
                                how="left"
                            )
                            
                            # Show breakdown by available hierarchy
                            primary_col = display_cols[0]  # Use first available (system or subsystem)
                            if primary_col in merged.columns:
                                col_counts = merged[primary_col].value_counts()
                                if not col_counts.empty:
                                    st.bar_chart(col_counts)
                                    st.caption(f"Most affected {primary_col}: {col_counts.index[0]}")
                                else:
                                    st.info("No hierarchy mapping available for correlated events.")
                            else:
                                st.info("No hierarchy mapping available for correlated events.")
                        else:
                            st.info("Asset hierarchy does not contain system/subsystem columns.")
                    else:
                        st.info("Asset hierarchy unavailable for event mapping.")
                else:
                    st.info("No events found within ±24 hours of detected anomalies.")
            else:
                st.info("Event correlation unavailable (missing event timestamps or anomaly data).")


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
        "Revenue View",
        "Generation View",
        "Heat Rate Analysis",
        "GenAI Chatbot",
    ])

    with tabs[0]:
        render_tab_mapping(catalog, filtered, start_dt, end_dt)

    with tabs[1]:
        render_tab_revenue(catalog, filtered, glossary)

    with tabs[2]:
        render_tab_generation(catalog, filtered, unit, start_dt, end_dt, resolution, glossary)

    with tabs[3]:
        render_tab_heat_rate(catalog, filtered, start_dt, end_dt)

    with tabs[4]:
        render_tab_chatbot(filtered, root / "docs", glossary)


if __name__ == "__main__":
    main()
