from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Dict, Optional, Set

import numpy as np
import pandas as pd
import streamlit as st

from bison_pedigree import BisonPedigree
from plotting import (
    plot_birth_hist,
    plot_generations_density,
    plot_inbreeding_trend,
    plot_pedigree_subgraph,
    plot_sex_distribution,
)


st.set_page_config(page_title="Rodowody Zubrow", layout="wide")
st.title("Analiza rodowodowa zubrow (szkielet)")


@st.cache_data(show_spinner=False)
def _read_uploaded_file(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    bio = BytesIO(file_bytes)
    name_lower = file_name.lower()
    if name_lower.endswith(".csv"):
        return pd.read_csv(bio)
    # Excel (xlsx/xls)
    return pd.read_excel(bio)


def _years_for_ids(engine: BisonPedigree, ids: Set[str]) -> pd.Series:
    years = {nid: engine.birth_of.get(nid) for nid in ids}
    s = pd.to_datetime(pd.Series(years), errors="coerce", utc=False)
    return s.dt.year


def _sex_for_ids(engine: BisonPedigree, ids: Set[str]) -> pd.Series:
    return pd.Series({nid: engine.sex_of.get(nid) for nid in ids}, name="sex")


def _get_cache_bucket() -> Dict:
    if "computed_cache" not in st.session_state:
        st.session_state.computed_cache = {}
    return st.session_state.computed_cache


def _get_genetics_results(
    engine: BisonPedigree,
    groups: object,
    inbreeding_max_depth: int,
    rp_birth_year_start: Optional[int],
    rp_birth_year_end: Optional[int],
) -> Dict[str, object]:
    rp = groups.rp
    cache_bucket = _get_cache_bucket()
    key = (
        "genetics",
        st.session_state.get("file_hash"),
        rp_birth_year_start,
        rp_birth_year_end,
        inbreeding_max_depth,
    )
    if key in cache_bucket:
        return cache_bucket[key]

    with st.spinner("Liczenie inbredu i metryk genetycznych..."):
        F = engine.compute_inbreeding_wright(rp, max_depth=inbreeding_max_depth)
        fe = engine.effective_number_of_founders(rp)
        fa = engine.effective_number_of_ancestors(rp)
        bottleneck = float("nan")
        if fa is not None and not (pd.isna(fa)) and fa > 0:
            bottleneck = float(fe) / float(fa)

        Ne = engine.Ne_from_inbreeding_trend(rp, F)
        gi = engine.intergenerational_interval(rp)
        traced = engine.traced_generations_stats(rp)
        gens_traced = engine.tracked_generations(rp)
        father_line = engine.line_length_distribution(rp, parent_role="father")
        mother_line = engine.line_length_distribution(rp, parent_role="mother")

        # Inbreeding trend by birth year.
        tmp = []
        for nid in rp:
            b = engine.birth_of.get(nid)
            if b is None or pd.isna(b):
                continue
            y = int(pd.to_datetime(b, errors="coerce").year)
            f = F.get(nid, np.nan)
            if pd.isna(f):
                continue
            tmp.append((y, float(f)))
        df_stats = pd.DataFrame(tmp, columns=["year", "F"]).groupby("year", as_index=False)["F"].mean()
        df_stats = df_stats.rename(columns={"F": "F_mean"}).sort_values("year")

    out = {
        "F": F,
        "fe": fe,
        "fa": fa,
        "bottleneck_fe_fa": bottleneck,
        "Ne": Ne,
        "intergenerational_interval": gi,
        "traced_generations_stats": traced,
        "gens_traced": gens_traced,
        "father_line": father_line,
        "mother_line": mother_line,
        "inbreeding_trend": df_stats,
    }
    cache_bucket[key] = out
    return out


with st.sidebar:
    st.header("Wejscie")
    uploaded = st.file_uploader("Wgraj CSV lub Excel", type=["csv", "xlsx", "xls"])

    st.divider()
    st.header("Definicja RP (Reference Population)")
    rp_start_year: Optional[int] = None
    rp_end_year: Optional[int] = None

    st.header("Parametry obliczen")
    max_tree_generations = st.slider("Generacje do wizualizacji drzewa", 1, 6, 4)
    inbreeding_max_depth = st.slider("Glebokosc przodkow dla F", 5, 30, 20)
    pci_max_generations = st.slider("Generacje dla PCI", 2, 6, 4)


if uploaded is None:
    st.info("Wgraj plik CSV/Excel, aby uruchomic analize.")
    st.stop()

file_bytes = uploaded.getvalue()
file_hash = hashlib.md5(file_bytes).hexdigest()
file_name = uploaded.name

if st.session_state.get("file_hash") != file_hash:
    df_raw = _read_uploaded_file(file_bytes, file_name)
    st.session_state.file_hash = file_hash
    st.session_state.df_raw = df_raw
    st.session_state.engine = None
    st.session_state.groups = None
    st.session_state.computed_cache = {}

    # Build engine.
    with st.spinner("Budowanie grafu rodowodowego (NetworkX)..."):
        st.session_state.engine = BisonPedigree(df_raw)

    engine: BisonPedigree = st.session_state.engine
    # Determine birth year bounds among dataset IDs.
    years = _years_for_ids(engine, engine.data_ids).dropna().astype(int)
    if len(years) > 0:
        min_y, max_y = int(years.min()), int(years.max())
    else:
        min_y, max_y = 0, 0

    # Default RP interval.
    st.session_state.rp_start_year = min_y
    st.session_state.rp_end_year = max_y

else:
    engine = st.session_state.engine


with st.sidebar:
    years_all = _years_for_ids(engine, engine.data_ids).dropna().astype(int)
    if len(years_all) > 0:
        min_y, max_y = int(years_all.min()), int(years_all.max())
        rp_start_year = st.slider("Start (rok urodzen) RP", min_y, max_y, st.session_state.get("rp_start_year", min_y))
        rp_end_year = st.slider("Koniec (rok urodzen) RP", min_y, max_y, st.session_state.get("rp_end_year", max_y))
    else:
        rp_start_year = None
        rp_end_year = None

    if rp_start_year is not None and rp_end_year is not None and rp_end_year < rp_start_year:
        st.error("Koniec RP musi byc >= start RP.")
        st.stop()


groups = engine.filter_populations(rp_birth_year_start=rp_start_year, rp_birth_year_end=rp_end_year)
st.session_state.groups = groups

tabs = st.tabs(["Dashboard", "Analiza Rodowodowa", "Rownorodnosc Genetyczna", "Walidacja", "Wizualizacje"])

tp = groups.tp
rp = groups.rp
anc = groups.anc

with tabs[0]:
    st.subheader("Populacje")
    col1, col2, col3 = st.columns(3)
    col1.metric("TP (wszystkie dane)", len(tp))
    col2.metric("RP (zakres urodzen)", len(rp))
    col3.metric("ANC (przodkowie RP)", len(anc))

    st.subheader("Plec")
    sex_tp = _sex_for_ids(engine, tp)
    fig = plot_sex_distribution(sex_tp, "Proporcja plci (TP)")
    st.pyplot(fig, clear_figure=True)

    if len(rp) > 0:
        st.subheader("Rok urodzenia (histogram RP)")
        years_rp = _years_for_ids(engine, rp).dropna().astype(int)
        fig = plot_birth_hist(years_rp, "Histogram urodzen RP", bins=20)
        st.pyplot(fig, clear_figure=True)
    else:
        st.info("Brak osobnikow w RP dla wybranego przedzialu lat.")

with tabs[1]:
    st.subheader("Kompletnosc rodowodu (PCI)")
    if len(rp) == 0:
        st.warning("Brak RP do wyliczenia PCI.")
    else:
        with st.spinner("Liczenie PCI..."):
            pci = engine.pci(rp, max_generations=pci_max_generations)
        st.write(pci)

    st.subheader("Wizualizacja drzewa wybranego osobnika")
    if len(rp) == 0:
        st.info("Wybierz inny przedzial lat, aby miec RP.")
    else:
        default_id = sorted(list(rp))[0]
        chosen = st.selectbox("ID osobnika (z RP)", sorted(list(rp)), index=0 if default_id else 0)
        subG = engine.pedigree_subgraph(chosen, generations=max_tree_generations)
        fig = plot_pedigree_subgraph(
            subG,
            individual_id=chosen,
            sex_of=engine.sex_of,
            birth_of=engine.birth_of,
            generations=max_tree_generations,
        )
        st.pyplot(fig, clear_figure=True)

with tabs[2]:
    st.subheader("Metryki genetyczne i demograficzne")
    if len(rp) == 0:
        st.warning("Brak RP do wyliczen genetycznych.")
    else:
        val = engine.validate()
        if not val["is_dag"]:
            st.error("Nie mozna liczyc inbredu Wrighta: w rodowodzie wykryto cykle (graf nie jest DAG).")
            st.stop()
        results = _get_genetics_results(
            engine,
            groups,
            inbreeding_max_depth=inbreeding_max_depth,
            rp_birth_year_start=rp_start_year,
            rp_birth_year_end=rp_end_year,
        )

        col1, col2, col3 = st.columns(3)
        col1.metric("fe (efektywna liczba zalozycieli)", f"{results['fe']:.3g}" if pd.notna(results["fe"]) else "nan")
        col2.metric("fa (efektywna liczba przodkow)", f"{results['fa']:.3g}" if pd.notna(results["fa"]) else "nan")
        bott = results.get("bottleneck_fe_fa", float("nan"))
        col3.metric("Efekt waskiego gardla fe/fa", f"{bott:.3g}" if pd.notna(bott) else "nan")

        st.markdown("**Trend inbredu (sredni F po latach urodzenia)**")
        st.pyplot(plot_inbreeding_trend(results["inbreeding_trend"], "Trend inbredu w RP"), clear_figure=True)

        st.subheader("Odstep miedzypokoleniowy")
        gi = results["intergenerational_interval"]
        st.write(gi)

        st.subheader("Ne (z trendu F)")
        st.write({"Ne": results["Ne"]})

        st.subheader("Sledzone pokolenia")
        st.write(results["traced_generations_stats"])

with tabs[3]:
    st.subheader("Walidacja danych i rodowodu")
    val = engine.validate()
    st.write("Graf DAG:", val["is_dag"])
    st.write("Przykladowe cykle:", val.get("cycles_sample", []))

    st.write("Liczba naruszen wieku (rodzic mlodszy od dziecka):", val["parent_age_violations_count"])
    if val["parent_age_violations_sample"]:
        st.dataframe(pd.DataFrame(val["parent_age_violations_sample"], columns=["child_id", "parent_id", "issue"]))

    st.write("Rodzice spoza tabeli (odwolania w kolumnach Ojciec/Matka):", val["external_parent_references_count"])

    st.divider()
    st.subheader("Dodatkowe kontrole w RP")
    if len(rp) > 0:
        missing_birth = [nid for nid in rp if engine.birth_of.get(nid) is None or pd.isna(engine.birth_of.get(nid))]
        missing_sex = [nid for nid in rp if engine.sex_of.get(nid) is None]
        st.write({"brak dat urodzenia w RP": len(missing_birth), "brak plci w RP": len(missing_sex)})
        if missing_birth:
            st.caption(f"Przyklad brakujacych dat: {missing_birth[:10]}")
        if missing_sex:
            st.caption(f"Przyklad brakujacych plci: {missing_sex[:10]}")

with tabs[4]:
    st.subheader("Wizualizacje: pokolenia i inbredu")
    if len(rp) == 0:
        st.info("Brak RP dla wybranego przedzialu lat.")
    else:
        val = engine.validate()
        if not val["is_dag"]:
            st.error("Nie mozna rysowac trendow inbredu: w rodowodzie wykryto cykle (graf nie jest DAG).")
            st.stop()
        results = _get_genetics_results(
            engine,
            groups,
            inbreeding_max_depth=inbreeding_max_depth,
            rp_birth_year_start=rp_start_year,
            rp_birth_year_end=rp_end_year,
        )
        st.pyplot(plot_generations_density(results["gens_traced"], "Gestosc: liczba pokolen sledzonych (RP)"), clear_figure=True)
        st.pyplot(plot_inbreeding_trend(results["inbreeding_trend"], "Trend inbredu w czasie (RP)"), clear_figure=True)

