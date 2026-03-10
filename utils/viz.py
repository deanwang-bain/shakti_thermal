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

    fig.update_layout(height=320, yaxis_title="RCR (%)", xaxis_title="Month", margin=dict(l=20, r=20, t=35, b=60),
                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
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
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=25, b=60), yaxis_title="Loss (USD)",
                      legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5))
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


def revenue_absolute_chart(
    revenue_df: pd.DataFrame,
    granularity: str = "monthly",
    show_annotations: bool = True,
) -> go.Figure:
    """Absolute revenue chart: actual vs target with loss as shaded area."""
    fig = go.Figure()
    if revenue_df.empty:
        return fig

    df = revenue_df.copy()
    time_col = "month" if granularity == "monthly" else "date"
    
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
        df = df.sort_values(time_col)
    
    # Determine target column name
    target_col = "max_potential_revenue" if "max_potential_revenue" in df.columns else "revenue_target"
    actual_col = "actual_total_revenue"
    
    if target_col not in df.columns or actual_col not in df.columns:
        return fig
    
    # Add target revenue line
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df[target_col],
            mode="lines",
            name="Target Revenue (Max Potential)",
            line=dict(color="#6B7280", width=2, dash="dash"),
        )
    )
    
    # Add actual revenue line
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df[actual_col],
            mode="lines+markers",
            name="Actual Revenue",
            line=dict(color="#2563EB", width=2),
        )
    )
    
    # Add shaded area for revenue loss
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df[target_col],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df[actual_col],
            mode="lines",
            line=dict(width=0),
            fill="tonexty",
            fillcolor="rgba(203, 32, 38, 0.18)",
            name="Revenue Loss",
            hovertemplate="Revenue Loss<extra></extra>",
        )
    )
    
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
    
    fig.update_layout(
        height=320,
        yaxis_title="Revenue (USD)",
        xaxis_title="Month" if granularity == "monthly" else "Date",
        margin=dict(l=20, r=20, t=35, b=60),
        legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5),
    )
    return fig


