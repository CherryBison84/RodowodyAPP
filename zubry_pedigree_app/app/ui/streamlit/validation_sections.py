"""
Podsekcje Walidacji: wybór w dwóch rzędach (przyciski), treść wg klucza oraz panel auto-poprawek.

Wywoływane z kontekstu Streamlit (`pages.section_validation`).
"""

from __future__ import annotations

import csv
from io import StringIO
from typing import Final, FrozenSet, Sequence

import pandas as pd
import streamlit as st

from app.data.dataset_loader import dataframe_app_schema_columns
from app.data.validator import ValidationIssue, ValidationReport, parent_field_nonempty
from app.ui import help_content as hc
from app.ui.streamlit import common as sc
import app.ui.streamlit.streamlit_plotting as splt

# Kolejność i klucze wewnętrzne (stabilne dla stanu sesji i mapowań).
VALIDATION_TAB_KEYS: Final[tuple[str, ...]] = (
    "excel",
    "id",
    "parents",
    "chrono",
    "graph",
    "lines",
    "ancestors",
    "report",
    "autofix",
)

VALIDATION_TAB_LABELS: Final[dict[str, str]] = {
    "excel": "Arkusz",
    "id": "ID / płeć",
    "parents": "Rodzice",
    "chrono": "Lata / daty",
    "graph": "Graf",
    "lines": "Linie Z/M",
    "ancestors": "Przodkowie",
    "report": "Raport + CSV",
    "autofix": "Auto-poprawki",
}

# Dwa rzędy przycisków nawigacji (krótsze etykiety, szerokość kolumn wg długości tekstu).
VALIDATION_TAB_ROWS: Final[tuple[tuple[str, ...], tuple[str, ...]]] = (
    ("excel", "id", "parents", "chrono", "graph"),
    ("lines", "ancestors", "report", "autofix"),
)

_SESSION_TAB_KEY: Final[str] = "validation_tab_key"

# Zachowana nazwa eksportu dla ewentualnych odwołań zewnętrznych — ta sama kolejność co VALIDATION_TAB_KEYS.
VALIDATION_TAB_ORDER: tuple[str, ...] = VALIDATION_TAB_KEYS

# Typy problemów z eksportu CSV (`typ_problemu`) przypisane do zakładki.
_EXPORT_TYPES_BY_TAB: dict[str, FrozenSet[str]] = {
    "excel": frozenset(),
    "id": frozenset(
        {
            "Duplikat ID",
            "Pusty lub niepoprawny identyfikator",
            "Niepoprawna płeć (sex)",
            "Brak birth_year",
        }
    ),
    "parents": frozenset(
        {
            "Brak rekordu ojca w bazie",
            "Brak rekordu matki w bazie",
            "Self-parent (ojciec)",
            "Self-parent (matka)",
            "Ten sam ID jako ojciec i matka",
            "Ojciec ma płeć F w rekordzie osobnika",
            "Matka ma płeć M w rekordzie osobnika",
        }
    ),
    "chrono": frozenset(
        {
            "birth_year poza zakresem",
            "Wiek ojca przy urodzeniu potomka poza 0–80 lat",
            "Wiek matki przy urodzeniu potomka poza 0–80 lat",
            "Daty: podejrzenie śmierci przed urodzeniem",
        }
    ),
    "graph": frozenset({"Cykl w rodowodzie"}),
    "lines": frozenset(
        {
            "Niespójność father_line z linią ojca w bazie",
            "Niespójność mother_line z linią matki w bazie",
        }
    ),
    "ancestors": frozenset(),
    "report": frozenset(),  # pełny zestaw w samej zakładce
    "autofix": frozenset(),
}

# Krótki opis zakładek z tabelą problemów z CSV (bez Excel / kompletności / raportu).
_TAB_DESCRIPTIONS: dict[str, str] = {
    "id": "Numery, duplikaty, płeć zapisana w polu, brak roku urodzenia.",
    "parents": "Odwołania do rodziców, self-parent, ta sama osoba jako oba rodzice, płeć vs rola.",
    "chrono": "Lata urodzenia w zakresie, wiek rodziców przy urodzeniu potomka, kolejność dat ur./zg.",
    "graph": "Cykle w grafie rodzic–dziecko (logicznie niemożliwe).",
    "lines": "Zgodność father_line / mother_line z linią osobnika-rodzica w bazie.",
}


