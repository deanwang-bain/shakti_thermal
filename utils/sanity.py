"""Startup sanity and reconciliation checks."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from utils.data import DataCatalog
from utils.metrics import standardize_dispatch_columns


@dataclass
class CheckResult:
    name: str
    status: str
    message: str


def _status_from_bool(ok: bool, warn: bool = False) -> str:
    if ok:
        return "pass"
    return "warn" if warn else "fail"


def check_required_presence(catalog: DataCatalog) -> list[CheckResult]:
    """Check if required datasets are present."""
    results: list[CheckResult] = []
    for key, st in catalog.statuses.items():
        if not st.required:
            continue
        ok = st.loaded
        results.append(
            CheckResult(
                name=f"Required dataset: {key}",
                status=_status_from_bool(ok, warn=True),
                message="Loaded" if ok else (st.warning or "Missing required dataset"),
            )
        )
    return results


def check_dispatch_delta(dispatch_df: pd.DataFrame) -> CheckResult:
    """Validate delta_mw and delta_mwh consistency."""
    if dispatch_df.empty:
        return CheckResult("Dispatch delta checks", "warn", "Dispatch dataset unavailable")

    df = standardize_dispatch_columns(dispatch_df)
    required = {"dispatch_target_mw", "net_generation_mw", "delta_mw"}
    if not required.issubset(df.columns):
        return CheckResult("Dispatch delta checks", "warn", "Missing columns for delta validation")

    calc = df["dispatch_target_mw"] - df["net_generation_mw"]
    err_mw = (df["delta_mw"] - calc).abs().median()

    err_mwh = np.nan
    if "delta_mwh" in df.columns:
        calc_mwh = calc * (5 / 60)
        err_mwh = (df["delta_mwh"] - calc_mwh).abs().median()

    ok_mw = err_mw < 0.5
    ok_mwh = np.isnan(err_mwh) or err_mwh < 0.1
    overall = ok_mw and ok_mwh

    return CheckResult(
        name="Dispatch delta checks",
        status=_status_from_bool(overall, warn=True),
        message=f"Median |delta_mw error|={err_mw:.3f}, |delta_mwh error|={err_mwh:.3f}" if not np.isnan(err_mwh) else f"Median |delta_mw error|={err_mw:.3f}",
    )


def check_revenue_reconciliation(recon_df: pd.DataFrame, tolerance: float = 1e-3) -> CheckResult:
    """Recompute RCR and loss from daily reconciliation file if available."""
    if recon_df.empty:
        return CheckResult("Revenue reconciliation", "warn", "daily_revenue_reconciliation.csv not available")

    cols = {"actual_revenue_usd", "max_potential_revenue_usd", "revenue_loss_usd", "revenue_capture_ratio"}
    if not cols.issubset(recon_df.columns):
        return CheckResult("Revenue reconciliation", "warn", "Reconciliation columns incomplete")

    df = recon_df.copy()
    actual = pd.to_numeric(df["actual_revenue_usd"], errors="coerce")
    potential = pd.to_numeric(df["max_potential_revenue_usd"], errors="coerce")
    loss = pd.to_numeric(df["revenue_loss_usd"], errors="coerce")
    rcr = pd.to_numeric(df["revenue_capture_ratio"], errors="coerce")

    loss_calc = potential - actual
    rcr_calc = actual / potential.replace(0, np.nan)

    err_loss = (loss - loss_calc).abs().median()
    err_rcr = (rcr - rcr_calc).abs().median()

    ok = (err_loss <= tolerance * max(1.0, float(loss_calc.abs().median()))) and (err_rcr <= 0.01)
    status = _status_from_bool(ok, warn=True)
    return CheckResult(
        name="Revenue reconciliation",
        status=status,
        message=f"Median loss diff={err_loss:.3f}, median RCR diff={err_rcr:.4f}",
    )


def run_startup_checks(catalog: DataCatalog) -> list[CheckResult]:
    """Run all non-fatal startup checks."""
    results = check_required_presence(catalog)
    results.append(check_dispatch_delta(catalog.tables.get("dispatch", pd.DataFrame())))
    results.append(check_revenue_reconciliation(catalog.tables.get("daily_reconciliation", pd.DataFrame())))

    if catalog.schema_issues:
        for key, missing in catalog.schema_issues.items():
            results.append(
                CheckResult(
                    name=f"Schema check: {key}",
                    status="warn",
                    message=f"Missing columns: {', '.join(missing)}",
                )
            )
    else:
        results.append(CheckResult("Schema checks", "pass", "No schema mismatches detected"))

    return results
