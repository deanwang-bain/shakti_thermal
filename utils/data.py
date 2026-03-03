"""Data loading, fallback resolution, caching, and health reporting."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from utils.schema import expected_for_alias, load_schema_manifest, validate_columns


@dataclass
class DatasetStatus:
    key: str
    selected_file: str | None
    loaded: bool
    required: bool
    warning: str | None = None


@dataclass
class DataCatalog:
    root: Path
    data_dir: Path
    docs_dir: Path
    schema_dir: Path
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    statuses: dict[str, DatasetStatus] = field(default_factory=dict)
    schema_issues: dict[str, list[str]] = field(default_factory=dict)
    health: pd.DataFrame = field(default_factory=pd.DataFrame)


FILE_CANDIDATES: dict[str, tuple[list[str], bool]] = {
    "asset_hierarchy": (["asset_hierarchy.csv"], True),
    "sensor_registry": (["sensor_registry.csv"], True),
    "ontology_nodes": (["ontology_nodes.csv"], False),
    "ontology_edges": (["ontology_edges.csv"], False),
    "events": (["outage_ledger.csv", "events_outages_derates.csv"], False),
    "media": (["media_index.csv", "media_metadata.csv"], False),
    "work_orders": (["work_orders.csv"], False),
    "alarms": (["alarms.csv"], False),
    "shift_logs": (["shift_logs.csv"], False),
    "emails": (["emails.csv"], False),
    "dispatch": (
        [
            "dispatch_timeseries_5min.parquet",
            "dispatch_timeseries_5min.csv",
            "dispatch_timeseries_5min.csv.gz",
        ],
        True,
    ),
    "historian": (
        [
            "sensor_timeseries_5min.parquet",
            "sensor_timeseries_5min.csv",
            "scada_unit1_5min.csv.gz",
            "scada_unit1_5min.csv",
        ],
        True,
    ),
    "heat_rate": (
        ["heat_rate_timeseries.parquet", "heat_rate_timeseries.csv", "heat_rate_hourly.csv"],
        True,
    ),
    "heat_rate_daily": (["heat_rate_daily.csv"], False),
    "heat_rate_monthly": (["heat_rate_monthly.csv"], False),
    "monthly_summary": (["revenue_summary_monthly.csv"], True),
    "daily_summary": (["revenue_summary_daily.csv"], False),
    "energy_settlement": (
        ["revenue_5min.csv", "energy_settlement_5min.csv.gz", "energy_settlement_5min.csv"],
        True,
    ),
    "capacity": (["capacity_revenue_daily.csv"], True),
    "attribution": (["lost_revenue_attribution.csv", "lost_revenue_attribution_daily.csv"], True),
    "penalties": (["penalties_daily.csv"], False),
    "fuel_cost": (["fuel_cost_daily.csv"], False),
    "daily_reconciliation": (["daily_revenue_reconciliation.csv"], False),
    "maintenance_crit": (["maintenance_criticality_asset_summary.csv"], False),
    "maintenance_event_impacts": (["maintenance_event_impacts.csv"], False),
    "maintenance_crit_ai": (["maintenance_criticality_ai_insights.csv"], False),
}


def _choose_file(data_dir: Path, candidates: list[str]) -> Path | None:
    for name in candidates:
        path = data_dir / name
        if path.exists():
            return path
    return None


def _read_file(path: Path) -> pd.DataFrame:
    lower = path.name.lower()
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    if lower.endswith(".csv.gz"):
        return pd.read_csv(path, compression="gzip")
    return pd.read_csv(path)


def _try_parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def _normalize_time_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        col_low = col.lower()
        if "time" in col_low or col_low in {"timestamp", "date", "month", "shift_start", "shift_end"}:
            parsed = _try_parse_datetime(out[col])
            if parsed.notna().mean() >= 0.6:
                out[col] = parsed
    return out


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _build_ontology_nodes(asset_df: pd.DataFrame, sensor_df: pd.DataFrame) -> pd.DataFrame:
    nodes: list[dict[str, str]] = []
    if not asset_df.empty:
        for row in asset_df.fillna("").to_dict("records"):
            nodes.append(
                {
                    "node_id": _safe_text(row.get("asset_id")),
                    "node_type": _safe_text(row.get("level", "Asset")),
                    "canonical_name": _safe_text(row.get("canonical_name", row.get("asset_id"))),
                    "description": _safe_text(row.get("system", "")),
                }
            )

    if not sensor_df.empty:
        for row in sensor_df.fillna("").to_dict("records"):
            nodes.append(
                {
                    "node_id": _safe_text(row.get("tag_id")),
                    "node_type": "Tag",
                    "canonical_name": _safe_text(row.get("tag_name", row.get("tag_id"))),
                    "description": _safe_text(row.get("description", "")),
                }
            )
    return pd.DataFrame(nodes).drop_duplicates(subset=["node_id"]) if nodes else pd.DataFrame()


def _build_ontology_edges(asset_df: pd.DataFrame, sensor_df: pd.DataFrame) -> pd.DataFrame:
    edges: list[dict[str, str]] = []
    if not asset_df.empty:
        parent_df = asset_df.dropna(subset=["parent_asset_id"]) if "parent_asset_id" in asset_df.columns else pd.DataFrame()
        for row in parent_df.fillna("").to_dict("records"):
            edges.append(
                {
                    "src_node_id": _safe_text(row.get("parent_asset_id")),
                    "edge_type": "PARENT_OF",
                    "dst_node_id": _safe_text(row.get("asset_id")),
                    "evidence_ref": "fallback_hierarchy",
                }
            )

    if not sensor_df.empty:
        for row in sensor_df.fillna("").to_dict("records"):
            edges.append(
                {
                    "src_node_id": _safe_text(row.get("tag_id")),
                    "edge_type": "MEASURES",
                    "dst_node_id": _safe_text(row.get("asset_id")),
                    "evidence_ref": "fallback_sensor_registry",
                }
            )
    return pd.DataFrame(edges) if edges else pd.DataFrame()


def _dataset_health(key: str, df: pd.DataFrame) -> dict[str, Any]:
    row: dict[str, Any] = {"dataset": key, "rows": int(len(df)), "timestamp_min": None, "timestamp_max": None, "nulls_key_cols": 0}
    if df.empty:
        return row

    datetime_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if datetime_cols:
        tcol = datetime_cols[0]
        row["timestamp_min"] = df[tcol].min()
        row["timestamp_max"] = df[tcol].max()

    key_cols = [col for col in ["timestamp", "date", "month", "unit_id", "asset_id", "event_id"] if col in df.columns]
    if key_cols:
        row["nulls_key_cols"] = int(df[key_cols].isna().sum().sum())
    return row


@st.cache_data(show_spinner=False)
def load_data_catalog(root_path: str) -> DataCatalog:
    """Load all datasets with robust fallback and schema checks."""
    root = Path(root_path)
    data_dir = root / "data"
    docs_dir = root / "docs"
    schema_dir = root / "schemas"

    schema_map = load_schema_manifest(schema_dir)
    catalog = DataCatalog(root=root, data_dir=data_dir, docs_dir=docs_dir, schema_dir=schema_dir)

    for key, (candidates, required) in FILE_CANDIDATES.items():
        selected = _choose_file(data_dir, candidates)
        if selected is None:
            catalog.statuses[key] = DatasetStatus(
                key=key,
                selected_file=None,
                loaded=False,
                required=required,
                warning=f"Missing files: {', '.join(candidates)}",
            )
            catalog.tables[key] = pd.DataFrame()
            continue

        try:
            df = _normalize_time_columns(_read_file(selected))
            catalog.tables[key] = df
            catalog.statuses[key] = DatasetStatus(
                key=key,
                selected_file=selected.name,
                loaded=True,
                required=required,
            )

            expected = expected_for_alias(selected.name, schema_map)
            if expected:
                ok, missing = validate_columns(list(df.columns), expected)
                if not ok:
                    catalog.schema_issues[key] = missing
        except Exception as exc:
            catalog.tables[key] = pd.DataFrame()
            catalog.statuses[key] = DatasetStatus(
                key=key,
                selected_file=selected.name,
                loaded=False,
                required=required,
                warning=f"Load failed: {exc}",
            )

    if catalog.tables.get("ontology_nodes", pd.DataFrame()).empty:
        catalog.tables["ontology_nodes"] = _build_ontology_nodes(
            catalog.tables.get("asset_hierarchy", pd.DataFrame()),
            catalog.tables.get("sensor_registry", pd.DataFrame()),
        )
        catalog.statuses["ontology_nodes"] = DatasetStatus(
            key="ontology_nodes",
            selected_file="<generated_fallback>",
            loaded=True,
            required=False,
            warning="ontology_nodes.csv missing; generated fallback nodes",
        )

    if catalog.tables.get("ontology_edges", pd.DataFrame()).empty:
        catalog.tables["ontology_edges"] = _build_ontology_edges(
            catalog.tables.get("asset_hierarchy", pd.DataFrame()),
            catalog.tables.get("sensor_registry", pd.DataFrame()),
        )
        catalog.statuses["ontology_edges"] = DatasetStatus(
            key="ontology_edges",
            selected_file="<generated_fallback>",
            loaded=True,
            required=False,
            warning="ontology_edges.csv missing; generated fallback edges",
        )

    health_rows = [_dataset_health(name, df) for name, df in catalog.tables.items()]
    catalog.health = pd.DataFrame(health_rows)
    return catalog


def available_units(catalog: DataCatalog) -> list[str]:
    """Return sorted unit list from any loaded table."""
    units: set[str] = set()
    for df in catalog.tables.values():
        if not df.empty and "unit_id" in df.columns:
            units.update(df["unit_id"].dropna().astype(str).unique().tolist())
    return sorted(units)


def best_default_date_range(catalog: DataCatalog) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Default date range: 2024-03-01 to 2024-12-31."""
    return pd.Timestamp("2024-03-01", tz="UTC"), pd.Timestamp("2024-12-31", tz="UTC")


