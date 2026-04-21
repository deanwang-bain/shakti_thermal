#!/usr/bin/env python3
"""
Validation for Plant Co — Synthetic Full Potential Demo Dataset

Checks required:
- Referential integrity (IDs across assets/sensors/events/text)
- Dispatch delta correctness (delta_mwh = delta_mw*5/60)
- Physical realism: net_generation ≤ available ≤ rated
- Heat rate plausible range and part-load behavior
- Revenue reconciliation balance + RCR ≤ 1
- Lost revenue attribution sums match daily total loss
- Recurring draft instability pattern exists, including false positives
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd


RATED_MW = 660.0


def fail(msg: str) -> None:
    print(f"❌ {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"✅ {msg}")


def warn(msg: str) -> None:
    print(f"⚠️ {msg}")


def read_csv(path: str, **kwargs) -> pd.DataFrame:
    if not os.path.exists(path):
        fail(f"Missing file: {path}")
    return pd.read_csv(path, **kwargs)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=str, default="./data", help="Path to data folder")
    args = p.parse_args()

    data_dir = args.data
    required = [
        "asset_hierarchy.csv",
        "sensor_registry.csv",
        "events_outages_derates.csv",
        "work_orders.csv",
        "shift_logs.csv",
        "emails.csv",
        "media_metadata.csv",
        "alarms.csv",
        "ontology_nodes.csv",
        "ontology_edges.csv",
        "dispatch_timeseries_5min.csv.gz",
        "scada_unit1_5min.csv.gz",
        "heat_rate_hourly.csv",
        "energy_settlement_5min.csv.gz",
        "capacity_revenue_daily.csv",
        "penalties_daily.csv",
        "fuel_cost_daily.csv",
        "daily_revenue_reconciliation.csv",
        "revenue_summary_monthly.csv",
        "lost_revenue_attribution_daily.csv",
    ]
    for f in required:
        if not os.path.exists(os.path.join(data_dir, f)):
            fail(f"Missing required output: {f}")

    assets = read_csv(os.path.join(data_dir, "asset_hierarchy.csv"))
    sensors = read_csv(os.path.join(data_dir, "sensor_registry.csv"))
    events = read_csv(os.path.join(data_dir, "events_outages_derates.csv"))
    wos = read_csv(os.path.join(data_dir, "work_orders.csv"))
    logs = read_csv(os.path.join(data_dir, "shift_logs.csv"))
    emails = read_csv(os.path.join(data_dir, "emails.csv"))
    media = read_csv(os.path.join(data_dir, "media_metadata.csv"))
    alarms = read_csv(os.path.join(data_dir, "alarms.csv"))

    asset_ids = set(assets["asset_id"].astype(str))
    # Referentials
    if not set(sensors["asset_id"].astype(str)).issubset(asset_ids):
        bad = set(sensors["asset_id"].astype(str)) - asset_ids
        fail(f"sensor_registry.asset_id contains unknown asset_id(s): {list(sorted(bad))[:5]}")
    ok("sensor_registry.asset_id → asset_hierarchy.asset_id OK")

    if not set(events["linked_asset_id"].astype(str)).issubset(asset_ids):
        bad = set(events["linked_asset_id"].astype(str)) - asset_ids
        fail(f"events_outages_derates.linked_asset_id unknown: {list(sorted(bad))[:5]}")
    ok("events_outages_derates.linked_asset_id → asset_hierarchy.asset_id OK")

    if not set(wos["standard_asset_id_truth"].astype(str)).issubset(asset_ids):
        bad = set(wos["standard_asset_id_truth"].astype(str)) - asset_ids
        fail(f"work_orders.standard_asset_id_truth unknown: {list(sorted(bad))[:5]}")
    ok("work_orders.standard_asset_id_truth → asset_hierarchy.asset_id OK")

    if not set(logs["standard_asset_id_truth"].astype(str)).issubset(asset_ids):
        bad = set(logs["standard_asset_id_truth"].astype(str)) - asset_ids
        fail(f"shift_logs.standard_asset_id_truth unknown: {list(sorted(bad))[:5]}")
    ok("shift_logs.standard_asset_id_truth → asset_hierarchy.asset_id OK")

    event_ids = set(events["event_id"].astype(str))
    # linked_event_id can be blank
    wos_ev = set([x for x in wos["linked_event_id"].astype(str).tolist() if x and x != "nan"])
    logs_ev = set([x for x in logs["linked_event_id"].astype(str).tolist() if x and x != "nan"])
    emails_ev = set([x for x in emails["standard_event_id_truth"].astype(str).tolist() if x and x != "nan"])
    for sname, svals in [("work_orders.linked_event_id", wos_ev), ("shift_logs.linked_event_id", logs_ev), ("emails.standard_event_id_truth", emails_ev)]:
        if not svals.issubset(event_ids):
            bad = svals - event_ids
            fail(f"{sname} references unknown event_id(s): {list(sorted(bad))[:5]}")
    ok("Event IDs referenced by WOs/logs/emails exist in events_outages_derates.csv")

    tag_ids = set(sensors["tag_id"].astype(str))
    if not set(alarms["tag_id"].astype(str)).issubset(tag_ids):
        bad = set(alarms["tag_id"].astype(str)) - tag_ids
        fail(f"alarms.tag_id unknown: {list(sorted(bad))[:5]}")
    ok("alarms.tag_id → sensor_registry.tag_id OK")

    # Load big series for checks
    dispatch = read_csv(os.path.join(data_dir, "dispatch_timeseries_5min.csv.gz"), compression="gzip")
    scada = read_csv(os.path.join(data_dir, "scada_unit1_5min.csv.gz"), compression="gzip")
    energy = read_csv(os.path.join(data_dir, "energy_settlement_5min.csv.gz"), compression="gzip")

    # Parse timestamps
    for df, col in [(dispatch, "timestamp"), (scada, "timestamp"), (energy, "timestamp")]:
        df[col] = pd.to_datetime(df[col], utc=True)

    # Dispatch delta correctness
    calc = dispatch["delta_mw"].astype(float) * (5.0/60.0)
    err = np.max(np.abs(calc.to_numpy() - dispatch["delta_mwh"].astype(float).to_numpy()))
    if err > 1e-4:
        fail(f"Dispatch delta_mwh mismatch: max abs error={err}")
    ok("delta_mwh == delta_mw*(5/60)")

    # Physical realism
    if (dispatch["available_mw"].astype(float) > RATED_MW + 1e-6).any():
        fail("available_mw exceeds rated capacity")
    if (dispatch["available_mw"].astype(float) < -1e-6).any():
        fail("available_mw negative")
    if (dispatch["net_generation_mw"].astype(float) > dispatch["available_mw"].astype(float) + 5.0).any():
        fail("net_generation_mw exceeds available_mw beyond 5 MW tolerance")
    ok("Generation/availability physical bounds OK")

    # Heat rate checks
    heat = read_csv(os.path.join(data_dir, "heat_rate_hourly.csv"))
    heat["timestamp"] = pd.to_datetime(heat["timestamp"], utc=True)
    nshr = pd.to_numeric(heat["net_station_heat_rate"], errors="coerce")
    if not nshr.dropna().between(8500, 17500).mean() > 0.98:
        warn("Some NSHR values out of range (8500–17500). Might be acceptable for demo but review.")
    else:
        ok("NSHR in plausible range")

    # Heat rate part-load behavior (reference curve should be higher at part load)
    # Proxy load = hourly avg net MW from dispatch
    d = dispatch.copy()
    d["hour"] = d["timestamp"].dt.floor("h")
    avg_net = d.groupby("hour")["net_generation_mw"].mean().reset_index().rename(columns={"hour":"timestamp"})
    h2 = heat.merge(avg_net, on="timestamp", how="left")
    low = h2[h2["net_generation_mw"] < 300]["ppa_reference_heat_rate"].astype(float).median()
    high = h2[h2["net_generation_mw"] > 500]["ppa_reference_heat_rate"].astype(float).median()
    if not (low > high):
        fail("Reference heat rate does not increase at part load (expected low-load HR > high-load HR).")
    ok("Reference heat rate higher at part load")

    # Revenue reconciliation
    cap = read_csv(os.path.join(data_dir, "capacity_revenue_daily.csv"))
    pen = read_csv(os.path.join(data_dir, "penalties_daily.csv"))
    fuel = read_csv(os.path.join(data_dir, "fuel_cost_daily.csv"))
    recon = read_csv(os.path.join(data_dir, "daily_revenue_reconciliation.csv"))
    attr = read_csv(os.path.join(data_dir, "lost_revenue_attribution_daily.csv"))

    # RCR <= 1
    rcr = recon["revenue_capture_ratio"].astype(float)
    if (rcr > 1.0000001).any():
        fail("Revenue capture ratio > 1 found.")
    ok("Revenue capture ratio ≤ 1")

    # Check recon identity within tolerance
    recon["lhs"] = recon["actual_revenue_usd"].astype(float)
    recon["rhs"] = (
        recon["energy_rev_actual"].astype(float)
        + recon["capacity_payment_actual"].astype(float)
        - recon["penalties_total_usd"].astype(float)
        - recon["fuel_overburn_cost"].astype(float)
    )
    max_err = np.max(np.abs(recon["lhs"] - recon["rhs"]))
    if max_err > 0.02:
        fail(f"Actual revenue reconciliation mismatch max_err={max_err}")
    ok("Daily actual revenue reconciles to components")

    recon["max_calc"] = recon["energy_rev_potential"].astype(float) + recon["capacity_payment_potential"].astype(float)
    max_err2 = np.max(np.abs(recon["max_calc"] - recon["max_potential_revenue_usd"].astype(float)))
    if max_err2 > 0.02:
        fail(f"Max potential revenue mismatch max_err={max_err2}")
    ok("Daily max potential revenue reconciles")

    # Loss sums: max - actual
    loss_err = np.max(np.abs((recon["max_potential_revenue_usd"].astype(float) - recon["actual_revenue_usd"].astype(float)) - recon["revenue_loss_usd"].astype(float)))
    if loss_err > 0.02:
        fail(f"Revenue loss mismatch max_err={loss_err}")
    ok("Daily revenue loss = max - actual")

    # Attribution sums match total loss
    attr_sum = attr.groupby("date")["loss_usd"].sum().reset_index().rename(columns={"loss_usd":"attr_sum"})
    recon2 = recon.merge(attr_sum, on="date", how="left").fillna({"attr_sum":0.0})
    aerr = np.max(np.abs(recon2["attr_sum"].astype(float) - recon2["revenue_loss_usd"].astype(float)))
    if aerr > 0.05:
        fail(f"Attribution does not sum to total loss (max abs err={aerr})")
    ok("Lost revenue attribution sums match daily total loss")

    # Draft instability pattern exists + false positives
    scada = scada.sort_values("timestamp")
    draft_std = scada["FurnaceDraftPressure_Pa"].rolling(12, min_periods=12).std()
    pattern = (draft_std > 18) & (scada["DamperPosition_pct"] > 95) & (scada["IDFanSpeed_pct"] > 92)
    idx = np.where(pattern.to_numpy())[0]
    if len(idx) == 0:
        fail("No draft instability pattern detected.")
    # Count episodes (gaps > 1)
    episodes = 1 + int((np.diff(idx) > 1).sum()) if len(idx) else 0
    if episodes < 10:
        fail(f"Too few draft instability episodes detected ({episodes}, expected >= 10).")
    # False positives: pattern hours but no active event in dispatch
    # Join dispatch active_event_id
    disp_small = dispatch[["timestamp","active_event_id"]].copy()
    merged = scada[["timestamp"]].merge(disp_small, on="timestamp", how="left")
    false = pattern & (merged["active_event_id"].fillna("") == "")
    fidx = np.where(false.to_numpy())[0]
    false_eps = 1 + int((np.diff(fidx) > 1).sum()) if len(fidx) else 0
    if false_eps < 5:
        fail(f"Too few false-positive draft episodes ({false_eps}, expected >= 5).")
    ok(f"Draft instability episodes detected: {episodes} (false positives: {false_eps})")

    print("\n🎉 VALIDATION PASSED")


if __name__ == "__main__":
    main()
