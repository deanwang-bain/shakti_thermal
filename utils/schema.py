"""Schema and validation helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMAS: dict[str, list[str]] = {
    "asset_hierarchy.csv": [
        "asset_id",
        "parent_asset_id",
        "level",
        "system",
        "canonical_name",
        "aliases_json",
    ],
    "sensor_registry.csv": ["tag_id", "asset_id", "tag_name", "aliases_json"],
    "events_outages_derates.csv": [
        "event_id",
        "unit_id",
        "start_time",
        "end_time",
        "linked_asset_id",
    ],
    "work_orders.csv": ["wo_id", "asset_description_raw"],
    "ontology_nodes.csv": ["node_id", "node_type", "canonical_name"],
    "ontology_edges.csv": ["src_node_id", "edge_type", "dst_node_id"],
    "dispatch_timeseries_5min.csv": [
        "timestamp",
        "unit_id",
        "dispatch_target_mw",
        "net_generation_mw",
    ],
    "scada_unit1_5min.csv": ["timestamp", "unit_id", "IDFanSpeed_pct", "DamperPosition_pct"],
    "heat_rate_hourly.csv": ["timestamp", "unit_id", "net_station_heat_rate"],
    "revenue_summary_monthly.csv": [
        "month",
        "unit_id",
        "actual_total_revenue",
        "max_potential_revenue",
        "revenue_capture_ratio",
    ],
    "energy_settlement_5min.csv": ["timestamp", "unit_id", "energy_revenue_actual"],
    "capacity_revenue_daily.csv": ["date", "unit_id", "capacity_payment_actual"],
    "lost_revenue_attribution_daily.csv": ["date", "unit_id", "loss_category", "loss_usd"],
    "daily_revenue_reconciliation.csv": [
        "date",
        "actual_revenue_usd",
        "max_potential_revenue_usd",
    ],
}


def load_schema_manifest(schema_dir: Path) -> dict[str, list[str]]:
    """Load external schema manifest if available."""
    manifest_path = schema_dir / "schema_manifest.json"
    if not manifest_path.exists():
        return EXPECTED_SCHEMAS
    try:
        raw: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {str(key): [str(c) for c in value] for key, value in raw.items() if isinstance(value, list)}
    except (json.JSONDecodeError, OSError, TypeError):
        return EXPECTED_SCHEMAS


def validate_columns(df_columns: list[str], expected_columns: list[str]) -> tuple[bool, list[str]]:
    """Return validation status and list of missing columns."""
    missing = [col for col in expected_columns if col not in df_columns]
    return len(missing) == 0, missing


def expected_for_alias(loaded_file_name: str, schema_map: dict[str, list[str]]) -> list[str]:
    """Return best matching expected columns by exact or stem-like matching."""
    if loaded_file_name in schema_map:
        return schema_map[loaded_file_name]

    base = loaded_file_name.replace(".gz", "")
    for key, cols in schema_map.items():
        key_base = key.replace(".gz", "")
        if base == key_base:
            return cols
        if base.split(".")[0] == key_base.split(".")[0]:
            return cols
    return []