def heat_rate_trend_chart(
    heat_rate_df: pd.DataFrame,
    granularity: str = "daily",
    highlight_anomalies: bool = True,
) -> go.Figure:
    """Heat rate trend chart with anomaly highlighting, PPA reference, and gross heat rate."""
    fig = go.Figure()
    if heat_rate_df.empty:
        return fig
    
    df = heat_rate_df.copy()
    time_col = "month" if granularity == "monthly" else "date"
    
    if time_col in df.columns:
        df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
        df = df.sort_values(time_col)
    
    # Calculate gross heat rate (estimated auxiliary heat rate penalty)
    # Assuming typical net generation ~500 MW for auxiliary heat rate impact calculation
    TYPICAL_NET_MW = 500.0
    has_aux_data = "aux_load_mw" in df.columns
    
    if has_aux_data:
        # Auxiliary heat rate penalty = (aux_load / net_gen) * net_heat_rate
        # Approximation: aux_heat_penalty ≈ (aux_load_mw / TYPICAL_NET_MW) * net_heat_rate
        aux_heat_penalty = (df["aux_load_mw"] / TYPICAL_NET_MW) * df["net_station_heat_rate"]
        df["gross_heat_rate_est"] = df["net_station_heat_rate"] + aux_heat_penalty
    
    # Add flat PPA reference line (around 9-9.5k)
    PPA_REFERENCE_FLAT = 9250  # Btu/kWh - typical contractual heat rate guarantee
    
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=[PPA_REFERENCE_FLAT] * len(df),
            mode="lines",
            name="PPA Guarantee (9,250)",
            line=dict(color="#9CA3AF", width=2, dash="dot"),
            hovertemplate="PPA Guarantee: 9,250 Btu/kWh<extra></extra>",
            yaxis="y",
        )
    )
    
    # Add gross heat rate (if we have aux data)
    if has_aux_data:
        # Add filled area between gross and net to highlight auxiliary impact
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["gross_heat_rate_est"],
                mode="lines",
                name="Gross Heat Rate (Est.)",
                line=dict(color="#F97316", width=2, dash="dash"),
                fill=None,
                yaxis="y",
            )
        )
        
        # Add fill area for auxiliary penalty
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["net_station_heat_rate"],
                mode="lines",
                name="Auxiliary Penalty",
                line=dict(color="#CB2026", width=0),
                fill="tonexty",
                fillcolor="rgba(249, 115, 22, 0.2)",
                hoverinfo="skip",
                showlegend=True,
                yaxis="y",
            )
        )
    
    # Add actual net heat rate
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df.get("net_station_heat_rate"),
            mode="lines+markers",
            name="Net Station Heat Rate",
            line=dict(color="#CB2026", width=2),
            marker=dict(size=4),
            yaxis="y",
        )
    )
    
    # Add auxiliary heat rate penalty on secondary y-axis (if available)
    # This shows the actual heat rate penalty in Btu/kWh that creates the gap
    if has_aux_data:
        fig.add_trace(
            go.Scatter(
                x=df[time_col],
                y=df["gross_heat_rate_est"] - df["net_station_heat_rate"],
                mode="lines",
                name="Auxiliary Heat Rate Penalty",
                line=dict(color="#8B5CF6", width=2),
                yaxis="y2",
                hovertemplate="Aux Penalty: %{y:.0f} Btu/kWh<br>Aux Load: ~%{customdata:.1f} MW<extra></extra>",
                customdata=df["aux_load_mw"],
            )
        )
    
    # Highlight anomalies
    if highlight_anomalies and granularity == "daily":
        if "anomaly_flag" in df.columns:
            anomalies = df[df["anomaly_flag"] == True]
            if not anomalies.empty:
                fig.add_trace(
                    go.Scatter(
                        x=anomalies[time_col],
                        y=anomalies["net_station_heat_rate"],
                        mode="markers",
                        name="Anomaly (Z-score)",
                        marker=dict(color="#F59E0B", size=10, symbol="diamond"),
                        yaxis="y",
                    )
                )
        
        if "sudden_change_flag" in df.columns:
            sudden = df[df["sudden_change_flag"] == True]
            if not sudden.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sudden[time_col],
                        y=sudden["net_station_heat_rate"],
                        mode="markers",
                        name="Sudden Change",
                        marker=dict(color="#DC2626", size=10, symbol="x"),
                        yaxis="y",
                    )
                )
    
    # Configure layout with dual y-axes
    layout_config = {
        "height": 360,
        "xaxis_title": "Month" if granularity == "monthly" else "Date",
        "margin": dict(l=20, r=100, t=25, b=20),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        "yaxis": dict(
            title="Heat Rate (Btu/kWh)",
            side="left",
        ),
    }
    
    # Add secondary y-axis only if we have aux data
    # Scale it to match the primary axis so the purple line height = gap size
    if has_aux_data:
        # Get the y-axis range of the main heat rate data
        y_min = df["net_station_heat_rate"].min() * 0.95
        y_max = df["gross_heat_rate_est"].max() * 1.02 if "gross_heat_rate_est" in df.columns else df["net_station_heat_rate"].max() * 1.05
        y_range = y_max - y_min
        
        # Set secondary axis range to match the main axis
        # This makes the aux penalty line height equal to the gap size
        layout_config["yaxis"] = dict(
            title="Heat Rate (Btu/kWh)",
            side="left",
            range=[y_min, y_max],
        )
        layout_config["yaxis2"] = dict(
            title="Aux Penalty (Btu/kWh)",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, y_range * 0.3],  # Scale to show penalty variation clearly
        )
    
    fig.update_layout(**layout_config)
    return fig


