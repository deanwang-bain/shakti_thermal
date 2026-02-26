"""Metrics calculations for generation and revenue views."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import streamlit as st


@dataclass
class RevenueKpis:
    actual_total_revenue: float
    max_potential_revenue: float
    total_loss: float
    revenue_capture_ratio: float


def _first_existing(columns: list[str], choices: list[str]) -> str | None:
    for col in choices:
        if col in columns:
            return col
    return None


def standardize_dispatch_columns(dispatch_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize generation column naming variations into canonical columns."""
    if dispatch_df.empty:
        return dispatch_df

    out = dispatch_df.copy()
    available_col = _first_existing(list(out.columns), ["available_mw", "available_capacity_mw"])
    target_col = _first_existing(list(out.columns), ["dispatch_target_mw", "grid_requirement_mw"])
    net_col = _first_existing(list(out.columns), ["net_generation_mw", "net_generation", "NetGeneration_MW"])

    if available_col and available_col != "available_mw":
        out["available_mw"] = out[available_col]
    if target_col and target_col != "dispatch_target_mw":
        out["dispatch_target_mw"] = out[target_col]
    if net_col and net_col != "net_generation_mw":
        out["net_generation_mw"] = out[net_col]

    for col in ["available_mw", "dispatch_target_mw", "net_generation_mw"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if {"dispatch_target_mw", "net_generation_mw"}.issubset(out.columns):
        out["delta_mw"] = out["dispatch_target_mw"] - out["net_generation_mw"]
        if "delta_mwh" not in out.columns:
            out["delta_mwh"] = out["delta_mw"] * (5 / 60)
    return out


def detect_5min_miss_points(dispatch_df: pd.DataFrame, threshold_mw: float = 5.0, epsilon: float = 2.0) -> pd.Series:
    """Infer misses when explicit label is unavailable."""
    if dispatch_df.empty:
        return pd.Series(dtype=bool)

    out = standardize_dispatch_columns(dispatch_df)
    if "deviation_type" in out.columns:
        explicit = out["deviation_type"].fillna("").astype(str).str.lower().eq("5-min miss")
        if explicit.any():
            return explicit

    cond = (out.get("delta_mw", 0) > threshold_mw) & (
        out.get("available_mw", np.nan) >= out.get("dispatch_target_mw", np.nan) - epsilon
    )
    return cond.fillna(False)


def availability_proxy(dispatch_df: pd.DataFrame) -> float:
    """Availability factor proxy from dispatch table."""
    out = standardize_dispatch_columns(dispatch_df)
    if out.empty:
        return float("nan")
    if "available_mw" in out.columns and "dispatch_target_mw" in out.columns:
        denom = out["dispatch_target_mw"].replace(0, np.nan)
        return float((out["available_mw"] / denom).clip(upper=1.1).mean())
    return float("nan")


def compute_revenue_kpis(
    monthly_df: pd.DataFrame,
    energy_df: pd.DataFrame,
    capacity_df: pd.DataFrame,
    penalties_df: pd.DataFrame,
    fuel_df: pd.DataFrame,
) -> RevenueKpis:
    """Aggregate revenue KPIs for selected context."""
    if not monthly_df.empty and {"actual_total_revenue", "max_potential_revenue"}.issubset(monthly_df.columns):
        actual = float(pd.to_numeric(monthly_df["actual_total_revenue"], errors="coerce").sum())
        potential = float(pd.to_numeric(monthly_df["max_potential_revenue"], errors="coerce").sum())
        loss = max(potential - actual, 0.0)
        rcr = (actual / potential) if potential > 0 else float("nan")
        return RevenueKpis(actual, potential, loss, rcr)

    energy_actual = float(pd.to_numeric(energy_df.get("energy_revenue_actual", 0), errors="coerce").sum())
    energy_potential = float(pd.to_numeric(energy_df.get("energy_revenue_potential", 0), errors="coerce").sum())
    cap_actual = float(pd.to_numeric(capacity_df.get("capacity_payment_actual", 0), errors="coerce").sum())
    cap_potential = float(pd.to_numeric(capacity_df.get("capacity_payment_potential", 0), errors="coerce").sum())
    penalties = float(pd.to_numeric(penalties_df.get("dsm_penalties_usd", 0), errors="coerce").sum())
    fuel_over = float(pd.to_numeric(fuel_df.get("fuel_overburn_cost", 0), errors="coerce").sum())

    actual = energy_actual + cap_actual - penalties - fuel_over
    potential = energy_potential + cap_potential
    loss = max(potential - actual, 0.0)
    rcr = (actual / potential) if potential > 0 else float("nan")
    return RevenueKpis(actual, potential, loss, rcr)


def top_loss_components(attribution_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    """Top components by lost revenue."""
    if attribution_df.empty or "component" not in attribution_df.columns:
        return pd.DataFrame()
    out = attribution_df.copy()
    out["loss_usd"] = pd.to_numeric(out.get("loss_usd", 0), errors="coerce").fillna(0)
    return (
        out.groupby(["system", "subsystem", "component"], dropna=False)["loss_usd"]
        .sum()
        .reset_index()
        .sort_values("loss_usd", ascending=False)
        .head(top_n)
    )


@st.cache_data(show_spinner=False)
def cached_correlations(
    historian_df: pd.DataFrame,
    generation_df: pd.DataFrame,
    unit: str,
    start_ts: pd.Timestamp,
    end_ts: pd.Timestamp,
    resolution: str,
) -> pd.DataFrame:
    """Compute correlation matrix cached by context."""
    if historian_df.empty or generation_df.empty:
        return pd.DataFrame()

    hist = historian_df.copy()
    gen = generation_df.copy()
    for df in [hist, gen]:
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    if "unit_id" in hist.columns:
        hist = hist[hist["unit_id"].astype(str) == str(unit)]
    if "unit_id" in gen.columns:
        gen = gen[gen["unit_id"].astype(str) == str(unit)]

    hist = hist[(hist["timestamp"] >= start_ts) & (hist["timestamp"] <= end_ts)]
    gen = gen[(gen["timestamp"] >= start_ts) & (gen["timestamp"] <= end_ts)]

    gen = standardize_dispatch_columns(gen)
    merged = pd.merge_asof(
        hist.sort_values("timestamp"),
        gen[["timestamp", "net_generation_mw"]].sort_values("timestamp"),
        on="timestamp",
        direction="nearest",
        tolerance=pd.Timedelta("10min"),
    ).dropna(subset=["net_generation_mw"])

    candidates = [
        "IDFanSpeed_pct",
        "draft_fan_speed",
        "DamperPosition_pct",
        "FurnaceDraftPressure_kPa",
        "FurnaceDraftPressure_Pa",
    ]
    available = [col for col in candidates if col in merged.columns]
    if not available:
        return pd.DataFrame()

    corr_rows = []
    for col in available:
        x = pd.to_numeric(merged[col], errors="coerce")
        y = pd.to_numeric(merged["net_generation_mw"], errors="coerce")
        corr = x.corr(y)
        corr_rows.append({"signal": col, "correlation_to_net_generation": corr})

    return pd.DataFrame(corr_rows).sort_values("correlation_to_net_generation", key=lambda s: s.abs(), ascending=False)


def correlation_explanation(corr_df: pd.DataFrame) -> str:
    """Deterministic explanation template from top correlation."""
    if corr_df.empty:
        return "No strong historian correlations were available in the selected window."
    top = corr_df.iloc[0]
    signal = top["signal"]
    val = float(top["correlation_to_net_generation"])
    strength = "strong" if abs(val) >= 0.6 else "moderate" if abs(val) >= 0.35 else "weak"
    direction = "positive" if val >= 0 else "negative"
    return (
        f"{signal} shows {strength} {direction} correlation with net generation during the selected window, "
        "consistent with draft control behavior in constrained operation."
    )
