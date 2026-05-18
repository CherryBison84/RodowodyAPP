"""
HUBA — kroki 1–3: wczytanie, walidacja i ręczne czyszczenie bazy.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from app.huba.modules.dataset_inspect import (
    InspectedDataset,
    inspect_dataframe,
    inspect_dataset_from_bytes,
)
from app.huba.modules.merge import merge_standardized_frames
from app.ui import help_content as hc
from app.ui.streamlit import common as sc
from app.ui.streamlit.huba_nav import MANUAL_CLEAN_ENABLED
from app.ui.streamlit.manual_edit_panel import render_manual_corrections_section
from app.ui.streamlit.validation_sections import (
    render_validation_summary_charts_expander,
    render_validation_workspace,
)

SESSION_CATALOG = "huba_m1_catalog"
SESSION_ACTIVE = "huba_m1_active"


def _init_catalog() -> None:
    if SESSION_CATALOG not in st.session_state:
        st.session_state[SESSION_CATALOG] = {}


def _entry_kind_label(d: object) -> str:
    merged = getattr(d, "merged_from", None)
    if merged:
        return "Połączenie"
    source = getattr(d, "source_label", "")
    if isinstance(source, str) and source.startswith("Połączenie:"):
        return "Połączenie"
    return "Plik"


def _merged_from_for(d: object) -> tuple[str, ...]:
    merged = getattr(d, "merged_from", None)
    if merged:
        return tuple(merged)
    source = getattr(d, "source_label", "")
    if isinstance(source, str) and source.startswith("Połączenie:"):
        body = source.replace("Połączenie:", "", 1).strip()
        if body:
            return tuple(p.strip() for p in body.split("+") if p.strip())
    return ()


def _upgrade_catalog_item(item: object) -> InspectedDataset | None:
    """Podnosi stary wpis sesji do bieżącej wersji ``InspectedDataset``."""
    if not (
        hasattr(item, "name")
        and hasattr(item, "df_std")
        and hasattr(item, "source_label")
        and hasattr(item, "validation_report")
    ):
        return None
    merged = _merged_from_for(item)
    if isinstance(item, InspectedDataset) and getattr(item, "merged_from", ()) == merged:
        _entry_kind_label(item)
        return item
    return inspect_dataframe(
        str(getattr(item, "name")),
        getattr(item, "df_std"),
        str(getattr(item, "source_label")),
        merged_from=merged,
    )


def _catalog() -> dict[str, InspectedDataset]:
    raw: dict[str, InspectedDataset] = st.session_state.get(SESSION_CATALOG, {})
    if not raw:
        return {}
    migrated: dict[str, InspectedDataset] = {}
    changed = False
    for name, item in raw.items():
        upgraded = _upgrade_catalog_item(item)
        if upgraded is None:
            changed = True
            continue
        migrated[name] = upgraded
        if upgraded is not item:
            changed = True
    if changed:
        st.session_state[SESSION_CATALOG] = migrated
        active = st.session_state.get(SESSION_ACTIVE)
        if active and active not in migrated:
            st.session_state.pop(SESSION_ACTIVE, None)
    return migrated


def _register(dataset: InspectedDataset) -> None:
    cat = dict(_catalog())
    cat[dataset.name] = dataset
    st.session_state[SESSION_CATALOG] = cat
    st.session_state[SESSION_ACTIVE] = dataset.name


def apply_catalog_edit(catalog_name: str, df_new: pd.DataFrame) -> InspectedDataset:
    """Zapisuje zmiany w katalogu HUBA i przelicza walidację."""
    cat = _catalog()
    if catalog_name not in cat:
        raise KeyError(f"Brak bazy {catalog_name!r} w katalogu.")
    old = cat[catalog_name]
    updated = inspect_dataframe(
        catalog_name,
        df_new,
        old.source_label,
        merged_from=old.merged_from,
    )
    _register(updated)
    return updated


def _page_intro(title: str, description: str) -> None:
    th = sc.THEME
    st.markdown(
        f'<h3 style="margin:0 0 0.35rem 0;color:{th.TEXT};">{html.escape(title)}</h3>',
        unsafe_allow_html=True,
    )
    st.caption(description)


def _holder_image_path() -> Path:
    """``app/assets/holder.jpeg`` — grafika placeholdera Kroku 3."""
    from app.runtime_path import assets_dir

    return assets_dir() / "holder.jpeg"


def render_manual_clean_placeholder() -> None:
    """Krok 3 niedostępny — podgląd z holder.jpeg w stylu reszty HUBA."""
    th = sc.THEME
    _page_intro(
        "Krok 3 — Czyszczenie ręczne",
        "Sekcja w przygotowaniu. Tymczasowo: popraw dane w arkuszu źródłowym lub użyj "
        "**Kroku 4 — Czyszczenie automatyczne**.",
    )

    sc.population_dashboard_group_header(
        "Wkrótce",
        "Ręczna edycja pól rekordu w aplikacji — funkcja w budowie.",
        accent=th.ACCENT,
        background=th.ENTRY_BG,
    )

    holder = _holder_image_path()
    with st.container(border=True):
        if holder.is_file():
            sc.show_image_at_scale(holder, scale=3, center=True)
        else:
            st.warning(f"Brak pliku podglądu: `{holder}`")

def _summary_table(cat: dict[str, InspectedDataset]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Nazwa": d.name,
                "Typ": _entry_kind_label(d),
                "Wiersze": d.rows,
                "ERROR": d.error_count,
                "WARN": d.warning_count,
            }
            for d in cat.values()
        ]
    )


def _dataset_picker_label(name: str, d: InspectedDataset) -> str:
    if d.error_count:
        mark = "●"
    elif d.warning_count:
        mark = "○"
    else:
        mark = "✓"
    return f"{mark} {name} · {d.rows} wierszy · {d.error_count}/{d.warning_count} err/warn"


def _render_merge_panel(cat: dict[str, InspectedDataset]) -> None:
    """UI łączenia co najmniej dwóch baz z katalogu."""
    if len(cat) < 2:
        return

    st.markdown("---")
    st.markdown("#### Łączenie baz z kilku plików")
    st.caption(
        "Połącz wybrane pozycje z katalogu w jedną bazę. Wynik trafia do katalogu jako **Połączenie**."
    )

    names = list(cat.keys())
    selected = st.multiselect(
        "Bazy do połączenia",
        names,
        default=names,
        key="huba_merge_pick",
    )

    c1, c2 = st.columns(2)
    with c1:
        merge_name = st.text_input(
            "Nazwa połączonej bazy",
            value="baza_polaczona",
            key="huba_merge_name",
        ).strip() or "baza_polaczona"
    with c2:
        dup_policy = st.selectbox(
            "Duplikaty `id`",
            options=[
                ("keep_first", "Pierwszy wiersz"),
                ("keep_last", "Ostatni wiersz"),
                ("keep_all", "Wszystkie (walidacja wykryje)"),
            ],
            format_func=lambda x: x[1],
            key="huba_merge_dup",
        )
        policy_key = dup_policy[0]

    if len(selected) < 2:
        st.info("Zaznacz co najmniej **dwa** wpisy z katalogu.")
        return

    if st.button("Połącz wybrane bazy", type="primary", use_container_width=True, key="huba_merge_btn"):
        try:
            parts = [(n, cat[n].df_std) for n in selected]
            merged = merge_standardized_frames(parts, on_duplicate_id=policy_key)  # type: ignore[arg-type]
            source_label = " + ".join(merged.source_names)
            inspected = inspect_dataframe(
                merge_name,
                merged.df_std,
                f"Połączenie: {source_label}",
                merged_from=merged.source_names,
            )
            _register(inspected)
            st.session_state["huba_merge_last_log"] = "\n".join(merged.log)
            st.success(f"Połączono jako **{merge_name}** ({inspected.rows} wierszy).")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    log_txt = st.session_state.get("huba_merge_last_log")
    if log_txt:
        with st.expander("Log ostatniego łączenia", expanded=False):
            st.code(log_txt)


def _render_validation_status_strip(active: InspectedDataset) -> None:
    """Jedna linia statusu zamiast wielu paneli."""
    th = sc.THEME
    rep = active.validation_report
    if active.error_count:
        bg, border = "#fdeaea", "#8b2e2e"
    elif active.warning_count:
        bg, border = "#faf3e0", "#7a5c1e"
    else:
        bg, border = "#e8f5ea", th.EDGE_PLOT

    merged = getattr(active, "merged_from", ()) or ()
    source = (
        f"Połączenie: {', '.join(merged)}"
        if merged
        else f"Źródło: {active.source_label}"
    )

    st.markdown(
        f'<div style="padding:12px 16px;border-radius:10px;background:{bg};'
        f'border:1px solid {border};border-left:5px solid {border};margin:0.25rem 0 1rem 0;">'
        f'<div style="font-weight:700;font-size:1.02rem;color:{th.TEXT};">'
        f"{html.escape(rep.short_status())}</div>"
        f'<div style="font-size:0.85rem;color:{th.MUTED};margin-top:6px;">'
        f"{html.escape(source)} · {active.rows} wierszy · "
        f"{active.error_count} ERROR · {active.warning_count} WARN</div></div>",
        unsafe_allow_html=True,
    )


def section_step1_load() -> None:
    """Krok 1 — wczytanie i walidacja wstępna plików."""
    _init_catalog()
    _page_intro(
        "Krok 1 — Wczytanie danych",
        "Dodaj pliki CSV/XLSX. Opcjonalnie połącz kilka plików w jedną bazę. Potem przejdź do **Kroku 2 — Walidacja**.",
    )

    uploaded = st.file_uploader(
        "Pliki wejściowe",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="huba_m1_uploader",
    )

    if uploaded and st.button("Wczytaj i zwaliduj", type="primary", use_container_width=True):
        errors: list[str] = []
        loaded = 0
        for i, f in enumerate(uploaded):
            try:
                inspected = inspect_dataset_from_bytes(
                    Path(f.name).stem or f"plik_{i+1}",
                    f.getvalue(),
                    f.name,
                )
                _register(inspected)
                loaded += 1
            except Exception as e:
                errors.append(f"{f.name}: {e}")
        for msg in errors:
            st.error(msg)
        if loaded:
            st.success(f"Wczytano {loaded} plik(ów). Otwórz **Krok 2 — Walidacja**.")
            st.rerun()

    cat = _catalog()
    if not cat:
        st.info("Brak wczytanych plików.")
        return

    st.dataframe(_summary_table(cat), width="stretch", hide_index=True)
    _render_merge_panel(cat)

    if st.button("Wyczyść katalog", use_container_width=True):
        st.session_state[SESSION_CATALOG] = {}
        st.session_state.pop(SESSION_ACTIVE, None)
        st.rerun()


def _pick_active_dataset(cat: dict[str, InspectedDataset], *, picker_key: str) -> tuple[str, InspectedDataset] | None:
    names = list(cat.keys())
    default_idx = (
        names.index(st.session_state[SESSION_ACTIVE])
        if st.session_state.get(SESSION_ACTIVE) in names
        else 0
    )
    picked = st.selectbox(
        "Baza w katalogu",
        names,
        index=default_idx,
        format_func=lambda n: _dataset_picker_label(n, cat[n]),
        key=picker_key,
    )
    st.session_state[SESSION_ACTIVE] = picked
    return picked, cat[picked]


def section_step2_errors() -> None:
    """Krok 2 — walidacja: lista kategorii + treść."""
    _init_catalog()
    _page_intro(
        "Krok 2 — Walidacja",
        "Przegląd problemów wg kategorii. Eksport i reguły wsadowe — w **Kroku 4**. "
        "(Krok 3 — czyszczenie ręczne — w przygotowaniu.)",
    )

    cat = _catalog()
    if not cat:
        st.warning("Najpierw wczytaj dane w **Kroku 1**.")
        return

    picked_active = _pick_active_dataset(cat, picker_key="huba_m1_picker")
    if picked_active is None:
        return
    picked, active = picked_active

    _render_validation_status_strip(active)

    def _on_dataset_updated(df_new: pd.DataFrame) -> None:
        apply_catalog_edit(picked, df_new)

    render_validation_workspace(
        active.df_std,
        active.validation_report,
        show_autofix=False,
        catalog_name=picked,
        on_dataset_updated=_on_dataset_updated,
        missing_data_hint="Brak raportu — wczytaj plik ponownie w **Kroku 1**.",
    )

    st.divider()
    with st.expander("Inne bazy w katalogu", expanded=False):
        st.dataframe(_summary_table(cat), width="stretch", hide_index=True)
    sc.help_expander("Co sprawdza walidacja?", hc.SECTION_VALIDATION, expanded=False)
    render_validation_summary_charts_expander(active.df_std, active.validation_report)


def section_step3_manual_clean() -> None:
    """Krok 3 — ręczna korekta pól w katalogu (lub placeholder gdy wyłączone)."""
    if not MANUAL_CLEAN_ENABLED:
        render_manual_clean_placeholder()
        return

    _init_catalog()
    _page_intro(
        "Krok 3 — Czyszczenie ręczne",
        "Popraw pojedyncze pola we wczytanej bazie. Po zapisie walidacja przelicza się od razu. "
        "Reguły wsadowe i eksport pliku — w **Kroku 4 — Czyszczenie automatyczne**.",
    )

    cat = _catalog()
    if not cat:
        st.warning("Najpierw wczytaj dane w **Kroku 1**.")
        return

    picked_active = _pick_active_dataset(cat, picker_key="huba_m3_picker")
    if picked_active is None:
        return
    picked, active = picked_active

    _render_validation_status_strip(active)

    def _on_dataset_updated(df_new: pd.DataFrame) -> None:
        apply_catalog_edit(picked, df_new)

    render_manual_corrections_section(
        active.df_std,
        active.validation_report,
        catalog_name=picked,
        on_dataset_updated=_on_dataset_updated,
    )
