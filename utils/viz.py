"""Plotly figure builders."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from utils.metrics import detect_5min_miss_points, standardize_dispatch_columns


def generation_main_chart(
    dispatch_df: pd.DataFrame,
    events_df: pd.DataFrame,
    show_outages: bool,
    show_misses: bool,
) -> go.Figure:
    """Main generation chart with delta shading and markers."""
    df = standardize_dispatch_columns(dispatch_df)
    fig = go.Figure()
    if df.empty or "timestamp" not in df.columns:
        return fig

    df = df.sort_values("timestamp")

    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df.get("available_mw"),
            mode="lines",
            name="Available Capacity",
            line=dict(color="#9CA3AF", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df.get("dispatch_target_mw"),
            mode="lines",
            name="Dispatch Target",
            line=dict(color="#CB2026", width=2),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df.get("net_generation_mw"),
            mode="lines",
            name="Net Generation",
            line=dict(color="#2563EB", width=2),
        )
    )

    if "delta_mw" in df.columns:
        gap = df["delta_mw"].clip(lower=0)
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df.get("net_generation_mw") + gap,
                mode="lines",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df.get("net_generation_mw"),
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor="rgba(203, 32, 38, 0.18)",
                name="Dispatch Gap (delta > 0)",
                hovertemplate="Gap shading<extra></extra>",
            )
        )

    if show_misses:
        misses = detect_5min_miss_points(df)
        miss_df = df[misses]
        if not miss_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=miss_df["timestamp"],
                    y=miss_df["net_generation_mw"],
                    mode="markers",
                    marker=dict(color="#CB2026", size=6, symbol="x"),
                    name="5-min Miss",
                )
            )

    if show_outages and not events_df.empty:
        events = events_df.copy()
        for col in ["start_time", "end_time"]:
            if col in events.columns:
                events[col] = pd.to_datetime(events[col], errors="coerce", utc=True)
        events = events.dropna(subset=["start_time"])
        for row in events.head(80).to_dict("records"):
            start = row.get("start_time")
            end = row.get("end_time")
            if pd.isna(start):
                continue
            if pd.isna(end):
                fig.add_vline(x=start, line_width=1, line_dash="dot", line_color="#F59E0B")
            else:
                fig.add_vrect(
                    x0=start,
                    x1=end,
                    fillcolor="rgba(245, 158, 11, 0.12)",
                    line_width=0,
                    annotation_text=str(row.get("type", "Outage")),
                    annotation_position="top left",
                )

    fig.update_layout(
        height=460,
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="MW",
        xaxis_title="Timestamp",
    )
    return fig


def dispatch_gap_attribution_chart(dispatch_df: pd.DataFrame, resolution: str = "daily") -> go.Figure:
    """Stacked bar chart showing dispatch gap breakdown by root cause category."""
    df = standardize_dispatch_columns(dispatch_df)
    
    if df.empty or "timestamp" not in df.columns or "root_cause_category" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="No root cause attribution data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig
    
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    df = df.dropna(subset=["timestamp", "root_cause_category"])
    
    # Only consider positive gaps (misses)
    df["gap_mwh"] = pd.to_numeric(df.get("delta_mwh", 0), errors="coerce").clip(lower=0)
    
    # Aggregate by time period and root cause
    if resolution == "hourly":
        df["period"] = df["timestamp"].dt.floor("H")
    else:
        df["period"] = df["timestamp"].dt.floor("D")
    
    pivot = df.groupby(["period", "root_cause_category"])["gap_mwh"].sum().reset_index()
    pivot = pivot.pivot(index="period", columns="root_cause_category", values="gap_mwh").fillna(0)
    
    if pivot.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No dispatch gaps in selected period",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig
    
    # Create stacked bar chart
    fig = go.Figure()
    
    colors = {
        "Boiler-side": "#CB2026",
        "Turbine-side": "#FF6B6B",
        "Cooling constraints": "#FFA500",
        "Fuel quality": "#FFD700",
        "Planned Maintenance": "#87CEEB",
        "Other": "#CCCCCC",
    }
    
    for col in pivot.columns:
        fig.add_trace(
            go.Bar(
                x=pivot.index,
                y=pivot[col],
                name=str(col),
                marker_color=colors.get(str(col), "#CCCCCC"),
            )
        )
    
    fig.update_layout(
        barmode="stack",
        title="Dispatch Gap Attribution by Root Cause",
        xaxis_title="Time Period",
        yaxis_title="Missed Generation (MWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        height=350,
    )
    
    return fig


def heat_rate_sync_chart(heat_df: pd.DataFrame) -> go.Figure:
    """Heat-rate and aux-load synchronized chart."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    if heat_df.empty or "timestamp" not in heat_df.columns:
        return fig

    df = heat_df.sort_values("timestamp").copy()
    
    # Clean PPA reference: set to NaN during offline hours for realistic visualization
    # During outages/offline periods, heat rate reference is not applicable
    if "ppa_reference_heat_rate" in df.columns:
        # Identify offline hours: low fuel input or low generation
        fuel_col = "fuel_heat_input_mmbtu" if "fuel_heat_input_mmbtu" in df.columns else None
        gen_col = "net_mw_est" if "net_mw_est" in df.columns else None
        
        offline_mask = pd.Series(False, index=df.index)
        if fuel_col and fuel_col in df.columns:
            offline_mask |= (pd.to_numeric(df[fuel_col], errors="coerce") < 100)  # < 100 MMBtu/hr ~ offline
        if gen_col and gen_col in df.columns:
            offline_mask |= (pd.to_numeric(df[gen_col], errors="coerce") < 50)  # < 50 MW ~ offline
        
        # Set reference to NaN during offline hours
        df.loc[offline_mask, "ppa_reference_heat_rate"] = float("nan")
    
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df.get("net_station_heat_rate"),
            mode="lines",
            name="NSHR",
            line=dict(color="#2563EB", width=2),
        ),
        secondary_y=False,
    )
    if "ppa_reference_heat_rate" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df.get("ppa_reference_heat_rate"),
                mode="lines",
                name="PPA Reference Heat Rate",
                line=dict(color="#6B7280", width=2, dash="dash"),
                connectgaps=False,  # Don't connect across NaN gaps
            ),
            secondary_y=False,
        )

    aux_col = "aux_load_mw" if "aux_load_mw" in df.columns else "AuxLoad_MW" if "AuxLoad_MW" in df.columns else None
    if aux_col:
        fig.add_trace(
            go.Scatter(
                x=df["timestamp"],
                y=df[aux_col],
                mode="lines",
                name="Aux Load",
                line=dict(color="#CB2026", width=2),
            ),
            secondary_y=True,
        )

    fig.update_yaxes(title_text="Heat Rate", secondary_y=False)
    fig.update_yaxes(title_text="Aux Load (MW)", secondary_y=True)
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=25, b=10))
    return fig


