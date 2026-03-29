"""
Wszystkie ekrany wersji przeglądarkowej w jednym miejscu (wczytywanie, osobniki, rodowód,
analizy, populacja, raporty, ustawienia, plan hodowlany).
"""

from __future__ import annotations

import io
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.analytics.inbreeding_wright import (
    batch_offspring_inbreeding_F_from_parent_pairs,
    wright_inbreeding_F,
)
from app.analytics.population_genetics import TEST_ID, compute_gi_and_family_data, compute_population_genetics_stats
from app.data.dataset_loader import (
    load_dataset_from_bytes,
    load_default_bison_report,
    load_raw_dataframe_from_url,
    standardize_bison_report_dataframe_with_column_mapping,
)
from app.pedigree.ancestor_pedigree import (
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
    get_ancestor_levels_unbounded,
)
from app.ui import help_content as hc
from app.ui.streamlit import common as sc
import app.ui.streamlit.streamlit_plotting as splt
from app.visualizations.ancestor_plot import plot_ancestor_pedigree


def section_loading() -> None:
    st.markdown("### Import i walidacja")
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
            st.caption(rep.ui_summary())
            with st.expander("Pełny raport walidacji (tekst)"):
                st.text(rep.to_text())
                st.download_button(
                    "Pobierz raport (.txt)",
                    data=rep.to_text(),
                    file_name="walidacja_bazy.txt",
                    mime="text/plain",
                )


def section_persons(df_std: pd.DataFrame) -> None:
    st.markdown("### Rejestr osobników")
    sc.help_expander("Rejestr osobników — jak czytać tabelę", hc.SECTION_PERSONS)
    lm = st.session_state.get("line_memberships") or {}
    base = df_std.copy()
    base["id"] = base["id"].astype(str)

    def _row_line(pid: str) -> str:
        m = lm.get(pid)
        if m is None:
            return "NA"
        return f"S:{m.sire_founder_id or 'NA'} / D:{m.dam_founder_id or 'NA'}"

    base["linia (sire/dam)"] = base["id"].map(lambda x: _row_line(str(x)))

    sort_col = st.selectbox("Sortuj po kolumnie", options=list(base.columns), index=0, key="p_sort")
    asc = st.toggle("Rosnąco (A→Z / małe→duże)", value=True, key="p_asc")
    preview_n = st.slider("Liczba wierszy podglądu", 25, 500, 250, 25, key="p_n")
    view = base.sort_values(by=[sort_col], ascending=bool(asc)).head(preview_n)
    st.dataframe(view, width="stretch", height=420)


def _build_pedigree_figure(
    *,
    person_id: str,
    people: dict,
    unbounded: bool,
    depth: int,
    readable: bool,
    click_highlight: bool = False,
):
    max_nodes = 280
    depth_i = max(0, min(30, int(depth)))
    if unbounded:
        levels_unc = get_ancestor_levels_unbounded(person_id=person_id, people=people)
        if len(levels_unc) > max_nodes:
            levels, edges = get_ancestor_levels_and_edges(
                person_id=person_id, depth=max(depth_i, 4), people=people
            )
            note = f"(graf: limit gęstości, N w pełnym={len(levels_unc)})"
        else:
            levels = levels_unc
            people_all_tmp = ensure_people_for_nodes(levels=levels, people=people)
            edges = []
            for child_id in levels.keys():
                p = people_all_tmp.get(child_id)
                if not p:
                    continue
                if getattr(p, "father_id", None) and p.father_id in levels:
                    edges.append((p.father_id, child_id))
                if getattr(p, "mother_id", None) and p.mother_id in levels:
                    edges.append((p.mother_id, child_id))
            note = f"(bez limitu pokoleń, N={len(levels)})"
    else:
        depth_for = depth_i
        levels = {}
        edges = []
        while depth_for >= 0:
            levels_try, edges_try = get_ancestor_levels_and_edges(
                person_id=person_id, depth=depth_for, people=people
            )
            if len(levels_try) <= max_nodes or depth_for == 0:
                levels, edges = levels_try, edges_try
                break
            depth_for -= 1
        note = f"(limit={depth_for}, N={len(levels)})"

    if not levels:
        return None, "Brak danych do wyświetlenia."
    people_all = ensure_people_for_nodes(levels=levels, people=people)
    fig = plot_ancestor_pedigree(
        person_id=person_id,
        levels=levels,
        edges=edges,
        people=people_all,
        readable_mode=readable,
        enable_click_highlight=click_highlight,
    )
    try:
        fig.suptitle(f"Rodowód przodków {note}", fontsize=11, y=0.98)
    except Exception:
        pass
    return fig, None


