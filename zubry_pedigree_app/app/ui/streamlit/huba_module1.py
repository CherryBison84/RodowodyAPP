"""
HUBA — kroki 1–2: wczytanie danych i przegląd błędów w bazie.
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
from app.ui.streamlit.validation_sections import render_validation_workspace

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


def _active_dataset() -> InspectedDataset | None:
    name = st.session_state.get(SESSION_ACTIVE)
    if not name:
        return None
    return _catalog().get(str(name))


def _page_intro(title: str, description: str) -> None:
    th = sc.THEME
    st.markdown(
        f'<h3 style="margin:0 0 0.35rem 0;color:{th.TEXT};">{html.escape(title)}</h3>',
        unsafe_allow_html=True,
    )
    st.caption(description)


def _summary_table(cat: dict[str, InspectedDataset]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Nazwa w katalogu": d.name,
                "Typ": _entry_kind_label(d),
                "Źródło": d.source_label,
                "Wiersze": d.rows,
                "Błędy (ERROR)": d.error_count,
                "Ostrzeżenia (WARN)": d.warning_count,
                "Status": d.status_label,
            }
            for d in cat.values()
        ]
    )


def _dataset_picker_label(name: str, d: InspectedDataset) -> str:
    """Etykieta listy rozwijanej z liczbami błędów i ostrzeżeń."""
    if d.error_count:
        flag = "● błędy"
    elif d.warning_count:
        flag = "○ ostrzeżenia"
    else:
        flag = "✓ OK"
    return f"{name} — {flag} · {d.rows} wierszy · {d.error_count} err. / {d.warning_count} warn."


def _render_merge_panel(cat: dict[str, InspectedDataset]) -> None:
    """UI łączenia co najmniej dwóch baz z katalogu."""
    if len(cat) < 2:
        return

    st.markdown("---")
    st.markdown("#### Łączenie baz z kilku plików")
    st.caption(
        "Połącz wybrane pozycje z katalogu w jedną bazę. Przydatne, gdy dane są rozdzielone "
        "na kilka arkuszy lub eksportów. Wynik trafia do katalogu jako osobna pozycja typu **Połączenie**."
    )

    names = list(cat.keys())
    selected = st.multiselect(
        "Bazy do połączenia",
        names,
        default=names,
        key="huba_merge_pick",
        help="Kolejność na liście ma znaczenie przy strategii „pierwszy/ostatni wiersz” dla duplikatów ID.",
    )

    c1, c2 = st.columns(2)
    with c1:
        merge_name = st.text_input(
            "Nazwa połączonej bazy w katalogu",
            value="baza_polaczona",
            key="huba_merge_name",
        ).strip() or "baza_polaczona"
    with c2:
        dup_policy = st.selectbox(
            "Duplikaty `id` między plikami",
            options=[
                ("keep_first", "Zostaw pierwszy wiersz (wg kolejności plików)"),
                ("keep_last", "Zostaw ostatni wiersz"),
                ("keep_all", "Zostaw wszystkie (walidacja wykryje duplikaty)"),
            ],
            format_func=lambda x: x[1],
            key="huba_merge_dup",
        )
        policy_key = dup_policy[0]

    if len(selected) < 2:
        st.info("Zaznacz co najmniej **dwa** wpisy z katalogu.")
        return

    if merge_name in cat and merge_name not in selected:
        st.warning(f"Nazwa „{merge_name}” jest już w katalogu — wybierz inną lub nadpisz po potwierdzeniu.")

    if st.button("Połącz wybrane bazy", type="primary", width="stretch", key="huba_merge_btn"):
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
            st.success(
                f"Utworzono połączoną bazę **{merge_name}** ({inspected.rows} wierszy). "
                f"Zobacz **Krok 2 — Walidacja**."
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))

    log_txt = st.session_state.get("huba_merge_last_log")
    if log_txt:
        with st.expander("Log ostatniego łączenia", expanded=False):
            st.code(log_txt)


def _status_banner(active: InspectedDataset) -> None:
    th = sc.THEME
    if active.error_count:
        bg, border, label = "#fdeaea", "#8b2e2e", "Wymaga poprawy przed eksportem"
    elif active.warning_count:
        bg, border, label = "#faf3e0", "#7a5c1e", "Do weryfikacji w arkuszu"
    else:
        bg, border, label = "#e8f5ea", th.EDGE_PLOT, "Krytycznych problemów nie wykryto"
    st.markdown(
        f'<div style="padding:12px 14px;border-radius:10px;background:{bg};'
        f'border:1px solid {border};border-left:5px solid {border};margin:0.5rem 0 1rem 0;">'
        f'<div style="font-weight:700;color:{th.TEXT};">{html.escape(active.validation_report.short_status())}</div>'
        f'<div style="font-size:0.85rem;color:{th.MUTED};margin-top:4px;">{html.escape(label)}</div></div>',
        unsafe_allow_html=True,
    )


def section_step1_load() -> None:
    """Krok 1 — wczytanie i walidacja wstępna plików."""
    _init_catalog()
    _page_intro(
        "Krok 1 — Wczytanie danych",
        "Wybierz pliki CSV/XLSX. Możesz **połączyć kilka plików w jedną bazę** (sekcja poniżej katalogu). "
        "Następnie przejdź do **Kroku 2 — Walidacja**, aby przejrzeć wyniki kontroli.",
    )

    uploaded = st.file_uploader(
        "Pliki wejściowe",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        key="huba_m1_uploader",
        help="Każdy plik trafi do katalogu sesji pod nazwą wziętą ze stem nazwy pliku.",
    )
    if uploaded:
        st.caption(
            f"Zaznaczono: {len(uploaded)} plik(ów) — {', '.join(f.name for f in uploaded[:5])}"
            + (" …" if len(uploaded) > 5 else "")
        )

    if uploaded and st.button("Wczytaj i zwaliduj", type="primary", width="stretch"):
        errors: list[str] = []
        loaded = 0
        for i, f in enumerate(uploaded):
            try:
                data = f.getvalue()
                stem = Path(f.name).stem or f"plik_{i+1}"
                inspected = inspect_dataset_from_bytes(stem, data, f.name)
                _register(inspected)
                loaded += 1
            except Exception as e:
                errors.append(f"{f.name}: {e}")
        for msg in errors:
            st.error(msg)
        if loaded:
            st.success(f"Wczytano: {loaded} plik(ów). Przejdź do **Kroku 2 — Walidacja**.")
            st.rerun()

    cat = _catalog()
    if not cat:
        st.info("Brak wczytanych plików — wybierz pliki i kliknij **Wczytaj i zwaliduj**.")
        return

    st.markdown("#### Katalog wczytanych plików")
    st.dataframe(_summary_table(cat), width="stretch", hide_index=True)

    _render_merge_panel(cat)

    if st.button("Wyczyść katalog", width="stretch"):
        st.session_state[SESSION_CATALOG] = {}
        st.session_state.pop(SESSION_ACTIVE, None)
        st.rerun()


def section_step2_errors() -> None:
    """Krok 2 — walidacja wybranej bazy (kategorie problemów i eksport)."""
    _init_catalog()
    th = sc.THEME
    _page_intro(
        "Krok 2 — Walidacja",
        "Wybierz bazę z katalogu, sprawdź podsumowanie i przejdź przez **kategorie problemów**. "
        "Pełną listę do Excela pobierzesz w kategorii **Pełny raport i eksport**. "
        "Automatyczne czyszczenie — w **Kroku 3**.",
    )

    cat = _catalog()
    if not cat:
        st.warning("Najpierw wczytaj dane w **Kroku 1 — Wczytanie danych**.")
        return

    names = list(cat.keys())
    default_idx = (
        names.index(st.session_state[SESSION_ACTIVE])
        if st.session_state.get(SESSION_ACTIVE) in names
        else 0
    )

    with st.container(border=True):
        st.markdown("#### Wybierz bazę do przeglądu")
        picked = st.selectbox(
            "Aktywna baza",
            names,
            index=default_idx,
            format_func=lambda n: _dataset_picker_label(n, cat[n]),
            key="huba_m1_picker",
            label_visibility="collapsed",
        )
        st.session_state[SESSION_ACTIVE] = picked
        active = cat[picked]

        merged_from = getattr(active, "merged_from", ()) or ()
        if merged_from:
            st.caption(
                f"**Połączenie** ({', '.join(merged_from)}) · `{active.source_label}`"
            )
        else:
            st.caption(f"Plik: `{active.source_label}`")

        m1, m2, m3 = st.columns(3)
        with m1:
            sc.population_dashboard_metric(
                "Wiersze w bazie",
                str(active.rows),
                accent=th.EDGE_PLOT,
                panel_bg=th.ENTRY_BG,
            )
        with m2:
            sc.population_dashboard_metric(
                "Błędy (ERROR)",
                str(active.error_count),
                accent="#8b2e2e",
                panel_bg="#fdeaea" if active.error_count else th.ENTRY_BG,
            )
        with m3:
            sc.population_dashboard_metric(
                "Ostrzeżenia (WARN)",
                str(active.warning_count),
                accent="#7a5c1e",
                panel_bg="#faf3e0" if active.warning_count else th.ENTRY_BG,
            )

        _status_banner(active)

    with st.expander("Podgląd wszystkich baz w katalogu", expanded=False):
        st.dataframe(_summary_table(cat), width="stretch", hide_index=True)

    sc.help_expander("Co sprawdza walidacja?", hc.SECTION_VALIDATION, expanded=False)

    st.markdown("---")
    render_validation_workspace(
        active.df_std,
        active.validation_report,
        show_autofix=False,
        layout="grouped",
        missing_data_hint="Brak raportu — wczytaj plik ponownie w **Kroku 1**.",
    )