def _subset_csv_string(rep: ValidationReport, types: FrozenSet[str]) -> str:
    """Buduje CSV (jak pełny raport), ale tylko dla wybranych `typ_problemu`."""
    buf = StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["id", "waga", "typ_problemu", "szczegoly"])
    for r in rep.export_rows:
        if r.problem_type in types:
            w.writerow([r.record_id, r.severity, r.problem_type, r.details])
    return buf.getvalue()


def _export_rows_dataframe(rep: ValidationReport, types: FrozenSet[str]) -> pd.DataFrame:
    """Wiersze `rep.export_rows` ograniczone do podanego zbioru typów problemu."""
    rows = [
        {"id": r.record_id, "waga": r.severity, "typ_problemu": r.problem_type, "szczegóły": r.details}
        for r in rep.export_rows
        if r.problem_type in types
    ]
    return pd.DataFrame(rows)


def _issues_for_tab(issues: Sequence[ValidationIssue], tab_key: str) -> list[ValidationIssue]:
    """Filtruje komunikaty ERROR/WARN z pełnego raportu do podglądu w danej podsekcji (`tab_key`)."""
    out: list[ValidationIssue] = []
    for it in issues:
        if it.severity not in ("ERROR", "WARN"):
            continue
        title = it.title
        if tab_key == "excel":
            if any(
                x in title
                for x in (
                    "birth_year: brak",
                    "Niepoprawne wartości `sex`",
                )
            ):
                out.append(it)
        elif tab_key == "id":
            if any(
                x in title
                for x in (
                    "Duplikaty ID",
                    "Identyfikator",
                    "płeć",
                    "Płeć",
                    "birth_year: brak",
                )
            ):
                out.append(it)
        elif tab_key == "parents":
            if any(
                x in title
                for x in (
                    "Rodzice:",
                    "Brak rekordów rodziców",
                    "Self-parent",
                    "Ten sam osobnik",
                    "oba rodzice",
                    "Niespójność płci",
                )
            ):
                out.append(it)
        elif tab_key == "chrono":
            if any(
                x in title
                for x in (
                    "birth_year poza",
                    "Wiek rodziców",
                    "Daty ur.",
                    "Nielogiczna kolejność",
                )
            ):
                out.append(it)
        elif tab_key == "graph":
            if "cykl" in title.lower() or "Cykl" in title:
                out.append(it)
        elif tab_key == "lines":
            if "father_line" in title or "mother_line" in title or "linią" in title:
                out.append(it)
        elif tab_key == "ancestors":
            if any(x in title for x in ("Kompletność danych o rodzicach", "Wszystkie rekordy bez wskazania")):
                out.append(it)
    return out


