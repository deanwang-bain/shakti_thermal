"""Styling utilities for Bain-branded Streamlit demo."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

BAIN_RED = "#CB2026"


def _load_svg_base64(svg_path: Path) -> str:
    if not svg_path.exists():
        return ""
    return base64.b64encode(svg_path.read_bytes()).decode("utf-8")


def apply_bain_style() -> None:
    """Inject global CSS aligned to Bain accent and accessibility constraints."""
    st.markdown(
        f"""
        <style>
            html, body, [class*="css"], .stApp {{
                font-family: Arial, sans-serif;
            }}
            h1, h2, h3, h4 {{
                color: #1F2937;
            }}
            .stButton > button {{
                background: {BAIN_RED} !important;
                color: white !important;
                border: 1px solid {BAIN_RED} !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
            }}
            .stButton > button:hover {{
                opacity: 0.92;
            }}
            a {{
                color: {BAIN_RED} !important;
            }}
            [data-baseweb="tab-highlight"] {{
                background-color: {BAIN_RED} !important;
            }}
            [data-baseweb="tab"] p {{
                font-weight: 600;
            }}
            .kpi-card {{
                border: 1px solid #E5E7EB;
                border-left: 4px solid {BAIN_RED};
                border-radius: 10px;
                padding: 10px 12px;
                background: #FFFFFF;
            }}
            .kpi-label {{
                color: #4B5563;
                font-size: 0.84rem;
            }}
            .kpi-value {{
                color: {BAIN_RED};
                font-size: 1.25rem;
                font-weight: 700;
            }}
            .status-pass {{ color: #166534; font-weight: 700; }}
            .status-warn {{ color: #9A3412; font-weight: 700; }}
            .status-fail {{ color: #991B1B; font-weight: 700; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(assets_dir: Path) -> None:
    """Render app header with placeholder logo."""
    logo_data = _load_svg_base64(assets_dir / "bain_logo_placeholder.svg")
    if logo_data:
        logo_html = (
            f'<img alt="Bain placeholder" src="data:image/svg+xml;base64,{logo_data}" '
            'style="height:38px; margin-left:8px;"/>'
        )
    else:
        logo_html = ""

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div>
                <h2 style="margin:0;">Plant Co — Full Potential Demo</h2>
            </div>
            <div>{logo_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_strip(items: list[tuple[str, str]]) -> None:
    """Render KPI strip cards."""
    cols = st.columns(len(items))
    for col, (label, value) in zip(cols, items):
        col.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-label">{label}</div>
                <div class="kpi-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
