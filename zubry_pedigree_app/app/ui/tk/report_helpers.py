"""
Składanie raportów tekstowych i PDF z wykresami dla jednego osobnika lub całej populacji.
"""

from __future__ import annotations

from typing import Any, Dict

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.analytics.population_genetics import compute_population_genetics_stats
from app.pedigree.ancestor_pedigree import (
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
    get_ancestor_levels_unbounded,
)
from app.visualizations.ancestor_plot import plot_ancestor_pedigree

# Zgodnie z gui_pro.POP_FOUNDERS_PI_TOP_N (unikamy importu cyklicznego gui_pro → report_helpers).
_POP_FOUNDERS_PI_TOP_N = 50


def write_text_pages_to_pdf(pdf: PdfPages, *, text: str) -> None:
    lines = text.splitlines()
    max_lines = 48
    for start in range(0, len(lines), max_lines):
        fig_t = plt.Figure(figsize=(8.27, 11.69), dpi=100)
        ax_t = fig_t.add_subplot(1, 1, 1)
        ax_t.axis("off")
        y = 0.98
        dy = 0.02
        for i, line in enumerate(lines[start : start + max_lines]):
            ax_t.text(0.02, y - i * dy, line, fontsize=9, va="top")
        fig_t.tight_layout()
        pdf.savefig(fig_t)
        plt.close(fig_t)