def _ancestor_preview_table(df_std: pd.DataFrame, *, limit: int = 300) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Zwraca podgląd wierszy bez pełnej pary rodziców oraz liczniki (pełna para / braki).

    `limit` ogranicza liczbę wierszy w ramce podglądu (UI).
    """
    if df_std is None or df_std.empty or "id" not in df_std.columns:
        return pd.DataFrame(), {}
    cols = ["id"]
    for c in ("name", "sex", "birth_year", "father_id", "mother_id"):
        if c in df_std.columns:
            cols.append(c)
    base = df_std.loc[:, [c for c in cols if c in df_std.columns]].copy()
    base["id"] = base["id"].astype(str)
    if "father_id" in base.columns:
        has_f = base["father_id"].map(parent_field_nonempty)
    else:
        has_f = pd.Series(False, index=base.index)
    if "mother_id" in base.columns:
        has_m = base["mother_id"].map(parent_field_nonempty)
    else:
        has_m = pd.Series(False, index=base.index)
    only_f = ~has_f & has_m
    only_m = has_f & ~has_m
    neither = ~has_f & ~has_m
    both = has_f & has_m
    stats = {
        "pełna_para": int(both.sum()),
        "brak_ojca": int(only_f.sum()),
        "brak_matki": int(only_m.sum()),
        "brak_obojga": int(neither.sum()),
    }
    preview = base.loc[~both].head(limit).reset_index(drop=True)
    return preview, stats


def render_validation_tab(tab_key: str, df_std: pd.DataFrame, rep: ValidationReport | None) -> None:
    """Rysuje treść jednej podsekcji Walidacji (wg `tab_key` z `VALIDATION_TAB_KEYS`)."""
    if rep is None:
        st.warning("Brak raportu walidacji — wczytaj bazę ponownie w **Import danych**.")
        return

    types = _EXPORT_TYPES_BY_TAB.get(tab_key, frozenset())

    if tab_key == "excel":
        st.caption(
            "Kompletność pól w arkuszu (jak w imporcie): mapa % braków i tabela. "
            "To nie jest błąd logiczny drzewa, ale jakość zapisu w pliku źródłowym."
        )
        df_miss = dataframe_app_schema_columns(df_std)
        fig_miss = splt.fig_column_missing_heatmap(df_miss)
        splt.show_matplotlib_figure_in_streamlit(
            fig_miss,
            download_filename="walidacja_mapa_brakow.png",
            download_key="val_miss_heatmap_xls",
            width=splt.ST_CHART_DISPLAY_WIDTH_PX,
            export_dpi=splt.ST_DPI_MISSING_MAP,
        )
        _miss_raw = splt.column_missing_percentages(df_miss).round(2)
        _miss_ord = splt.registry_like_column_order(_miss_raw.index)
        _miss_pct = _miss_raw.reindex(_miss_ord)
        st.dataframe(_miss_pct.to_frame("% braków"), width="stretch", height=min(420, 120 + 22 * len(_miss_pct)))
        sub_issues = _issues_for_tab(rep.issues, tab_key)
        if sub_issues:
            st.markdown("**Powiązane komunikaty walidacji**")
            for it in sub_issues:
                st.markdown(f"- **{it.severity}:** {it.title}" + (f" — {it.details}" if it.details else ""))
        return

    if tab_key == "ancestors":
        st.caption(
            "Bezpośredni brak ojca / matki w rekordzie oraz podsumowanie z pełnego raportu. "
            "Uzupełnij `father_id` / `mother_id` w arkuszu, aby rozbudować drzewo."
        )
        preview, stats = _ancestor_preview_table(df_std)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pełna para rodziców", str(stats.get("pełna_para", 0)))
        c2.metric("Brak ojca (jest matka)", str(stats.get("brak_ojca", 0)))
        c3.metric("Brak matki (jest ojciec)", str(stats.get("brak_matki", 0)))
        c4.metric("Brak obojga", str(stats.get("brak_obojga", 0)))
        st.markdown(f"**Podgląd pierwszych {len(preview)} rekordów** z luką (max 300 w tabeli)")
        if preview.empty:
            st.success("Wszyscy mają wypełnioną parę rodziców — brak wierszy do podglądu.")
        else:
            st.dataframe(preview, width="stretch", height=380)
        sub_issues = _issues_for_tab(rep.issues, tab_key)
        for it in sub_issues:
            st.info(f"**{it.title}**" + (f" — {it.details}" if it.details else ""))
        return

    if tab_key == "report":
        st.caption("Pełne podsumowanie, wykres zbiorczy oraz eksport całej listy problemów do pracy w Excelu.")
        st.caption("**Wykres:** liczba wpisów ERROR/WARN oraz najczęstsze typy problemów.")
        fig_val = splt.fig_validation_findings(rep)
        splt.show_matplotlib_figure_in_streamlit(
            fig_val,
            download_filename="walidacja_podsumowanie_problemow.png",
            download_key="val_findings_bar_png",
            width=splt.ST_CHART_DISPLAY_WIDTH_PX,
            export_dpi=splt.ST_DPI_EXPORT,
        )
        st.markdown(rep.ui_summary())
        st.download_button(
            "Pobierz pełną listę problemów (CSV)",
            data=rep.to_csv_string().encode("utf-8-sig"),
            file_name="walidacja_problemy.csv",
            mime="text/csv",
            key="val_csv_dl_full",
        )
        with st.expander("Pełny raport walidacji (tekst)"):
            st.text(rep.to_text())
            st.download_button(
                "Pobierz raport (.txt)",
                data=rep.to_text(),
                file_name="walidacja_bazy.txt",
                mime="text/plain",
                key="val_txt_dl_full",
            )
        sc.help_expander("Legenda walidacji", hc.SECTION_VALIDATION, expanded=False)
        return

    # Pozostałe zakładki: tabela problemów z CSV + eksport częściowy + skrót komunikatów
    st.caption(_TAB_DESCRIPTIONS.get(tab_key, ""))

    slug_map = {
        "id": "id",
        "parents": "rodzice",
        "chrono": "chrono",
        "graph": "graf",
        "lines": "linie",
    }
    slug = slug_map.get(tab_key, "inne")

    df_rows = _export_rows_dataframe(rep, types)
    st.metric("Liczba wpisów w tej kategorii", str(len(df_rows)))
    if df_rows.empty:
        st.success("Brak wykrytych problemów w tej kategorii (wg typów przypisanych do zakładki).")
    else:
        st.dataframe(df_rows, width="stretch", height=min(460, 80 + 28 * min(len(df_rows), 14)))
        csv_part = _subset_csv_string(rep, types)
        st.download_button(
            f"Pobierz problemy tej zakładki (CSV, {len(df_rows)} wierszy)",
            data=csv_part.encode("utf-8-sig"),
            file_name=f"walidacja_{slug}.csv",
            mime="text/csv",
            key=f"val_csv_tab_{slug}",
        )

    sub_issues = _issues_for_tab(rep.issues, tab_key)
    if sub_issues:
        with st.expander("Powiązane podsumowania z raportu", expanded=False):
            for it in sub_issues:
                st.markdown(f"- **{it.severity}:** {it.title}" + (f" — {it.details}" if it.details else ""))


def render_automatic_corrections_panel(df_std: pd.DataFrame) -> None:
    """
    Panel reguł auto-poprawek, podglądu logu, zastosowania zmian w sesji oraz przywrócenia kopii importu.

    Wymaga wcześniejszego wywołania `set_dataset` z domyślnym zapisem migawki importu.
    """
    from app.config import get_config
    from app.data.auto_fix import AutoFixOptions, apply_auto_fixes, default_year_max

    st.markdown("#### Reguły i log")
    st.caption(
        "Zmiany tylko w tej sesji (nie zapisują się do pliku źródłowego). "
        "Przywrócenie kopii z ostatniego importu — przycisk na dole panelu."
    )

    cfg = get_config()
    y_min = int(getattr(cfg, "validation_min_year", 1800))
    y_max = default_year_max(cfg)
    p_min = int(getattr(cfg, "auto_fix_parent_min_age_at_birth", 12))
    p_max = int(getattr(cfg, "auto_fix_parent_max_age_at_birth", 80))

    with st.expander("Opcje i uruchomienie automatycznych poprawek", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            o_dedupe = st.checkbox(
                "Usuń duplikaty numeru osobnika (zostaje pierwszy wiersz)",
                value=True,
                key="auto_fix_dedupe",
            )
            o_drop_empty = st.checkbox(
                "Usuń wiersze bez numeru osobnika (ostrożnie — bezpowrotnie)",
                value=False,
                key="auto_fix_drop_empty_id",
            )
            o_clear_by = st.checkbox(
                f"Wyczyść rok urodzenia poza zakresem ({y_min}–{y_max})",
                value=True,
                key="auto_fix_clear_by",
            )
            o_clear_death = st.checkbox(
                "Wyczyść pole śmierci przy sprzeczności ze śmiercią przed ur. (tekst dat)",
                value=True,
                key="auto_fix_clear_death",
            )
            o_self = st.checkbox(
                "Usuń pętle: osobnik wskazany jako własny ojciec lub własna matka",
                value=True,
                key="auto_fix_self",
            )
        with c2:
            o_miss = st.checkbox(
                "Odetnij odniesienie do nieistniejącego rekordu rodzica",
                value=True,
                key="auto_fix_miss",
            )
            o_sex = st.checkbox(
                "Odetnij rodzica przy kolizji płci biologicznej",
                value=True,
                key="auto_fix_sex",
            )
            o_young = st.checkbox(
                f"Odetnij zbyt młodego rodzica (różnica lat < {p_min} wg konfiguracji)",
                value=True,
                key="auto_fix_young",
            )
            o_old = st.checkbox(
                f"Odetnij „zbyt starego” rodzica (różnica lat > {p_max}; niska pewność)",
                value=False,
                key="auto_fix_old",
            )

        opts = AutoFixOptions(
            dedupe_ids=o_dedupe,
            drop_rows_without_id=o_drop_empty,
            clear_birth_year_out_of_range=o_clear_by,
            clear_death_date_on_conflict=o_clear_death,
            remove_self_parent=o_self,
            cut_missing_parent_record=o_miss,
            cut_parent_sex_collision=o_sex,
            cut_parent_too_young=o_young,
            cut_parent_too_old=o_old,
        )

        b1, b2, b3 = st.columns(3)
        with b1:
            preview = st.button("Podgląd logu poprawek (bez zapisu)", key="auto_fix_preview")
        with b2:
            apply_btn = st.button("Zastosuj poprawki i przelicz analizę", type="primary", key="auto_fix_apply")
        with b3:
            restore_btn = st.button("Przywróć surowy zbiór z importu", key="auto_fix_restore")

        if preview:
            _, log_lines = apply_auto_fixes(
                df_std,
                opts,
                year_min=y_min,
                year_max=y_max,
                parent_min_age_at_birth=p_min,
                parent_max_age_at_birth=p_max,
            )
            st.session_state["auto_fix_last_log"] = "\n".join(log_lines)

        if apply_btn:
            new_df, log_lines = apply_auto_fixes(
                df_std,
                opts,
                year_min=y_min,
                year_max=y_max,
                parent_min_age_at_birth=p_min,
                parent_max_age_at_birth=p_max,
            )
            st.session_state["auto_fix_last_log"] = "\n".join(log_lines)
            src = str(st.session_state.get("source", "Baza"))
            sc.set_dataset(new_df, src, update_import_snapshot=False)
            st.success(f"Zastosowano poprawki. Wierszy w bazie: **{len(new_df)}**. Przeliczono walidację i graf.")
            st.rerun()

        if restore_btn:
            snap = st.session_state.get("df_std_import_snapshot")
            if snap is None or getattr(snap, "empty", True):
                st.error("Brak zapisanej kopii z importu — wczytaj plik ponownie w sekcji Import.")
            else:
                src = str(st.session_state.get("source", "Import"))
                sc.set_dataset(snap.copy(), src, update_import_snapshot=False)
                st.success("Przywrócono dane sprzed automatycznych poprawek (ostatni import).")
                st.rerun()

        log_txt = st.session_state.get("auto_fix_last_log")
        if log_txt:
            st.markdown("**Log (ostatni podgląd lub zastosowanie)**")
            st.code(log_txt)


def _column_weights(keys: tuple[str, ...]) -> list[int]:
    """Wagi kolumn `st.columns` proporcjonalne do długości etykiety (szerszy przycisk dla dłuższego tekstu)."""
    return [max(6, len(VALIDATION_TAB_LABELS[k])) for k in keys]


def render_validation_workspace(df_std: pd.DataFrame, rep: ValidationReport | None) -> None:
    """
    Dwa rzędy przycisków podsekcji, potem treść wybranej pozycji (w tym **Auto-poprawki**).
    """
    if _SESSION_TAB_KEY not in st.session_state:
        st.session_state[_SESSION_TAB_KEY] = VALIDATION_TAB_KEYS[0]

    st.caption("Wybierz podsekcję — pierwszy rząd: arkusz i jakość rekordu; drugi: linie, przodkowie, raport, auto-poprawki.")

    for row_keys in VALIDATION_TAB_ROWS:
        cols = st.columns(_column_weights(row_keys))
        for col, key in zip(cols, row_keys, strict=True):
            with col:
                current = st.session_state[_SESSION_TAB_KEY]
                if st.button(
                    VALIDATION_TAB_LABELS[key],
                    key=f"val_nav_btn_{key}",
                    use_container_width=True,
                    type="primary" if current == key else "secondary",
                ):
                    st.session_state[_SESSION_TAB_KEY] = key

    selected = st.session_state[_SESSION_TAB_KEY]
    st.markdown("---")

    if selected == "autofix":
        render_automatic_corrections_panel(df_std)
    else:
        render_validation_tab(selected, df_std, rep)
