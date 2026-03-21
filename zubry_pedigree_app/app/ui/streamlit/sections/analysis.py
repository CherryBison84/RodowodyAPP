"""Zakładka Analizy: Inbred + Mating."""

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
from app.ui import help_content as hc
from app.ui.streamlit import common as sc


def section_analysis_inbred(people: dict) -> None:
    st.markdown("#### Inbred (Wright F)")
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
    st.markdown("#### Mating — ranking par (minimalne F potomka)")
    sc.help_expander("Mating — jak interpretować ranking", hc.SECTION_MATING)
    st.caption("Filtr wieku: ostatnie 15 lat (jak w Tk). Limity kandydatów ograniczają czas obliczeń.")

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

    if st.button("Policz ranking TOP 10", type="primary", key="mat_go"):
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
        ranked = sorted(zip(Fs, pairs), key=lambda x: x[0])[:10]
        lines = []
        for i, (fv, (sire_id, dam_id)) in enumerate(ranked, 1):
            sn = getattr(people.get(sire_id), "name", None)
            dn = getattr(people.get(dam_id), "name", None)
            lines.append(
                f"{i}. F={fv:.6f} | sire={sire_id} ({sn or '-'}) × dam={dam_id} ({dn or '-'})"
            )
        st.text("\n".join(lines))