def get_available_date_range(catalog: DataCatalog) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Get min/max date range from dispatch data for slider bounds."""
    dispatch = catalog.tables.get("dispatch", pd.DataFrame())
    if dispatch.empty or "timestamp" not in dispatch.columns:
        return pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-12-31", tz="UTC")

    series = pd.to_datetime(dispatch["timestamp"], errors="coerce", utc=True).dropna()
    if series.empty:
        return pd.Timestamp("2023-01-01", tz="UTC"), pd.Timestamp("2025-12-31", tz="UTC")

    return pd.Timestamp(series.min()), pd.Timestamp(series.max())


def filter_by_unit_and_time(
    df: pd.DataFrame,
    unit_id: str | None,
    start: pd.Timestamp,
    end: pd.Timestamp,
    ts_col_candidates: list[str] | None = None,
) -> pd.DataFrame:
    """Filter by unit and timestamp/date range."""
    if df.empty:
        return df

    out = df.copy()
    if unit_id and "unit_id" in out.columns:
        out = out[out["unit_id"].astype(str) == str(unit_id)]

    ts_col_candidates = ts_col_candidates or ["timestamp", "start_time", "date", "month"]
    ts_col = next((c for c in ts_col_candidates if c in out.columns), None)
    if ts_col:
        ts_vals = pd.to_datetime(out[ts_col], errors="coerce", utc=True)
        
        # For monthly data, check if the month overlaps with the date range
        if ts_col == "month":
            # Month overlaps if: month_start <= range_end AND month_end >= range_start
            month_start = ts_vals
            month_end = ts_vals + pd.offsets.MonthEnd(0)  # End of each month
            out = out[(month_start <= end) & (month_end >= start)]
        else:
            out = out[(ts_vals >= start) & (ts_vals <= end)]
    return out


def downsample_for_plotting(
    df: pd.DataFrame,
    resolution: str,
    max_days_5min: int = 30,
    ts_col: str = "timestamp",
) -> pd.DataFrame:
    """Downsample to hourly for plotting when range exceeds threshold."""
    if df.empty or ts_col not in df.columns:
        return df
    if resolution != "5-min":
        return df

    ts = pd.to_datetime(df[ts_col], errors="coerce", utc=True)
    if ts.dropna().empty:
        return df

    span_days = (ts.max() - ts.min()).days
    if span_days <= max_days_5min:
        return df

    out = df.copy()
    out[ts_col] = ts
    numeric_cols = out.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return df

    grouped = out.set_index(ts_col)[numeric_cols].resample("1H").mean().reset_index()

    passthrough = [c for c in ["unit_id", "deviation_type", "root_cause_category", "active_event_id"] if c in out.columns]
    for col in passthrough:
        grouped[col] = out.set_index(ts_col)[col].resample("1H").agg(lambda s: s.dropna().iloc[-1] if not s.dropna().empty else None).values
    return grouped
