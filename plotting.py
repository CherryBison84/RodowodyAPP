from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx


def plot_sex_distribution(sex_series: pd.Series, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    vc = sex_series.dropna().value_counts(normalize=True)
    # Keep stable order for M/F.
    order = ["M", "F"]
    heights = [float(vc.get(k, 0.0)) for k in order]
    ax.bar(order, heights, color=["#4C78A8", "#F58518"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Proporcja")
    ax.set_title(title)
    return fig


def plot_birth_hist(years: pd.Series, title: str, bins: int = 20) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    years = pd.to_numeric(years, errors="coerce").dropna().astype(int)
    if len(years) == 0:
        ax.set_title(title)
        ax.axis("off")
        return fig
    ax.hist(years, bins=bins, color="#54A24B", alpha=0.85)
    ax.set_xlabel("Rok urodzenia")
    ax.set_ylabel("Liczba osobnikow")
    ax.set_title(title)
    return fig


def plot_inbreeding_trend(df_stats: pd.DataFrame, title: str) -> plt.Figure:
    """
    df_stats expected columns: year, F_mean
    """
    fig, ax = plt.subplots(figsize=(8, 4))
    if df_stats.empty:
        ax.set_title(title)
        ax.axis("off")
        return fig
    sns.lineplot(data=df_stats, x="year", y="F_mean", marker="o", ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Rok urodzenia")
    ax.set_ylabel("Sredni inbreeding Wrighta (F)")
    ax.set_ylim(bottom=0)
    return fig


def plot_generations_density(generations: pd.Series, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    x = pd.to_numeric(generations, errors="coerce").dropna()
    if x.empty:
        ax.set_title(title)
        ax.axis("off")
        return fig
    sns.kdeplot(x=x, fill=True, bw_adjust=0.5, ax=ax)
    ax.set_xlabel("Liczba pokolen sledzonych (do founderow)")
    ax.set_ylabel("Gestosc")
    ax.set_title(title)
    return fig


def plot_pedigree_subgraph(
    G: nx.DiGraph,
    individual_id: str,
    sex_of: Dict[str, Optional[str]],
    birth_of: Dict[str, object],
    generations: int,
    max_nodes: int = 250,
) -> plt.Figure:
    """
    Draw a small pedigree subgraph (node + ancestors up to `generations`) in a DAG-friendly layout.
    """
    # Limit draw size for UI.
    nodes = list(G.nodes)
    if len(nodes) > max_nodes:
        # If too big, just draw induced by immediate ancestors (fallback).
        # This keeps UI responsive for extreme pedigrees.
        H = G.copy()
        nodes = nodes[:max_nodes]
        G = H.subgraph(nodes).copy()

    # Compute generation levels using reverse distances from the individual.
    # Levels: 0 = individual, 1 = parents, ...
    rev = G.reverse(copy=False)
    level: Dict[str, int] = {individual_id: 0}
    from collections import deque

    q = deque([individual_id])
    while q:
        cur = q.popleft()
        d = level[cur]
        if d >= generations:
            continue
        for parent in rev.successors(cur):
            if parent in level:
                continue
            level[parent] = d + 1
            q.append(parent)

    # Position nodes by levels (y coordinate), x coordinate by index within level.
    levels_sorted = sorted(level.values())
    nodes_by_level: Dict[int, list] = {g: [] for g in levels_sorted}
    for n, d in level.items():
        if d <= generations:
            nodes_by_level[d].append(n)
    for d in nodes_by_level:
        nodes_by_level[d].sort()

    pos: Dict[str, tuple] = {}
    for d in levels_sorted:
        arr = nodes_by_level.get(d, [])
        if not arr:
            continue
        # Spread nodes across x range.
        xs = np.linspace(-1, 1, num=len(arr)) if len(arr) > 1 else np.array([0.0])
        for i, n in enumerate(arr):
            pos[n] = (float(xs[i]), float(-d))

    # Colors by sex.
    def node_color(n: str) -> str:
        s = sex_of.get(n)
        if s == "M":
            return "#4C78A8"
        if s == "F":
            return "#F58518"
        return "#BDBDBD"

    labels = {}
    for n in G.nodes:
        short = str(n)
        if len(short) > 10:
            short = short[:7] + "..."
        if n in birth_of and birth_of[n] is not None and not pd.isna(birth_of[n]):
            b = pd.to_datetime(birth_of[n], errors="coerce")
            if not pd.isna(b):
                labels[n] = f"{short}\n({int(b.year)})"
            else:
                labels[n] = short
        else:
            labels[n] = short

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_axis_off()

    # Draw edges first.
    for u, v in G.edges:
        # parent -> child, so u should be at higher level number than v (since v is descendant).
        if u not in pos or v not in pos:
            continue
        x1, y1 = pos[u]
        x2, y2 = pos[v]
        ax.plot([x1, x2], [y1, y2], color="#444444", linewidth=1, alpha=0.6, zorder=1)

    # Draw nodes on top.
    for n in G.nodes:
        if n not in pos:
            continue
        x, y = pos[n]
        is_target = n == individual_id
        size = 900 if is_target else 600
        ax.scatter(
            [x],
            [y],
            s=size,
            color=node_color(n),
            edgecolors="black" if is_target else "none",
            linewidths=2 if is_target else 0,
            zorder=2,
            alpha=0.95,
        )
        ax.text(x, y, labels.get(n, str(n)), ha="center", va="center", fontsize=8, zorder=3)

    ax.set_title(f"Rodowod: {individual_id} (do {generations} pok.)")
    return fig

