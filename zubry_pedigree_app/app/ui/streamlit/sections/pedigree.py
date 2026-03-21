"""
Podgląd drzewa przodków dla wybranego numeru ID i zapis rysunku do pliku.
"""

from __future__ import annotations

import io

import streamlit as st

from app.pedigree.ancestor_pedigree import (
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
    get_ancestor_levels_unbounded,
)
from app.ui import help_content as hc
from app.ui.streamlit import common as sc
from app.visualizations.ancestor_plot import plot_ancestor_pedigree


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
    st.markdown("### Rodowód")
    sc.help_expander("Rodowód — graf i linie (sire/dam)", hc.SECTION_PEDIGREE)
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
