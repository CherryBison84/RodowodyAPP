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
    section_breeding_placeholder,
    section_import,
    section_persons,
    section_population,
    section_reports,
    section_settings,
    section_validation,
)


@st.cache_data(show_spinner=False)
def _methods_guide_pdf_cached() -> bytes:
    from app.ui.methods_guide_pdf import methods_guide_pdf_bytes

    return methods_guide_pdf_bytes()


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
            st.image(str(_logo_path), width=140)
        st.markdown("### WisentPedigree Pro+")
        st.caption("Analiza rodowodów żubrów")
        section = st.radio(
            "Nawigacja",
            [
                "Import danych",
                "Walidacja bazy",
                "Rejestr osobników",
                "Analiza osobnika",
                "Analiza par i kojarzenia",
                "Metryki populacji",
                "Raportowanie",
                "Plan hodowli",
                "Konfiguracja",
            ],
            label_visibility="collapsed",
        )
        st.caption(
            "Przepływ: import → walidacja → rejestr → osobnik → pary → populacja → raport."
        )
        st.markdown("---")
        st.caption("Autor: Magdalena Perlińska-Teresiak • 2026")
        with st.expander("Słownik parametrów (F, GI, f_e, RIA…)", expanded=False):
            st.markdown(sc.GLOSSARY)
        with st.expander("Walidacja — skrót (po imporcie)", expanded=False):
            st.markdown(sc.SECTION_VALIDATION)
        with st.expander("Literatura — źródła metod (F, p_i, N_e…)", expanded=False):
            st.markdown(sc.SECTION_REFERENCES)
        st.download_button(
            "Pobierz przewodnik metod (PDF — cytowania)",
            data=_methods_guide_pdf_cached(),
            file_name="WisentPedigree_Pro_przewodnik_metod_2026.pdf",
            mime="application/pdf",
            key="sidebar_methods_pdf",
        )

    st.markdown(
        f'<p style="color:{sc.THEME.MUTED};font-family:{sc.FONT_FAMILY_CSS};font-size:1.05rem;line-height:1.5;margin-top:0;">'
        "Import → walidacja → rejestr → analiza osobnika → analiza par → populacja → raport"
        "</p>",
        unsafe_allow_html=True,
    )

    if section == "Import danych":
        section_import()
        return

    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")

    if section == "Walidacja bazy":
        if df_std is None or people is None or len(df_std) == 0:
            st.warning("Najpierw wczytaj dane w sekcji **Import danych**.")
            return
        section_validation()
        return

    if df_std is None or people is None or len(df_std) == 0:
        st.warning("Najpierw wczytaj dane w sekcji **Import danych**.")
        return

    if section == "Rejestr osobników":
        section_persons(df_std)
    elif section == "Analiza osobnika":
        section_analysis_individual(df_std, people)
    elif section == "Analiza par i kojarzenia":
        section_analysis_pairs_and_mating(df_std, people)
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