def historian_overlay_chart(merged_df: pd.DataFrame, signals: list[str]) -> go.Figure:
    """Small multiples-like overlay for selected signals."""
    fig = go.Figure()
    if merged_df.empty:
        return fig

    for sig in signals:
        if sig in merged_df.columns:
            fig.add_trace(go.Scatter(x=merged_df["timestamp"], y=merged_df[sig], mode="lines", name=sig))

    if "net_generation_mw" in merged_df.columns:
        fig.add_trace(
            go.Scatter(
                x=merged_df["timestamp"],
                y=merged_df["net_generation_mw"],
                mode="lines",
                name="net_generation_mw",
                line=dict(width=3, color="#111827"),
            )
        )
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
    return fig


def rcr_over_time_chart(monthly_df: pd.DataFrame, show_annotations: bool = True) -> go.Figure:
    """Revenue capture ratio over time."""
    fig = go.Figure()
    if monthly_df.empty:
        return fig

    df = monthly_df.copy()
    if "month" in df.columns:
        df["month"] = pd.to_datetime(df["month"], errors="coerce", utc=True)

    fig.add_trace(
        go.Scatter(
            x=df.get("month"),
            y=df.get("revenue_capture_ratio", 0) * 100,
            mode="lines+markers",
            name="RCR (%)",
            line=dict(color="#CB2026", width=2),
        )
    )

    fig.add_hline(y=100, line_dash="dash", line_color="#6B7280", annotation_text="100% Benchmark")

    if show_annotations:
        interventions = [
            {"date": "2024-06-15", "label": "Draft Control Tuning"},
            {"date": "2024-10-01", "label": "Condenser Cleaning"},
        ]
        for item in interventions:
            x_dt = pd.Timestamp(item["date"]).to_pydatetime()
            fig.add_shape(
                type="line",
                x0=x_dt,
                x1=x_dt,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color="#2563EB", dash="dot", width=1.5),
            )
            fig.add_annotation(
                x=x_dt,
                y=1.02,
                xref="x",
                yref="paper",
                text=item["label"],
                showarrow=False,
                font=dict(color="#2563EB", size=11),
            )

    fig.update_layout(height=320, yaxis_title="RCR (%)", xaxis_title="Month", margin=dict(l=20, r=20, t=35, b=20))
    return fig


def lost_revenue_driver_chart(attribution_df: pd.DataFrame) -> go.Figure:
    """Stacked bar by loss category."""
    if attribution_df.empty:
        return go.Figure()

    df = attribution_df.copy()
    df["loss_usd"] = pd.to_numeric(df.get("loss_usd", 0), errors="coerce").fillna(0)
    grouped = df.groupby(["date", "loss_category"], dropna=False)["loss_usd"].sum().reset_index()
    grouped["date"] = pd.to_datetime(grouped["date"], errors="coerce", utc=True)
    fig = px.bar(grouped, x="date", y="loss_usd", color="loss_category", barmode="stack")
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=25, b=20), yaxis_title="Loss (USD)")
    return fig


def loss_treemap(attribution_df: pd.DataFrame) -> go.Figure:
    """Treemap for system -> subsystem -> component losses."""
    if attribution_df.empty:
        return go.Figure()

    df = attribution_df.copy()
    df["loss_usd"] = pd.to_numeric(df.get("loss_usd", 0), errors="coerce").fillna(0)
    fig = px.treemap(
        df,
        path=["system", "subsystem", "component"],
        values="loss_usd",
        color="loss_usd",
        color_continuous_scale="Reds",
    )
    fig.update_layout(height=430, margin=dict(l=10, r=10, t=35, b=10))
    return fig
