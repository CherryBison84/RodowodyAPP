from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.analytics.population_genetics import TEST_ID, compute_population_genetics_stats
from app.data.dataset_loader import (
    load_dataset_from_bytes,
    load_default_bison_report,
    load_raw_dataframe_from_url,
    standardize_bison_report_dataframe_with_column_mapping,
)
from app.data.validator import validate_loaded_dataset
from app.pedigree.ancestor_pedigree import (
    build_people_map,
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
)
from app.visualizations.ancestor_plot import plot_ancestor_pedigree


def _id_sort_key(s: str) -> tuple[int, str]:
    m = re.match(r"^(\d+)([A-Za-z]*)$", s)
    if not m:
        return (10**30, s)
    return (int(m.group(1)), m.group(2) or "")


def _set_dataset(df_std: pd.DataFrame, source: str) -> None:
    st.session_state["df_std"] = df_std
    st.session_state["source"] = source
    st.session_state["people"] = build_people_map(df_std)
    st.session_state["validation_report"] = validate_loaded_dataset(df_std=df_std, people=st.session_state["people"])


def _render_logo() -> None:
    logo_path = Path(__file__).resolve().parents[2] / "logo.png"
    if logo_path.exists():
        try:
            st.image(str(logo_path), width=110)
        except Exception:
            pass


def _load_default_once() -> None:
    if "df_std" in st.session_state:
        return
    try:
        df_std, _ = load_default_bison_report()
        _set_dataset(df_std, "Domyslna baza")
    except Exception:
        pass


