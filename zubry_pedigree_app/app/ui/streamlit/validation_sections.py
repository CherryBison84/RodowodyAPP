"""
Podsekcje Walidacji: nawigacja (kompaktowa lub panel boczny z grupami) i treść kategorii.

Wywoływane z kroku HUBA „Walidacja” oraz ze strony analityki (`pages.section_validation`).
"""

from __future__ import annotations

import csv
import html
from io import StringIO
from typing import Final, FrozenSet, Literal, Sequence

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

# Pełne tytuły sekcji (nagłówek nad treścią zakładki).
VALIDATION_TAB_HEADINGS: Final[dict[str, str]] = {
    "excel": "Kompletność pól w arkuszu",
    "id": "Identyfikatory, płeć i rok urodzenia",
    "parents": "Powiązania rodzic–dziecko",
    "chrono": "Lata urodzenia i daty",
    "graph": "Cykle w grafie rodowodu",
    "lines": "Linie założycielskie (Z / M)",
    "ancestors": "Braki wskazania rodziców",
    "report": "Pełny raport i eksport",
    "autofix": "Automatyczne poprawki",
}

# Układ grupowy nawigacji (krok Walidacja HUBA i czytelny tryb „grouped”).
VALIDATION_NAV_GROUPS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("Jakość danych w pliku", ("excel", "id", "chrono")),
    ("Rodowód i spójność", ("parents", "ancestors", "graph", "lines")),
    ("Podsumowanie", ("report",)),
)

_GRAPH_CYCLE_HELP: Final[str] = (
    "Program buduje **skierowany graf**: krawędź od dziecka do ojca i od dziecka do matki "
    "(gdy wskazany numer ma rekord w bazie). **Cykl** to zamknięta pętla — w rodowodzie biologicznym "
    "jest to niemożliwe. Typowe przyczyny: literówka lub duplikat ID, zamiana kolumn ojciec/matka, "
    "błędny merge arkuszy. W CSV: ERROR „Cykl w rodowodzie”, wiersz z `id` = **`_GLOBAL_`** "
    "oraz przykładowe węzły na cyklu."
)

# Dwa rzędy przycisków nawigacji (krótsze etykiety, szerokość kolumn wg długości tekstu).
VALIDATION_TAB_ROWS: Final[tuple[tuple[str, ...], tuple[str, ...]]] = (
    ("excel", "id", "parents", "chrono", "graph"),
    ("lines", "ancestors", "report", "autofix"),
)

_SESSION_TAB_KEY: Final[str] = "validation_tab_key"
_SESSION_ONLY_ISSUES: Final[str] = "validation_nav_only_issues"

# Skróty etykiet w podmenu (pełny tytuł — w nagłówku treści).
VALIDATION_TAB_MENU_LABELS: Final[dict[str, str]] = {
    "excel": "Arkusz i braki pól",
    "id": "ID, płeć, rok",
    "parents": "Rodzice w bazie",
    "chrono": "Lata i daty",
    "graph": "Cykle w grafie",
    "lines": "Linie Z / M",
    "ancestors": "Braki rodziców",
    "report": "Raport i eksport CSV",
    "autofix": "Auto-poprawki",
}

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

