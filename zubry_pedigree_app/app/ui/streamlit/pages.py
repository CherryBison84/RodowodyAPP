"""
Wszystkie ekrany wersji przeglądarkowej w jednym miejscu (wczytywanie, osobniki, rodowód,
analizy, populacja, raporty, ustawienia, plan hodowlany).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from io import StringIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

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
from app.analytics.population_genetics import (
    TEST_ID,
    FounderContributionComputer,
    compute_gi_and_family_data,
    compute_population_genetics_stats,
)
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


def section_import() -> None:
    st.markdown("### Import danych")
    st.caption("Plik CSV/XLSX lub URL z mapowaniem kolumn. Po wczytaniu przejdź do **Walidacja bazy**.")
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
        st.success(
            f"W pamięci sesji: **{st.session_state.get('source', '-')}** • **n =** {len(df_std)}. "
            "Następny krok: **Walidacja bazy** w menu."
        )


def section_validation() -> None:
    st.markdown("### Walidacja bazy")
    st.caption("Sprawdzenie spójności po imporcie. Potem: rejestr → analiza osobnika / par → populacja → raport.")
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
    st.markdown("### Rejestr osobników")
    sc.help_expander("Rejestr osobników — jak czytać tabelę", hc.SECTION_PERSONS)
    lm = st.session_state.get("line_memberships") or {}
    people = st.session_state.get("people") or {}
    base = df_std.copy()
    base["id"] = base["id"].astype(str)

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
    if q:
        mask = base["id"].astype(str).str.contains(q, case=False, na=False, regex=False)
        filtered = base.loc[mask].copy()
        st.caption(f"Po filtrze ID: **{len(filtered)}** wierszy (z {len(base)}).")

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


def _individual_pcl_dataframe(person_id: str, people: dict) -> tuple[pd.DataFrame, float, float]:
    levels = get_ancestor_levels_unbounded(person_id=person_id, people=people)
    by_gen: dict[int, int] = {}
    for _aid, lvl in levels.items():
        if lvl is None or lvl <= 0:
            continue
        by_gen[int(lvl)] = by_gen.get(int(lvl), 0) + 1
    if not by_gen:
        return pd.DataFrame(), 0.0, 0.0
    g_max = max(by_gen.keys())
    rows: list[dict] = []
    eg = 0.0
    pcl_sum = 0.0
    for g in range(1, g_max + 1):
        a_g = by_gen.get(g, 0)
        pcl_g = float(a_g) / float(2**g)
        pcl_sum += pcl_g
        eg += pcl_g
        rows.append(
            {
                "Pokolenie g": g,
                "Znani przodkowie a_g": a_g,
                "Max miejsc 2^g": 2**g,
                "PCL = a_g/2^g": round(pcl_g, 6),
            }
        )
    pci = pcl_sum / float(g_max)
    return pd.DataFrame(rows), eg, pci


def section_analysis_individual(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Analiza osobnika")
    st.caption("Graf przodków, F (Wright), kompletność (EG/PCI), linie sire/dam, wspólni przodkowie rodziców.")
    section_individual_pedigree_analysis(df_std, people)


def section_analysis_pairs_and_mating(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Analiza par i kojarzenia")
    st.caption("Kinship pary (Φ, R, wyjaśnienie ścieżek) oraz ranking kojarzeń.")
    t1, t2 = st.tabs(["Para", "Ranking kojarzeń"])
    with t1:
        section_pair_kinship_analysis(df_std, people)
    with t2:
        section_mating_ranking(df_std, people)


def section_individual_pedigree_analysis(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Analiza rodowodowa — osobnik")
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
        sc.help_expander("Graf pedigree — linie (sire/dam)", hc.SECTION_PEDIGREE)
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
                fig, err = _build_pedigree_figure(
                    person_id=str(pid),
                    people=people,
                    unbounded=unbounded,
                    depth=int(depth),
                    readable=readable,
                )
                if err:
                    st.warning(err)
                elif fig is not None:
                    st.pyplot(fig, width="stretch")
                    buf = io.BytesIO()
                    fig.savefig(buf, format="jpeg", dpi=160, bbox_inches="tight")
                    st.download_button(
                        "Pobierz wykres (JPEG)",
                        data=buf.getvalue(),
                        file_name=f"rodowod_{pid}.jpg",
                        mime="image/jpeg",
                        key="hub_rod_jpeg",
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
                fig, ax = plt.subplots(figsize=(8, 3.8))
                ax.plot(depths, Fs, marker="o", color=sc.THEME.EDGE_PLOT, linewidth=2)
                ax.set_title(f"Diagnostyka F vs max pokoleń (ID {pid})")
                ax.set_xlabel("max pokoleń")
                ax.set_ylabel("F")
                ax.grid(True, alpha=0.25)
                st.pyplot(fig, width="stretch")
                b = io.BytesIO()
                fig.savefig(b, format="jpeg", dpi=160, bbox_inches="tight")
                st.download_button(
                    "Pobierz wykres (JPEG)", b.getvalue(), f"inbred_diag_{pid}.jpg", "image/jpeg", key="hub_inb_jpeg"
                )

    with st3:
        st.caption("Kompletność wg poziomów przodków (PCL), EG i PCI — jak w metrykach populacji.")
        if st.button("Przelicz kompletność", key="hub_comp_go"):
            df_c, eg, pci = _individual_pcl_dataframe(str(pid), people)
            if df_c.empty:
                st.info("Brak poziomów przodków powyżej 0.")
            else:
                st.metric("EG (pokolenia równoważne)", f"{eg:.4f}")
                st.metric("PCI (średnia PCL po poziomach)", f"{pci:.4f}")
                st.dataframe(df_c, width="stretch", height=min(400, 60 + 28 * len(df_c)))
                fig, ax = plt.subplots(figsize=(8, 3.2))
                ax.bar(df_c["Pokolenie g"].astype(int), df_c["PCL = a_g/2^g"], color=sc.THEME.EDGE_PLOT, alpha=0.85)
                ax.set_xlabel("Pokolenie g")
                ax.set_ylabel("PCL")
                ax.set_title("Kompletność per pokolenie (PCL)")
                ax.grid(True, axis="y", alpha=0.25)
                st.pyplot(fig, width="stretch")

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
    st.markdown("#### Analiza rodowodowa — para")
    sc.help_expander("Optymalizacja kojarzeń — interpretacja rankingu", hc.SECTION_MATING)
    id_opts = sorted(df_std["id"].astype(str).unique().tolist(), key=sc.id_sort_key)
    c0, c1 = st.columns(2)
    with c0:
        pair_ub = st.checkbox("Φ bez limitu pokoleń (wolniejsze)", value=False, key="pair_ub")
    with c1:
        pair_d = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, key="pair_d", disabled=pair_ub)
    kc1, kc2 = st.columns(2)
    with kc1:
        kin_a = st.selectbox("Osobnik A", id_opts, key="pair_kin_a")
    with kc2:
        kin_b = st.selectbox(
            "Osobnik B",
            id_opts,
            index=min(1, len(id_opts) - 1) if len(id_opts) > 1 else 0,
            key="pair_kin_b",
        )
    max_back = None if pair_ub else int(pair_d)
    if st.button("Oblicz Φ, R, F potomka i wyjaśnienie", type="primary", key="pair_calc"):
        try:
            phi_v, r_v = wright_kinship_phi_and_relationship_R(
                str(kin_a), str(kin_b), people, max_generations_back=max_back
            )
            f_pot = wright_offspring_inbreeding_F_from_parents(
                str(kin_a), str(kin_b), people, max_generations_back=max_back
            )
            st.session_state["pair_phi"] = phi_v
            st.session_state["pair_r"] = r_v
            st.session_state["pair_fpot"] = f_pot
            st.session_state["pair_explain"] = explain_pair_kinship(
                str(kin_a), str(kin_b), people, max_generations_back=max_back
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
        m3.metric("F potomka (A×B)", f"{float(st.session_state.get('pair_fpot', phi_v)):.6f}")
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
                    "krawędzie A/B": f"{d.n_edges_a}+{d.n_edges_b}",
                    "Wkład Φ": round(d.contribution_to_phi, 8),
                    "Ścieżka A": "→".join(d.path_a) if d.path_a else "·",
                    "Ścieżka B": "→".join(d.path_b) if d.path_b else "·",
                }
            )
        with st.expander("Najsilniejsze pary ścieżek", expanded=True):
            st.dataframe(pd.DataFrame(pr), width="stretch", height=min(420, 60 + 26 * min(len(pr), 12)))


def section_mating_ranking(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("#### Optymalizacja kojarzeń (ranking par, minimalne F potomka)")
    sc.help_expander("Optymalizacja kojarzeń — interpretacja rankingu", hc.SECTION_MATING)
    st.caption(
        "Filtr wieku: ostatnie 15 lat (jak w Tk). Ranking: do 36 par (najmniejsze Φ = F potomka), "
        "R = 2Φ; każdy osobnik w liście wynikowej max 3×. Limity kandydatów ograniczają czas obliczeń."
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
            st.session_state.pop("mating_ranking_text", None)
            st.session_state.pop("mating_phi_csv", None)
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
    c1, c2, c3 = st.columns(3)
    with c1:
        pop_ub = st.checkbox("F populacji: bez limitu (do founderów)", value=False, key="pop_ub")
    with c2:
        pop_depth = st.number_input("Max pokoleń (gdy limit)", 0, 30, 4, disabled=pop_ub, key="pop_dep")
    with c3:
        act_years = st.number_input(
            "Kohorta „aktywna”: lata wstecz od dziś (rok ur.)",
            min_value=5,
            max_value=60,
            value=20,
            key="pop_act_y",
        )
    c4, c5 = st.columns(2)
    with c4:
        vuln_recent = st.number_input(
            "Tabela ryzyka linii: urodzenia z ostatnich N lat",
            min_value=5,
            max_value=80,
            value=30,
            key="pop_vuln_r",
        )
    with c5:
        vuln_active = st.number_input(
            "Tabela ryzyka linii: okno kohorty aktywnych (lat)",
            min_value=5,
            max_value=60,
            value=20,
            key="pop_vuln_a",
        )

    max_gen = None if pop_ub else int(pop_depth)

    df_use = df_std.copy()
    df_use["id"] = df_use["id"].astype(str)
    df_use = df_use[df_use["id"] != TEST_ID].reset_index(drop=True)

    with st.spinner("Liczenie metryk populacji, kohorty, okresów…"):
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

    st.markdown("#### Dashboard startowy")
    st.caption(
        "**RIA** — odsetek osobników z F>0 (jak na wykresach trendów). **f_ge** — liczba odrębnych „węzłów” "
        "założycielskich w modelu wkładów (founder-stop). **Koncentracja** — udział potomstwa z znanym ojcem "
        "przypisany do 5 / 10 najczęstszych ojców."
    )
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("n (bez test ID)", str(stats.n))
    d2.metric("Średnie F", f"{stats.inbreeding.mean_F:.4f}")
    d3.metric("f_e", f"{stats.founders.f_e:.4f}")
    d4.metric("f_a", f"{stats.founders.f_a:.4f}")
    d5, d6, d7, d8 = st.columns(4)
    d5.metric("RIA % (F > 0)", f"{ria_pct:.1f}")
    d6.metric("f_ge (węzły założ.)", str(f_ge_n))
    d7.metric("Średni EG", f"{stats.completeness.mean_EG:.4f}")
    d8.metric("Średni GI (lat)", f"{gi_all:.2f}" if gi_all is not None else "—")
    d9, d10, d11, d12 = st.columns(4)
    d9.metric("% rek. z brakiem ojca lub matki", f"{pct_inc_par:.1f}%")
    d10.metric("% pustych slotów (2n)", f"{pct_slot:.1f}%")
    d11.metric("Założyciele (rek. z ≥1 brakiem)", str(stats.n_founders_any_missing_parent))
    if _n_fa:
        d12.metric(
            "Konc. ojców top5 / top10",
            f"{p5:.1f}% / {p10:.1f}%",
            help=f"Potomstwo z znanym ojcem: n = {_n_fa}",
        )
    else:
        d12.metric("Konc. ojców top5 / top10", f"{p5:.1f}% / {p10:.1f}%")
    d13, d14, d15, d16 = st.columns(4)
    d13.metric(f"Kohorta ur. ({act_years} lat): n", str(act.n_total))
    d14.metric("Kohorta: M / F", f"{act.n_males} / {act.n_females}")
    d15.metric("Reprod. (unik. ojc./mat.)", f"{act.n_reproducer_males} / {act.n_reproducer_females}")
    d16.metric("Reprod. w koh. (M / F)", f"{act.n_reproducer_males_in_cohort} / {act.n_reproducer_females_in_cohort}")
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
        "Okresy, ryzyko, reprodukcja, udział linii",
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
        st.caption(
            "Porównanie trzech przedziałów urodzeń (1950–1980, 1981–2000, 2001–dziś) przy tym samym limicie F co powyżej. "
            "Ryzyko linii — heurystyka dla LB/LC (wyższy score = mniej urodzeń / mniej aktywnych ID). "
            "W bazie są tylko dwie nazwane linie hodowlane; „rzadka” linia to ta z niższymi liczbami w tabeli."
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
        st.pyplot(fig_rp, width="stretch")
        st.markdown("**Udział linii w czasie (skumulowane 100 % w dekadzie)**")
        fig_ls = splt.fig_line_share_percent_stacked(df_std)
        st.pyplot(fig_ls, width="stretch")

    with tabs[1]:
        st.caption("Liczba urodzeń w dekadach (1881–obecny rok), podział M/F.")
        sc.help_expander("Interpretacja: Urodzenia wg płci", hc.CHART_BIRTH_SEX, expanded=verbose)
        fig = splt.fig_birth_decades_sex(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[2]:
        st.caption("Urodzenia w dekadach wg linii (LB vs LC).")
        sc.help_expander("Interpretacja: Urodzenia wg linii", hc.CHART_BIRTH_LINE, expanded=verbose)
        fig = splt.fig_birth_decades_line(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[3]:
        st.caption("Stosunek F/M w dekadach od 1900.")
        sc.help_expander("Interpretacja: Female/Male ratio", hc.CHART_FM_RATIO, expanded=verbose)
        fig = splt.fig_female_male_ratio(df_std)
        st.pyplot(fig, width="stretch")

    with tabs[4]:
        st.caption("Średnie MG, CG, EG wg płci.")
        sc.help_expander("Interpretacja: Kompletność (MG/CG/EG) wg płci", hc.CHART_COMP_SEX, expanded=verbose)
        fc, _ = splt.fig_completeness_sex_line(df_std, people)
        st.pyplot(fc, width="stretch")

    with tabs[5]:
        st.caption("Średnie MG, CG, EG wg linii LB/LC/NA.")
        sc.help_expander("Interpretacja: Kompletność wg linii", hc.CHART_COMP_LINE, expanded=verbose)
        _, fl = splt.fig_completeness_sex_line(df_std, people)
        st.pyplot(fl, width="stretch")

    with tabs[6]:
        st.caption("Histogram F w populacji (przy wybranym limicie pokoleń).")
        sc.help_expander("Interpretacja: rozkład F", hc.CHART_HIST_F, expanded=verbose)
        fig = splt.fig_histogram_f(stats.f_values or [])
        st.pyplot(fig, width="stretch")

    with tabs[7]:
        st.caption("Top 20 wkładu genetycznego założycieli (p_i).")
        sc.help_expander("Interpretacja: założyciele p_i", hc.CHART_FOUNDERS_PI, expanded=verbose)
        fig = splt.fig_founder_contributions(stats.founder_contributions or {}, people)
        st.pyplot(fig, width="stretch")

    with tabs[8]:
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

    with tabs[9]:
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

    with tabs[10]:
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

    with tabs[11]:
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

    with tabs[12]:
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