def _section_loading() -> None:
    st.subheader("Wczytywanie bazy")
    st.caption("Plik (CSV/XLSX), URL oraz podstawowa walidacja po wczytaniu.")

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Wczytaj domyslna baze", use_container_width=True):
            try:
                df_std, _ = load_default_bison_report()
                _set_dataset(df_std, "Domyslna baza")
                st.success(f"Wczytano domyslna baze: {len(df_std)} wierszy.")
            except Exception as e:
                st.error(f"Nie udalo sie wczytac domyslnej bazy: {e}")

    with c2:
        uploaded = st.file_uploader("Wybierz plik bazy", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            try:
                df_std, _ = load_dataset_from_bytes(data=uploaded.read(), filename=uploaded.name)
                _set_dataset(df_std, f"Plik: {uploaded.name}")
                st.success(f"Wczytano plik: {uploaded.name}")
            except Exception as e:
                st.error(f"Blad wczytywania pliku: {e}")

    with st.expander("Pobieranie z URL + mapowanie kolumn", expanded=False):
        url = st.text_input("URL do pliku CSV/XLSX", value="")
        if st.button("Pobierz z URL", use_container_width=True):
            if not url.strip():
                st.warning("Podaj URL.")
            else:
                try:
                    raw = load_raw_dataframe_from_url(url.strip())
                    st.session_state["raw_df"] = raw
                    st.success(f"Pobrano surowa baze: {len(raw)} wierszy.")
                except Exception as e:
                    st.error(f"Blad pobierania: {e}")

        raw_df = st.session_state.get("raw_df")
        if raw_df is not None and not raw_df.empty:
            cols = ["<brak>"] + [str(c) for c in raw_df.columns]
            st.write("Mapowanie wymaganych kolumn:")
            m1, m2, m3 = st.columns(3)
            with m1:
                id_col = st.selectbox("id", cols, index=1 if len(cols) > 1 else 0)
                sex_col = st.selectbox("sex", cols, index=1 if len(cols) > 1 else 0)
            with m2:
                line_col = st.selectbox("line", cols, index=1 if len(cols) > 1 else 0)
                birth_col = st.selectbox("birth_year", cols, index=1 if len(cols) > 1 else 0)
            with m3:
                father_col = st.selectbox("father_id", cols, index=1 if len(cols) > 1 else 0)
                mother_col = st.selectbox("mother_id", cols, index=1 if len(cols) > 1 else 0)

            if st.button("Zastosuj mapowanie i wczytaj", use_container_width=True):
                mapping = {
                    "id": None if id_col == "<brak>" else id_col,
                    "sex": None if sex_col == "<brak>" else sex_col,
                    "line": None if line_col == "<brak>" else line_col,
                    "birth_year": None if birth_col == "<brak>" else birth_col,
                    "father_id": None if father_col == "<brak>" else father_col,
                    "mother_id": None if mother_col == "<brak>" else mother_col,
                }
                try:
                    df_std = standardize_bison_report_dataframe_with_column_mapping(raw_df, mapping, test_id=TEST_ID)
                    _set_dataset(df_std, "URL + mapowanie")
                    st.success(f"Wczytano baze po mapowaniu: {len(df_std)} wierszy.")
                except Exception as e:
                    st.error(f"Blad mapowania: {e}")

    df_std = st.session_state.get("df_std")
    if df_std is not None and not df_std.empty:
        st.info(f"Zrodlo: {st.session_state.get('source', '-')} • n={len(df_std)}")
        ids = df_std["id"].dropna().astype(str)
        if len(ids) > 0:
            st.caption(f"Zakres ID: min {min(ids.tolist(), key=_id_sort_key)}, max {max(ids.tolist(), key=_id_sort_key)}")
        report = st.session_state.get("validation_report")
        if report is not None:
            st.caption(f"Walidacja: {report.short_status()}")


def _section_persons(df_std: pd.DataFrame) -> None:
    st.subheader("Osobniki")
    sort_col = st.selectbox("Sortuj po kolumnie", options=list(df_std.columns), index=0)
    asc = st.toggle("Rosnaco", value=True)
    preview_n = st.slider("Liczba wierszy podgladu", min_value=25, max_value=500, value=250, step=25)
    view = df_std.sort_values(by=[sort_col], ascending=bool(asc)).head(preview_n)
    st.dataframe(view, use_container_width=True)


def _section_pedigree(df_std: pd.DataFrame, people: dict) -> None:
    st.subheader("Rodowod")
    default_id = str(df_std.iloc[0]["id"]) if not df_std.empty else ""
    person_id = st.text_input("ID (Number)", value=default_id, key="st_anc_id")
    depth = st.slider("Max pokolen", min_value=0, max_value=10, value=4, step=1)
    readable = st.checkbox("Tryb czytelny", value=True)
    if st.button("Generuj rodowod", type="primary"):
        if not person_id.strip() or person_id.strip() not in people:
            st.error("Podaj poprawne ID.")
            return
        levels, edges = get_ancestor_levels_and_edges(person_id=person_id.strip(), depth=int(depth), people=people)
        if not levels:
            st.warning("Brak danych przodkow w podanym limicie.")
            return
        fig = plot_ancestor_pedigree(
            person_id=person_id.strip(),
            levels=levels,
            edges=edges,
            people=ensure_people_for_nodes(levels=levels, people=people),
            readable_mode=bool(readable),
        )
        st.pyplot(fig, use_container_width=True)


def _section_analysis(df_std: pd.DataFrame, people: dict) -> None:
    st.subheader("Analizy osobnika")
    default_id = str(df_std.iloc[0]["id"]) if not df_std.empty else ""
    person_id = st.text_input("ID (Number)", value=default_id, key="st_inb_id")
    unbounded = st.checkbox("Bez limitu (do founderow)", value=True)
    depth = st.slider("Max pokolen (gdy limit)", min_value=0, max_value=20, value=4, step=1, disabled=unbounded)

    if st.button("Policz F (Wright)", type="primary"):
        if not person_id.strip() or person_id.strip() not in people:
            st.error("Podaj poprawne ID.")
            return
        f_res = wright_inbreeding_F(
            person_id=person_id.strip(),
            people=people,
            max_generations_back=None if unbounded else int(depth),
        )
        st.success(f"Inbred (Wright F): {f_res.F:.6f}")
        st.caption(
            f"Father={f_res.father_id} ({f_res.father_name}); Mother={f_res.mother_id} ({f_res.mother_name}); "
            f"used_generations={f_res.used_generations}."
        )


def _section_population(df_std: pd.DataFrame, people: dict) -> None:
    st.subheader("Populacja")
    with st.spinner("Liczenie statystyk populacyjnych..."):
        stats = compute_population_genetics_stats(
            df_std=df_std,
            people=people,
            max_generations_back=4,
            calc_f=True,
            calc_completeness=True,
            calc_founders=True,
            calc_lines=True,
        )
    c1, c2, c3 = st.columns(3)
    c1.metric("Liczba osobnikow", f"{stats.n}")
    c2.metric("Srednie F", f"{stats.inbreeding.mean_F:.4f}")
    c3.metric("Mean PCI", f"{stats.completeness.mean_PCI:.4f}")

    if stats.f_values:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.hist(stats.f_values, bins=30, color="#d5c4ae", edgecolor="#4b3a2a")
        ax.set_title("Rozklad F (Wright)")
        ax.set_xlabel("F")
        ax.set_ylabel("liczba osobnikow")
        st.pyplot(fig, use_container_width=True)


def run_streamlit_direct() -> None:
    st.set_page_config(page_title="WisentPedigree Pro+", layout="wide")
    _load_default_once()

    _render_logo()
    st.title("WisentPedigree Pro+")
    st.caption("Wersja Streamlit (robocza)")

    section = st.sidebar.radio(
        "Nawigacja",
        [
            "Wczytywanie bazy",
            "Osobniki",
            "Rodowod",
            "Analizy",
            "Populacja",
            "Raporty",
            "Plan hodowlany",
            "Ustawienia",
        ],
    )

    if section == "Wczytywanie bazy":
        _section_loading()
        return

    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")
    if df_std is None or people is None or len(df_std) == 0:
        st.warning("Najpierw wczytaj baze w sekcji 'Wczytywanie bazy'.")
        return

    if section == "Osobniki":
        _section_persons(df_std)
    elif section == "Rodowod":
        _section_pedigree(df_std, people)
    elif section == "Analizy":
        _section_analysis(df_std, people)
    elif section == "Populacja":
        _section_population(df_std, people)
    elif section == "Raporty":
        st.subheader("Raporty")
        st.info("Sekcja Streamlit jest w przygotowaniu. Uzyj wersji Tk do pelnego eksportu DOCX/PDF.")
    elif section == "Plan hodowlany":
        st.subheader("Plan hodowlany")
        st.info("Sekcja jest w przygotowaniu i wymaga dalszego dopracowania.")
    elif section == "Ustawienia":
        st.subheader("Ustawienia")
        st.info("Sekcja ustawien dla Streamlit bedzie dodana w kolejnej iteracji.")


if __name__ == "__main__":
    run_streamlit_direct()

