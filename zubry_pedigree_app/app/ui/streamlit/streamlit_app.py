"""
HUBA — Hybrid Unified Batch Analyzer (interfejs Streamlit).

Czyszczenie i standaryzacja wielu plików wejściowych; moduły analityki genetycznej są wyłączone.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Streamlit uruchamia ten plik bezpośrednio — ustaw katalog projektu na sys.path.
_pkg_root = Path(__file__).resolve().parents[3]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))

import streamlit as st

from app.config import app_icon_pil_best
from app.ui.streamlit import common as sc
from app.ui.streamlit.huba_ui import NAV_SECTIONS, NAV_STEP1, _NAV_LEGACY, run_huba_app

HUBA_TAGLINE = "Hybrid Unified Batch Analyzer"


def _render_sidebar() -> None:
    with st.sidebar:
        _logo_path = Path(__file__).resolve().parents[2] / "logo_new.png"
        if _logo_path.exists():
            st.image(str(_logo_path), width="stretch")
        st.markdown(
            f'<p style="margin:0.35rem 0 0.1rem 0;font-size:1.05rem;font-weight:700;color:{sc.THEME.TEXT};">'
            f"HUBA</p>"
            f'<p style="margin:0 0 0.5rem 0;font-size:0.72rem;color:{sc.THEME.MUTED};">'
            f"{HUBA_TAGLINE}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="margin:0.6rem 0 0.35rem 0;font-size:0.78rem;font-weight:700;'
            f'letter-spacing:0.04em;text-transform:uppercase;color:{sc.THEME.MUTED};">'
            f"Kroki</p>",
            unsafe_allow_html=True,
        )
        nav = st.session_state.get("huba_nav", NAV_STEP1)
        if nav in _NAV_LEGACY:
            nav = _NAV_LEGACY[str(nav)]
        if nav not in NAV_SECTIONS:
            nav = NAV_STEP1
        idx = NAV_SECTIONS.index(nav)
        section = st.radio(
            "Kroki",
            NAV_SECTIONS,
            index=idx,
            label_visibility="collapsed",
        )
        st.session_state["huba_nav"] = section
        st.markdown("---")
        st.caption(
            "Autor: [Magdalena Perlińska-Teresiak](https://github.com/CherryBison84) · 2026"
        )


def run_streamlit_direct() -> None:
    _icon_img = app_icon_pil_best()
    st.set_page_config(
        page_title="HUBA — Hybrid Unified Batch Analyzer",
        page_icon=_icon_img if _icon_img is not None else "🦬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    sc.apply_page_style()
    _render_sidebar()
    run_huba_app()


if __name__ == "__main__":
    run_streamlit_direct()
