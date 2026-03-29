"""
Główny ekran wersji przeglądarkowej: wybór zakładki i przełączanie między ekranami wczytywania,
listy osobników, populacji, analiz itd.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.ui.streamlit import common as sc
from app.ui.streamlit.pages import (
    section_analysis_inbred,
    section_analysis_mating,
    section_breeding_placeholder,
    section_loading,
    section_pedigree,
    section_persons,
    section_population,
    section_reports,
    section_settings,
)


def run_streamlit_direct() -> None:
    st.set_page_config(
        page_title="WisentPedigree Pro+",
        page_icon="🦬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    sc.apply_page_style()
    sc.load_default_once()

    with st.sidebar:
        _logo_path = Path(__file__).resolve().parents[2] / "logo.png"
        if _logo_path.exists():
            st.image(str(_logo_path), width=140)
        st.markdown("### WisentPedigree Pro+")
        st.caption("Analiza rodowodów żubrów")
        section = st.radio(
            "Nawigacja",
            [
                "Import i walidacja",
                "Rejestr osobników",
                "Graf pedigree",
                "Analityka hodowlana",
                "Metryki populacji",
                "Raportowanie",
                "Plan hodowli",
                "Konfiguracja",
            ],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("Autor: Magdalena Perlińska-Teresiak • 2026")
        with st.expander("Słownik parametrów (F, GI, f_e, RIA…)", expanded=False):
            st.markdown(sc.GLOSSARY)
        with st.expander("Walidacja bazy — skrót", expanded=False):
            st.markdown(sc.SECTION_VALIDATION)

    st.markdown(
        f'<p style="color:{sc.THEME.MUTED};font-family:{sc.FONT_FAMILY_CSS};font-size:1.05rem;line-height:1.5;margin-top:0;">'
        "Import danych • Analityka • Pedigree • Metryki populacji • Raportowanie"
        "</p>",
        unsafe_allow_html=True,
    )

    if section == "Import i walidacja":
        section_loading()
        return

    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")
    if df_std is None or people is None or len(df_std) == 0:
        st.warning("Najpierw wczytaj dane w sekcji **Import i walidacja**.")
        return

    if section == "Rejestr osobników":
        section_persons(df_std)
    elif section == "Graf pedigree":
        section_pedigree(df_std, people)
    elif section == "Analityka hodowlana":
        t1, t2 = st.tabs(["Inbred — współczynnik F", "Optymalizacja kojarzeń"])
        with t1:
            section_analysis_inbred(people)
        with t2:
            section_analysis_mating(df_std, people)
    elif section == "Metryki populacji":
        section_population(df_std, people)
    elif section == "Raportowanie":
        section_reports()
    elif section == "Plan hodowli":
        section_breeding_placeholder()
    elif section == "Konfiguracja":
        section_settings()


if __name__ == "__main__":
    run_streamlit_direct()