def heat_rate_anomaly_table(heat_rate_daily_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Return top N heat rate anomalies sorted by deviation."""
    if heat_rate_daily_df.empty:
        return pd.DataFrame()
    
    df = heat_rate_daily_df.copy()
    
    # Filter to only anomalies or sudden changes
    anomaly_mask = pd.Series(False, index=df.index)
    if "anomaly_flag" in df.columns:
        anomaly_mask |= (df["anomaly_flag"] == True)
    if "sudden_change_flag" in df.columns:
        anomaly_mask |= (df["sudden_change_flag"] == True)
    
    anomalies = df[anomaly_mask].copy()
    
    if anomalies.empty:
        return pd.DataFrame()
    
    # Sort by absolute deviation
    if "heat_rate_deviation_percent" in anomalies.columns:
        anomalies["abs_deviation"] = pd.to_numeric(
            anomalies["heat_rate_deviation_percent"], errors="coerce"
        ).abs()
        anomalies = anomalies.sort_values("abs_deviation", ascending=False)
    
    # Select relevant columns
    cols = ["date", "net_station_heat_rate", "ppa_reference_heat_rate", 
            "heat_rate_deviation_percent", "fuel_cost_impact_usd", "restart_count"]
    cols = [c for c in cols if c in anomalies.columns]
    
    result = anomalies[cols].head(top_n)
    
    # Format for display
    if "date" in result.columns:
        result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.date
    if "heat_rate_deviation_percent" in result.columns:
        result["heat_rate_deviation_percent"] = result["heat_rate_deviation_percent"].round(2)
    if "fuel_cost_impact_usd" in result.columns:
        result["fuel_cost_impact_usd"] = result["fuel_cost_impact_usd"].round(0)
    
    return result.reset_index(drop=True)


def maintenance_criticality_bubble_chart(df: pd.DataFrame, color_mode: str = "system") -> go.Figure:
    """Bubble chart for maintenance criticality mapping.
    
    Args:
        df: DataFrame with columns: maintenance_cost_usd, revenue_impact_usd, event_count, asset_path, etc.
        color_mode: 'system', 'criticality_quadrant', 'level', or 'criticality_band'
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No maintenance criticality data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig
    
    # Prepare data
    plot_df = df.copy()
    
    # Ensure numeric columns
    for col in ["maintenance_cost_usd", "revenue_impact_usd", "event_count"]:
        if col in plot_df.columns:
            plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce").fillna(0)
    
    # Calculate criticality band (1-5) based on combined cost and impact
    if "maintenance_criticality_index" in plot_df.columns:
        # Use existing MCI if available
        mci = pd.to_numeric(plot_df["maintenance_criticality_index"], errors="coerce").fillna(0)
    else:
        # Calculate composite score: normalize cost and impact, then average
        cost_norm = plot_df["maintenance_cost_usd"] / plot_df["maintenance_cost_usd"].max() if plot_df["maintenance_cost_usd"].max() > 0 else 0
        impact_norm = plot_df["revenue_impact_usd"] / plot_df["revenue_impact_usd"].max() if plot_df["revenue_impact_usd"].max() > 0 else 0
        mci = (cost_norm + impact_norm) / 2
    
    # Assign bands A-E using quintiles (A = highest criticality, E = lowest)
    try:
        plot_df["criticality_band"] = pd.qcut(
            mci, 
            q=5, 
            labels=["E", "D", "C", "B", "A"],
            duplicates="drop"
        ).astype(str)
    except (ValueError, TypeError):
        # Fallback: if qcut fails, use simple value-based binning
        max_mci = mci.max() if mci.max() > 0 else 1
        plot_df["criticality_band"] = pd.cut(
            mci,
            bins=[0, 0.2*max_mci, 0.4*max_mci, 0.6*max_mci, 0.8*max_mci, max_mci+0.01],
            labels=["E", "D", "C", "B", "A"],
            include_lowest=True
        ).astype(str)
    
    # Determine color column
    if color_mode == "criticality_band":
        color_col = "criticality_band"
    else:
        color_col = color_mode if color_mode in plot_df.columns else "system"
    
    # Create hover data
    hover_cols = ["maintenance_criticality_index", "work_order_count", "top_root_cause_category", "criticality_band"]
    hover_data = {col: True for col in hover_cols if col in plot_df.columns}
    
    # Create scatter plot
    fig = px.scatter(
        plot_df,
        x="maintenance_cost_usd",
        y="revenue_impact_usd",
        size="event_count",
        color=color_col,
        hover_name="asset_path",
        hover_data=hover_data,
        size_max=60,
    )
    
    # Add quadrant reference lines using medians
    if not plot_df.empty and "maintenance_cost_usd" in plot_df.columns and "revenue_impact_usd" in plot_df.columns:
        x_median = plot_df["maintenance_cost_usd"].median()
        y_median = plot_df["revenue_impact_usd"].median()
        
        # Vertical median line
        fig.add_vline(
            x=x_median,
            line_width=1,
            line_dash="dot",
            line_color="#9CA3AF",
            annotation_text=f"Median Cost: ${x_median:,.0f}",
            annotation_position="top",
        )
        
        # Horizontal median line
        fig.add_hline(
            y=y_median,
            line_width=1,
            line_dash="dot",
            line_color="#9CA3AF",
            annotation_text=f"Median Impact: ${y_median:,.0f}",
            annotation_position="right",
        )
    
    fig.update_layout(
        height=500,
        xaxis_title="Maintenance Cost (USD)",
        yaxis_title="Revenue Impact (USD)",
        margin=dict(l=20, r=20, t=35, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    
    return fig


def build_heat_rate_chart(
    df: pd.DataFrame,
    x_col: str,
    net_col: str = "net_station_heat_rate",
    ppa_flat_value: float = 9300.0,
    gross_col: str | None = None,
    aux_col: str | None = None,
    highlight_anomalies: bool = False,
) -> go.Figure:
    """Build heat rate chart with net, gross (if available), and flat PPA reference.
    
    Args:
        df: DataFrame with heat rate data
        x_col: Column name for x-axis (timestamp, date, or month)
        net_col: Column name for net station heat rate
        ppa_flat_value: Flat PPA reference value (Btu/kWh)
        gross_col: Optional column name for gross heat rate (pre-computed)
        aux_col: Optional column name for auxiliary heat rate (pre-computed)
        highlight_anomalies: Whether to highlight anomalies (for daily data)
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    if df.empty or x_col not in df.columns or net_col not in df.columns:
        fig.add_annotation(
            text="Insufficient heat rate data",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
        )
        return fig
    
    plot_df = df.copy()
    plot_df[x_col] = pd.to_datetime(plot_df[x_col], errors="coerce", utc=True)
    plot_df = plot_df.sort_values(x_col)
    
    # Add flat PPA reference line
    fig.add_trace(
        go.Scatter(
            x=plot_df[x_col],
            y=[ppa_flat_value] * len(plot_df),
            mode="lines",
            name=f"PPA Guarantee ({ppa_flat_value:,.0f})",
            line=dict(color="#9CA3AF", width=2, dash="dot"),
            hovertemplate=f"PPA Guarantee: {ppa_flat_value:,.0f} Btu/kWh<extra></extra>",
        )
    )
    
    # Check if we have gross and aux columns
    has_gross = gross_col and gross_col in plot_df.columns
    has_aux = aux_col and aux_col in plot_df.columns
    
    # Add gross heat rate trace (if available)
    if has_gross:
        fig.add_trace(
            go.Scatter(
                x=plot_df[x_col],
                y=plot_df[gross_col],
                mode="lines",
                name="Gross Heat Rate",
                line=dict(color="#F97316", width=2, dash="dash"),
                hovertemplate="Gross HR: %{y:,.0f} Btu/kWh<extra></extra>",
            )
        )
        
        # Add filled area between gross and net (auxiliary penalty)
        fig.add_trace(
            go.Scatter(
                x=plot_df[x_col],
                y=plot_df[net_col],
                mode="lines",
                name="Auxiliary (Gross − Net)",
                line=dict(color="#CB2026", width=0),
                fill="tonexty",
                fillcolor="rgba(249, 115, 22, 0.2)",
                hoverinfo="skip",
                showlegend=True,
            )
        )
    
    # Add net station heat rate
    fig.add_trace(
        go.Scatter(
            x=plot_df[x_col],
            y=plot_df[net_col],
            mode="lines+markers",
            name="Net Station Heat Rate",
            line=dict(color="#CB2026", width=2),
            marker=dict(size=4),
            hovertemplate="Net HR: %{y:,.0f} Btu/kWh<extra></extra>",
        )
    )
    
    # Add auxiliary heat rate penalty on secondary y-axis (if available)
    if has_aux:
        fig.add_trace(
            go.Scatter(
                x=plot_df[x_col],
                y=plot_df[aux_col],
                mode="lines",
                name="Auxiliary Heat Rate Penalty",
                line=dict(color="#8B5CF6", width=2),
                yaxis="y2",
                hovertemplate="Aux Penalty: %{y:,.0f} Btu/kWh<extra></extra>",
            )
        )
    
    # Highlight anomalies (for daily data)
    if highlight_anomalies and "anomaly_flag" in plot_df.columns:
        anomalies = plot_df[plot_df["anomaly_flag"] == True]
        if not anomalies.empty:
            fig.add_trace(
                go.Scatter(
                    x=anomalies[x_col],
                    y=anomalies[net_col],
                    mode="markers",
                    name="Anomaly (Z-score)",
                    marker=dict(color="#F59E0B", size=10, symbol="diamond"),
                )
            )
    
    if highlight_anomalies and "sudden_change_flag" in plot_df.columns:
        sudden = plot_df[plot_df["sudden_change_flag"] == True]
        if not sudden.empty:
            fig.add_trace(
                go.Scatter(
                    x=sudden[x_col],
                    y=sudden[net_col],
                    mode="markers",
                    name="Sudden Change",
                    marker=dict(color="#DC2626", size=10, symbol="x"),
                )
            )
    
    # Configure layout
    layout_config = {
        "height": 400,
        "xaxis_title": x_col.replace("_", " ").title(),
        "margin": dict(l=20, r=100 if has_aux else 20, t=25, b=20),
        "legend": dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        "yaxis": dict(title="Heat Rate (Btu/kWh)", side="left"),
    }
    
    # Add secondary y-axis if we have auxiliary penalty
    if has_aux:
        y_min = plot_df[net_col].min() * 0.95
        y_max = plot_df[gross_col].max() * 1.02 if has_gross else plot_df[net_col].max() * 1.05
        y_range = y_max - y_min
        
        layout_config["yaxis"]["range"] = [y_min, y_max]
        layout_config["yaxis2"] = dict(
            title="Aux Penalty (Btu/kWh)",
            overlaying="y",
            side="right",
            showgrid=False,
            range=[0, y_range * 0.3],
        )
    
    fig.update_layout(**layout_config)
    return fig
