"""
WisentPedigree DataCleaner (interfejs Streamlit).

Przygotowanie baz do analizy rodowodowej.
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
from app.runtime_path import assets_dir
from app.ui.streamlit import common as sc
from app.ui.streamlit.huba_nav import NAV_SECTIONS, NAV_STEP1, _NAV_LEGACY
from app.ui.streamlit.huba_ui import run_huba_app

HUBA_APP_NAME = "WisentPedigree DataCleaner"
HUBA_TAGLINE = "przygotowanie baz do analizy rodowodowej"
HUBA_VERSION = "1.2.0"


def _render_sidebar() -> None:
    """Renderuje logo, metadane aplikacji i nawigację po krokach HUBA."""
    with st.sidebar:
        _logo_path = assets_dir() / "logo.png"
        if _logo_path.exists():
            st.image(str(_logo_path), width="stretch")
        st.markdown(
            '<div class="huba-sidebar-title">'
            f"<p>{HUBA_APP_NAME}</p>"
            f"<span>{HUBA_TAGLINE}</span>"
            f'<strong class="huba-sidebar-version">v{HUBA_VERSION}</strong>'
            "</div>",
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
        st.markdown(
            '<div class="huba-terminal-card">'
            '<p class="huba-terminal-title">Wersja terminalowa</p>'
            '<p>DataCleaner można uruchomić bez UI, bezpośrednio w terminalu:</p>'
            '<code>cd zubry_pedigree_app &amp;&amp; python run_cli.py run --input data/EBPB_bison_report.xlsx --project-name terminal_demo</code>'
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div class="huba-sidebar-footer">'
            '<span>Autor: </span>'
            '<a href="https://github.com/CherryBison84" target="_blank">Magdalena Perlińska-Teresiak</a>'
            '<span> · </span>'
            '<a href="https://bw.sggw.edu.pl/info/author/WULS3c538856ad724c8ab12824cb5666f3f1?r=author&tab=&title=Profil%2Bosoby%2B%25E2%2580%2593%2BMagdalena%2BPerli%25C5%2584ska-Teresiak%2B%25E2%2580%2593%2BSzko%25C5%2582a%2BG%25C5%2582%25C3%25B3wna%2BGospodarstwa%2BWiejskiego%2Bw%2BWarszawie&lang=pl" target="_blank">SGGW</a>'
            '<span> · 2026</span>'
            "</div>",
            unsafe_allow_html=True,
        )


def run_streamlit_direct() -> None:
    """Konfiguruje stronę Streamlit i uruchamia główny widok aplikacji."""
    _icon_img = app_icon_pil_best()
    st.set_page_config(
        page_title=HUBA_APP_NAME,
        page_icon=_icon_img if _icon_img is not None else "🦬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    sc.apply_page_style()
    _render_sidebar()
    run_huba_app()


if __name__ == "__main__":
    run_streamlit_direct()
