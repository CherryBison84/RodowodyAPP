"""
Główny ekran wersji przeglądarkowej: wybór zakładki i przełączanie między ekranami wczytywania,
listy osobników, populacji, analiz itd.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.config import app_icon_pil_best
from app.ui.streamlit import common as sc
from app.ui.streamlit.pages import (
    section_analysis_individual,
    section_analysis_pairs_and_mating,
    section_breeding,
    section_import,
    section_persons,
    section_population,
    section_reports,
    section_validation,
)

# Etykiety nawigacji (krótkie; pełny opis w nagłówkach sekcji).
NAV_IMPORT = "Import danych"
NAV_VALIDATION = "Walidacja"
NAV_PERSONS = "Rejestr"
NAV_ANALYSIS_IND = "Analiza osobnicza"
NAV_ANALYSIS_PAIRS = "Pary i kojarzenia"
NAV_POPULATION = "Populacja"
NAV_BREEDING = "Plan hodowlany"
NAV_REPORTS = "Raporty"

NAV_SECTIONS = [
    NAV_IMPORT,
    NAV_VALIDATION,
    NAV_PERSONS,
    NAV_ANALYSIS_IND,
    NAV_POPULATION,
    NAV_ANALYSIS_PAIRS,
    NAV_BREEDING,
    NAV_REPORTS,
]


def _render_page_footer() -> None:
    """Pomoc na dole strony: słownik i literatura (zwinięte)."""
    st.markdown("---")
    st.caption("Pomoc, skróty i materiały")
    with st.expander("Słownik parametrów (F, GI, f_e, RIA…)", expanded=False):
        st.markdown(sc.GLOSSARY)
    with st.expander("Literatura — źródła metod (F, p_i, N_e…)", expanded=False):
        st.markdown(sc.SECTION_REFERENCES)


def run_streamlit_direct() -> None:
    _icon_img = app_icon_pil_best()
    st.set_page_config(
        page_title="WisentPedigree Pro+",
        page_icon=_icon_img if _icon_img is not None else "🦬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    sc.apply_page_style()
    sc.load_default_once()

    with st.sidebar:
        _logo_path = Path(__file__).resolve().parents[2] / "logo.png"
        if _logo_path.exists():
            st.image(str(_logo_path), width="stretch")
        st.markdown(
            f'<p style="margin:0.6rem 0 0.35rem 0;font-size:0.78rem;font-weight:700;'
            f"letter-spacing:0.04em;text-transform:uppercase;color:{sc.THEME.MUTED};"
            f'">Nawigacja</p>',
            unsafe_allow_html=True,
        )
        section = st.radio(
            "Nawigacja",
            NAV_SECTIONS,
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("Autor: Magdalena Perlińska-Teresiak • 2026")

    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")

    if section == NAV_IMPORT:
        section_import()
    elif section == NAV_VALIDATION:
        if df_std is None or people is None or len(df_std) == 0:
            st.warning(f"Najpierw wczytaj dane w sekcji **{NAV_IMPORT}**.")
        else:
            section_validation()
    elif df_std is None or people is None or len(df_std) == 0:
        st.warning(f"Najpierw wczytaj dane w sekcji **{NAV_IMPORT}**.")
    elif section == NAV_PERSONS:
        section_persons(df_std)
    elif section == NAV_ANALYSIS_IND:
        section_analysis_individual(df_std, people)
    elif section == NAV_POPULATION:
        section_population(df_std, people)
    elif section == NAV_ANALYSIS_PAIRS:
        section_analysis_pairs_and_mating(df_std, people)
    elif section == NAV_REPORTS:
        section_reports()
    elif section == NAV_BREEDING:
        section_breeding(df_std, people)

    _render_page_footer()


if __name__ == "__main__":
    run_streamlit_direct()
