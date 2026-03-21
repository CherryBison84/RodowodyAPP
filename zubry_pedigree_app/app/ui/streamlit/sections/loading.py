"""
Ekran wyboru pliku z danymi, mapowania kolumn i ewentualnego pobrania zestawienia z internetu.
"""

from __future__ import annotations

import streamlit as st

from app.analytics.population_genetics import TEST_ID
from app.data.dataset_loader import (
    load_dataset_from_bytes,
    load_default_bison_report,
    load_raw_dataframe_from_url,
    standardize_bison_report_dataframe_with_column_mapping,
)
from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_loading() -> None:
    st.markdown("### Wczytywanie bazy")
    st.caption("Plik CSV/XLSX, URL z mapowaniem kolumn, walidacja spójności.")
    sc.help_expander(
        "Co oznacza wczytywanie i walidacja?",
        hc.SECTION_LOADING + "\n\n" + hc.SECTION_VALIDATION,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Wczytaj domyślną bazę", width="stretch", type="primary"):
            try:
                df_std, _ = load_default_bison_report()
                sc.set_dataset(df_std, "Domyślna baza")
                st.success(f"Wczytano: {len(df_std)} wierszy.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with c2:
        uploaded = st.file_uploader("Wybierz plik bazy", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            try:
                df_std, _ = load_dataset_from_bytes(data=uploaded.read(), filename=uploaded.name)
                sc.set_dataset(df_std, f"Plik: {uploaded.name}")
                st.success(f"Wczytano plik: {uploaded.name}")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with st.expander("Pobieranie z internetu (URL) i mapowanie kolumn"):
        url = st.text_input("URL do pliku CSV/XLSX", key="st_url")
        if st.button("Pobierz z URL"):
            if not url.strip():
                st.warning("Podaj URL.")
            else:
                try:
                    raw = load_raw_dataframe_from_url(url.strip())
                    st.session_state["raw_df"] = raw
                    st.success(f"Pobrano: {len(raw)} wierszy.")
                except Exception as e:
                    st.error(str(e))
        raw_df = st.session_state.get("raw_df")
        if raw_df is not None and not raw_df.empty:
            cols = ["<brak>"] + [str(c) for c in raw_df.columns]
            st.markdown("**Mapowanie wymaganych pól**")
            m1, m2, m3 = st.columns(3)
            with m1:
                id_col = st.selectbox("id", cols, key="map_id")
                sex_col = st.selectbox("sex", cols, key="map_sex")
            with m2:
                line_col = st.selectbox("line", cols, key="map_line")
                birth_col = st.selectbox("birth_year", cols, key="map_by")
            with m3:
                father_col = st.selectbox("father_id", cols, key="map_f")
                mother_col = st.selectbox("mother_id", cols, key="map_m")
            if st.button("Zastosuj mapowanie i wczytaj"):
                mapping = {
                    "id": None if id_col == "<brak>" else id_col,
                    "sex": None if sex_col == "<brak>" else sex_col,
                    "line": None if line_col == "<brak>" else line_col,
                    "birth_year": None if birth_col == "<brak>" else birth_col,
                    "father_id": None if father_col == "<brak>" else father_col,
                    "mother_id": None if mother_col == "<brak>" else mother_col,
                }
                try:
                    df_std = standardize_bison_report_dataframe_with_column_mapping(
                        raw_df, mapping, test_id=TEST_ID
                    )
                    sc.set_dataset(df_std, "URL + mapowanie")
                    st.success(f"Wczytano po mapowaniu: {len(df_std)} wierszy.")
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    df_std = st.session_state.get("df_std")
    if df_std is not None and not df_std.empty:
        st.info(f"**Źródło:** {st.session_state.get('source', '-')} • **n =** {len(df_std)}")
        ids = df_std["id"].dropna().astype(str)
        if len(ids) > 0:
            st.caption(
                f"Zakres ID: min **{min(ids.tolist(), key=sc.id_sort_key)}**, "
                f"max **{max(ids.tolist(), key=sc.id_sort_key)}**"
            )
        rep = st.session_state.get("validation_report")
        if rep is not None:
            st.caption(f"Walidacja: **{rep.short_status()}**")
            with st.expander("Pełny raport walidacji (tekst)"):
                st.text(rep.to_text())
                st.download_button(
                    "Pobierz raport (.txt)",
                    data=rep.to_text(),
                    file_name="walidacja_bazy.txt",
                    mime="text/plain",
                )