def section_pedigree(df_std, people: dict) -> None:
    st.markdown("### Graf pedigree")
    sc.help_expander("Graf pedigree — linie (sire/dam)", hc.SECTION_PEDIGREE)
    lm = st.session_state.get("line_memberships") or {}
    default_id = str(df_std.iloc[0]["id"]) if not df_std.empty else ""
    pid = st.text_input("ID (Number)", value=default_id, key="rod_id")
    col1, col2, col3 = st.columns(3)
    with col1:
        unbounded = st.checkbox("Bez limitu (do founderów)", value=True, key="rod_ub")
    with col2:
        depth = st.slider("Max pokoleń (gdy limit)", 0, 30, 4, key="rod_d", disabled=unbounded)
    with col3:
        readable = st.checkbox("Tryb czytelny (mniej etykiet)", value=True, key="rod_r")

    if pid.strip() in lm:
        st.markdown("**Linie (sireline / damline)**")
        st.text(sc.fmt_line_block(lm.get(pid.strip())))
        fa = people.get(pid.strip()).father_id if people.get(pid.strip()) else None
        mo = people.get(pid.strip()).mother_id if people.get(pid.strip()) else None
        c1, c2 = st.columns(2)
        with c1:
            if fa:
                st.caption("Ojciec")
                st.text(sc.fmt_line_block(lm.get(str(fa))))
        with c2:
            if mo:
                st.caption("Matka")
                st.text(sc.fmt_line_block(lm.get(str(mo))))

    if st.button("Generuj graf przodków", type="primary", key="rod_go"):
        if not pid.strip() or pid.strip() not in people:
            st.error("Podaj istniejące ID.")
            return
        fig, err = _build_pedigree_figure(
            person_id=pid.strip(),
            people=people,
            unbounded=unbounded,
            depth=int(depth),
            readable=readable,
        )
        if err:
            st.warning(err)
            return
        if fig is not None:
            st.pyplot(fig, width="stretch")
            buf = io.BytesIO()
            fig.savefig(buf, format="jpeg", dpi=160, bbox_inches="tight")
            st.download_button(
                "Pobierz wykres (JPEG)",
                data=buf.getvalue(),
                file_name=f"rodowod_{pid.strip()}.jpg",
                mime="image/jpeg",
            )


def section_analysis_inbred(people: dict) -> None:
    st.markdown("#### Inbred — współczynnik F (Wright)")
    sc.help_expander("Inbred F — definicja i wykres diagnostyczny", hc.SECTION_INBRED)
    default_id = str(st.session_state["df_std"].iloc[0]["id"]) if len(st.session_state["df_std"]) else ""
    pid = st.text_input("ID (Number)", value=default_id, key="inb_pid")
    c1, c2 = st.columns(2)
    with c1:
        unbounded = st.checkbox("Bez limitu (do founderów)", value=True, key="inb_ub")
    with c2:
        depth = st.slider("Max pokoleń (gdy limit)", 0, 30, 4, key="inb_d", disabled=unbounded)

    if st.button("Policz F (Wright)", type="primary", key="inb_calc"):
        if not pid.strip() or pid.strip() not in people:
            st.error("Podaj poprawne ID.")
            return
        f_res = wright_inbreeding_F(
            person_id=pid.strip(),
            people=people,
            max_generations_back=None if unbounded else int(depth),
        )
        st.metric("F (Wright)", f"{f_res.F:.6f}")
        st.caption(
            f"Ojciec: {f_res.father_id} ({f_res.father_name or '-'}), "
            f"Matka: {f_res.mother_id} ({f_res.mother_name or '-'}). "
            f"Użyte pokolenia (ścieżki): {f_res.used_generations}."
        )
        st.caption(
            "Metoda: F(i)=Φ(ojciec, matka); Φ liczone rekurencyjnie. Brak rodziców = founder (Φ=0 między niepowiązanymi)."
        )
        max_trace = min(20, int(f_res.used_generations) if f_res.used_generations else 0)
        depths = list(range(0, max_trace + 1))
        Fs = [
            wright_inbreeding_F(
                person_id=pid.strip(), people=people, max_generations_back=int(d)
            ).F
            for d in depths
        ]
        fig, ax = plt.subplots(figsize=(8, 3.8))
        ax.plot(depths, Fs, marker="o", color=sc.THEME.EDGE_PLOT, linewidth=2)
        ax.set_title(f"Diagnostyka F vs max pokoleń (ID {pid.strip()})")
        ax.set_xlabel("max pokoleń")
        ax.set_ylabel("F")
        ax.grid(True, alpha=0.25)
        st.pyplot(fig, width="stretch")
        b = io.BytesIO()
        fig.savefig(b, format="jpeg", dpi=160, bbox_inches="tight")
        st.download_button("Pobierz wykres (JPEG)", b.getvalue(), f"inbred_diag_{pid.strip()}.jpg", "image/jpeg")


