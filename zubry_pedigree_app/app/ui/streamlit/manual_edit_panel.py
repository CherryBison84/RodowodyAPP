"""Panel ręcznej edycji pól — Krok 4 HUBA (Czyszczenie ręczne)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Final

import pandas as pd
import streamlit as st

from app.data.manual_edit import (
    FieldPatch,
    apply_record_patches,
    editable_columns,
    find_row_indices,
    normalize_field_value,
    parse_cycle_nodes_from_details,
    suggest_fields_for_problem,
    validate_patch,
)
from app.data.validator import ValidationReport, id_cell_string
from app.ui.streamlit import common as sc

from app.ui.streamlit.huba_nav import NAV_STEP4

_SESSION_UNDO: Final[str] = "huba_edit_undo"
_SESSION_LOG: Final[str] = "huba_edit_log"
_SESSION_PICK_ID: Final[str] = "huba_manual_pick_id"
_SESSION_PICK_PROBLEM: Final[str] = "huba_manual_pick_problem"
_SESSION_PICK_ROW: Final[str] = "huba_manual_pick_row"

_MANUAL_ACCENT: Final[str] = "#3d5a4a"

_FIELD_LABELS: Final[dict[str, str]] = {
    "id": "ID osobnika",
    "name": "Nazwa",
    "alt_name": "Nazwa alternatywna",
    "sex": "Płeć",
    "line": "Linia",
    "birth_year": "Rok urodzenia",
    "status": "Status",
    "father_id": "ID ojca",
    "father_name": "Nazwa ojca",
    "father_line": "Linia ojca (Z)",
    "mother_id": "ID matki",
    "mother_name": "Nazwa matki",
    "mother_line": "Linia matki (M)",
    "birth_date": "Data urodzenia",
    "death_date": "Data śmierci",
    "birth_location": "Miejsce urodzenia",
}


def open_manual_corrections_panel() -> None:
    """Przechodzi do **Kroku 4 — Czyszczenie ręczne** (np. z tabeli problemów w Kroku 2)."""
    st.session_state["huba_nav"] = NAV_STEP4


def _cell_display(v: object) -> str:
    """Normalizuje wartość komórki do tekstu formularza."""
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


def _push_undo(catalog_name: str, df: pd.DataFrame) -> None:
    """Zapamiętuje migawkę ramki przed ręczną edycją."""
    undo: dict[str, pd.DataFrame] = st.session_state.setdefault(_SESSION_UNDO, {})
    undo[catalog_name] = df.copy(deep=True)


def _pop_undo(catalog_name: str) -> pd.DataFrame | None:
    """Zwraca i usuwa ostatnią migawkę undo dla wskazanej bazy."""
    undo: dict[str, pd.DataFrame] = st.session_state.get(_SESSION_UNDO, {})
    snap = undo.pop(catalog_name, None)
    st.session_state[_SESSION_UNDO] = undo
    return snap


def _append_log(message: str) -> None:
    """Dodaje wpis do krótkiego dziennika ręcznych edycji w sesji."""
    log: list[str] = st.session_state.setdefault(_SESSION_LOG, [])
    log.insert(0, message)
    st.session_state[_SESSION_LOG] = log[:12]


def _known_ids(df: pd.DataFrame) -> list[str]:
    """Zwraca posortowane, niepuste identyfikatory rekordów z ramki."""
    if "id" not in df.columns:
        return []
    ids = [id_cell_string(x) for x in df["id"]]
    return sorted({x for x in ids if x}, key=lambda s: (len(s), s))


def _problem_picker_options(rep: ValidationReport) -> tuple[list[str], list[tuple[str, str]]]:
    """Etykiety listy i pary (record_id, problem_type) z eksportu walidacji."""
    options: list[str] = []
    meta: list[tuple[str, str]] = []
    for row in rep.export_rows:
        rid = str(row.record_id).strip()
        ptype = str(row.problem_type).strip()
        if rid == "_GLOBAL_" and ptype == "Cykl w rodowodzie":
            nodes = parse_cycle_nodes_from_details(row.details)
            if nodes:
                for nid in nodes[:12]:
                    options.append(f"{nid} | {ptype} (węzeł cyklu)")
                    meta.append((nid, ptype))
                continue
        if not rid or rid == "_GLOBAL_":
            continue
        sev = row.severity
        options.append(f"{rid} | {ptype} ({sev})")
        meta.append((rid, ptype))
    return options, meta


def _render_report_problem_picker(rep: ValidationReport) -> None:
    """Renderuje wybór rekordu na podstawie eksportu problemów walidacji."""
    options, meta = _problem_picker_options(rep)
    if not options:
        st.caption("Brak pojedynczych wpisów w raporcie — użyj wyszukiwania po ID poniżej.")
        return

    prev = st.session_state.get(_SESSION_PICK_ID)
    default_idx = 0
    for i, (rid, _) in enumerate(meta):
        if rid == prev:
            default_idx = i
            break

    choice = st.selectbox(
        "Wpis z raportu walidacji",
        options,
        index=default_idx,
        key="huba_manual_report_pick",
        help="Po wyborze formularz poniżej podpowie pola związane z tym typem problemu.",
    )
    idx = options.index(choice)
    record_id, problem_type = meta[idx]
    st.session_state[_SESSION_PICK_ID] = record_id
    st.session_state[_SESSION_PICK_PROBLEM] = problem_type
    if record_id == "_GLOBAL_":
        st.info("Problem globalny — wybierz konkretny ID z listy węzłów cyklu.")


def _render_field_input(
    df: pd.DataFrame,
    column: str,
    current: object,
    *,
    key_prefix: str,
    known_ids: list[str],
) -> object:
    """Renderuje kontrolkę formularza właściwą dla typu edytowanej kolumny."""
    label = _FIELD_LABELS.get(column, column)
    cur_s = _cell_display(current)
    empty_opt = "(puste)"

    if column == "sex":
        opts = [empty_opt, "M", "F"]
        idx = opts.index(cur_s) if cur_s in opts else 0
        picked = st.selectbox(label, opts, index=idx, key=f"{key_prefix}_sex")
        return None if picked == empty_opt else picked

    if column in {"father_line", "mother_line", "line"}:
        opts = [empty_opt, "LB", "LC", "NA"]
        up = cur_s.upper() if cur_s else empty_opt
        idx = opts.index(up) if up in opts else 0
        picked = st.selectbox(label, opts, index=idx, key=f"{key_prefix}_line")
        return None if picked == empty_opt else picked

    if column in {"father_id", "mother_id"}:
        opts = [empty_opt] + known_ids
        if cur_s and cur_s not in opts:
            opts = [empty_opt, cur_s] + known_ids
        try:
            idx = opts.index(cur_s) if cur_s else 0
        except ValueError:
            idx = 0
        picked = st.selectbox(label, opts, index=idx, key=f"{key_prefix}_{column}")
        return None if picked == empty_opt else picked

    if column == "birth_year":
        return st.text_input(
            label,
            value=cur_s,
            key=f"{key_prefix}_year",
            placeholder="np. 1998 lub puste",
        )

    return st.text_input(label, value=cur_s, key=f"{key_prefix}_txt")


def _render_record_form(
    df_std: pd.DataFrame,
    record_id: str,
    *,
    problem_type: str | None,
    catalog_name: str,
    on_dataset_updated: Callable[[pd.DataFrame], None],
    key_prefix: str,
) -> None:
    """Renderuje formularz edycji jednego rekordu i obsługuje zapis oraz undo."""
    indices = find_row_indices(df_std, record_id)
    if not indices:
        st.error(f"Nie znaleziono wiersza z id **{record_id}**.")
        return

    row_index: int | None = indices[0]
    if len(indices) > 1:
        pick = st.selectbox(
            "Ten sam ID w wielu wierszach — wybierz wiersz",
            indices,
            format_func=lambda i: f"Indeks {i}",
            key=f"{key_prefix}_dup_row",
        )
        row_index = int(pick)
        st.session_state[_SESSION_PICK_ROW] = row_index

    row = df_std.loc[row_index]
    hint_cols = suggest_fields_for_problem(problem_type or "")
    cols_to_show = [c for c in hint_cols if c in editable_columns(df_std)]
    extra = st.checkbox("Pokaż wszystkie pola schematu", key=f"{key_prefix}_all_fields")
    if extra:
        cols_to_show = editable_columns(df_std)

    if problem_type:
        st.caption(f"Kontekst problemu: **{problem_type}**")

    known = _known_ids(df_std)
    year_max = datetime.now().year + 2
    edits: dict[str, object] = {}
    warnings: list[str] = []

    for col in cols_to_show:
        current = row.get(col)
        new_val = _render_field_input(
            df_std,
            col,
            current,
            key_prefix=f"{key_prefix}_{col}",
            known_ids=known,
        )
        norm_new = normalize_field_value(col, new_val)
        norm_old = normalize_field_value(col, current)
        new_empty = norm_new is None or (isinstance(norm_new, float) and norm_new != norm_new)
        old_empty = norm_old is None or (isinstance(norm_old, float) and norm_old != norm_old)
        if new_empty != old_empty or (not new_empty and str(norm_new) != str(norm_old)):
            edits[col] = new_val
            warnings.extend(
                validate_patch(
                    df_std,
                    FieldPatch(record_id=record_id, column=col, new_value=new_val, row_index=row_index),
                    year_max=year_max,
                )
            )

    if warnings:
        for w in dict.fromkeys(warnings):
            st.warning(w)

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        save = st.button("Zapisz zmiany", type="primary", key=f"{key_prefix}_save", use_container_width=True)
    with c2:
        undo_btn = st.button("Cofnij ostatnią", key=f"{key_prefix}_undo", use_container_width=True)
    with c3:
        st.caption("Zmiany w sesji — plik wynikowy po **Kroku 4** (czyszczenie automatyczne).")

    if undo_btn:
        snap = _pop_undo(catalog_name)
        if snap is None:
            st.error("Brak zapisanej kopii do cofnięcia.")
        else:
            on_dataset_updated(snap)
            _append_log(f"Cofnięto ostatnią edycję ({catalog_name}).")
            st.success("Przywrócono poprzedni stan bazy.")
            st.rerun()

    if save:
        if not edits:
            st.info("Nie wprowadzono żadnych zmian.")
        else:
            _push_undo(catalog_name, df_std)
            new_df, msgs = apply_record_patches(df_std, record_id, edits, row_index=row_index)
            on_dataset_updated(new_df)
            summary = "; ".join(msgs[:3])
            _append_log(f"{catalog_name} / {record_id}: {summary}")
            st.success("Zapisano. Przeliczono walidację.")
            st.rerun()


def _render_edit_log() -> None:
    """Pokazuje ostatnie ręczne edycje wykonane w bieżącej sesji."""
    log: list[str] = st.session_state.get(_SESSION_LOG, [])
    if not log:
        return
    with st.expander("Ostatnie edycje (sesja)", expanded=False):
        for line in log[:8]:
            st.caption(line)


def render_manual_corrections_section(
    df_std: pd.DataFrame,
    rep: ValidationReport | None,
    *,
    catalog_name: str,
    on_dataset_updated: Callable[[pd.DataFrame], None] | None,
) -> None:
    """Sekcja Kroku 4 — czyszczenie ręczne (pojedyncze pola)."""
    sc.population_dashboard_group_header(
        "Czyszczenie ręczne",
        "Edycja pojedynczych pól wczytanej bazy. Zapis przelicza walidację i liczniki z Kroku 2.",
        accent=_MANUAL_ACCENT,
        background=sc.THEME.ENTRY_BG,
    )

    if on_dataset_updated is None:
        st.warning("Brak aktywnej bazy w katalogu — wczytaj dane w **Kroku 1**.")
        return

    with st.container(border=True):
        st.caption(f"Aktywna baza: **{catalog_name}**")

        if rep is not None and rep.has_export_rows:
            st.markdown("##### 1. Wybór z raportu problemów")
            _render_report_problem_picker(rep)
            st.divider()

        st.markdown("##### 2. Osobnik (ID)")
        known = _known_ids(df_std)
        if not known:
            st.warning("Baza nie ma poprawnych identyfikatorów — uzupełnij kolumnę `id`.")
            return

        default_id = st.session_state.get(_SESSION_PICK_ID)
        if default_id not in known:
            default_id = known[0]

        picked_id = st.selectbox(
            "ID osobnika",
            known,
            index=known.index(default_id) if default_id in known else 0,
            key="huba_manual_search_id",
        )
        st.session_state[_SESSION_PICK_ID] = picked_id

        if rep is not None:
            n_issues = sum(1 for r in rep.export_rows if r.record_id == picked_id)
            if n_issues:
                st.caption(f"Dla tego ID raport wskazuje **{n_issues}** wpis(ów) w eksporcie problemów.")

        st.divider()
        st.markdown("##### 3. Formularz pól")
        _render_record_form(
            df_std,
            picked_id,
            problem_type=st.session_state.get(_SESSION_PICK_PROBLEM),
            catalog_name=catalog_name,
            on_dataset_updated=on_dataset_updated,
            key_prefix="huba_manual_section",
        )

    _render_edit_log()
