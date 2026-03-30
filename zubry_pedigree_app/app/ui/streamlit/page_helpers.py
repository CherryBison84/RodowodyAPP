"""Wspólne helpery UI Streamlit: grafy rodowodów, metryki PCI/plan hodowlany."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from app.pedigree.ancestor_pedigree import (
    Person,
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
    get_ancestor_levels_unbounded,
)
import app.ui.streamlit.streamlit_plotting as splt
from app.visualizations.ancestor_plot import plot_ancestor_pedigree

PLAN_HYPO_ID = "__PLAN_HYPO_OFFSPRING__"


def pci_bundle_for_breeding(pid: str, pmap: dict) -> tuple[int, float, float]:
    """MG, EG, PCI dla przodków bez limitu głębokości (kompletność rodowodu)."""
    mg, eg, pci = 0, 0.0, 0.0
    try:
        levels = get_ancestor_levels_unbounded(person_id=pid, people=pmap)
        by_gen: dict[int, int] = {}
        for _aid, lvl in levels.items():
            if lvl is None:
                continue
            try:
                g = int(lvl)
            except Exception:
                continue
            if g <= 0:
                continue
            by_gen[g] = by_gen.get(g, 0) + 1
        if by_gen:
            mg = int(max(by_gen.keys()))
            pci_sum = 0.0
            for g in range(1, mg + 1):
                a_g = int(by_gen.get(g, 0))
                pcl_g = float(a_g) / float(2**g)
                eg += pcl_g
                pci_sum += pcl_g
            pci = pci_sum / float(mg) if mg > 0 else 0.0
    except Exception:
        pass
    return mg, eg, pci


def plan_pedigree_plot_depth(max_back: int | None) -> int:
    if max_back is None:
        return 4
    return max(1, min(int(max_back), 4))


def breeding_hypo_offspring_figure(
    sire_id: str,
    dam_id: str,
    people: dict,
    max_generations_back: int | None,
):
    """Graf przodków hipotetycznego potomka (ograniczona głębokość wizualna dla czytelności)."""
    plot_depth = plan_pedigree_plot_depth(max_generations_back)
    people_h = dict(people)
    people_h[PLAN_HYPO_ID] = Person(
        id=PLAN_HYPO_ID,
        name="potomek (hipotetyczny)",
        sex=None,
        line=None,
        father_id=str(sire_id),
        mother_id=str(dam_id),
        birth_year=None,
    )
    levels, edges = get_ancestor_levels_and_edges(
        person_id=PLAN_HYPO_ID,
        depth=plot_depth,
        people=people_h,
    )
    people_all = ensure_people_for_nodes(levels=levels, people=people_h)
    fig = plot_ancestor_pedigree(
        person_id=PLAN_HYPO_ID,
        levels=levels,
        edges=edges,
        people=people_all,
        readable_mode=True,
        enable_click_highlight=False,
    )
    try:
        fig.suptitle(
            f"Hipotetyczny potomek: {sire_id} × {dam_id}  (do {plot_depth} pok. wstecz)",
            fontsize=splt.ST_FS_TITLE,
            y=0.98,
        )
    except Exception:
        pass
    return fig


def build_pedigree_figure(
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
        fig.suptitle(f"Rodowód przodków {note}", fontsize=splt.ST_FS_TITLE, y=0.98)
    except Exception:
        pass
    return fig, None


def individual_pcl_dataframe(person_id: str, people: dict) -> tuple[pd.DataFrame, float, float]:
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
