"""
Interfejs HUBA-WPB Cleaner — wczytanie, walidacja, czyszczenie i eksport bazy rodowodu żubra.
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from app.data.auto_fix import AutoFixOptions
from app.huba.archive import zip_directory
from app.huba.config_io import load_project_config, project_config_to_dict, repo_root
from app.huba.engine import run_project
from app.huba.models import ExportFormat, HubProjectConfig, HubRunResult, InputSource, OutputSpec, ProcessingRules
from app.ui.streamlit.huba_module1 import (
    SESSION_ACTIVE,
    SESSION_CATALOG,
    section_step1_load,
    section_step2_errors,
    section_step3_manual_clean,
)
from app.ui.streamlit.huba_nav import (
    NAV_SECTIONS,
    NAV_STEP1,
    NAV_STEP2,
    NAV_STEP3,
    NAV_STEP4,
    NAV_STEP5,
    _NAV_LEGACY,
)

# Re-eksport dla ``streamlit_app`` i innych modułów.
__all__ = [
    "NAV_SECTIONS",
    "NAV_STEP1",
    "NAV_STEP2",
    "NAV_STEP3",
    "NAV_STEP4",
    "NAV_STEP5",
    "_NAV_LEGACY",
    "run_huba_app",
]

SESSION_LAST_RUN = "huba_last_run"
SESSION_SHOW_HTML_REPORT = "huba_show_html_report"

# (klucz session_state, etykieta UI, wartość domyślna)
FIX_RULES: tuple[tuple[str, str, bool], ...] = (
    ("af_dedupe", "Usuń duplikaty numeru osobnika (zostaje pierwszy wiersz)", True),
    ("af_drop_no_id", "Usuń wiersze bez numeru osobnika", False),
    ("af_year", "Wyczyść rok urodzenia poza dopuszczalnym zakresem", True),
    ("af_death", "Wyczyść pole śmierci przy sprzeczności z datą urodzenia", True),
    ("af_self", "Usuń powiązanie: osobnik jako własny ojciec lub matka", True),
    ("af_missing", "Odetnij odwołanie do nieistniejącego rekordu rodzica", True),
    ("af_sex", "Odetnij rodzica przy kolizji płci (ojciec ≠ M, matka ≠ F)", True),
    ("af_young", "Odetnij zbyt młodego rodzica (wiek rodzica przy urodzeniu potomka)", True),
    ("af_old", "Odetnij zbyt starego rodzica (wiek > próg z konfiguracji)", False),
)


def _init_session() -> None:
    """Ustawia domyślne wartości stanu sesji dla kroków HUBA."""
    if "huba_project_name" not in st.session_state:
        st.session_state["huba_project_name"] = f"run_{datetime.now().strftime('%Y%m%d_%H%M')}"
    if "huba_exclude_test" not in st.session_state:
        st.session_state["huba_exclude_test"] = True
    if "huba_export_format" not in st.session_state:
        st.session_state["huba_export_format"] = "xlsx"
    for key, _label, default in FIX_RULES:
        if key not in st.session_state:
            st.session_state[key] = default


def _auto_fix_options_from_ui() -> AutoFixOptions:
    """Buduje opcje automatycznych poprawek z aktualnych kontrolek UI."""
    return AutoFixOptions(
        dedupe_ids=bool(st.session_state.get("af_dedupe", True)),
        drop_rows_without_id=bool(st.session_state.get("af_drop_no_id", False)),
        clear_birth_year_out_of_range=bool(st.session_state.get("af_year", True)),
        clear_death_date_on_conflict=bool(st.session_state.get("af_death", True)),
        remove_self_parent=bool(st.session_state.get("af_self", True)),
        cut_missing_parent_record=bool(st.session_state.get("af_missing", True)),
        cut_parent_sex_collision=bool(st.session_state.get("af_sex", True)),
        cut_parent_too_young=bool(st.session_state.get("af_young", True)),
        cut_parent_too_old=bool(st.session_state.get("af_old", False)),
    )


def _any_fix_selected(opts: AutoFixOptions) -> bool:
    """Sprawdza, czy zaznaczono przynajmniej jedną regułę automatycznej poprawki."""
    return any(
        (
            opts.dedupe_ids,
            opts.drop_rows_without_id,
            opts.clear_birth_year_out_of_range,
            opts.clear_death_date_on_conflict,
            opts.remove_self_parent,
            opts.cut_missing_parent_record,
            opts.cut_parent_sex_collision,
            opts.cut_parent_too_young,
            opts.cut_parent_too_old,
        )
    )


def _rules_from_ui() -> ProcessingRules:
    """Buduje reguły przetwarzania wsadowego z ustawień formularza."""
    auto_fix = _auto_fix_options_from_ui()
    return ProcessingRules(
        apply_auto_fix=_any_fix_selected(auto_fix),
        auto_fix=auto_fix,
        exclude_test_records=bool(st.session_state.get("huba_exclude_test", True)),
    )


def _output_from_ui() -> OutputSpec:
    """Buduje specyfikację eksportu z ustawień formularza."""
    fmt: ExportFormat = "csv" if st.session_state.get("huba_export_format") == "csv" else "xlsx"
    return OutputSpec(export_format=fmt)


def _build_project(inputs: tuple[InputSource, ...]) -> HubProjectConfig:
    """Składa konfigurację projektu HUBA dla wskazanych źródeł wejściowych."""
    name = str(st.session_state.get("huba_project_name", "huba_run")).strip() or "huba_run"
    return HubProjectConfig(
        project_name=name,
        output_dir=repo_root() / "outputs",
        inputs=inputs,
        rules=_rules_from_ui(),
        output=_output_from_ui(),
    )


def _render_fix_checklist() -> None:
    """Renderuje listę przełączników reguł automatycznego czyszczenia."""
    st.markdown("#### Lista poprawek")
    half = (len(FIX_RULES) + 1) // 2
    c1, c2 = st.columns(2)
    with c1:
        for key, label, _default in FIX_RULES[:half]:
            st.checkbox(label, key=key)
    with c2:
        for key, label, _default in FIX_RULES[half:]:
            st.checkbox(label, key=key)


def _run_project_from_catalog(
    project: HubProjectConfig,
    dataframes: dict[str, pd.DataFrame],
) -> HubRunResult:
    """Uruchamia wsad na ramkach z katalogu UI (bez ponownego mapowania kolumn)."""
    return run_project(project, upload_dataframes=dataframes)


def _show_html_report_after_download() -> None:
    """Otwiera podgląd raportu HTML po kliknięciu pobierania."""
    st.session_state[SESSION_SHOW_HTML_REPORT] = True


def _apply_json_config(raw: dict) -> None:
    """Wczytuje konfigurację JSON i przenosi jej ustawienia do stanu sesji."""
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(raw, tmp)
        loaded = load_project_config(tmp.name)
    st.session_state["huba_project_name"] = loaded.project_name
    st.session_state["huba_exclude_test"] = loaded.rules.exclude_test_records
    st.session_state["huba_export_format"] = loaded.output.export_format
    af = loaded.rules.auto_fix
    st.session_state["af_dedupe"] = af.dedupe_ids
    st.session_state["af_drop_no_id"] = af.drop_rows_without_id
    st.session_state["af_year"] = af.clear_birth_year_out_of_range
    st.session_state["af_death"] = af.clear_death_date_on_conflict
    st.session_state["af_self"] = af.remove_self_parent
    st.session_state["af_missing"] = af.cut_missing_parent_record
    st.session_state["af_sex"] = af.cut_parent_sex_collision
    st.session_state["af_young"] = af.cut_parent_too_young
    st.session_state["af_old"] = af.cut_parent_too_old


def section_step4_auto_clean() -> None:
    """Renderuje krok wyboru reguł automatycznego czyszczenia i eksportu."""
    st.markdown("### Krok 4 — Czyszczenie automatyczne")
    st.caption(
        "Wybierz bazy z katalogu, zaznacz reguły auto-poprawek i wyeksportuj oczyszczone pliki. "
        "Wyniki pobierzesz w **Kroku 5 — Wyniki**. Ręczne korekty pól — w **Kroku 3**."
    )

    catalog: dict = st.session_state.get(SESSION_CATALOG, {})
    if not catalog:
        st.warning("Najpierw wczytaj dane w **Kroku 1 — Wczytanie danych**.")
        return

    st.markdown("#### Bazy do oczyszczenia")
    names = list(catalog.keys())
    active = st.session_state.get(SESSION_ACTIVE)
    default_sel = [active] if active in names else ([names[0]] if names else [])
    selected = st.multiselect(
        "Wybierz jedną lub więcej pozycji z katalogu",
        names,
        default=default_sel,
        key="huba_clean_pick",
    )

    _render_fix_checklist()

    st.markdown("#### Eksport")
    st.text_input("Nazwa projektu (podkatalog w `outputs/`)", key="huba_project_name")
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Format pliku wynikowego", ["xlsx", "csv"], key="huba_export_format")
    with c2:
        st.checkbox("Pomiń rekord testowy (ID 99999)", key="huba_exclude_test")

    with st.expander("Konfiguracja z pliku JSON (opcjonalnie)", expanded=False):
        cfg_upload = st.file_uploader("Wczytaj `huba_project.json`", type=["json"], key="huba_cfg_json")
        if cfg_upload is not None:
            try:
                _apply_json_config(json.loads(cfg_upload.getvalue().decode("utf-8")))
                st.success("Wczytano ustawienia z pliku JSON.")
                st.rerun()
            except Exception as e:
                st.error(f"Nie udało się wczytać JSON: {e}")
        st.download_button(
            "Pobierz szablon konfiguracji (JSON)",
            data=json.dumps(project_config_to_dict(_build_project(())), ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="huba_project.template.json",
            mime="application/json",
        )

    if not selected:
        st.info("Wybierz co najmniej jedną bazę z katalogu.")
        return

    if st.button("Wykonaj czyszczenie i eksport", type="primary", width="stretch"):
        inputs = tuple(InputSource(name=n, path=None) for n in selected)
        dataframes = {n: catalog[n].df_std.copy() for n in selected}
        with st.spinner("Czyszczenie i zapis wyników…"):
            try:
                result = _run_project_from_catalog(_build_project(inputs), dataframes)
                st.session_state[SESSION_LAST_RUN] = result
                st.success(f"Zakończono. Wyniki w **Kroku 5 — Wyniki** (`{result.project_dir}`).")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def section_step5_results() -> None:
    """Renderuje tabelę wyników oraz przyciski pobierania plików po czyszczeniu."""
    st.markdown("### Krok 5 — Wyniki")
    result: HubRunResult | None = st.session_state.get(SESSION_LAST_RUN)
    if result is None:
        st.info("Brak wyników — wykonaj czyszczenie automatyczne w **Kroku 4**.")
        return

    st.caption(f"Katalog: `{result.project_dir}`")
    rows = [
        {
            "wejście": d.input_name,
            "wiersze_we": d.rows_in,
            "wiersze_wy": d.rows_out,
            "błędy": d.validation_errors,
            "ostrzeżenia": d.validation_warnings,
            "status": d.status,
        }
        for d in result.datasets
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    downloads: list[dict[str, object]] = []
    if result.comparison_path and result.comparison_path.is_file():
        downloads.append(
            {
                "label": "Pobierz comparison.csv",
                "data": result.comparison_path.read_bytes(),
                "file_name": "comparison.csv",
                "mime": "text/csv",
                "type": "secondary",
            }
        )
    if result.final_report_html_path.is_file():
        downloads.append(
            {
                "label": "Pobierz raport HTML",
                "data": result.final_report_html_path.read_bytes(),
                "file_name": "final_report.html",
                "mime": "text/html",
                "type": "primary",
            }
        )
    if result.manifest_path.is_file():
        downloads.append(
            {
                "label": "Pobierz manifest.json",
                "data": result.manifest_path.read_bytes(),
                "file_name": "manifest.json",
                "mime": "application/json",
                "type": "secondary",
            }
        )

    try:
        zip_bytes = zip_directory(result.project_dir)
        downloads.append(
            {
                "label": "Pobierz cały katalog wyników (ZIP)",
                "data": zip_bytes,
                "file_name": f"{result.project_dir.name}.zip",
                "mime": "application/zip",
                "type": "primary",
            }
        )
    except Exception as e:
        st.warning(f"Nie udało się spakować wyników: {e}")

    if downloads:
        cols = st.columns(len(downloads))
        for col, item in zip(cols, downloads):
            with col:
                if str(item["file_name"]) == "final_report.html":
                    st.download_button(
                        str(item["label"]),
                        data=item["data"],
                        file_name=str(item["file_name"]),
                        mime=str(item["mime"]),
                        type=str(item["type"]),  # type: ignore[arg-type]
                        use_container_width=True,
                        on_click=_show_html_report_after_download,
                    )
                else:
                    st.download_button(
                        str(item["label"]),
                        data=item["data"],
                        file_name=str(item["file_name"]),
                        mime=str(item["mime"]),
                        type=str(item["type"]),  # type: ignore[arg-type]
                        use_container_width=True,
                    )

    if result.final_report_html_path.is_file():
        c_preview, c_hide = st.columns([1, 1])
        with c_preview:
            if st.button("Wyświetl raport HTML", use_container_width=True):
                st.session_state[SESSION_SHOW_HTML_REPORT] = True
        with c_hide:
            if st.button("Ukryj raport", use_container_width=True):
                st.session_state[SESSION_SHOW_HTML_REPORT] = False

        if st.session_state.get(SESSION_SHOW_HTML_REPORT):
            st.markdown("#### Podgląd raportu HTML")
            components.html(
                result.final_report_html_path.read_text(encoding="utf-8"),
                height=760,
                scrolling=True,
            )

    with st.expander("Struktura katalogów (podgląd)", expanded=False):
        lines = [str(p.relative_to(result.project_dir)) for p in sorted(result.project_dir.rglob("*")) if p.is_file()]
        st.code("\n".join(lines) if lines else "(pusto)", language=None)


def run_huba_app() -> None:
    """Uruchamia aktualnie wybrany krok aplikacji HUBA-WPB Cleaner."""
    _init_session()
    section = st.session_state.get("huba_nav", NAV_STEP1)
    if section in _NAV_LEGACY:
        section = _NAV_LEGACY[str(section)]
    if section == NAV_STEP1:
        section_step1_load()
    elif section == NAV_STEP2:
        section_step2_errors()
    elif section == NAV_STEP3:
        section_step3_manual_clean()
    elif section == NAV_STEP4:
        section_step4_auto_clean()
    else:
        section_step5_results()