def build_individual_report_figures(
    *,
    person_id: str,
    people: Dict[str, Any],
    ind_unbounded: bool,
    ind_depth: int,
    colors: Any,
) -> list[plt.Figure]:
    figs: list[plt.Figure] = []
    if not person_id or person_id not in people:
        return figs

    if ind_unbounded:
        f_res = wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=None)
        graph_depth_fallback = max(0, int(ind_depth))
        max_pedigree_nodes = 280
    else:
        depth = max(0, int(ind_depth))
        f_res = wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=depth)
        graph_depth_fallback = depth
        max_pedigree_nodes = 280

    # pedigree
    try:
        if ind_unbounded:
            levels_unc = get_ancestor_levels_unbounded(person_id=person_id, people=people)
            if len(levels_unc) > max_pedigree_nodes:
                levels, edges = get_ancestor_levels_and_edges(
                    person_id=person_id,
                    depth=graph_depth_fallback,
                    people=people,
                )
                note_txt = f"(graf przodków: limit do {graph_depth_fallback} dla wydajności; N={len(levels_unc)})"
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
                note_txt = f"(graf przodków: bez limitu; N={len(levels)})"
        else:
            target_depth = max(0, int(ind_depth))
            depth_for_graph = target_depth
            levels = {}
            edges = []
            while depth_for_graph >= 0:
                levels_try, edges_try = get_ancestor_levels_and_edges(
                    person_id=person_id,
                    depth=depth_for_graph,
                    people=people,
                )
                if len(levels_try) <= max_pedigree_nodes or depth_for_graph == 0:
                    levels = levels_try
                    edges = edges_try
                    break
                depth_for_graph -= 1
            note_txt = f"(graf przodków: limit={depth_for_graph} (N={len(levels)}))"

        if levels:
            people_all = ensure_people_for_nodes(levels=levels, people=people)
            fig_g = plot_ancestor_pedigree(
                person_id=person_id,
                levels=levels,
                edges=edges,
                people=people_all,
                readable_mode=True,
                enable_click_highlight=False,
                full_labels_limit=90,
            )
            fig_g.suptitle(f"Rodowód przodków (ID {person_id}) {note_txt}", fontsize=11, y=0.98)
            figs.append(fig_g)
    except Exception:
        pass

    # F diagnostic
    try:
        max_trace_depth = min(20, int(f_res.used_generations) if f_res.used_generations else 0)
        depths = list(range(0, max_trace_depth + 1))
        Fs = [
            wright_inbreeding_F(
                person_id=person_id,
                people=people,
                max_generations_back=int(d),
            ).F
            for d in depths
        ]
        fig, ax = plt.subplots(figsize=(8.2, 4.1), dpi=100)
        ax.plot(depths, Fs, marker="o", linewidth=2, color=colors.EDGE_PLOT)
        ax.set_title(f"Inbred (Wright F) — diagnostyka (ID {person_id})")
        ax.set_xlabel("max pokoleń")
        ax.set_ylabel("F")
        ax.grid(True, alpha=0.25)
        figs.append(fig)
    except Exception:
        pass

    # completeness
    try:
        levels = get_ancestor_levels_unbounded(person_id=person_id, people=people)
        by_gen: dict[int, int] = {}
        for _aid, lvl in levels.items():
            try:
                g = int(lvl)
            except Exception:
                continue
            if g <= 0:
                continue
            by_gen[g] = by_gen.get(g, 0) + 1

        fig2 = plt.Figure(figsize=(8.2, 4.1), dpi=100)
        ax_a = fig2.add_subplot(1, 2, 1)
        ax_pcl = fig2.add_subplot(1, 2, 2)
        if by_gen:
            gens = sorted(by_gen.keys())
            a_vals = [by_gen[g] for g in gens]
            pcl_vals = [float(by_gen[g]) / float(2**g) for g in gens]
            ax_a.bar([str(g) for g in gens], a_vals, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
            ax_a.set_title("Ankiety przodków (a_g)")
            ax_a.set_xlabel("pokolenie (g)")
            ax_a.set_ylabel("a_g")
            ax_a.tick_params(axis="x", labelsize=8)

            ax_pcl.plot(gens, pcl_vals, marker="o", linewidth=2, color=colors.BUTTON_BG)
            ax_pcl.axhline(1.0, color=colors.ACCENT, linewidth=1, alpha=0.6)
            ax_pcl.set_title("Kompletność per pokolenie (PCL)")
            ax_pcl.set_xlabel("pokolenie (g)")
            ax_pcl.set_ylabel("PCL = a_g / 2^g")
            ax_pcl.set_ylim(0, 1.05)
            ax_pcl.grid(True, alpha=0.25)
        else:
            ax_a.text(0.5, 0.5, "Brak danych ANC", ha="center", va="center")
            ax_a.axis("off")
            ax_pcl.axis("off")

        fig2.tight_layout()
        figs.append(fig2)
    except Exception:
        pass

    return figs


def build_population_report_figures(
    *,
    people: Dict[str, Any],
    df_std: Any,
    pop_unbounded: bool,
    pop_depth: int,
    colors: Any,
) -> list[plt.Figure]:
    figs: list[plt.Figure] = []
    try:
        max_generations_back = None if bool(pop_unbounded) else max(0, int(pop_depth))
    except Exception:
        max_generations_back = 4

    try:
        stats = compute_population_genetics_stats(
            df_std=df_std,
            people=people,
            max_generations_back=max_generations_back,
            calc_f=True,
            calc_completeness=True,
            calc_founders=True,
            calc_lines=True,
        )

        if stats.f_values:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.2, 4.1), dpi=100)
            ax1.hist(stats.f_values, bins=30, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
            ax1.set_title("Rozkład F (Wright) w populacji")
            ax1.set_xlabel("F")
            ax1.set_ylabel("liczba osobników")

            ax2.boxplot(stats.f_values, vert=True, patch_artist=True)
            ax2.set_title("Boxplot F (Wright)")
            ax2.set_ylabel("F")
            ax2.grid(True, alpha=0.2)
            figs.append(fig)

        if stats.founder_contributions:
            items = sorted(stats.founder_contributions.items(), key=lambda kv: kv[1], reverse=True)[
                :_POP_FOUNDERS_PI_TOP_N
            ]
            labels = [str(kv[0]) for kv in items]
            vals = [float(kv[1]) for kv in items]
            fig_b = plt.subplots(figsize=(11.0, 4.2), dpi=100)[0]
            axb = fig_b.gca()
            axb.bar(labels, vals, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
            axb.set_title(f"Top {len(items)} p_i — wkład genetyczny założycieli")
            axb.set_xlabel("ID założyciela")
            axb.set_ylabel("p_i (znorm.)")
            axb.tick_params(axis="x", labelsize=7, rotation=75)
            figs.append(fig_b)
    except Exception:
        pass

    return figs