# Krótki lead pod nagłówkiem sekcji (1–2 zdania).
_TAB_LEADS: Final[dict[str, str]] = {
    "excel": (
        "Mapa pokazuje, jak często brakuje wartości w kolumnach modelu aplikacji. "
        "To jakość zapisu w pliku — niekoniecznie błąd logiczny drzewa."
    ),
    "id": "Numery osobników muszą być unikalne; płeć to M lub F; rok urodzenia ułatwia kontrolę wieku rodziców.",
    "parents": (
        "Sprawdzenie, czy wskazani rodzice istnieją w bazie, czy nie ma self-parent "
        "ani tej samej osoby jako ojca i matki, oraz zgodności płci z rolą."
    ),
    "chrono": "Rok urodzenia w dopuszczalnym zakresie, rozsądny wiek rodziców przy urodzeniu potomka, kolejność dat.",
    "graph": "Wykrywanie zamkniętych pętli w grafie dziecko → rodzic (patrz pomoc poniżej, jeśli coś jest niejasne).",
    "lines": "Porównanie kolumn `father_line` / `mother_line` z linią zapisaną przy rekordzie rodzica w bazie.",
    "ancestors": (
        "Rekordy bez pełnej pary `father_id` i `mother_id` — podgląd ułatwia uzupełnienie braków w arkuszu."
    ),
    "report": "Zbiorczy wykres, skrót komunikatów oraz pliki CSV/TXT do poprawy danych w Excelu.",
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


def _display_issues_dataframe(df_rows: pd.DataFrame) -> None:
    """Tabela problemów z czytelnymi nagłówkami i sortowaniem (ERROR przed WARN)."""
    if df_rows.empty:
        return
    display = df_rows.rename(
        columns={
            "id": "Numer osobnika",
            "waga": "Waga",
            "typ_problemu": "Typ problemu",
            "szczegóły": "Szczegóły",
        }
    )
    if "Waga" in display.columns:
        order = {"ERROR": 0, "WARN": 1}
        display = display.assign(
            _sort=display["Waga"].map(lambda s: order.get(str(s), 9))
        ).sort_values("_sort", kind="stable").drop(columns="_sort")
    height = min(520, 96 + 32 * min(len(display), 16))
    st.dataframe(
        display,
        width="stretch",
        height=height,
        hide_index=True,
        column_config={
            "Numer osobnika": st.column_config.TextColumn(width="small"),
            "Waga": st.column_config.TextColumn(width="small"),
            "Typ problemu": st.column_config.TextColumn(width="medium"),
            "Szczegóły": st.column_config.TextColumn(width="large"),
        },
    )


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


def _tab_accent(tab_key: str) -> str:
    accents = {
        "excel": sc.THEME.COMPLETENESS_ACCENT,
        "id": sc.THEME.EDGE_PLOT,
        "parents": sc.THEME.LINK,
        "chrono": sc.THEME.ACCENT,
        "graph": "#6b4a5a",
        "lines": sc.THEME.EDGE_PLOT,
        "ancestors": sc.THEME.LINK,
        "report": sc.THEME.EDGE_PLOT,
        "autofix": sc.THEME.ACCENT,
    }
    return accents.get(tab_key, sc.THEME.EDGE_PLOT)


def _render_tab_heading(tab_key: str) -> None:
    title = VALIDATION_TAB_HEADINGS.get(tab_key, VALIDATION_TAB_LABELS.get(tab_key, tab_key))
    lead = _TAB_LEADS.get(tab_key, "")
    sc.population_dashboard_group_header(
        title,
        lead,
        accent=_tab_accent(tab_key),
        background=sc.THEME.PANEL_BG2 if tab_key in {"excel", "report"} else sc.THEME.ENTRY_BG,
    )


def _render_issue_list(issues: Sequence[ValidationIssue], *, empty_ok: bool = False) -> None:
    """Lista komunikatów ERROR/WARN w czytelnym układzie (badge + tytuł + szczegóły)."""
    problems = [i for i in issues if i.severity in ("ERROR", "WARN")]
    if not problems:
        if empty_ok:
            st.success("Brak komunikatów ERROR/WARN w tej kategorii.")
        return
    th = sc.THEME
    severity_rank = {"ERROR": 0, "WARN": 1}
    problems.sort(key=lambda i: (severity_rank.get(i.severity, 9), i.title))
    for it in problems:
        if it.severity == "ERROR":
            badge_bg, badge_fg, card_bg = "#8b2e2e", "#ffffff", "#fdeaea"
        else:
            badge_bg, badge_fg, card_bg = "#7a5c1e", "#ffffff", "#faf3e0"
        title = html.escape(it.title)
        details = html.escape(it.details) if it.details else ""
        detail_html = (
            f'<p style="margin:8px 0 0 0;font-size:0.92rem;line-height:1.45;color:{th.TEXT};">{details}</p>'
            if details
            else ""
        )
        st.markdown(
            f'<div style="margin:0 0 12px 0;padding:14px 16px;border-radius:10px;'
            f"background:{card_bg};border:1px solid {th.BORDER_SUBTLE};"
            f'border-left:5px solid {badge_bg};">'
            f'<div style="display:flex;align-items:flex-start;gap:10px;flex-wrap:wrap;">'
            f'<span style="flex-shrink:0;font-size:0.75rem;font-weight:700;letter-spacing:0.05em;'
            f"padding:3px 10px;border-radius:5px;background:{badge_bg};color:{badge_fg};"
            f'">{html.escape(it.severity)}</span>'
            f'<span style="flex:1;min-width:12rem;font-weight:600;font-size:0.98rem;'
            f'line-height:1.35;color:{th.TEXT};">{title}</span></div>'
            f"{detail_html}</div>",
            unsafe_allow_html=True,
        )


def _count_tab_issues(rep: ValidationReport, tab_key: str) -> tuple[int, int]:
    """Liczba ERROR i WARN w danej kategorii (eksport CSV lub komunikaty zbiorcze)."""
    types = _EXPORT_TYPES_BY_TAB.get(tab_key, frozenset())
    if types:
        n_err = n_warn = 0
        for row in rep.export_rows:
            if row.problem_type not in types:
                continue
            if row.severity == "ERROR":
                n_err += 1
            elif row.severity == "WARN":
                n_warn += 1
        return n_err, n_warn
    issues = _issues_for_tab(rep.issues, tab_key)
    n_err = sum(1 for i in issues if i.severity == "ERROR")
    n_warn = sum(1 for i in issues if i.severity == "WARN")
    return n_err, n_warn


def _issue_count_suffix(err: int, warn: int) -> str:
    if err:
        part = f"{err} bł."
        if warn:
            return f" · {part}, {warn} ostrz."
        return f" · {part}"
    if warn:
        return f" · {warn} ostrz."
    return " · OK"


def _tab_has_issues(rep: ValidationReport | None, tab_key: str) -> bool:
    if rep is None:
        return False
    err, warn = _count_tab_issues(rep, tab_key)
    return bool(err or warn)


def _category_card_caption(tab_key: str, rep: ValidationReport | None) -> str:
    if rep is None:
        return ""
    err, warn = _count_tab_issues(rep, tab_key)
    if err or warn:
        return _issue_count_suffix(err, warn).strip(" ·")
    return "brak problemów"


def _validation_nav_groups(*, show_autofix: bool) -> tuple[tuple[str, tuple[str, ...]], ...]:
    groups = VALIDATION_NAV_GROUPS
    if show_autofix:
        return groups + (("Narzędzia", ("autofix",)),)
    return groups


def _render_validation_overview_table(rep: ValidationReport | None, keys: Sequence[str]) -> None:
    """Tabela podglądu: wszystkie kategorie i liczba problemów."""
    rows = []
    for key in keys:
        title = VALIDATION_TAB_MENU_LABELS.get(key, VALIDATION_TAB_LABELS.get(key, key))
        if rep is None:
            rows.append({"Kategoria": title, "Błędy": "—", "Ostrzeżenia": "—", "Status": "—"})
            continue
        err, warn = _count_tab_issues(rep, key)
        status = "Do poprawy" if err else ("Do weryfikacji" if warn else "OK")
        rows.append(
            {
                "Kategoria": title,
                "Błędy": err,
                "Ostrzeżenia": warn,
                "Status": status,
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=min(320, 48 + 36 * len(rows)))


def _render_category_card_grid(
    group_keys: tuple[str, ...],
    rep: ValidationReport | None,
    *,
    current_tab: str,
    only_issues: bool,
) -> list[str]:
    """Siatka kart wyboru kategorii; zwraca listę widocznych kluczy."""
    visible = [k for k in group_keys if not only_issues or _tab_has_issues(rep, k)]
    if not visible:
        st.caption("W tej grupie nie ma kategorii z wykrytymi problemami.")
        return []

    th = sc.THEME
    n_cols = 2 if len(visible) > 1 else 1
    cols = st.columns(n_cols)
    for i, key in enumerate(visible):
        err, warn = _count_tab_issues(rep, key) if rep else (0, 0)
        if err:
            accent, bg = "#8b2e2e", "#fdeaea"
        elif warn:
            accent, bg = "#7a5c1e", "#faf3e0"
        else:
            accent, bg = th.EDGE_PLOT, th.ENTRY_BG
        title = VALIDATION_TAB_MENU_LABELS.get(key, VALIDATION_TAB_LABELS.get(key, key))
        caption = _category_card_caption(key, rep)
        with cols[i % n_cols]:
            st.markdown(
                f'<div style="margin:0 0 6px 0;padding:10px 12px;border-radius:8px;'
                f'background:{bg};border:1px solid {th.BORDER_SUBTLE};border-left:4px solid {accent};">'
                f'<div style="font-weight:600;font-size:0.92rem;color:{th.TEXT};">'
                f"{html.escape(title)}</div>"
                f'<div style="font-size:0.8rem;color:{th.MUTED};margin-top:4px;">'
                f"{html.escape(caption)}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button(
                "Otwórz" if key != current_tab else "Wybrano",
                key=f"val_pick_{key}",
                use_container_width=True,
                type="primary" if key == current_tab else "secondary",
            ):
                st.session_state[_SESSION_TAB_KEY] = key
                st.rerun()
    return visible


def _render_grouped_category_picker(
    rep: ValidationReport | None,
    *,
    show_autofix: bool,
    all_keys: list[str],
) -> None:
    """Zakładki grup + siatka kart kategorii (nawigacja pozioma, treść poniżej)."""
    groups = _validation_nav_groups(show_autofix=show_autofix)
    current_tab = str(st.session_state.get(_SESSION_TAB_KEY, all_keys[0]))
    if current_tab not in all_keys:
        current_tab = all_keys[0]
        st.session_state[_SESSION_TAB_KEY] = current_tab

    if _SESSION_ONLY_ISSUES not in st.session_state:
        st.session_state[_SESSION_ONLY_ISSUES] = False

    head_l, head_r = st.columns([2.2, 1])
    with head_l:
        st.caption("Wybierz kartę kategorii — szczegóły pojawią się pod spodem.")
    with head_r:
        only_issues = st.checkbox(
            "Tylko z problemami",
            value=bool(st.session_state[_SESSION_ONLY_ISSUES]),
            key="val_only_issues_cb",
        )
        st.session_state[_SESSION_ONLY_ISSUES] = only_issues

    if rep is not None:
        total_err = total_warn = 0
        for key in all_keys:
            e, w = _count_tab_issues(rep, key)
            total_err += e
            total_warn += w
        m1, m2, m3 = st.columns(3)
        th = sc.THEME
        with m1:
            sc.population_dashboard_metric(
                "Kategorie z błędami",
                str(sum(1 for k in all_keys if _count_tab_issues(rep, k)[0] > 0)),
                accent="#8b2e2e",
                panel_bg="#fdeaea" if total_err else th.ENTRY_BG,
            )
        with m2:
            sc.population_dashboard_metric(
                "Wpisy ERROR (łącznie)",
                str(total_err),
                accent="#8b2e2e",
                panel_bg="#fdeaea" if total_err else th.ENTRY_BG,
            )
        with m3:
            sc.population_dashboard_metric(
                "Wpisy WARN (łącznie)",
                str(total_warn),
                accent="#7a5c1e",
                panel_bg="#faf3e0" if total_warn else th.ENTRY_BG,
            )

    with st.expander("Mapa wszystkich kategorii", expanded=False):
        _render_validation_overview_table(rep, all_keys)

    group_labels = [g[0] for g in groups]
    group_tabs = st.tabs(group_labels)
    for gtab, (_gtitle, gkeys) in zip(group_tabs, groups, strict=True):
        with gtab:
            visible = _render_category_card_grid(
                gkeys,
                rep,
                current_tab=current_tab,
                only_issues=only_issues,
            )
            if current_tab in gkeys and current_tab not in visible and visible:
                st.info(
                    f"Aktywna kategoria **{VALIDATION_TAB_MENU_LABELS.get(current_tab, current_tab)}** "
                    f"jest ukryta przez filtr — wyłącz „Tylko z problemami” lub wybierz inną kartę."
                )


def _nav_button_label(tab_key: str, *, nav_label_style: Literal["short", "full"]) -> str:
    if nav_label_style == "full":
        return VALIDATION_TAB_HEADINGS.get(tab_key, VALIDATION_TAB_LABELS.get(tab_key, tab_key))
    return VALIDATION_TAB_LABELS.get(tab_key, tab_key)


def _render_nav_buttons(
    row_keys: tuple[str, ...],
    *,
    key_prefix: str,
    nav_label_style: Literal["short", "full"] = "short",
) -> None:
    cols = st.columns(_column_weights(row_keys, nav_label_style=nav_label_style))
    for col, key in zip(cols, row_keys, strict=True):
        with col:
            current = st.session_state[_SESSION_TAB_KEY]
            if st.button(
                _nav_button_label(key, nav_label_style=nav_label_style),
                key=f"{key_prefix}_{key}",
                use_container_width=True,
                type="primary" if current == key else "secondary",
            ):
                st.session_state[_SESSION_TAB_KEY] = key


def _render_active_category_header(tab_key: str) -> None:
    """Wyraźny nagłówek aktualnie wybranej kategorii (pod nawigacją)."""
    title = VALIDATION_TAB_HEADINGS.get(tab_key, VALIDATION_TAB_LABELS.get(tab_key, tab_key))
    lead = _TAB_LEADS.get(tab_key, "")
    sc.population_dashboard_group_header(
        title,
        lead,
        accent=_tab_accent(tab_key),
        background=sc.THEME.PANEL_BG2 if tab_key in {"excel", "report"} else sc.THEME.ENTRY_BG,
    )


def render_validation_tab(
    tab_key: str,
    df_std: pd.DataFrame,
    rep: ValidationReport | None,
    *,
    missing_data_hint: str = "Brak raportu walidacji — wczytaj bazę ponownie w **Import danych**.",
    show_tab_heading: bool = True,
) -> None:
    """Rysuje treść jednej podsekcji Walidacji (wg `tab_key` z `VALIDATION_TAB_KEYS`)."""
    if rep is None:
        st.warning(missing_data_hint)
        return

    types = _EXPORT_TYPES_BY_TAB.get(tab_key, frozenset())
    if show_tab_heading:
        _render_tab_heading(tab_key)

    if tab_key == "excel":
        st.markdown("**Mapa braków w kolumnach**")
        df_miss = dataframe_app_schema_columns(df_std)
        fig_miss = splt.fig_column_missing_heatmap(df_miss)
        splt.show_matplotlib_figure_in_streamlit(
            fig_miss,
            download_filename="walidacja_mapa_brakow.png",
            download_key="val_miss_heatmap_xls",
            width="stretch",
            export_dpi=splt.ST_DPI_MISSING_MAP,
            save_pad_inches=0.24,
        )
        sub_issues = _issues_for_tab(rep.issues, tab_key)
        if sub_issues:
            st.markdown("##### Powiązane komunikaty")
            _render_issue_list(sub_issues)
        return

    if tab_key == "ancestors":
        preview, stats = _ancestor_preview_table(df_std)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pełna para rodziców", str(stats.get("pełna_para", 0)))
        c2.metric("Brak ojca (jest matka)", str(stats.get("brak_ojca", 0)))
        c3.metric("Brak matki (jest ojciec)", str(stats.get("brak_matki", 0)))
        c4.metric("Brak obojga", str(stats.get("brak_obojga", 0)))
        st.markdown("##### Rekordy z luką w rodzicach (podgląd)")
        st.caption(f"Pokazano do {len(preview)} wierszy (limit 300 w tabeli).")
        if preview.empty:
            st.success("Wszyscy mają wypełnioną parę rodziców — brak wierszy do podglądu.")
        else:
            st.dataframe(preview, width="stretch", height=380)
        sub_issues = _issues_for_tab(rep.issues, tab_key)
        if sub_issues:
            st.markdown("##### Podsumowania z raportu")
            _render_issue_list(sub_issues)
        return

    if tab_key == "report":
        st.markdown("##### Wykres zbiorczy")
        st.caption("Liczba wpisów ERROR/WARN oraz najczęstsze typy problemów.")
        fig_val = splt.fig_validation_findings(rep)
        splt.show_matplotlib_figure_in_streamlit(
            fig_val,
            download_filename="walidacja_podsumowanie_problemow.png",
            download_key="val_findings_bar_png",
            width=splt.ST_CHART_DISPLAY_WIDTH_PX,
            export_dpi=splt.ST_DPI_EXPORT,
        )
        st.markdown("##### Skrót komunikatów")
        st.markdown(rep.ui_summary())
        st.markdown("##### Eksport do Excela")
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "Pobierz listę problemów (CSV)",
                data=rep.to_csv_string().encode("utf-8-sig"),
                file_name="walidacja_problemy.csv",
                mime="text/csv",
                key="val_csv_dl_full",
                width="stretch",
            )
        with d2:
            with st.expander("Raport tekstowy (.txt)"):
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

    if tab_key == "graph":
        sc.help_expander("Co oznacza cykl w rodowodzie?", _GRAPH_CYCLE_HELP, expanded=False)

    slug_map = {
        "id": "id",
        "parents": "rodzice",
        "chrono": "chrono",
        "graph": "graf",
        "lines": "linie",
    }
    slug = slug_map.get(tab_key, "inne")

    df_rows = _export_rows_dataframe(rep, types)
    st.markdown("##### Tabela problemów")
    sc.population_dashboard_metric(
        "Wpisy w tej kategorii",
        str(len(df_rows)),
        accent=_tab_accent(tab_key),
        panel_bg=sc.THEME.ENTRY_BG,
        help_text="Liczba wierszy w eksporcie CSV przypisanych do tej sekcji.",
    )
    if df_rows.empty:
        st.success("Brak wykrytych problemów w tej kategorii.")
    else:
        _display_issues_dataframe(df_rows)
        csv_part = _subset_csv_string(rep, types)
        st.download_button(
            f"Pobierz CSV tej sekcji ({len(df_rows)} wierszy)",
            data=csv_part.encode("utf-8-sig"),
            file_name=f"walidacja_{slug}.csv",
            mime="text/csv",
            key=f"val_csv_tab_{slug}",
        )

    sub_issues = _issues_for_tab(rep.issues, tab_key)
    if sub_issues:
        st.markdown("##### Podsumowania z raportu")
        _render_issue_list(sub_issues)


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


def _column_weights(
    keys: tuple[str, ...],
    *,
    nav_label_style: Literal["short", "full"] = "short",
) -> list[int]:
    """Wagi kolumn `st.columns` proporcjonalne do długości etykiety (szerszy przycisk dla dłuższego tekstu)."""
    return [
        max(8, len(_nav_button_label(k, nav_label_style=nav_label_style)) // 4 + 6)
        for k in keys
    ]


def _tab_rows_for_workspace(*, show_autofix: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if show_autofix:
        return VALIDATION_TAB_ROWS
    row0 = tuple(k for k in VALIDATION_TAB_ROWS[0])
    row1 = tuple(k for k in VALIDATION_TAB_ROWS[1] if k != "autofix")
    return row0, row1


def _all_tab_keys(*, show_autofix: bool, layout: Literal["compact", "grouped"]) -> list[str]:
    if layout == "grouped":
        keys: list[str] = []
        for _title, group_keys in VALIDATION_NAV_GROUPS:
            keys.extend(group_keys)
        if show_autofix:
            keys.append("autofix")
        return keys
    tab_rows = _tab_rows_for_workspace(show_autofix=show_autofix)
    return [k for row in tab_rows for k in row]


def _render_validation_nav(
    *,
    show_autofix: bool,
    layout: Literal["compact", "grouped"],
    nav_label_style: Literal["short", "full"],
) -> None:
    if layout == "grouped":
        return

    st.caption(
        "Wybierz kategorię — pierwszy rząd: arkusz i rekord; drugi: linie, przodkowie, raport"
        + (", auto-poprawki." if show_autofix else ".")
    )
    for ri, row_keys in enumerate(_tab_rows_for_workspace(show_autofix=show_autofix)):
        _render_nav_buttons(
            row_keys,
            key_prefix=f"val_row{ri}",
            nav_label_style=nav_label_style,
        )


def render_validation_workspace(
    df_std: pd.DataFrame,
    rep: ValidationReport | None,
    *,
    show_autofix: bool = True,
    layout: Literal["compact", "grouped"] = "compact",
    missing_data_hint: str = "Brak raportu walidacji — wczytaj bazę ponownie w **Import danych**.",
) -> None:
    """
    Nawigacja podsekcji i treść wybranej kategorii (opcjonalnie **Auto-poprawki**).
    """
    nav_label_style: Literal["short", "full"] = "short"
    show_tab_heading = layout != "grouped"

    all_keys = _all_tab_keys(show_autofix=show_autofix, layout=layout)
    if _SESSION_TAB_KEY not in st.session_state or st.session_state[_SESSION_TAB_KEY] not in all_keys:
        st.session_state[_SESSION_TAB_KEY] = all_keys[0]

    def _render_body(selected: str) -> None:
        if selected == "autofix":
            render_automatic_corrections_panel(df_std)
            return
        if not show_tab_heading:
            _render_active_category_header(selected)
        render_validation_tab(
            selected,
            df_std,
            rep,
            missing_data_hint=missing_data_hint,
            show_tab_heading=show_tab_heading,
        )

    if layout == "grouped":
        st.markdown("#### Szczegóły walidacji")
        _render_grouped_category_picker(
            rep,
            show_autofix=show_autofix,
            all_keys=all_keys,
        )
        st.markdown("---")
        selected = str(st.session_state[_SESSION_TAB_KEY])
        _render_body(selected)
        return

    _render_validation_nav(
        show_autofix=show_autofix,
        layout=layout,
        nav_label_style=nav_label_style,
    )
    selected = str(st.session_state[_SESSION_TAB_KEY])
    st.markdown("---")
    _render_body(selected)
