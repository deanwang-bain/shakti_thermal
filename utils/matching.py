"""Fuzzy mapping helpers for GenAI-like matching UX."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd
from rapidfuzz import fuzz


@dataclass
class MatchEntity:
    entity_type: str
    entity_id: str
    canonical_name: str
    aliases: list[str]


def _safe_aliases(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
        return [text]
    return []


def build_entity_catalog(asset_df: pd.DataFrame, sensor_df: pd.DataFrame) -> list[MatchEntity]:
    """Create searchable entities from asset and sensor tables."""
    entities: list[MatchEntity] = []
    if not asset_df.empty:
        for row in asset_df.fillna("").to_dict("records"):
            entities.append(
                MatchEntity(
                    entity_type="asset",
                    entity_id=str(row.get("asset_id", "")),
                    canonical_name=str(row.get("canonical_name", row.get("asset_id", ""))),
                    aliases=_safe_aliases(row.get("aliases_json")),
                )
            )

    if not sensor_df.empty:
        for row in sensor_df.fillna("").to_dict("records"):
            entities.append(
                MatchEntity(
                    entity_type="tag",
                    entity_id=str(row.get("tag_id", "")),
                    canonical_name=str(row.get("tag_name", row.get("tag_id", ""))),
                    aliases=_safe_aliases(row.get("aliases_json")),
                )
            )
    return entities


def fuzzy_match(query: str, entities: list[MatchEntity], top_n: int = 10) -> pd.DataFrame:
    """Return top fuzzy matches with combined confidence score."""
    if not query.strip() or not entities:
        return pd.DataFrame()

    query_clean = query.strip()
    rows = []
    for entity in entities:
        alias_space = " | ".join([entity.canonical_name, *entity.aliases])
        token = fuzz.token_sort_ratio(query_clean, alias_space)
        partial = fuzz.partial_ratio(query_clean, alias_space)
        combined = round(0.55 * token + 0.45 * partial, 1)

        if combined >= 90:
            confidence = "High"
        elif combined >= 75:
            confidence = "Medium"
        else:
            confidence = "Low"

        hit_aliases = [a for a in entity.aliases if fuzz.partial_ratio(query_clean, a) >= 80][:2]
        explain = (
            f"Matched due to overlap with aliases: {', '.join(hit_aliases)}"
            if hit_aliases
            else "Matched by lexical similarity to canonical name and aliases"
        )
        rows.append(
            {
                "entity_type": entity.entity_type,
                "canonical_name": entity.canonical_name,
                "id": entity.entity_id,
                "token_sort_ratio": token,
                "partial_ratio": partial,
                "combined_score": combined,
                "confidence": confidence,
                "explanation": explain,
            }
        )

    out = pd.DataFrame(rows).sort_values("combined_score", ascending=False).head(top_n)
    return out.reset_index(drop=True)


def map_work_orders(
    work_orders_df: pd.DataFrame,
    entities: list[MatchEntity],
    sample_size: int = 50,
) -> pd.DataFrame:
    """Predict top asset match for work order messy descriptions."""
    if work_orders_df.empty or not entities:
        return pd.DataFrame()

    sample_df = work_orders_df.sample(min(sample_size, len(work_orders_df)), random_state=42).copy()

    predictions = []
    for row in sample_df.fillna("").to_dict("records"):
        raw = str(row.get("asset_description_raw", ""))
        candidates = fuzzy_match(raw, entities, top_n=5)
        if candidates.empty:
            predictions.append(
                {
                    "wo_id": row.get("wo_id"),
                    "asset_description_raw": raw,
                    "predicted_asset_id": None,
                    "predicted_asset_name": None,
                    "score": 0.0,
                    "top5_asset_ids": "",
                    "standard_asset_id_truth": row.get("standard_asset_id_truth"),
                }
            )
            continue

        top = candidates.iloc[0]
        top5_assets = candidates[candidates["entity_type"] == "asset"]["id"].tolist()
        predictions.append(
            {
                "wo_id": row.get("wo_id"),
                "asset_description_raw": raw,
                "predicted_asset_id": top["id"],
                "predicted_asset_name": top["canonical_name"],
                "score": top["combined_score"],
                "top5_asset_ids": "|".join(top5_assets[:5]),
                "standard_asset_id_truth": row.get("standard_asset_id_truth"),
            }
        )

    return pd.DataFrame(predictions)


def compute_mapping_accuracy(mapped_df: pd.DataFrame) -> dict[str, float]:
    """Compute accuracy@1 and @5 when truth column exists."""
    if mapped_df.empty or "standard_asset_id_truth" not in mapped_df.columns:
        return {"accuracy_at_1": float("nan"), "accuracy_at_5": float("nan")}

    eval_df = mapped_df.dropna(subset=["standard_asset_id_truth"]).copy()
    if eval_df.empty:
        return {"accuracy_at_1": float("nan"), "accuracy_at_5": float("nan")}

    acc1 = (eval_df["predicted_asset_id"] == eval_df["standard_asset_id_truth"]).mean()

    def in_top5(row: pd.Series) -> bool:
        truth = str(row["standard_asset_id_truth"])
        top5 = str(row.get("top5_asset_ids", "")).split("|")
        return truth in top5

    acc5 = eval_df.apply(in_top5, axis=1).mean()
    return {"accuracy_at_1": float(acc1), "accuracy_at_5": float(acc5)}
