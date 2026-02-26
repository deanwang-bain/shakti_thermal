"""Ontology graph and inspector utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
from pyvis.network import Network


def _safe_aliases(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


def _node_color(node_type: str) -> str:
    t = str(node_type).lower()
    if "plant" in t:
        return "#CB2026"
    if "unit" in t:
        return "#EA6A6E"
    if "system" in t:
        return "#F0A3A6"
    if "subsystem" in t:
        return "#BBD7EE"
    if "component" in t:
        return "#92B7D5"
    if "tag" in t:
        return "#6B7280"
    return "#9CA3AF"


def _edge_color(edge_type: str) -> str:
    """Return color based on edge mapping method."""
    etype = str(edge_type).upper()
    # Mapped by ID (structural hierarchy and direct references)
    if etype in ("PARENT_OF", "LINKED_TO", "REFERS_TO", "SENT_FROM", "SENT_TO"):
        return "#2563EB"  # Blue
    # Mapped by fuzzy logic (text-based matching)
    if etype in ("MENTIONS", "EVIDENCE_FOR"):
        return "#F59E0B"  # Amber
    # Mapped by timestamp/time window (temporal relationships)
    if etype in ("CAPTURED_AT", "AFFECTS", "MEASURES"):
        return "#10B981"  # Green
    return "#6B7280"  # Gray default


def build_pyvis_html(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    events_df: pd.DataFrame,
    work_orders_df: pd.DataFrame,
) -> str:
    """Build pyvis graph and return HTML content."""
    graph = Network(height="620px", width="100%", directed=True, bgcolor="#FFFFFF", font_color="#111827")
    graph.barnes_hut(gravity=-2000, central_gravity=0.2)
    existing_nodes: set[str] = set()

    def ensure_node(node_id: str, label: str | None = None, title: str | None = None, group: str = "Unmapped") -> None:
        node_id = str(node_id).strip()
        if not node_id or node_id in existing_nodes:
            return
        graph.add_node(
            node_id,
            label=(label or node_id)[:26],
            title=title or f"{node_id}<br>Type: {group}",
            color=_node_color(group),
            group=group,
        )
        existing_nodes.add(node_id)

    if not nodes_df.empty:
        for row in nodes_df.fillna("").to_dict("records"):
            node_id = str(row.get("node_id", "")).strip()
            if not node_id:
                continue
            node_type = str(row.get("node_type", "Unknown"))
            canonical = str(row.get("canonical_name", node_id))
            desc = str(row.get("description", ""))
            ensure_node(
                node_id=node_id,
                label=canonical,
                title=f"{canonical}<br>Type: {node_type}<br>{desc}",
                group=node_type,
            )

    if not edges_df.empty:
        for row in edges_df.fillna("").to_dict("records"):
            src = str(row.get("src_node_id", "")).strip()
            dst = str(row.get("dst_node_id", "")).strip()
            if not src or not dst:
                continue
            etype = str(row.get("edge_type", "LINK"))
            ensure_node(src)
            ensure_node(dst)
            graph.add_edge(src, dst, label=etype, title=etype, color=_edge_color(etype))

    if not events_df.empty:
        for row in events_df.fillna("").head(120).to_dict("records"):
            event_id = str(row.get("event_id", "")).strip()
            asset = str(row.get("linked_asset_id", "")).strip()
            if not event_id:
                continue
            event_type = str(row.get("type", "Event"))
            ensure_node(
                node_id=event_id,
                label=event_id,
                title=f"{event_type}<br>{row.get('root_cause_category', '')}",
                group="Event",
            )
            if asset:
                ensure_node(asset)
                graph.add_edge(event_id, asset, label="AFFECTS", title="AFFECTS", color=_edge_color("AFFECTS"))

    if not work_orders_df.empty:
        for row in work_orders_df.fillna("").head(100).to_dict("records"):
            wo_id = str(row.get("wo_id", "")).strip()
            if not wo_id:
                continue
            linked_event = str(row.get("linked_event_id", "")).strip()
            text = str(row.get("asset_description_raw", ""))
            ensure_node(wo_id, label=wo_id, title=text, group="WorkOrder")
            if linked_event:
                ensure_node(linked_event, group="Event")
                graph.add_edge(wo_id, linked_event, label="REFERENCES", title="REFERENCES", color=_edge_color("REFERS_TO"))

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
        graph.save_graph(tmp.name)
        return Path(tmp.name).read_text(encoding="utf-8")


def node_options(nodes_df: pd.DataFrame) -> list[str]:
    """List node ids for selector."""
    if nodes_df.empty or "node_id" not in nodes_df.columns:
        return []
    return sorted(nodes_df["node_id"].astype(str).unique().tolist())


def get_node_inspector(
    node_id: str,
    nodes_df: pd.DataFrame,
    sensor_df: pd.DataFrame,
    events_df: pd.DataFrame,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> dict[str, object]:
    """Return details for selected node."""
    summary: dict[str, object] = {
        "node": {},
        "aliases": [],
        "linked_tags": pd.DataFrame(),
        "recent_events": pd.DataFrame(),
    }
    if not node_id:
        return summary

    # Extract plain ID by stripping type prefixes like "ASSET::" or "TAG::"
    plain_id = node_id
    if "::" in node_id:
        plain_id = node_id.split("::", 1)[1]

    if not nodes_df.empty and "node_id" in nodes_df.columns:
        hit = nodes_df[nodes_df["node_id"].astype(str) == str(node_id)]
        if not hit.empty:
            summary["node"] = hit.iloc[0].to_dict()
            aliases = _safe_aliases(hit.iloc[0].get("aliases_json"))
            summary["aliases"] = aliases

    if not sensor_df.empty and "asset_id" in sensor_df.columns:
        summary["linked_tags"] = sensor_df[sensor_df["asset_id"].astype(str) == str(plain_id)].copy()

    if not events_df.empty and "linked_asset_id" in events_df.columns:
        recent = events_df[events_df["linked_asset_id"].astype(str) == str(plain_id)].copy()
        if "start_time" in recent.columns:
            recent["start_time"] = pd.to_datetime(recent["start_time"], errors="coerce", utc=True)
            recent = recent[(recent["start_time"] >= start) & (recent["start_time"] <= end)]
            recent = recent.sort_values("start_time", ascending=False)
        summary["recent_events"] = recent.head(8)

    return summary
