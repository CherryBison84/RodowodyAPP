"""Zakładka: statystyki populacji i wykresy."""

from __future__ import annotations

import io

import matplotlib.pyplot as plt
import streamlit as st

import app.ui.streamlit.streamlit_plotting as splt
from app.analytics.population_gi import compute_gi_and_family_data
from app.analytics.population_genetics import TEST_ID, compute_population_genetics_stats
from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def _figure_to_jpeg_bytes(fig: plt.Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", dpi=110, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def section_population(df_std: pd.DataFrame, people: dict) -> None:
    st.markdown("### Populacja")
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
        "Urodzenia: płeć",
        "Urodzenia: LB/LC",
        "F/M ratio",
        "Kompletność: płeć",
        "Kompletność: linie",
        "Rozkład F",
        "Założyciele p_i",
        "GI (średni)",
        "GI trend",
        "Rodziny (pełne)",
        "F/RIA: płeć",
        "F/RIA: linie",
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
        st.caption("Top 10 wkładu genetycznego założycieli (p_i).")
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
