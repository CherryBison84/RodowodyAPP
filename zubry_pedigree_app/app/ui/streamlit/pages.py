"""
Ekrany Streamlit: wczytywanie, rejestr, analizy, populacja, raporty, plan hodowlany.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.analytics.breeding_pairs import normalize_line, suggest_pairs_with_constraints
from app.analytics.inbreeding_wright import (
    batch_offspring_inbreeding_F_from_parent_pairs,
    wright_inbreeding_F,
    wright_kinship_phi_and_relationship_R,
    wright_offspring_inbreeding_F_from_parents,
)
from app.analytics.kinship_decomposition import close_kinship_note, explain_pair_kinship
from app.analytics.population_dashboard import (
    compare_birth_periods,
    global_ria_percent,
    line_vulnerability_table,
    pct_individuals_incomplete_parents,
    pct_missing_parent_slots,
    sire_offspring_concentration,
    summarize_active_cohort,
)
from app.analytics.mean_kinship import mean_kinship_pairwise
from app.analytics.population_genetics import (
    TEST_ID,
    FounderContributionComputer,
    compute_gi_and_family_data,
    compute_population_genetics_stats,
)
from app.data.dataset_loader import (
    dataframe_app_schema_columns,
    load_dataset_from_bytes,
    load_default_bison_report,
    load_raw_dataframe_from_url,
    standardize_bison_report_dataframe_with_column_mapping,
)
from app.config import get_config
from app.pedigree.ancestor_pedigree import get_ancestor_levels_unbounded
from app.ui import help_content as hc
from app.ui.streamlit import common as sc
from app.ui.streamlit.page_helpers import (
    breeding_hypo_offspring_figure,
    build_pedigree_figure,
    individual_pcl_dataframe,
    pci_bundle_for_breeding,
    plan_pedigree_plot_depth,
)
import app.ui.streamlit.streamlit_plotting as splt

CFG = get_config()

# Grupy zakładek wykresów (Populacja) — kolejność i indeksy spójne z dashboardem.
_SECTION_POP_CHART_TAB_GROUPS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("Populacja i urodzenia", (0, 1, 2, 3)),
    ("Inbred i trendy", (6, 11, 12)),
    ("Założyciele (p_i)", (7,)),
    ("Kompletność i PCL", (4, 5, 13)),
    ("GI i rodziny", (8, 9, 10)),
)


def _on_pop_chart_viz_tab_changed() -> None:
    lab = st.session_state.get("pop_chart_viz_tabs")
    if lab is None:
        return
    for title, ids in _SECTION_POP_CHART_TAB_GROUPS:
        if title == lab:
            st.session_state.pop_chart_idx = ids[0]
            return


def section_import() -> None:
    st.markdown("### Import i standaryzacja danych")
    st.caption("Plik CSV/XLSX lub URL z mapowaniem kolumn. Po wczytaniu przejdź do **Walidacja spójności zbioru**.")
    sc.help_expander(
        "Co oznacza wczytywanie?",
        hc.SECTION_LOADING,
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
                birth_loc_col = st.selectbox("birth_location (opcjonalnie)", cols, key="map_bl")
            with m3:
                father_col = st.selectbox("father_id", cols, key="map_f")
                mother_col = st.selectbox("mother_id", cols, key="map_m")
            if st.button("Zastosuj mapowanie i wczytaj"):
                mapping = {
                    "id": None if id_col == "<brak>" else id_col,
                    "sex": None if sex_col == "<brak>" else sex_col,
                    "line": None if line_col == "<brak>" else line_col,
                    "birth_year": None if birth_col == "<brak>" else birth_col,
                    "birth_location": None if birth_loc_col == "<brak>" else birth_loc_col,
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
        st.success(
            f"W pamięci sesji: **{st.session_state.get('source', '-')}** • **n =** {len(df_std)}. "
            "Następny krok: **Walidacja spójności zbioru** w menu."
        )


def section_validation() -> None:
    st.markdown("### Walidacja spójności zbioru")
    st.caption(
        "Kontrola spójności rodowodu i rekordów po imporcie. Potem: rejestr osobniczy → analizy osobnicze i par → "
        "parametry populacyjne → raport."
    )
    sc.help_expander(
        "Co sprawdza walidacja?",
        hc.SECTION_VALIDATION,
    )
    df_std = st.session_state.get("df_std")
    if df_std is None or df_std.empty:
        st.info("Brak wczytanej bazy — użyj **Import danych**.")
        return
    st.info(f"**Źródło:** {st.session_state.get('source', '-')} • **n =** {len(df_std)}")
    ids = df_std["id"].dropna().astype(str)
    if len(ids) > 0:
        st.caption(
            f"Zakres ID: min **{min(ids.tolist(), key=sc.id_sort_key)}**, "
            f"max **{max(ids.tolist(), key=sc.id_sort_key)}**"
        )
    st.markdown("**Braki danych — heatmapa**")
    df_miss = dataframe_app_schema_columns(df_std)
    fig_miss = splt.fig_column_missing_heatmap(df_miss)
    splt.show_matplotlib_figure_in_streamlit(
        fig_miss,
        download_filename="walidacja_mapa_brakow.png",
        download_key="val_miss_heatmap_png",
        width="stretch",
    )
    _miss_raw = splt.column_missing_percentages(df_miss).round(2)
    _miss_ord = splt.registry_like_column_order(_miss_raw.index)
    _miss_pct = _miss_raw.reindex(_miss_ord)
    with st.expander("Tabela % braków (według kolumn)", expanded=False):
        st.dataframe(_miss_pct.to_frame("% braków"), width="stretch")

    rep = st.session_state.get("validation_report")
    if rep is not None:
        st.markdown(rep.ui_summary())
        st.download_button(
            "Pobierz listę problemów walidacji (CSV — id, typ, szczegóły)",
            data=rep.to_csv_string().encode("utf-8-sig"),
            file_name="walidacja_problemy.csv",
            mime="text/csv",
            key="val_csv_dl",
        )
        with st.expander("Pełny raport walidacji (tekst)"):
            st.text(rep.to_text())
            st.download_button(
                "Pobierz raport (.txt)",
                data=rep.to_text(),
                file_name="walidacja_bazy.txt",
                mime="text/plain",
            )
    else:
        st.warning("Brak raportu walidacji — wczytaj bazę ponownie.")


def section_persons(df_std: pd.DataFrame) -> None:
    st.markdown("### Rejestr osobniczy populacji")
    sc.help_expander("Rejestr osobniczy populacji — jak czytać tabelę", hc.SECTION_PERSONS)
    lm = st.session_state.get("line_memberships") or {}
    people = st.session_state.get("people") or {}
    base = df_std.copy()
    if base.columns.duplicated().any():
        base = base.loc[:, ~base.columns.duplicated(keep="first")]
    base["id"] = base["id"].astype(str)
    _p_cols = splt.registry_like_column_order(base.columns)
    base = base[_p_cols]

    def _row_line(pid: str) -> str:
        m = lm.get(pid)
        if m is None:
            return "NA"
        return f"S:{m.sire_founder_id or 'NA'} / D:{m.dam_founder_id or 'NA'}"

    base["linia (sire/dam)"] = base["id"].map(lambda x: _row_line(str(x)))

    search_q = st.text_input(
        "Szybkie wyszukiwanie po ID (pełne lub fragment)",
        value="",
        key="p_id_search",
        placeholder="np. 12345 lub początek numeru",
    )
    q = str(search_q).strip()
    filtered = base

    # Filtr miejsca urodzenia (birth_location).
    bl_opts: list[str] = ["Bez filtra"]
    if "birth_location" in base.columns:
        bl_norm = base["birth_location"].astype(str).str.strip()
        bl_norm = bl_norm.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
        uniq = sorted(set(bl_norm.tolist()) - {"nan", "None"}, key=str.lower)
        if "NA" in uniq:
            uniq = [x for x in uniq if x != "NA"]
            bl_opts = bl_opts + uniq + ["NA"]
        else:
            bl_opts = bl_opts + uniq

    birth_loc_filter = st.selectbox("Filtr miejsca urodzenia (birth_location)", bl_opts, index=0, key="p_birth_loc")
    if birth_loc_filter and birth_loc_filter != "Bez filtra":
        loc_norm = filtered["birth_location"].astype(str).str.strip()
        loc_norm = loc_norm.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
        filtered = filtered.loc[loc_norm == birth_loc_filter].copy()
        st.caption(f"Po filtrze miejsca ur.: **{len(filtered)}** wierszy (z {len(base)}).")

    if q:
        before_n = len(filtered)
        mask = filtered["id"].astype(str).str.contains(q, case=False, na=False, regex=False)
        filtered = filtered.loc[mask].copy()
        st.caption(f"Po filtrze ID: **{len(filtered)}** wierszy (z {before_n}).")

    sort_col = st.selectbox("Sortuj po kolumnie", options=list(filtered.columns), index=0, key="p_sort")
    asc = st.toggle("Rosnąco (A→Z / małe→duże)", value=True, key="p_asc")
    preview_n = st.slider("Liczba wierszy podglądu", 25, 500, 250, 25, key="p_n")
    view = filtered.sort_values(by=[sort_col], ascending=bool(asc)).head(preview_n)
    st.dataframe(view, width="stretch", height=420)

    id_opts = sorted(filtered["id"].astype(str).unique().tolist(), key=sc.id_sort_key)
    if not id_opts:
        st.warning("Brak rekordów pasujących do wyszukiwania — wyczyść pole lub zmień fragment ID.")
        return

    _detail_key = "p_detail_id"
    if _detail_key in st.session_state and st.session_state[_detail_key] not in id_opts:
        del st.session_state[_detail_key]

    with st.expander("Szczegóły osobnika — udział założycieli w genach (founder-stop)", expanded=bool(q)):
        detail_id = st.selectbox("Wybierz ID do podglądu", options=id_opts, key=_detail_key)
        pid = str(detail_id).strip()
        p = people.get(pid) if people else None
        if p is None:
            st.error("Brak danych osobnika w grafie rodowodowym.")
            return
        c1, c2, c3 = st.columns(3)
        c1.metric("Płeć", str(p.sex) if p.sex else "—")
        c2.metric("Linia (plik)", str(p.line) if p.line else "—")
        c3.metric("Rok ur.", str(p.birth_year) if p.birth_year is not None else "—")
        st.caption(f"Ojciec: **{p.father_id or '—'}**  •  Matka: **{p.mother_id or '—'}**")
        mem = lm.get(pid)
        if mem is not None:
            st.caption(
                f"Linie sire/dam: sire → {mem.sire_founder_id or 'NA'} ({mem.sire_steps} kroków); "
                f"dam → {mem.dam_founder_id or 'NA'} ({mem.dam_steps} kroków)."
            )
        comp = FounderContributionComputer(people)
        contribs = comp.contributions_for(pid)
        if not contribs:
            st.info("Brak rozkładu udziałów (np. osobnik poza mapą `people`).")
        else:
            rows = []
            for fid, share in sorted(contribs.items(), key=lambda kv: kv[1], reverse=True):
                fp = people.get(fid)
                fname = (fp.name if fp and fp.name else "") or "—"
                rows.append(
                    {
                        "Założyciel (ID)": fid,
                        "Imię": fname,
                        "Udział": share,
                        "Udział %": round(share * 100.0, 6),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch", height=min(420, 28 + 36 * min(len(rows), 14)))
            st.caption(
                "Udziały sumują się do 100 % w modelu founder-stop (brak ojca lub matki = koniec gałęzi), "
                "spójnie z liczeniem F w aplikacji."
            )


def section_analysis_individual(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Analiza osobnicza: inbred i kompletność")
    st.caption("Graf przodków, F (Wright), kompletność (EG/PCI), linie sire/dam, wspólni przodkowie rodziców.")
    section_individual_pedigree_analysis(df_std, people)


def section_analysis_pairs_and_mating(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Analiza par i optymalizacja kojarzeń")
    st.caption("Pokrewieństwo par rodzicielskich (Φ, R, dekompozycja ścieżek) oraz ranking rekomendowanych kojarzeń.")
    t1, t2 = st.tabs(
        ["Pokrewieństwo par (Φ, R)", "Ranking rekomendowanych kojarzeń"],
    )
    with t1:
        section_pair_kinship_analysis(df_std, people)
    with t2:
        section_mating_ranking(df_std, people)


def section_individual_pedigree_analysis(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Analiza rodowodowa osobnika")
    id_opts = sorted(df_std["id"].astype(str).unique().tolist(), key=sc.id_sort_key)
    if not id_opts:
        st.warning("Brak ID w bazie.")
        return
    pid = st.selectbox("Wybierz ID osobnika", id_opts, key="hub_ind_id")
    lm = st.session_state.get("line_memberships") or {}

    st1, st2, st3, st4, st5 = st.tabs(
        ["1. Pedigree", "2. F (Wright)", "3. Kompletność", "4. Linie sire/dam", "5. Wspólni przodkowie"]
    )

    with st1:
        sc.help_expander("Wizualizacja rodowodu (pedigree) — linie sire / dam", hc.SECTION_PEDIGREE)
        col1, col2, col3 = st.columns(3)
        with col1:
            unbounded = st.checkbox("Bez limitu (do founderów)", value=True, key="hub_rod_ub")
        with col2:
            depth = st.slider("Max pokoleń (gdy limit)", 0, 30, 4, key="hub_rod_d", disabled=unbounded)
        with col3:
            readable = st.checkbox("Tryb czytelny (mniej etykiet)", value=True, key="hub_rod_r")
        if st.button("Generuj graf przodków", type="primary", key="hub_rod_go"):
            if pid not in people:
                st.error("Nieprawidłowe ID.")
            else:
                fig, err = build_pedigree_figure(
                    person_id=str(pid),
                    people=people,
                    unbounded=unbounded,
                    depth=int(depth),
                    readable=readable,
                )
                if err:
                    st.warning(err)
                elif fig is not None:
                    splt.show_matplotlib_figure_in_streamlit(
                        fig,
                        download_filename=f"rodowod_{pid}.png",
                        download_key=f"hub_rod_png_{pid}",
                        width="stretch",
                    )

    with st2:
        sc.help_expander("Inbred F — definicja i wykres diagnostyczny", hc.SECTION_INBRED)
        c1, c2 = st.columns(2)
        with c1:
            unbounded = st.checkbox("Bez limitu (do founderów)", value=True, key="hub_inb_ub")
        with c2:
            depth = st.slider("Max pokoleń (gdy limit)", 0, 30, 4, key="hub_inb_d", disabled=unbounded)
        if st.button("Policz F (Wright)", type="primary", key="hub_inb_calc"):
            if str(pid) not in people:
                st.error("Nieprawidłowe ID.")
            else:
                f_res = wright_inbreeding_F(
                    person_id=str(pid),
                    people=people,
                    max_generations_back=None if unbounded else int(depth),
                )
                st.metric("F (Wright)", f"{f_res.F:.6f}")
                st.caption(
                    f"Ojciec: {f_res.father_id} ({f_res.father_name or '-'}), "
                    f"Matka: {f_res.mother_id} ({f_res.mother_name or '-'}). "
                    f"Użyte pokolenia (ścieżki): {f_res.used_generations}."
                )
                max_trace = min(20, int(f_res.used_generations) if f_res.used_generations else 0)
                depths = list(range(0, max_trace + 1))
                Fs = [
                    wright_inbreeding_F(
                        person_id=str(pid), people=people, max_generations_back=int(d)
                    ).F
                    for d in depths
                ]
                fig, ax = plt.subplots(figsize=(splt.ST_FIG_F_DIAG_W, splt.ST_FIG_F_DIAG_H))
                ax.plot(
                    depths,
                    Fs,
                    marker="o",
                    markersize=4.0,
                    color=sc.THEME.EDGE_PLOT,
                    linewidth=2.0,
                )
                ax.set_title(f"Diagnostyka F vs max pokoleń (ID {pid})", fontsize=splt.ST_FS_TITLE)
                ax.set_xlabel("max pokoleń", fontsize=splt.ST_FS_AXIS)
                ax.set_ylabel("F", fontsize=splt.ST_FS_AXIS)
                ax.tick_params(axis="both", labelsize=splt.ST_FS_TICK)
                ax.grid(True, alpha=0.25)
                splt.show_matplotlib_figure_in_streamlit(
                    fig,
                    download_filename=f"inbred_diag_{pid}.png",
                    download_key=f"hub_inb_png_{pid}",
                )

    with st3:
        st.caption("Kompletność wg poziomów przodków (PCL), EG i PCI — jak w metrykach populacji.")
        if st.button("Przelicz kompletność", key="hub_comp_go"):
            df_c, eg, pci = individual_pcl_dataframe(str(pid), people)
            if df_c.empty:
                st.info("Brak poziomów przodków powyżej 0.")
            else:
                st.metric("EG (pokolenia równoważne)", f"{eg:.4f}")
                st.metric("PCI (średnia PCL po poziomach)", f"{pci:.4f}")
                st.dataframe(df_c, width="stretch", height=min(400, 60 + 28 * len(df_c)))
                fig, ax = plt.subplots(figsize=(splt.ST_FIG_PCL_BAR_W, splt.ST_FIG_PCL_BAR_H))
                ax.bar(df_c["Pokolenie g"].astype(int), df_c["PCL = a_g/2^g"], color=sc.THEME.EDGE_PLOT, alpha=0.85)
                ax.set_xlabel("Pokolenie g", fontsize=splt.ST_FS_AXIS)
                ax.set_ylabel("PCL", fontsize=splt.ST_FS_AXIS)
                ax.set_title("Kompletność per pokolenie (PCL)", fontsize=splt.ST_FS_TITLE)
                ax.tick_params(axis="both", labelsize=splt.ST_FS_TICK)
                ax.grid(True, axis="y", alpha=0.25)
                splt.show_matplotlib_figure_in_streamlit(
                    fig,
                    download_filename=f"kompletnosc_PCL_{pid}.png",
                    download_key=f"hub_pcl_png_{pid}",
                )

    with st4:
        if str(pid) in lm:
            st.markdown("**Linie (sireline / damline)**")
            st.text(sc.fmt_line_block(lm.get(str(pid))))
            per = people.get(str(pid))
            fa = per.father_id if per else None
            mo = per.mother_id if per else None
            c1, c2 = st.columns(2)
            with c1:
                if fa:
                    st.caption("Ojciec")
                    st.text(sc.fmt_line_block(lm.get(str(fa))))
            with c2:
                if mo:
                    st.caption("Matka")
                    st.text(sc.fmt_line_block(lm.get(str(mo))))
        else:
            st.info("Brak danych o liniach — wczytaj bazę ponownie lub sprawdź mapowanie.")

    with st5:
        st.caption(
            "Wspólni przodkowie **ojca i matki** tego osobnika — to przez nich przepływa F "
            "(F = Φ(ojciec, matka)). Widać główne źródła inbredu i liczbę par niezależnych ścieżek."
        )
        per = people.get(str(pid))
        if not per or not per.father_id or not per.mother_id:
            st.warning("Do analizy potrzebna jest pełna para rodziców w bazie.")
        elif st.button("Rozłóż F na wspólnych przodków", key="hub_ibd_go"):
            ex = explain_pair_kinship(
                str(per.father_id), str(per.mother_id), people, max_generations_back=None
            )
            st.metric("Φ(ojciec, matka) = F osobnika", f"{ex.phi_recursive:.6f}")
            st.caption(
                f"Łącznie **{ex.n_path_pairs}** par ścieżek (ojciec→C, matka→C) do wspólnych przodków; "
                f"**{ex.n_distinct_common_ancestors}** różnych węzłów wspólnych."
            )
            if ex.path_discrepancy > 1e-4:
                st.caption(
                    f"Suma surowych wyrazów ścieżkowych ({ex.phi_path_sum_raw:.6f}) różni się od Φ — "
                    f"skalowanie proporcjonalne współczynnik **{ex.path_scale:.4f}** (nakładanie się przepływów genów)."
                )
            rows = []
            for aid, to_phi, raw_v, npair in ex.by_ancestor[:40]:
                ap = people.get(aid)
                rows.append(
                    {
                        "Wspólny przodek": aid,
                        "Imię": (ap.name if ap and ap.name else "—"),
                        "Wkład do Φ": round(to_phi, 8),
                        "% z Φ": round(100.0 * to_phi / ex.phi_recursive, 4) if ex.phi_recursive > 1e-15 else 0.0,
                        "Pary ścieżek": npair,
                        "Suma surowa": round(raw_v, 8),
                    }
                )
            st.dataframe(pd.DataFrame(rows), width="stretch", height=min(420, 60 + 28 * min(len(rows), 12)))
            top_pairs = ex.path_pairs[:24]
            pr = []
            for d in top_pairs:
                pr.append(
                    {
                        "Przodek": d.ancestor_id,
                        "Krawędzie o→p": f"{d.n_edges_a}+{d.n_edges_b}",
                        "Wkład Φ": round(d.contribution_to_phi, 8),
                        "Ścieżka ojciec": "→".join(d.path_a) if d.path_a else "—",
                        "Ścieżka matka": "→".join(d.path_b) if d.path_b else "—",
                    }
                )
            with st.expander("Top ścieżki (szczegóły)", expanded=False):
                st.dataframe(pd.DataFrame(pr), width="stretch", height=min(400, 60 + 26 * min(len(pr), 10)))


def section_pair_kinship_analysis(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Analiza rodowodowa — para rodziców (ojciec × matka)")
    sc.help_expander("Optymalizacja kojarzeń — interpretacja rankingu", hc.SECTION_MATING)
    df_ids = df_std.copy()
    df_ids["id"] = df_ids["id"].astype(str)
    if "sex" in df_ids.columns:
        sx = df_ids["sex"].astype(str).str.strip().str.upper()
        male_opts = sorted(df_ids.loc[sx == "M", "id"].drop_duplicates().tolist(), key=sc.id_sort_key)
        female_opts = sorted(df_ids.loc[sx == "F", "id"].drop_duplicates().tolist(), key=sc.id_sort_key)
    else:
        male_opts, female_opts = [], []
    st.caption(
        "Listy zawierają tylko ID z płcią M / F. Możesz też wpisać numer ID w polu tekstowym (nadpisuje wybór z listy)."
    )
    c0, c1 = st.columns(2)
    with c0:
        pair_ub = st.checkbox("Φ bez limitu pokoleń (wolniejsze)", value=False, key="pair_ub")
    with c1:
        pair_d = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, key="pair_d", disabled=pair_ub)
    kc1, kc2 = st.columns(2)
    with kc1:
        st.markdown("**Ojciec (samiec M)**")
        kin_sire_sel = st.selectbox(
            "Wybór z listy",
            [""] + male_opts,
            key="pair_kin_sire_sel",
            format_func=lambda x: "— wybierz —" if x == "" else str(x),
        )
        kin_sire_txt = st.text_input("Lub wpisz ID", "", key="pair_kin_sire_txt", placeholder="np. 12345")
    with kc2:
        st.markdown("**Matka (samica F)**")
        kin_dam_sel = st.selectbox(
            "Wybór z listy",
            [""] + female_opts,
            key="pair_kin_dam_sel",
            format_func=lambda x: "— wybierz —" if x == "" else str(x),
        )
        kin_dam_txt = st.text_input("Lub wpisz ID", "", key="pair_kin_dam_txt", placeholder="np. 12345")
    sire_id = (kin_sire_txt or "").strip() or (kin_sire_sel or "").strip()
    dam_id = (kin_dam_txt or "").strip() or (kin_dam_sel or "").strip()
    max_back = None if pair_ub else int(pair_d)
    if st.button("Oblicz Φ, R, F potomka i wyjaśnienie", type="primary", key="pair_calc"):
        if not sire_id or not dam_id:
            st.error("Wybierz lub wpisz ID ojca (M) i matki (F).")
        elif sire_id not in people or dam_id not in people:
            st.error("Oba ID muszą istnieć w wczytanej bazie.")
        else:

            def _sx(pid: str) -> str | None:
                p = people.get(pid)
                if not p:
                    return None
                s = (p.sex or "").strip().upper()
                return s if s else None

            sx_s, sx_d = _sx(sire_id), _sx(dam_id)
            if sx_s and sx_s != "M":
                st.error("Pole ojca: w bazie ten osobnik nie jest oznaczony jako M (samiec).")
            elif sx_d and sx_d != "F":
                st.error("Pole matki: w bazie ten osobnik nie jest oznaczony jako F (samica).")
            else:
                try:
                    phi_v, r_v = wright_kinship_phi_and_relationship_R(
                        sire_id, dam_id, people, max_generations_back=max_back
                    )
                    f_pot = wright_offspring_inbreeding_F_from_parents(
                        sire_id, dam_id, people, max_generations_back=max_back
                    )
                    st.session_state["pair_phi"] = phi_v
                    st.session_state["pair_r"] = r_v
                    st.session_state["pair_fpot"] = f_pot
                    st.session_state["pair_explain"] = explain_pair_kinship(
                        sire_id, dam_id, people, max_generations_back=max_back
                    )
                except Exception as e:
                    st.session_state.pop("pair_explain", None)
                    st.error(str(e))

    if st.session_state.get("pair_explain") is not None:
        ex = st.session_state["pair_explain"]
        phi_v = float(st.session_state.get("pair_phi", ex.phi_recursive))
        r_v = float(st.session_state.get("pair_r", 2.0 * phi_v))
        m1, m2, m3 = st.columns(3)
        m1.metric("Φ (coancestry)", f"{phi_v:.6f}")
        m2.metric("R = 2Φ", f"{r_v:.6f}")
        m3.metric("F potomka (ojciec×matka)", f"{float(st.session_state.get('pair_fpot', phi_v)):.6f}")
        warn = close_kinship_note(phi_v)
        if warn:
            st.warning(warn)
        st.markdown("##### Dlaczego ta para ma taki wynik?")
        st.markdown(
            f"- **Φ z rekurencji Wrighta (symetryczne):** {ex.phi_recursive:.6f}.\n"
            f"- **Niezależne pary ścieżek** do wspólnych przodków (liczba kombinacji ścieżek w grafie): **{ex.n_path_pairs}**.\n"
            f"- **Wspólnych węzłów** z niezerowym wkładem (po skalowaniu do Φ): **{ex.n_distinct_common_ancestors}**.\n"
            f"- Kolumna *Wkład do Φ* sumuje się do Φ; *Suma surowa* pokazuje klasyczne wyrazy ścieżkowe "
            f"(mogą sumować się powyżej Φ przy nakładających się drogach genów — stąd skala **{ex.path_scale:.4f}**)."
        )
        rows = []
        for aid, to_phi, raw_v, npair in ex.by_ancestor[:35]:
            ap = people.get(aid)
            rows.append(
                {
                    "Wspólny przodek": aid,
                    "Imię": (ap.name if ap and ap.name else "—"),
                    "Wkład do Φ": round(to_phi, 8),
                    "% z Φ": round(100.0 * to_phi / ex.phi_recursive, 4) if ex.phi_recursive > 1e-15 else 0.0,
                    "Pary ścieżek": npair,
                    "Suma surowa": round(raw_v, 8),
                }
            )
        st.dataframe(pd.DataFrame(rows), width="stretch", height=min(400, 60 + 28 * min(len(rows), 10)))
        top_pairs = ex.path_pairs[:30]
        pr = []
        for d in top_pairs:
            pr.append(
                {
                    "Przodek": d.ancestor_id,
                    "krawędzie (ojciec/matka)": f"{d.n_edges_a}+{d.n_edges_b}",
                    "Wkład Φ": round(d.contribution_to_phi, 8),
                    "Ścieżka (ojciec)": "→".join(d.path_a) if d.path_a else "·",
                    "Ścieżka (matka)": "→".join(d.path_b) if d.path_b else "·",
                }
            )
        with st.expander("Najsilniejsze pary ścieżek", expanded=True):
            st.dataframe(pd.DataFrame(pr), width="stretch", height=min(420, 60 + 26 * min(len(pr), 12)))


def section_mating_ranking(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Optymalizacja kojarzeń (ranking par, minimalne F potomka)")
    sc.help_expander("Optymalizacja kojarzeń — interpretacja rankingu", hc.SECTION_MATING)
    top_n_cfg = int(CFG.mating_ranking_top_n)
    age_limit_cfg = int(CFG.mating_age_limit_years)
    st.caption(
        f"Filtr wieku: ostatnie {age_limit_cfg} lat. Ranking: do {top_n_cfg} par (najmniejsze Φ = F potomka), "
        "R = 2Φ; każdy osobnik w liście wynikowej max 3×. Limity kandydatów ograniczają czas obliczeń."
    )

    mating_unbounded = st.checkbox("F bez limitu pokoleń (wolniejsze)", value=False, key="mat_ub")
    mating_depth = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, key="mat_d", disabled=mating_unbounded)
    c1, c2 = st.columns(2)
    with c1:
        male_limit = st.number_input("Max samców (M)", 1, 500, int(CFG.mating_default_male_limit))
    with c2:
        female_limit = st.number_input("Max samic (F)", 1, 500, int(CFG.mating_default_female_limit))

    cy = datetime.now().year
    cutoff = cy - age_limit_cfg
    st.caption(f"Rok odniesienia {cy}: używane osobniki z birth_year ≥ {cutoff}.")

    # Filtr miejsca urodzenia (birth_location).
    bl_opts: list[str] = ["Bez filtra"]
    if "birth_location" in df_std.columns:
        bl_norm = df_std["birth_location"].astype(str).str.strip()
        bl_norm = bl_norm.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
        uniq = sorted(set(bl_norm.tolist()) - {"nan", "None"}, key=str.lower)
        if "NA" in uniq:
            uniq = [x for x in uniq if x != "NA"]
            bl_opts = bl_opts + uniq + ["NA"]
        else:
            bl_opts = bl_opts + uniq

    birth_loc_filter = st.selectbox("Filtr miejsca urodzenia (birth_location)", bl_opts, index=0)

    if st.button(f"Oblicz ranking kojarzeń (TOP {top_n_cfg})", type="primary", key="mat_go"):
        df_tmp = df_std.copy()
        df_tmp["id"] = df_tmp["id"].astype(str)
        df_tmp["birth_year_num"] = pd.to_numeric(df_tmp.get("birth_year"), errors="coerce")
        ids_set = set(people.keys())
        df_tmp = df_tmp[df_tmp["id"].isin(ids_set)]
        df_tmp = df_tmp[df_tmp["sex"].isin(["M", "F"])]
        df_tmp = df_tmp[df_tmp["birth_year_num"].notna()]
        df_tmp = df_tmp[df_tmp["birth_year_num"] >= float(cutoff)]

        if birth_loc_filter and birth_loc_filter != "Bez filtra":
            try:
                loc_norm = df_tmp["birth_location"].astype(str).str.strip()
                loc_norm = loc_norm.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
                df_tmp = df_tmp[loc_norm == birth_loc_filter]
            except Exception:
                pass

        males_df = df_tmp[df_tmp["sex"] == "M"].sort_values("birth_year_num", ascending=False)
        females_df = df_tmp[df_tmp["sex"] == "F"].sort_values("birth_year_num", ascending=False)
        males = males_df["id"].tolist()[: int(male_limit)]
        females = females_df["id"].tolist()[: int(female_limit)]
        pairs = [(s, d) for s in males for d in females]
        if not pairs:
            st.warning("Brak kandydatów po filtrze wieku.")
            st.session_state.pop("mating_ranking_text", None)
            st.session_state.pop("mating_phi_csv", None)
            return
        max_back = None if mating_unbounded else int(mating_depth)
        with st.spinner(f"Liczenie {len(pairs)} par…"):
            Fs = batch_offspring_inbreeding_F_from_parent_pairs(pairs, people, max_generations_back=max_back)
        ranked_all = sorted(zip(Fs, pairs), key=lambda x: x[0])
        use_count: dict[str, int] = {}
        top_n = top_n_cfg
        max_uses = 3
        ranked: list[tuple[float, tuple[str, str]]] = []
        for fv, (sire_id, dam_id) in ranked_all:
            if len(ranked) >= top_n:
                break
            if use_count.get(sire_id, 0) >= max_uses or use_count.get(dam_id, 0) >= max_uses:
                continue
            ranked.append((fv, (sire_id, dam_id)))
            use_count[sire_id] = use_count.get(sire_id, 0) + 1
            use_count[dam_id] = use_count.get(dam_id, 0) + 1
        lines = [
            f"Wybrano {len(ranked)} par (cel do {top_n}; max {max_uses}× ten sam ID w liście).",
            "",
            "Φ = kinship (współzgodność) sire×dam = F potomka; R = 2Φ.",
            "",
        ]
        for i, (fv, (sire_id, dam_id)) in enumerate(ranked, 1):
            rv = 2.0 * fv
            sn = getattr(people.get(sire_id), "name", None)
            dn = getattr(people.get(dam_id), "name", None)
            lines.append(
                f"{i}. Φ=F={fv:.6f}  R={rv:.6f} | sire={sire_id} ({sn or '-'}) × dam={dam_id} ({dn or '-'})"
            )
        st.session_state["mating_ranking_text"] = "\n".join(lines)
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        nf = len(females)
        w.writerow(["sire_id"] + [str(x) for x in females])
        for i, mid in enumerate(males):
            row = [str(mid)] + [f"{Fs[i * nf + j]:.10g}" for j in range(nf)]
            w.writerow(row)
        st.session_state["mating_phi_csv"] = buf.getvalue()

    if st.session_state.get("mating_ranking_text"):
        st.text(st.session_state["mating_ranking_text"])
    if st.session_state.get("mating_phi_csv"):
        st.download_button(
            "Pobierz macierz Φ (CSV, sire × dam)",
            data=st.session_state["mating_phi_csv"].encode("utf-8"),
            file_name="macierz_phi_kojarzenia.csv",
            mime="text/csv",
            key="mat_phi_dl",
        )


def section_population(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Parametry populacyjne i genetyka grupy")
    _ph = hc.POPULATION_METRIC_HELP
    _ch = hc.POPULATION_CONTROL_HELP
    sc.help_expander("Krótki opis sekcji", hc.SECTION_POPULATION, expanded=False)
    verbose = st.checkbox(
        "Rozwijaj domyślnie „Interpretacja” pod wykresami",
        value=True,
        key="st_verbose_pop_captions",
        help=_ch["verbose"],
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        pop_ub = st.checkbox(
            "F populacji: bez limitu (do founderów)",
            value=False,
            key="pop_ub",
            help=_ch["f_ub"],
        )
    with c2:
        pop_depth = st.number_input(
            "Max pokoleń (gdy limit)",
            0,
            30,
            4,
            disabled=pop_ub,
            key="pop_dep",
            help=_ch["f_dep"],
        )
    with c3:
        act_years = st.number_input(
            "Kohorta aktywna: lat wstecz (rok ur.)",
            min_value=5,
            max_value=60,
            value=20,
            key="pop_act_y",
            help=_ch["act_y"],
        )
    c4, c5 = st.columns(2)
    with c4:
        vuln_recent = st.number_input(
            "Ryzyko linii: urodzenia z ostatnich N lat",
            min_value=5,
            max_value=80,
            value=30,
            key="pop_vuln_r",
            help=_ch["vuln_r"],
        )
    with c5:
        vuln_active = st.number_input(
            "Ryzyko linii: okno kohorty aktywnych (lat)",
            min_value=5,
            max_value=60,
            value=20,
            key="pop_vuln_a",
            help=_ch["vuln_a"],
        )

    max_gen = None if pop_ub else int(pop_depth)

    df_use = df_std.copy()
    df_use["id"] = df_use["id"].astype(str)
    df_use = df_use[df_use["id"] != TEST_ID].reset_index(drop=True)

    with st.spinner("Liczenie parametrów populacyjnych, kohort, okresów…"):
        stats = compute_population_genetics_stats(
            df_std=df_std,
            people=people,
            max_generations_back=max_gen,
            calc_f=True,
            calc_completeness=True,
            calc_founders=True,
            calc_lines=True,
        )
        gi_data = compute_gi_and_family_data(df_use, people)

    mk_phi, mk_r, mk_note = None, None, ""
    with st.spinner("Średni kinship (Φ po parach)…"):
        try:
            _ids_pop = df_use["id"].astype(str).tolist()
            mk_phi, mk_r, mk_note = mean_kinship_pairwise(
                people,
                _ids_pop,
                max_generations_back=max_gen,
            )
        except Exception:
            mk_phi, mk_r, mk_note = None, None, "nie udało się policzyć"
        ria_pct = global_ria_percent(stats.f_values)
        f_ge_n = len(stats.founder_contributions or {})
        pct_inc_par = pct_individuals_incomplete_parents(df_use)
        pct_slot = pct_missing_parent_slots(df_use)
        act = summarize_active_cohort(df_std, window_years=int(act_years))
        p5, p10, _n_fa = sire_offspring_concentration(df_std)
        vuln_df = line_vulnerability_table(
            df_std,
            recent_years=int(vuln_recent),
            active_window=int(vuln_active),
        )
        periods_df = compare_birth_periods(df_std, people, max_generations_back=max_gen)

    with st.spinner("Liczenie F dla trendów w czasie (średnie F / RIA wg roku)…"):
        dfc_trend, warn_trend = splt.prepare_inbreeding_trends_dataframe(df_use, people, max_gen)

    gi_all = gi_data.get("gi_all")
    fam_sizes: list = gi_data.get("family_sizes") or []
    fam_n = len(fam_sizes)
    fam_mean = float(sum(fam_sizes)) / float(fam_n) if fam_n else None
    ne_est = splt.estimate_ne_from_f_trend(
        df_use, people, gi_all, max_gen, dfc_precomputed=dfc_trend
    )
    _ne_disp = f"{ne_est:.1f}" if ne_est is not None else "—"
    mk_help = (mk_note[:480] + "…") if mk_note and len(mk_note) > 480 else mk_note
    _mk_h = mk_help or "Średnia Φ po parach i≠j; przy dużym n — losowa próba osobników."
    _conc_help = _ph["conc"] + (f" Potomstwo z znanym ojcem: n = {_n_fa}." if _n_fa else "")

    st.markdown("#### Dashboard")
    _t = sc.THEME

    sc.population_dashboard_group_header(
        "Populacja, kohorta i reprodukcja",
        "Wielkość zbioru, kohorta wg ustawień lat, struktura płci oraz reproduktorzy globalnie i w kohordzie.",
        accent=_t.EDGE_PLOT,
        background=_t.PANEL_BG2,
    )
    _g1a = st.columns(3)
    with _g1a[0]:
        sc.population_dashboard_metric(
            "n (bez test ID)",
            str(stats.n),
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["n"],
        )
    with _g1a[1]:
        sc.population_dashboard_metric(
            f"Kohorta ({act_years} lat): n",
            str(act.n_total),
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["coh_n"],
        )
    with _g1a[2]:
        sc.population_dashboard_metric(
            "Kohorta: M / F",
            f"{act.n_males} / {act.n_females}",
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["coh_mf"],
        )
    _g1b = st.columns(3)
    with _g1b[0]:
        sc.population_dashboard_metric(
            "Założyciele (rek. z ≥1 brakiem)",
            str(stats.n_founders_any_missing_parent),
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["founders_n"],
        )
    with _g1b[1]:
        sc.population_dashboard_metric(
            "Reprod. (unik. ojc./mat.)",
            f"{act.n_reproducer_males} / {act.n_reproducer_females}",
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["repr_all"],
        )
    with _g1b[2]:
        sc.population_dashboard_metric(
            "Reprod. w koh. (M / F)",
            f"{act.n_reproducer_males_in_cohort} / {act.n_reproducer_females_in_cohort}",
            accent=_t.EDGE_PLOT,
            panel_bg=_t.PANEL_BG2,
            help_text=_ph["repr_coh"],
        )

    sc.population_dashboard_group_header(
        "Inbred i średnie pokrewieństwo",
        "Średni współczynnik F, udział inbrednych (RIA), mean kinship Φ̄ oraz średnie R = 2Φ̄.",
        accent=_t.ACCENT,
        background=_t.ENTRY_BG,
    )
    _g2 = st.columns(4)
    with _g2[0]:
        sc.population_dashboard_metric(
            "Średnie F",
            f"{stats.inbreeding.mean_F:.4f}",
            accent=_t.ACCENT,
            panel_bg=_t.ENTRY_BG,
            help_text=_ph["mean_f"],
        )
    with _g2[1]:
        sc.population_dashboard_metric(
            "RIA % (F > 0)",
            f"{ria_pct:.1f}",
            accent=_t.ACCENT,
            panel_bg=_t.ENTRY_BG,
            help_text=_ph["ria"],
        )
    with _g2[2]:
        sc.population_dashboard_metric(
            "Mean kinship Φ̄",
            f"{mk_phi:.6f}" if mk_phi is not None else "—",
            accent=_t.ACCENT,
            panel_bg=_t.ENTRY_BG,
            help_text=_mk_h,
        )
    with _g2[3]:
        sc.population_dashboard_metric(
            "Średnie R (2Φ̄)",
            f"{mk_r:.6f}" if mk_r is not None else "—",
            accent=_t.ACCENT,
            panel_bg=_t.ENTRY_BG,
            help_text=_mk_h,
        )

    sc.population_dashboard_group_header(
        "Efektywna różnorodność założycielska",
        "Liczby efektywne z rozkładu wkładów (f_e, f_a), liczba węzłów f_ge oraz orientacyjne N_e.",
        accent=_t.LINK,
        background=_t.PANEL_BG,
    )
    _g3 = st.columns(4)
    with _g3[0]:
        sc.population_dashboard_metric(
            "f_e",
            f"{stats.founders.f_e:.4f}",
            accent=_t.LINK,
            panel_bg=_t.PANEL_BG,
            help_text=_ph["fe"],
        )
    with _g3[1]:
        sc.population_dashboard_metric(
            "f_a",
            f"{stats.founders.f_a:.4f}",
            accent=_t.LINK,
            panel_bg=_t.PANEL_BG,
            help_text=_ph["fa"],
        )
    with _g3[2]:
        sc.population_dashboard_metric(
            "f_ge",
            str(f_ge_n),
            accent=_t.LINK,
            panel_bg=_t.PANEL_BG,
            help_text=_ph["fge"],
        )
    with _g3[3]:
        sc.population_dashboard_metric(
            "N_e (orient.)",
            _ne_disp,
            accent=_t.LINK,
            panel_bg=_t.PANEL_BG,
            help_text=_ph["ne"],
        )

    sc.population_dashboard_group_header(
        "Kompletność zapisu rodowodu",
        "Braki po stronie rodziców, puste sloty w modelu 2n oraz średnia miara głębokości EG.",
        accent=_t.COMPLETENESS_ACCENT,
        background=_t.TREE_BG,
    )
    _g4 = st.columns(3)
    with _g4[0]:
        sc.population_dashboard_metric(
            "% rek. z brakiem ojca lub matki",
            f"{pct_inc_par:.1f}%",
            accent=_t.COMPLETENESS_ACCENT,
            panel_bg=_t.TREE_BG,
            help_text=_ph["pct_par"],
        )
    with _g4[1]:
        sc.population_dashboard_metric(
            "% pustych slotów (2n)",
            f"{pct_slot:.1f}%",
            accent=_t.COMPLETENESS_ACCENT,
            panel_bg=_t.TREE_BG,
            help_text=_ph["pct_slot"],
        )
    with _g4[2]:
        sc.population_dashboard_metric(
            "Średni EG",
            f"{stats.completeness.mean_EG:.4f}",
            accent=_t.COMPLETENESS_ACCENT,
            panel_bg=_t.TREE_BG,
            help_text=_ph["eg"],
        )

    sc.population_dashboard_group_header(
        "Odstęp pokoleniowy i koncentracja kojarzeń",
        "Średni interwał pokoleniowy (GI) oraz koncentracja najczęstszych ojców u potomstwa z znanym ojcem.",
        accent=_t.EDGE_PLOT,
        background=_t.TAB_BG,
    )
    _g5 = st.columns(2)
    with _g5[0]:
        sc.population_dashboard_metric(
            "Średni GI (lat)",
            f"{gi_all:.2f}" if gi_all is not None else "—",
            accent=_t.EDGE_PLOT,
            panel_bg=_t.TAB_BG,
            help_text=_ph["gi"],
        )
    with _g5[1]:
        sc.population_dashboard_metric(
            "Konc. ojców top5 / top10",
            f"{p5:.1f}% / {p10:.1f}%",
            accent=_t.EDGE_PLOT,
            panel_bg=_t.TAB_BG,
            help_text=_conc_help,
        )

    gi_txt = f"{gi_all:.2f} lat" if gi_all is not None else "—"
    fam_txt = f"{fam_n} rodzin, śr. {fam_mean:.2f}" if fam_n else "—"
    st.caption(f"Linie: {stats.line_counts} · **GI** (śr.): {gi_txt} · **Rodziny pełne**: {fam_txt}")

    _pop_short = (
        "Okresy, ryzyko, reprodukcja",
        "Urodzenia: płeć",
        "Urodzenia: linie",
        "Stosunek F/M",
        "Kompletność: płeć",
        "Kompletność: linie",
        "Histogram F",
        "Założyciele (p_i)",
        "GI średni",
        "GI w czasie",
        "Rodziny rodzeństwa",
        "Trend F/RIA: płeć",
        "Trend F/RIA: linie",
        "PCL vs MG",
    )
    if "pop_chart_idx" not in st.session_state:
        st.session_state.pop_chart_idx = 0
    _pop_clicked: int | None = None
    _sel_ui = max(0, min(len(_pop_short) - 1, int(st.session_state.pop_chart_idx)))
    st.markdown("#### Wykresy")
    st.markdown(sc.population_viz_tabs_css(), unsafe_allow_html=True)
    # Bez st.rerun() przy wyborze wykresu — wymuszony rerun zrywał MediaFileStorage („Missing file …png”).
    _viz_tabs = st.tabs(
        [g[0] for g in _SECTION_POP_CHART_TAB_GROUPS],
        key="pop_chart_viz_tabs",
        on_change=_on_pop_chart_viz_tab_changed,
    )
    for _ti, (_tab_title, _indices) in enumerate(_SECTION_POP_CHART_TAB_GROUPS):
        with _viz_tabs[_ti]:
            _row = st.columns(len(_indices))
            for _ci, _pidx in enumerate(_indices):
                with _row[_ci]:
                    if st.button(
                        _pop_short[_pidx],
                        key=f"pop_chart_btn_{_pidx}",
                        use_container_width=True,
                        type="primary" if _sel_ui == _pidx else "secondary",
                    ):
                        _pop_clicked = _pidx
    if _pop_clicked is not None:
        st.session_state.pop_chart_idx = _pop_clicked
    sel = max(0, min(len(_pop_short) - 1, int(st.session_state.pop_chart_idx)))
    st.caption(f"**Wyświetlany wykres:** {_pop_short[sel]}")

    if sel == 0:
        st.caption(
            "Trzy przedziały urodzeń (1950–1980, 1981–2000, 2001–dziś), ranking ryzyka LB/LC, reproduktorzy i udział linii."
        )
        st.markdown("**Porównanie okresów**")
        st.dataframe(periods_df, width="stretch", hide_index=True)
        st.markdown("**Ranking ryzyka utraty linii (LB / LC)**")
        if vuln_df is not None and not vuln_df.empty:
            st.dataframe(vuln_df, width="stretch", hide_index=True)
        else:
            st.info("Brak danych do tabeli ryzyka linii.")
        st.markdown("**Trend liczby efektywnych reproduktorów (unikalni rodzice wg dekady urodzenia potomstwa)**")
        fig_rp = splt.fig_reproducers_by_decade(df_std)
        splt.show_matplotlib_figure_in_streamlit(
            fig_rp,
            download_filename="pop_reproduktorzy_dekady.png",
            download_key="pop_dl_reproducers",
        )
        st.markdown("**Udział linii w czasie (skumulowane 100 % w dekadzie)**")
        fig_ls = splt.fig_line_share_percent_stacked(df_std)
        splt.show_matplotlib_figure_in_streamlit(
            fig_ls,
            download_filename="pop_udzial_linii_dekady.png",
            download_key="pop_dl_line_share",
        )

    elif sel == 1:
        st.caption("Liczba urodzeń w dekadach (1881–obecny rok), podział M/F.")
        sc.help_expander("Interpretacja: Urodzenia wg płci", hc.CHART_BIRTH_SEX, expanded=verbose)
        fig = splt.fig_birth_decades_sex(df_std)
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_urodzenia_dekady_plec.png",
            download_key="pop_dl_birth_sex",
        )

    elif sel == 2:
        st.caption("Urodzenia w dekadach wg linii (LB vs LC).")
        sc.help_expander("Interpretacja: Urodzenia wg linii", hc.CHART_BIRTH_LINE, expanded=verbose)
        fig = splt.fig_birth_decades_line(df_std)
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_urodzenia_dekady_linie.png",
            download_key="pop_dl_birth_line",
        )

    elif sel == 3:
        st.caption("Stosunek F/M w dekadach od 1900.")
        sc.help_expander("Interpretacja: Female/Male ratio", hc.CHART_FM_RATIO, expanded=verbose)
        fig = splt.fig_female_male_ratio(df_std)
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_stosunek_F_M.png",
            download_key="pop_dl_fm_ratio",
        )

    elif sel == 4:
        st.caption("Średnie MG, CG, EG wg płci.")
        sc.help_expander("Interpretacja: Kompletność (MG/CG/EG) wg płci", hc.CHART_COMP_SEX, expanded=verbose)
        fc, _ = splt.fig_completeness_sex_line(df_std, people)
        splt.show_matplotlib_figure_in_streamlit(
            fc,
            download_filename="pop_kompletnosc_plec_MGCGEG.png",
            download_key="pop_dl_comp_sex",
        )

    elif sel == 5:
        st.caption("Średnie MG, CG, EG wg linii LB/LC/NA.")
        sc.help_expander("Interpretacja: Kompletność wg linii", hc.CHART_COMP_LINE, expanded=verbose)
        _, fl = splt.fig_completeness_sex_line(df_std, people)
        splt.show_matplotlib_figure_in_streamlit(
            fl,
            download_filename="pop_kompletnosc_linie_MGCGEG.png",
            download_key="pop_dl_comp_line",
        )

    elif sel == 6:
        st.caption("Histogram F w populacji (przy wybranym limicie pokoleń).")
        sc.help_expander("Interpretacja: rozkład F", hc.CHART_HIST_F, expanded=verbose)
        fig = splt.fig_histogram_f(stats.f_values or [])
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_histogram_F_Wright.png",
            download_key="pop_dl_hist_f",
        )

    elif sel == 7:
        st.caption("Top 20 wkładu genetycznego założycieli (p_i).")
        sc.help_expander("Interpretacja: założyciele p_i", hc.CHART_FOUNDERS_PI, expanded=verbose)
        fig = splt.fig_founder_contributions(stats.founder_contributions or {}, people)
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_zalozyciele_pi_top.png",
            download_key="pop_dl_founders_pi",
        )

    elif sel == 8:
        st.caption("Średni odstęp międzypokoleniowy (GI) — ojciec/matka vs syn/córka.")
        sc.help_expander("Interpretacja: GI (średni)", hc.CHART_GI_BAR, expanded=verbose)
        fig_gi = splt.fig_gi_mean_bar(gi_data)
        splt.show_matplotlib_figure_in_streamlit(
            fig_gi,
            download_filename="pop_GI_sredni.png",
            download_key="pop_dl_gi_bar",
        )

    elif sel == 9:
        st.caption("Trend średniego GI w dekadach urodzenia potomstwa.")
        sc.help_expander("Interpretacja: GI trend", hc.CHART_GI_TREND, expanded=verbose)
        fig_tr = splt.fig_gi_trend_decades(gi_data)
        splt.show_matplotlib_figure_in_streamlit(
            fig_tr,
            download_filename="pop_GI_trend_dekady.png",
            download_key="pop_dl_gi_trend",
        )

    elif sel == 10:
        st.caption("Histogram wielkości rodzin pełnego rodzeństwa (ta sama para rodziców).")
        sc.help_expander("Interpretacja: rodziny pełnego rodzeństwa", hc.CHART_FAMILY, expanded=verbose)
        fig_fam = splt.fig_family_full_siblings(fam_sizes)
        splt.show_matplotlib_figure_in_streamlit(
            fig_fam,
            download_filename="pop_rodziny_pelne_rodzenstwo.png",
            download_key="pop_dl_families",
        )

    elif sel == 11:
        st.caption("Średnie F oraz RIA (% z F>0) w roku urodzenia — wg płci (F liczone raz na wejściu do Populacja).")
        sc.help_expander("Interpretacja: trendy F i RIA wg płci", hc.CHART_INBRED_TP_SEX, expanded=verbose)
        fig_sex, warn_sex = splt.fig_inbreeding_year_trends_sex(
            df_use, people, max_gen, dfc_precomputed=dfc_trend, trend_warn=warn_trend
        )
        if warn_sex:
            st.warning(warn_sex)
        splt.show_matplotlib_figure_in_streamlit(
            fig_sex,
            download_filename="pop_inbred_trend_plec_RIA.png",
            download_key="pop_dl_inbred_sex",
        )

    elif sel == 12:
        st.caption("Średnie F oraz RIA w roku urodzenia — wg linii LB/LC/NA.")
        sc.help_expander("Interpretacja: trendy F i RIA wg linii", hc.CHART_INBRED_TP_LINE, expanded=verbose)
        fig_ln, warn_ln = splt.fig_inbreeding_year_trends_line(
            df_use, people, max_gen, dfc_precomputed=dfc_trend, trend_warn=warn_trend
        )
        if warn_ln:
            st.warning(warn_ln)
        splt.show_matplotlib_figure_in_streamlit(
            fig_ln,
            download_filename="pop_inbred_trend_linie_RIA.png",
            download_key="pop_dl_inbred_line",
        )

    elif sel == 13:
        st.caption("PCL_max (a_MG/2^MG) w funkcji MG: Ancestors (ANC) vs Reference Population (RP).")

        # Pamiętaj: ten wykres jest kosztowny na dużych bazach.
        MAX_RP_IDS = 160
        MAX_ANC_IDS = 450

        # RP: kohorta aktywna (jak w poprzednich metrykach) => birth_year >= birth_year_min.
        cy = int(act.reference_year)
        lo = int(act.birth_year_min)

        def _parse_year(v: object) -> int | None:
            if v is None:
                return None
            try:
                if isinstance(v, float) and v != v:
                    return None
            except Exception:
                pass
            try:
                y = int(float(v))
            except Exception:
                return None
            if y < 1800 or y > cy + 1:
                return None
            return y

        df_rp = df_std.copy()
        df_rp["id"] = df_rp["id"].astype(str)
        df_rp = df_rp[df_rp["id"] != TEST_ID].reset_index(drop=True)
        if "birth_year" not in df_rp.columns:
            st.info("Brak kolumny `birth_year` — nie da się zdefiniować RP.")
            st.stop()

        df_rp["_y"] = df_rp["birth_year"].map(_parse_year)
        df_rp = df_rp[df_rp["_y"].notna() & (df_rp["_y"] >= lo)]
        rp_ids_all = sorted(df_rp["id"].astype(str).unique().tolist(), key=sc.id_sort_key)
        if not rp_ids_all:
            st.info("Brak osób w RP (kohorcie aktywnej) dla bieżących ustawień.")
            st.stop()

        rp_ids = rp_ids_all
        rp_note = ""
        if len(rp_ids_all) > MAX_RP_IDS:
            rp_ids = rp_ids_all[:MAX_RP_IDS]
            rp_note = f" (z próby {MAX_RP_IDS} z {len(rp_ids_all)})"

        # ANC: unia przodków wszystkich RP (tylko identyfikatory obecne w `people`).
        anc_ids_set: set[str] = set()
        with st.spinner("Liczenie MG i kompletności dla ANC/RP…"):
            for pid in rp_ids:
                levels = get_ancestor_levels_unbounded(person_id=str(pid), people=people)
                for aid, lvl in levels.items():
                    if lvl is None:
                        continue
                    try:
                        g = int(lvl)
                    except Exception:
                        continue
                    if g <= 0:
                        continue
                    if aid in people:
                        anc_ids_set.add(str(aid))

            anc_ids_all = sorted(anc_ids_set, key=sc.id_sort_key)
            if anc_ids_all:
                anc_ids = anc_ids_all
            else:
                anc_ids = []

            anc_note = ""
            if len(anc_ids_all) > MAX_ANC_IDS:
                anc_ids = anc_ids_all[:MAX_ANC_IDS]
                anc_note = f" (z próby {MAX_ANC_IDS} z {len(anc_ids_all)})"

            pcl_mg_cache: dict[str, tuple[int, float]] = {}

            def _pcl_max_and_mg(pid: str) -> tuple[int, float]:
                if pid in pcl_mg_cache:
                    return pcl_mg_cache[pid]
                levels_u = get_ancestor_levels_unbounded(person_id=str(pid), people=people)
                by_gen: dict[int, int] = {}
                for _aid, lvl in levels_u.items():
                    if lvl is None:
                        continue
                    try:
                        g = int(lvl)
                    except Exception:
                        continue
                    if g <= 0:
                        continue
                    by_gen[g] = by_gen.get(g, 0) + 1
                if not by_gen:
                    pcl_mg_cache[pid] = (0, 0.0)
                    return 0, 0.0
                mg = int(max(by_gen.keys()))
                a_mg = float(by_gen.get(mg, 0))
                pcl_max = a_mg / float(2**mg) if mg > 0 else 0.0
                pcl_mg_cache[pid] = (mg, pcl_max)
                return mg, pcl_max

            rp_rows = []
            for pid in rp_ids:
                mg, pcl_max = _pcl_max_and_mg(str(pid))
                if mg > 0:
                    rp_rows.append({"MG": mg, "PCL_max": pcl_max, "Grupa": "RP (horses)"})

            anc_rows = []
            for pid in anc_ids:
                mg, pcl_max = _pcl_max_and_mg(str(pid))
                if mg > 0:
                    anc_rows.append({"MG": mg, "PCL_max": pcl_max, "Grupa": "ANC (ancestors)"})

        if not rp_rows and not anc_rows:
            st.info("Brak danych do wykresu PCL_max vs MG (MG=0 dla wszystkich).")
            st.stop()

        df_plot = pd.DataFrame(rp_rows + anc_rows)
        st.caption(f"RP={len(rp_rows)} wykresowych koni{rp_note}; ANC={len(anc_rows)} przodków{anc_note}.")

        colors_map = {
            "ANC (ancestors)": sc.THEME.BUTTON_BG,
            "RP (horses)": sc.THEME.BUTTON_BG2,
        }

        fig, ax = plt.subplots(figsize=(splt.ST_FIG_SCATTER_W, splt.ST_FIG_SCATTER_H))
        for grp, sub in df_plot.groupby("Grupa"):
            c = colors_map.get(grp, sc.THEME.EDGE_PLOT)
            ax.scatter(sub["MG"], sub["PCL_max"], s=28, alpha=0.45, color=c, label=grp)
            by_mg = sub.groupby("MG")["PCL_max"].mean().sort_index()
            ax.plot(by_mg.index.tolist(), by_mg.values.tolist(), color=c, linewidth=2.0, alpha=0.9)

        ax.set_title("PCL_max (a_MG/2^MG) względem MG — ANC vs RP", fontsize=splt.ST_FS_TITLE)
        ax.set_xlabel("MG (maksymalna liczba prześledzonych pokoleń)", fontsize=splt.ST_FS_AXIS)
        ax.set_ylabel("PCL_max = a_MG / 2^MG", fontsize=splt.ST_FS_AXIS)
        ax.set_ylim(0, 1.05)
        ax.grid(True, alpha=0.25)
        ax.tick_params(axis="both", labelsize=splt.ST_FS_TICK)
        ax.legend(loc="best", fontsize=splt.ST_FS_TICK)
        splt.show_matplotlib_figure_in_streamlit(
            fig,
            download_filename="pop_PCLmax_vs_MG_ANC_RP.png",
            download_key="pop_dl_pcl_scatter",
        )


def section_reports() -> None:
    st.markdown("### Raporty i eksport wyników")
    sc.help_expander("Raporty — co zawierają", hc.SECTION_REPORTS)
    st.caption("Podgląd poniżej — pobierz raport jako **.txt** lub **.docx**. Wykresy z sekcji populacji możesz zapisać osobno (**Pobierz wykres PNG**).")
    df_std = st.session_state.get("df_std")
    people = st.session_state.get("people")
    rep = st.session_state.get("validation_report")
    lines = ["WisentPedigree Pro+ — raport (Streamlit)", "", f"Źródło danych: {st.session_state.get('source', '-')}", ""]
    if rep is not None:
        lines.append("=== Walidacja ===")
        lines.append(rep.to_text())
        lines.append("")
    if df_std is not None and people:
        try:
            stats = compute_population_genetics_stats(
                df_std=df_std,
                people=people,  # type: ignore[arg-type]
                max_generations_back=4,
                calc_f=True,
                calc_completeness=True,
                calc_founders=True,
                calc_lines=True,
            )
            lines.append("=== Populacja (skrót) ===")
            lines.append(f"n={stats.n}, mean F={stats.inbreeding.mean_F:.6f}, mean PCI={stats.completeness.mean_PCI:.4f}")
            lines.append(f"f_e={stats.founders.f_e:.4f}, f_a={stats.founders.f_a:.4f}")
            lines.append(
                f"LB={stats.line_counts.get('LB', 0)}, LC={stats.line_counts.get('LC', 0)}, NA={stats.line_counts.get('NA', 0)}"
            )

            # Mean kinship (skrót w raporcie tekstowym).
            try:
                id_list = [str(x) for x in df_std["id"].tolist()]
                mk_phi, mk_r, mk_note = mean_kinship_pairwise(
                    people,  # type: ignore[arg-type]
                    id_list,
                    max_generations_back=4,
                )
                if mk_phi is not None and mk_r is not None:
                    lines.append(f"mean kinship: Φ={mk_phi:.6f}, R={mk_r:.6f}")
                    if mk_note:
                        lines.append(f"mean kinship — uwaga: {mk_note}")
            except Exception:
                pass

            # GI i rodziny pełnego rodzeństwa.
            try:
                gi_data = compute_gi_and_family_data(df_std, people)
                gi_bits: list[str] = []
                if gi_data.get("gi_all") is not None:
                    gi_bits.append(f"GI={float(gi_data['gi_all']):.2f} lat")
                if gi_data.get("gi_fs") is not None:
                    gi_bits.append(f"O->S={float(gi_data['gi_fs']):.2f}")
                if gi_data.get("gi_fd") is not None:
                    gi_bits.append(f"O->C={float(gi_data['gi_fd']):.2f}")
                if gi_data.get("gi_ms") is not None:
                    gi_bits.append(f"M->S={float(gi_data['gi_ms']):.2f}")
                if gi_data.get("gi_md") is not None:
                    gi_bits.append(f"M->C={float(gi_data['gi_md']):.2f}")
                if gi_bits:
                    lines.append("GI: " + ", ".join(gi_bits))
                fam = gi_data.get("family_sizes") or []
                if fam:
                    lines.append(
                        f"rodziny pełnego rodzeństwa: n={len(fam)}, średnia wielkość={float(sum(fam))/float(len(fam)):.2f}"
                    )
            except Exception:
                pass

            # Top miejsc urodzenia po dodaniu birth_location.
            try:
                if "birth_location" in df_std.columns:
                    loc = df_std["birth_location"].astype(str).str.strip()
                    loc = loc.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
                    top = loc.value_counts(dropna=False).head(8).to_dict()
                    lines.append("miejsce urodzenia (top): " + " | ".join([f"{k}={int(v)}" for k, v in top.items()]))
            except Exception:
                pass
        except Exception as e:
            lines.append(f"Błąd metryk: {e}")
    text = "\n".join(lines)
    st.text_area("Podgląd", text, height=320)
    c_dl1, c_dl2 = st.columns(2)
    with c_dl1:
        st.download_button("Pobierz raport (.txt)", data=text, file_name="raport_wisent.txt", mime="text/plain")
    with c_dl2:
        try:
            from app.ui.docx_report import report_plain_text_to_docx_bytes

            docx_bytes = report_plain_text_to_docx_bytes(
                text,
                title="WisentPedigree Pro+ — Raport (Streamlit)",
                footer_note="Raport tekstowy z podglądu (walidacja, skrót populacji). Wykresy dołącz ręcznie z pobranych plików PNG.",
            )
        except Exception as e:
            st.warning(f"Eksport DOCX wymaga pakietu python-docx (`pip install python-docx`). Szczegóły: {e}")
        else:
            st.download_button(
                "Pobierz raport (.docx)",
                data=docx_bytes,
                file_name="raport_wisent.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )


def section_breeding(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Scenariusze planu hodowlanego")
    sc.help_expander("Scenariusze planu hodowlanego — dobieranie par", hc.SECTION_BREEDING)
    st.caption(
        "Heurystyczny ranking par przy filtrach wieku, linii i miejsca urodzenia; minimalizacja F potomka "
        "z limitami użyć samicy/samca i opcjonalnym progiem maks. F."
    )

    df_ids = df_std.copy()
    df_ids["id"] = df_ids["id"].astype(str)
    if "sex" in df_ids.columns:
        sx = df_ids["sex"].astype(str).str.strip().str.upper()
        male_opts = sorted(df_ids.loc[sx == "M", "id"].drop_duplicates().tolist(), key=sc.id_sort_key)
        female_opts = sorted(df_ids.loc[sx == "F", "id"].drop_duplicates().tolist(), key=sc.id_sort_key)
    else:
        male_opts, female_opts = [], []

    pr1, pr2 = st.columns(2)
    with pr1:
        plan_ub = st.checkbox("Ryzyko inbredu: bez limitu pokoleń (do founderów)", value=False, key="plan_risk_ub")
    with pr2:
        plan_d = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, key="plan_risk_d", disabled=plan_ub)

    def plan_max_back() -> int | None:
        return None if plan_ub else int(plan_d)

    st.markdown("#### Policz ryzyko dla pojedynczej pary")
    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown("**Samica (F)**")
        plan_dam_sel = st.selectbox(
            "Z listy",
            [""] + female_opts,
            key="plan_dam_sel",
            format_func=lambda x: "— wybierz —" if x == "" else str(x),
        )
        plan_dam_txt = st.text_input("Lub ID", "", key="plan_dam_txt", placeholder="np. 123")
    with pc2:
        st.markdown("**Samiec (M)**")
        plan_sire_sel = st.selectbox(
            "Z listy",
            [""] + male_opts,
            key="plan_sire_sel",
            format_func=lambda x: "— wybierz —" if x == "" else str(x),
        )
        plan_sire_txt = st.text_input("Lub ID", "", key="plan_sire_txt", placeholder="np. 456")

    dam_one = (plan_dam_txt or "").strip() or (plan_dam_sel or "").strip()
    sire_one = (plan_sire_txt or "").strip() or (plan_sire_sel or "").strip()
    if st.button("Policz ryzyko F potomka", key="plan_calc_one_pair"):
        if not dam_one or not sire_one:
            st.error("Podaj ID samicy i samca.")
        elif dam_one not in people or sire_one not in people:
            st.error("Oba ID muszą być w wczytanej bazie.")
        else:
            pairs = [(sire_one, dam_one)]
            mb = plan_max_back()
            try:
                F_off = batch_offspring_inbreeding_F_from_parent_pairs(pairs, people, max_generations_back=mb)[0]
            except Exception as e:
                st.error(str(e))
            else:
                dl = normalize_line(getattr(people.get(dam_one), "line", None))
                sl = normalize_line(getattr(people.get(sire_one), "line", None))
                st.success(f"**F potomka** = {F_off:.6f}  (samica linia {dl}, samiec linia {sl})")

    st.markdown("#### Podpowiedz pary (TOP-N)")
    cg1, cg2, cg3 = st.columns(3)
    with cg1:
        line_mode = st.selectbox(
            "Linia (oboje rodzice)",
            ["Bez filtra", "LB", "LC", "LB+LC", "NA"],
            key="plan_line_mode",
        )
        bl_opts: list[str] = ["Bez filtra"]
        if "birth_location" in df_std.columns:
            bl_norm = df_std["birth_location"].astype(str).str.strip()
            bl_norm = bl_norm.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
            uniq = sorted(set(bl_norm.tolist()) - {"nan", "None"}, key=str.lower)
            if "NA" in uniq:
                uniq = [x for x in uniq if x != "NA"]
                bl_opts = bl_opts + uniq + ["NA"]
            else:
                bl_opts = bl_opts + uniq
        origin_mode = st.selectbox("Miejsce urodzenia (birth_location)", bl_opts, key="plan_origin")
    with cg2:
        min_age = st.number_input("Wiek min (lata)", 0, 120, 0, key="plan_min_age")
        max_age = st.number_input("Wiek max (lata)", 0, 120, 80, key="plan_max_age")
    with cg3:
        cand_limit = st.number_input("Limit kandydatów (M i F)", 1, 500, 25, key="plan_cand_lim")
        top_n = st.number_input("TOP N par", 1, 200, 20, key="plan_top_n")

    with st.expander("Cele różnorodności (progi F, limity użyć)", expanded=False):
        g1, g2 = st.columns(2)
        with g1:
            goal_mean_en = st.checkbox("Uwaga: średnie F zestawu ≤", value=False, key="plan_goal_mean_en")
            goal_mean_F = st.number_input("próg średniej F", 0.0, 1.0, 0.05, format="%.4f", key="plan_goal_mean_f")
        with g2:
            goal_max_en = st.checkbox("Tylko pary z F potomka ≤", value=False, key="plan_goal_max_en")
            goal_max_F = st.number_input("próg max F", 0.0, 1.0, 0.10, format="%.4f", key="plan_goal_max_f")
        u1, u2 = st.columns(2)
        with u1:
            max_dam_uses = st.number_input("Max użyć tej samej samicy", 1, 50, 3, key="plan_max_dam_u")
        with u2:
            max_sire_uses = st.number_input("Max użyć tego samego samca", 1, 50, 3, key="plan_max_sire_u")

    cy = datetime.now().year
    if st.button("Podpowiedz pary", type="primary", key="plan_suggest_go"):
        mb = plan_max_back()
        try:
            with st.spinner("Liczenie rankingów par…"):
                pair_result = suggest_pairs_with_constraints(
                    df_std,
                    people,  # type: ignore[arg-type]
                    min_age=int(min_age),
                    max_age=int(max_age),
                    line_mode=str(line_mode),
                    origin_mode=str(origin_mode),
                    candidate_limit=int(cand_limit),
                    top_n=int(top_n),
                    max_generations_back=mb,
                    max_dam_uses=int(max_dam_uses),
                    max_sire_uses=int(max_sire_uses),
                    goal_max_enabled=bool(goal_max_en),
                    goal_max_F=float(goal_max_F),
                    current_year=cy,
                )
        except Exception as e:
            st.session_state.pop("breeding_pair_result", None)
            st.error(f"Nie udało się policzyć rankingów par: {e}")
        else:
            st.session_state["breeding_pair_result"] = pair_result
            accepted = pair_result.suggestions
            if accepted:
                mean_f = pair_result.mean_F
                max_f = pair_result.max_F
                warn_mean = bool(goal_mean_en) and mean_f > float(goal_mean_F)
                warn_txt = " **UWAGA:** średnie F przekracza wybrany próg (tylko informacja)." if warn_mean else ""
                st.session_state["breeding_pair_msg"] = (
                    f"TOP {len(accepted)}/{int(top_n)} par. Śr. F={mean_f:.6f}, max F={max_f:.6f}. "
                    f"Kandydatki: {pair_result.female_candidates}, samce: {pair_result.male_candidates}.{warn_txt}"
                )
            else:
                st.session_state["breeding_pair_msg"] = "Brak par spełniających ograniczenia."

    if st.session_state.get("breeding_pair_msg"):
        st.info(st.session_state["breeding_pair_msg"])

    pair_result = st.session_state.get("breeding_pair_result")
    if pair_result and pair_result.suggestions:
        rows = []
        for r in pair_result.suggestions:
            rows.append(
                {
                    "Samica (ID)": r.dam_id,
                    "Samica linia": r.dam_line,
                    "Samica wiek": r.dam_age,
                    "Samiec (ID)": r.sire_id,
                    "Samiec linia": r.sire_line,
                    "Samiec wiek": r.sire_age,
                    "F potomka": round(r.offspring_F, 6),
                }
            )
        st.dataframe(pd.DataFrame(rows), width="stretch", height=min(420, 60 + 28 * min(len(rows), 12)))
        labels = [
            f"{i + 1}. {s.dam_id} × {s.sire_id}  F={s.offspring_F:.6f}" for i, s in enumerate(pair_result.suggestions)
        ]
        pick = st.selectbox(
            "Para — szczegóły i rodowód hipotetycznego potomka",
            list(range(len(pair_result.suggestions))),
            format_func=lambda i: labels[int(i)],
            key="plan_pick_pair",
        )
        sel = pair_result.suggestions[int(pick)]
        dam_id, sire_id = sel.dam_id, sel.sire_id
        mb = plan_max_back()
        try:
            F_off = wright_offspring_inbreeding_F_from_parents(
                father_id=sire_id, mother_id=dam_id, people=people, max_generations_back=mb
            )
        except Exception:
            F_off = float("nan")
        try:
            F_dam = wright_inbreeding_F(person_id=dam_id, people=people, max_generations_back=mb).F
        except Exception:
            F_dam = float("nan")
        try:
            F_sire = wright_inbreeding_F(person_id=sire_id, people=people, max_generations_back=mb).F
        except Exception:
            F_sire = float("nan")
        MG_d, EG_d, PCI_d = pci_bundle_for_breeding(dam_id, people)
        MG_s, EG_s, PCI_s = pci_bundle_for_breeding(sire_id, people)
        d_nm = getattr(people.get(dam_id), "name", None) or "-"
        s_nm = getattr(people.get(sire_id), "name", None) or "-"
        mb_note = "bez limitu (do founderów)" if mb is None else f"max {mb} pokoleń"
        detail_lines = [
            f"Samica: {dam_id} ({d_nm})  |  linia: {sel.dam_line}  |  wiek: {sel.dam_age}",
            f"Samiec: {sire_id} ({s_nm})  |  linia: {sel.sire_line}  |  wiek: {sel.sire_age}",
            "",
            f"Parametry F jak przy ryzyku ({mb_note}).",
            f"F potomka Φ(samiec, samica) = {F_off:.6f}  (w tabeli: {sel.offspring_F:.6f})",
            f"F samicy = {F_dam:.6f}  |  F samca = {F_sire:.6f}",
            "",
            f"Kompletność rodowodu (bez limitu) — samica: MG={MG_d}, EG={EG_d:.4f}, PCI={PCI_d:.4f}",
            f"Kompletność rodowodu (bez limitu) — samiec: MG={MG_s}, EG={EG_s:.4f}, PCI={PCI_s:.4f}",
        ]
        st.text("\n".join(detail_lines))
        pd_depth = plan_pedigree_plot_depth(mb)
        st.caption(f"Graf poniżej: do {pd_depth} pokoleń wstecz (tryb czytelny dla podglądu w przeglądarce).")
        fig_h = breeding_hypo_offspring_figure(sire_id, dam_id, people, mb)
        splt.show_matplotlib_figure_in_streamlit(
            fig_h,
            download_filename=f"plan_potomek_{dam_id}_{sire_id}.png",
            download_key=f"plan_hypo_png_{dam_id}_{sire_id}",
            width="stretch",
        )