def section_analysis_mating(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Optymalizacja kojarzeń (ranking par, minimalne F potomka)")
    sc.help_expander("Optymalizacja kojarzeń — interpretacja rankingu", hc.SECTION_MATING)
    st.caption(
        "Filtr wieku: ostatnie 15 lat (jak w Tk). Ranking: do 36 par (najmniejsze F), "
        "każdy osobnik w liście wynikowej max 3× (jako sire lub dam). Limity kandydatów ograniczają czas obliczeń."
    )

    mating_unbounded = st.checkbox("F bez limitu pokoleń (wolniejsze)", value=False, key="mat_ub")
    mating_depth = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, key="mat_d", disabled=mating_unbounded)
    c1, c2 = st.columns(2)
    with c1:
        male_limit = st.number_input("Max samców (M)", 1, 500, 200)
    with c2:
        female_limit = st.number_input("Max samic (F)", 1, 500, 200)

    cy = datetime.now().year
    cutoff = cy - 15
    st.caption(f"Rok odniesienia {cy}: używane osobniki z birth_year ≥ {cutoff}.")

    if st.button("Oblicz ranking kojarzeń (TOP 36)", type="primary", key="mat_go"):
        df_tmp = df_std.copy()
        df_tmp["id"] = df_tmp["id"].astype(str)
        df_tmp["birth_year_num"] = pd.to_numeric(df_tmp.get("birth_year"), errors="coerce")
        ids_set = set(people.keys())
        df_tmp = df_tmp[df_tmp["id"].isin(ids_set)]
        df_tmp = df_tmp[df_tmp["sex"].isin(["M", "F"])]
        df_tmp = df_tmp[df_tmp["birth_year_num"].notna()]
        df_tmp = df_tmp[df_tmp["birth_year_num"] >= float(cutoff)]

        males_df = df_tmp[df_tmp["sex"] == "M"].sort_values("birth_year_num", ascending=False)
        females_df = df_tmp[df_tmp["sex"] == "F"].sort_values("birth_year_num", ascending=False)
        males = males_df["id"].tolist()[: int(male_limit)]
        females = females_df["id"].tolist()[: int(female_limit)]
        pairs = [(s, d) for s in males for d in females]
        if not pairs:
            st.warning("Brak kandydatów po filtrze wieku.")
            return
        max_back = None if mating_unbounded else int(mating_depth)
        with st.spinner(f"Liczenie {len(pairs)} par…"):
            Fs = batch_offspring_inbreeding_F_from_parent_pairs(pairs, people, max_generations_back=max_back)
        ranked_all = sorted(zip(Fs, pairs), key=lambda x: x[0])
        use_count: dict[str, int] = {}
        top_n = 36
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
        lines = [f"Wybrano {len(ranked)} par (cel do {top_n}; max {max_uses}× ten sam ID w liście).", ""]
        for i, (fv, (sire_id, dam_id)) in enumerate(ranked, 1):
            sn = getattr(people.get(sire_id), "name", None)
            dn = getattr(people.get(dam_id), "name", None)
            lines.append(
                f"{i}. F={fv:.6f} | sire={sire_id} ({sn or '-'}) × dam={dam_id} ({dn or '-'})"
            )
        st.text("\n".join(lines))


def _figure_to_jpeg_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def section_population(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Metryki populacji")
    verbose = bool(st.session_state.get("st_verbose_pop_captions", True))
    sc.help_expander(
        "Metryki populacji (średnie F, f_e, f_a, GI, N_e…)",
        hc.SECTION_POPULATION + "\n\n*Pełny słownik skrótów: panel boczny → „Słownik parametrów”.*",
        expanded=False,
    )
    c1, c2 = st.columns(2)
    with c1:
        pop_ub = st.checkbox("F populacji: bez limitu (do founderów)", value=False, key="pop_ub")
    with c2:
        pop_depth = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, disabled=pop_ub, key="pop_dep")

    max_gen = None if pop_ub else int(pop_depth)

    df_use = df_std.copy()
    df_use["id"] = df_use["id"].astype(str)
    df_use = df_use[df_use["id"] != TEST_ID].reset_index(drop=True)

    with st.spinner("Liczenie metryk populacji…"):
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

    with st.spinner("Liczenie F dla trendów w czasie (średnie F / RIA wg roku)…"):
        dfc_trend, warn_trend = splt.prepare_inbreeding_trends_dataframe(df_use, people, max_gen)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("n (bez test ID)", str(stats.n))
    m2.metric("Średnie F", f"{stats.inbreeding.mean_F:.4f}")
    m3.metric("f_e", f"{stats.founders.f_e:.4f}")
    m4.metric("f_a", f"{stats.founders.f_a:.4f}")

    gi_all = gi_data.get("gi_all")
    fam_sizes: list = gi_data.get("family_sizes") or []
    fam_n = len(fam_sizes)
    fam_mean = float(sum(fam_sizes)) / float(fam_n) if fam_n else None
    ne_est = splt.estimate_ne_from_f_trend(
        df_use, people, gi_all, max_gen, dfc_precomputed=dfc_trend
    )

    st.caption(
        f"Założyciele (brak ojca lub matki): {stats.n_founders_any_missing_parent}. "
        f"Linie LB/LC/NA: {stats.line_counts}"
    )
    gi_txt = f"{gi_all:.2f} lat" if gi_all is not None else "—"
    fam_txt = f"{fam_n} rodzin, śr. wielkość {fam_mean:.2f}" if fam_n else "—"
    ne_txt = f"{ne_est:.1f}" if ne_est is not None else "— (wymaga wzrostu F i GI)"
    st.caption(
        f"**GI** (średni, 4 ścieżki łącznie): {gi_txt} • **Rodziny pełne** (para rodziców): {fam_txt} • "
        f"**N_e** (z trendu F×GI): {ne_txt}"
    )

    tab_names = [
        "Urodzenia według płci",
        "Urodzenia według linii (LB/LC)",
        "Stosunek płci (ur. ≥ 1900)",
        "Kompletność rodowodu — płeć",
        "Kompletność rodowodu — linie",
        "Rozkład F (Wright)",
        "Ranking wkładu założycieli (p_i)",
        "Średni interwał pokoleniowy (GI)",
        "Trend interwału pokoleniowego",
        "Kompletność struktury rodzin",
        "Trend F i RIA — płeć",
        "Trend F i RIA — linie",
    ]
    tabs = st.tabs(tab_names)

    with tabs[0]:
        st.caption("Liczba urodzeń w dekadach (1881–obecny rok), podział M/F.")
        sc.help_expander("Interpretacja: Urodzenia wg płci", hc.CHART_BIRTH_SEX, expanded=verbose)
        fig = splt.fig_birth_decades_sex(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[1]:
        st.caption("Urodzenia w dekadach wg linii (LB vs LC).")
        sc.help_expander("Interpretacja: Urodzenia wg linii", hc.CHART_BIRTH_LINE, expanded=verbose)
        fig = splt.fig_birth_decades_line(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[2]:
        st.caption("Stosunek F/M w dekadach od 1900.")
        sc.help_expander("Interpretacja: Female/Male ratio", hc.CHART_FM_RATIO, expanded=verbose)
        fig = splt.fig_female_male_ratio(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[3]:
        st.caption("Średnie MG, CG, EG wg płci.")
        sc.help_expander("Interpretacja: Kompletność (MG/CG/EG) wg płci", hc.CHART_COMP_SEX, expanded=verbose)
        fc, _ = splt.fig_completeness_sex_line(df_std, people)
        st.pyplot(fc, width="stretch")

    with tabs[4]:
        st.caption("Średnie MG, CG, EG wg linii LB/LC/NA.")
        sc.help_expander("Interpretacja: Kompletność wg linii", hc.CHART_COMP_LINE, expanded=verbose)
        _, fl = splt.fig_completeness_sex_line(df_std, people)
        st.pyplot(fl, width="stretch")

    with tabs[5]:
        st.caption("Histogram F w populacji (przy wybranym limicie pokoleń).")
        sc.help_expander("Interpretacja: rozkład F", hc.CHART_HIST_F, expanded=verbose)
        fig = splt.fig_histogram_f(stats.f_values or [])
        st.pyplot(fig, width="stretch")

    with tabs[6]:
        st.caption("Top 20 wkładu genetycznego założycieli (p_i).")
        sc.help_expander("Interpretacja: założyciele p_i", hc.CHART_FOUNDERS_PI, expanded=verbose)
        fig = splt.fig_founder_contributions(stats.founder_contributions or {}, people)
        st.pyplot(fig, width="stretch")

    with tabs[7]:
        st.caption("Średni odstęp międzypokoleniowy (GI) — ojciec/matka vs syn/córka (jak w Tk).")
        sc.help_expander("Interpretacja: GI (średni)", hc.CHART_GI_BAR, expanded=verbose)
        fig_gi = splt.fig_gi_mean_bar(gi_data)
        st.pyplot(fig_gi, width="stretch")
        st.download_button(
            "Zapis wykresu (JPEG)",
            data=_figure_to_jpeg_bytes(fig_gi),
            file_name="pop_gi_sredni.jpeg",
            mime="image/jpeg",
            key="dl_gi_bar",
        )

    with tabs[8]:
        st.caption("Trend średniego GI w dekadach urodzenia potomstwa.")
        sc.help_expander("Interpretacja: GI trend", hc.CHART_GI_TREND, expanded=verbose)
        fig_tr = splt.fig_gi_trend_decades(gi_data)
        st.pyplot(fig_tr, width="stretch")
        st.download_button(
            "Zapis wykresu (JPEG)",
            data=_figure_to_jpeg_bytes(fig_tr),
            file_name="pop_gi_trend.jpeg",
            mime="image/jpeg",
            key="dl_gi_trend",
        )

    with tabs[9]:
        st.caption("Histogram wielkości rodzin pełnego rodzeństwa (ta sama para rodziców).")
        sc.help_expander("Interpretacja: rodziny pełnego rodzeństwa", hc.CHART_FAMILY, expanded=verbose)
        fig_fam = splt.fig_family_full_siblings(fam_sizes)
        st.pyplot(fig_fam, width="stretch")
        st.download_button(
            "Zapis wykresu (JPEG)",
            data=_figure_to_jpeg_bytes(fig_fam),
            file_name="pop_rodziny.jpeg",
            mime="image/jpeg",
            key="dl_fam",
        )

    with tabs[10]:
        st.caption("Średnie F oraz RIA (% z F>0) w roku urodzenia — wg płci (F liczone raz na wejściu do Populacja).")
        sc.help_expander("Interpretacja: trendy F i RIA wg płci", hc.CHART_INBRED_TP_SEX, expanded=verbose)
        fig_sex, warn_sex = splt.fig_inbreeding_year_trends_sex(
            df_use, people, max_gen, dfc_precomputed=dfc_trend, trend_warn=warn_trend
        )
        if warn_sex:
            st.warning(warn_sex)
        st.pyplot(fig_sex, width="stretch")
        st.download_button(
            "Zapis wykresu (JPEG)",
            data=_figure_to_jpeg_bytes(fig_sex),
            file_name="pop_inbred_trend_plec.jpeg",
            mime="image/jpeg",
            key="dl_inb_sex",
        )

    with tabs[11]:
        st.caption("Średnie F oraz RIA w roku urodzenia — wg linii LB/LC/NA.")
        sc.help_expander("Interpretacja: trendy F i RIA wg linii", hc.CHART_INBRED_TP_LINE, expanded=verbose)
        fig_ln, warn_ln = splt.fig_inbreeding_year_trends_line(
            df_use, people, max_gen, dfc_precomputed=dfc_trend, trend_warn=warn_trend
        )
        if warn_ln:
            st.warning(warn_ln)
        st.pyplot(fig_ln, width="stretch")
        st.download_button(
            "Zapis wykresu (JPEG)",
            data=_figure_to_jpeg_bytes(fig_ln),
            file_name="pop_inbred_trend_linie.jpeg",
            mime="image/jpeg",
            key="dl_inb_line",
        )


def section_reports() -> None:
    st.markdown("### Raportowanie")
    sc.help_expander("Raporty — co zawierają", hc.SECTION_REPORTS)
    st.caption("Podgląd tekstowy; pełny eksport DOCX/PDF jest w wersji Tk.")
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
        except Exception as e:
            lines.append(f"Błąd metryk: {e}")
    text = "\n".join(lines)
    st.text_area("Podgląd", text, height=320)
    st.download_button("Pobierz raport (.txt)", data=text, file_name="raport_wisent.txt", mime="text/plain")


def section_settings() -> None:
    st.markdown("### Konfiguracja (sesja)")
    sc.help_expander("Ustawienia sesji Streamlit", hc.SECTION_SETTINGS)
    st.caption("W Streamlit ustawienia są trzymane w tej sesji przeglądarki.")
    st.checkbox(
        "Domyślnie: rozwinięte bloki „Interpretacja wykresu” w Metrykach populacji",
        value=True,
        key="st_verbose_pop_captions",
    )


def section_breeding_placeholder() -> None:
    st.info(
        "Plan hodowli — sekcja synchronizowana z wersją desktop (Tk); logika hodowlana w rozwoju."
    )
    sc.help_expander("Plan hodowli (Tk vs Streamlit)", hc.SECTION_BREEDING)
