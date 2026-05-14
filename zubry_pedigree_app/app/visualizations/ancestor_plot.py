"""Rysowanie grafu rodowodu (networkx + matplotlib, bez backendu GUI)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

_mpl_dir = Path(__file__).resolve().parents[3] / ".mplconfig"
try:
    _mpl_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(_mpl_dir))
    # Fontconfig/Matplotlib korzysta też z cache w stylu ~/.cache, a w sandboxie nie zawsze jest to katalog zapisywalny.
    _cache_home = Path(__file__).resolve().parents[3] / ".cache"
    _cache_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("XDG_CACHE_HOME", str(_cache_home))
except Exception:
    # W najgorszym przypadku zostawiamy ustawienia systemowe (może pojawić się ostrzeżenie).
    pass

import matplotlib

matplotlib.use("Agg")  # Brak interaktywnego backendu — rysunek tylko do bufora / pliku.

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.lines import Line2D
from matplotlib import patheffects

from app.pedigree.ancestor_pedigree import Person
from app.ui.typography import apply_matplotlib_fonts

apply_matplotlib_fonts()


def _node_color(sex: Optional[str]) -> str:
    if sex == "M":
        return "#9ecbff"
    if sex == "F":
        return "#ffb4c1"
    return "#d6d0c4"


def _birth_year_label(person: Person | None) -> str:
    if person is None:
        return "NA"
    y = getattr(person, "birth_year", None)
    if y is None:
        return "NA"
    try:
        # numpy floating NaN handling
        if isinstance(y, float) and np.isnan(y):
            return "NA"
    except Exception:
        pass
    try:
        y_int = int(float(y))
    except Exception:
        return "NA"
    if 1000 <= y_int <= 9999:
        return str(y_int)
    return "NA"


def _line_text_and_color(line: Optional[str]) -> Tuple[str, str]:
    """
    LB/LC pod rokiem urodzenia na węzłach.
    """

    if line == "LB":
        return "LB", "#d64545"
    if line == "LC":
        return "LC", "#2e8b57"
    return "NA", "#9aa3a2"


def _draw_pedigree_edges(
    *,
    G: nx.DiGraph,
    pos: Dict[str, Tuple[float, float]],
    ax,
    readable_mode: bool,
    max_level: int,
    edge_width: float,
    edge_alpha: float,
) -> None:
    if readable_mode:
        nx.draw_networkx_edges(
            G,
            pos,
            ax=ax,
            arrows=True,
            arrowstyle="-|>",
            arrowsize=14,
            width=edge_width,
            edge_color="#6b5b4d",
            alpha=edge_alpha,
            connectionstyle="arc3,rad=0.07" if max_level >= 3 else "arc3,rad=0.05",
        )
        return

    nx.draw_networkx_edges(
        G,
        pos,
        ax=ax,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=12,
        width=edge_width,
        edge_color="#4f443a",
        alpha=edge_alpha,
        connectionstyle="arc3,rad=0.05",
    )


def _draw_line_badges(
    *,
    ax,
    pos: Dict[str, Tuple[float, float]],
    line_text_map: Dict[str, str],
    line_color_map: Dict[str, str],
    label_font_size: int,
    node_size: int,
) -> None:
    max_abs_x = max((abs(float(x)) for x, _ in pos.values()), default=1.0)
    dx_badge = min(0.18, max(0.06, 0.05 * max_abs_x))
    dy_badge = 0.05
    badge_font_size = max(6, label_font_size - 2)
    badge_size = max(45.0, float(node_size) * 0.05)

    for nid, (x, y) in pos.items():
        line_txt = line_text_map.get(nid)
        line_color = line_color_map.get(nid)
        if not line_txt or line_txt == "NA" or not line_color:
            continue

        bx = float(x) + dx_badge
        by = float(y) + dy_badge

        ax.scatter(
            [bx],
            [by],
            s=badge_size,
            marker="s",
            c=[line_color],
            edgecolors="#333333",
            linewidths=0.75,
            zorder=5,
        )
        ax.text(
            bx,
            by,
            line_txt,
            ha="center",
            va="center",
            fontsize=badge_font_size,
            fontweight="bold",
            color="white",
            zorder=6,
        )


def _add_combined_legend(ax) -> None:
    handles = [
        Line2D([0], [0], marker="o", linestyle="None", markersize=10, markerfacecolor=_node_color("M"), markeredgecolor="#333333"),
        Line2D([0], [0], marker="o", linestyle="None", markersize=10, markerfacecolor=_node_color("F"), markeredgecolor="#333333"),
        Line2D([0], [0], marker="s", linestyle="None", markersize=10, markerfacecolor="#d64545", markeredgecolor="#333333"),
        Line2D([0], [0], marker="s", linestyle="None", markersize=10, markerfacecolor="#2e8b57", markeredgecolor="#333333"),
    ]
    ax.legend(
        handles,
        ["M (ojciec)", "F (matka)", "LB", "LC"],
        loc="upper right",
        frameon=True,
        fontsize=9,
        borderpad=0.25,
        labelspacing=0.25,
        handletextpad=0.5,
        ncol=2,
    )


def plot_layered_pedigree(
    person_id: str,
    vertical: Dict[str, int],
    edges: List[Tuple[str, str]],
    people: Dict[str, Person],
    *,
    max_nodes_for_layout_warning: int = 250,
    readable_mode: bool = True,
    full_labels_limit: int = 220,
    readable_label_depth: int = 2,
    enable_click_highlight: bool = False,
    on_node_click: Optional[Callable[[str, bool], None]] = None,
) -> plt.Figure:
    """
    Warstwowy graf **rodzic → dziecko** z dowolnym podziałem pionowym.

    `vertical[n]` to współrzędna Y węzła `n` (matplotlib): np. **ujemne** — przodkowie
    (ojciec/matka pod osią osoby startowej, jak dotychczas), **0** — osoba startowa,
    **dodatnie** — potomkowie (nad osią startu). Łączenie przodków i potomków w jednym
    rysunku: `vertical = {-L_anc … 0 … +L_desc}`.
    """
    if not vertical:
        fig, ax = plt.subplots(figsize=(10.5, 5.25))
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig

    if len(vertical) > max_nodes_for_layout_warning:
        pass

    G = nx.DiGraph()
    for nid in vertical.keys():
        G.add_node(nid)
    for parent, child in edges:
        if parent in vertical and child in vertical:
            G.add_edge(parent, child)

    by_band: Dict[int, List[str]] = {}
    for nid, band in vertical.items():
        by_band.setdefault(int(band), []).append(nid)
    for b in by_band:
        by_band[b].sort()

    bands_sorted = sorted(by_band.keys())
    y_span = float(max(bands_sorted) - min(bands_sorted)) if bands_sorted else 0.0
    total_nodes = len(vertical)

    in_neighbors: Dict[str, List[str]] = {}
    out_neighbors: Dict[str, List[str]] = {}
    for parent, child in edges:
        if parent not in vertical or child not in vertical:
            continue
        out_neighbors.setdefault(parent, []).append(child)
        in_neighbors.setdefault(child, []).append(parent)

    def _reorder_levels(iterations: int = 4) -> None:
        for _ in range(iterations):
            for i in range(1, len(bands_sorted)):
                prev_band = bands_sorted[i - 1]
                cur_band = bands_sorted[i]
                prev_nodes = by_band.get(prev_band, [])
                idx_prev = {nid: j for j, nid in enumerate(prev_nodes)}

                cur_nodes = by_band.get(cur_band, [])
                if not cur_nodes:
                    continue

                def score(nid: str) -> float:
                    parents = [p for p in in_neighbors.get(nid, []) if vertical.get(p) == prev_band]
                    if not parents:
                        return float("inf")
                    return float(sum(idx_prev.get(p, 0) for p in parents)) / float(len(parents))

                by_band[cur_band] = sorted(cur_nodes, key=lambda nid: (score(nid), str(nid)))

            for i in range(len(bands_sorted) - 2, -1, -1):
                cur_band = bands_sorted[i]
                next_band = bands_sorted[i + 1]
                next_nodes = by_band.get(next_band, [])
                idx_next = {nid: j for j, nid in enumerate(next_nodes)}

                cur_nodes = by_band.get(cur_band, [])
                if not cur_nodes:
                    continue

                def score2(nid: str) -> float:
                    children = [c for c in out_neighbors.get(nid, []) if vertical.get(c) == next_band]
                    if not children:
                        return float("inf")
                    return float(sum(idx_next.get(c, 0) for c in children)) / float(len(children))

                by_band[cur_band] = sorted(cur_nodes, key=lambda nid: (score2(nid), str(nid)))

    _reorder_levels(iterations=4)

    pos: Dict[str, Tuple[float, float]] = {}
    for band in bands_sorted:
        nodes = by_band.get(band, [])
        if not nodes:
            continue

        max_chars = 0
        for nid in nodes:
            person = people.get(nid)
            name = getattr(person, "name", None) if person else None
            year_str = _birth_year_label(person)
            name_part = ""
            v_here = vertical.get(nid, 0)
            shallow = v_here == 0 or abs(int(v_here)) == 1
            if not readable_mode or total_nodes <= full_labels_limit:
                name_part = str(name) if name else ""
            else:
                if shallow and name:
                    name_part = str(name)
            est = len(str(nid)) + len(name_part) + len(year_str)
            max_chars = max(max_chars, est)

        x_span = float(1.35 + max_chars / 84.0 + 0.29 * float(len(nodes)))

        if len(nodes) == 1:
            xs = [0.0]
        else:
            xs = np.linspace(-x_span, x_span, num=len(nodes))

        y = float(band)
        for i, nid in enumerate(nodes):
            pos[nid] = (float(xs[i]), y)

    max_nodes_in_level = max((len(v) for v in by_band.values()), default=1)
    fig_width = min(56.0, 14.0 + 0.94 * float(max_nodes_in_level))
    fig_height = max(8.2, 6.35 + 0.74 * max(y_span, float(len(bands_sorted) - 1)))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_title(f"Osobnik numer: {person_id}", fontsize=11.75, fontweight="semibold", pad=10)
    ax.axis("off")

    base_edge_alpha = 0.55 if total_nodes <= 200 else 0.22
    edge_alpha = float(base_edge_alpha) * (0.45 if enable_click_highlight else 1.0)
    edge_width = 1.28 if total_nodes <= 200 else 0.85
    if total_nodes > 320:
        edge_alpha = min(edge_alpha, 0.18)
        edge_width = 0.58

    edge_layout_depth = max(3, len(bands_sorted), int(y_span) + 1)
    _draw_pedigree_edges(
        G=G,
        pos=pos,
        ax=ax,
        readable_mode=readable_mode,
        max_level=edge_layout_depth,
        edge_width=edge_width,
        edge_alpha=edge_alpha,
    )

    node_ids = list(G.nodes())
    node_colors = [_node_color(people.get(nid).sex if nid in people else None) for nid in node_ids]
    # node_size jest polem (area) w punktach, więc daje wyraźnie większe kółka.
    base_node_size = 3200 if readable_mode else 2400
    node_size = int(max(340, base_node_size / np.sqrt(max(1.0, total_nodes / 150.0))))
    node_artist = nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        nodelist=node_ids,
        node_color=node_colors,
        node_size=node_size,
        linewidths=1.0,
        edgecolors="#333333",
    )

    labels: Dict[str, str] = {}
    # Pomocnicze struktury do nakładania LB/LC pod rokiem.
    label_line_counts: Dict[str, int] = {}
    line_text_map: Dict[str, str] = {}
    line_color_map: Dict[str, str] = {}
    dense_mode = bool(readable_mode and total_nodes > full_labels_limit)
    for nid in G.nodes():
        v = vertical.get(nid)
        person = people.get(nid)
        name = person.name if person and person.name else None
        year_str = _birth_year_label(person)
        line_text, line_color = _line_text_and_color(person.line if person else None)
        shallow = v is not None and (int(v) == 0 or abs(int(v)) == 1)

        if not readable_mode or total_nodes <= full_labels_limit:
            if name:
                name = str(name)
                if len(name) > 18:
                    name = name[:18] + "…"
                labels[nid] = f"{nid}\n{name}\n{year_str}"
                label_line_counts[nid] = 3
            else:
                labels[nid] = f"{nid}\n{year_str}"
                label_line_counts[nid] = 2
        else:
            if v is None:
                labels[nid] = f"{nid}\n{year_str}"
                label_line_counts[nid] = 2
            elif shallow:
                if dense_mode and v != 0:
                    labels[nid] = f"{nid}"
                    label_line_counts[nid] = 1
                elif dense_mode and v == 0:
                    labels[nid] = f"{nid}"
                    label_line_counts[nid] = 1
                else:
                    if name:
                        name = str(name)
                        if len(name) > 18:
                            name = name[:18] + "…"
                        labels[nid] = f"{nid}\n{name}\n{year_str}"
                        label_line_counts[nid] = 3
                    else:
                        labels[nid] = f"{nid}\n{year_str}"
                        label_line_counts[nid] = 2
            else:
                if dense_mode:
                    labels[nid] = f"{nid}"
                    label_line_counts[nid] = 1
                else:
                    labels[nid] = f"{nid}\n{year_str}"
                    label_line_counts[nid] = 2

        # Zapis do późniejszego nakładania LB/LC.
        line_text_map[nid] = line_text
        line_color_map[nid] = line_color

    if labels:
        # Dynamiczne zmniejszanie fontu przy gęstości.
        if readable_mode:
            label_font_size = 10 if max_nodes_in_level <= 6 else (9 if max_nodes_in_level <= 10 else 8)
        else:
            label_font_size = 9 if max_nodes_in_level <= 8 else 8
        font_color = "#0b2f22" if readable_mode else "white"
        label_artists = nx.draw_networkx_labels(
            G,
            pos,
            ax=ax,
            labels=labels,
            font_size=label_font_size,
            font_color=font_color,
        )
        # Delikatny obrys zwiększa kontrast etykiet przy gęstych układach i jasnych węzłach.
        stroke_color = "#f7f8f4" if readable_mode else "#1a1a1a"
        for _txt in label_artists.values():
            try:
                _txt.set_path_effects(
                    [patheffects.withStroke(linewidth=1.2, foreground=stroke_color, alpha=0.9)]
                )
            except Exception:
                pass

        _draw_line_badges(
            ax=ax,
            pos=pos,
            line_text_map=line_text_map,
            line_color_map=line_color_map,
            label_font_size=label_font_size,
            node_size=node_size,
        )

    # Delikatne linie poziome pomagają “odczytać piętra” hierarchii.
    # (Oś jest wyłączona, ale linie rysujemy mimo wszystko.)
    for band in bands_sorted:
        ax.axhline(float(band), color="#ede7d8", linewidth=0.95, alpha=0.55, zorder=0)

    _add_combined_legend(ax)

    # --- Interakcja: klik w węzeł -> podświetlenie ---
    if enable_click_highlight and len(vertical) > 0:
        selected_marker: dict[str, object] = {"artist": None}
        highlight_edge_artists: dict[str, object] = {"artist": None}
        highlight_node_artists: dict[str, object] = {"artist": None}
        selected_edge = "#111111"
        selected_size = float(node_size) * 1.45

        def _find_nearest_node(x: float, y: float) -> str | None:
            best_id: str | None = None
            best_d2 = float("inf")
            for nid in node_ids:
                px, py = pos[nid]
                dx = float(px) - float(x)
                dy = float(py) - float(y)
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    best_id = nid
            return best_id

        def _on_click(event) -> None:
            if event.inaxes is None:
                return
            if event.xdata is None or event.ydata is None:
                return
            nid = _find_nearest_node(float(event.xdata), float(event.ydata))
            if nid is None:
                return

            if selected_marker["artist"] is not None:
                try:
                    selected_marker["artist"].remove()
                except Exception:
                    pass

            # Czyścimy poprzednie podświetlenie ścieżki (krawędzie + węzły).
            if highlight_edge_artists["artist"] is not None:
                try:
                    highlight_edge_artists["artist"].remove()
                except Exception:
                    pass
            if highlight_node_artists["artist"] is not None:
                try:
                    highlight_node_artists["artist"].remove()
                except Exception:
                    pass

            sx, sy = pos[nid]
            selected_marker["artist"] = ax.scatter(
                [sx],
                [sy],
                s=selected_size,
                facecolors="none",
                edgecolors=selected_edge,
                linewidths=2.0,
                zorder=10,
            )

            # --- Podświetlenie ścieżki przodków do wskazanego węzła ---
            # `in_neighbors` = child -> parents, więc BFS idzie "w górę" po rodzicach.
            try:
                from collections import deque

                visited: set[str] = {nid}
                q = deque([nid])
                while q:
                    cur = q.popleft()
                    for par in in_neighbors.get(cur, []):
                        if par not in visited:
                            visited.add(par)
                            q.append(par)

                highlight_edges = [(a, b) for (a, b) in edges if a in visited and b in visited]
                visited_list = list(visited)

                # Highlight krawędzi
                if highlight_edges:
                    edge_coll = nx.draw_networkx_edges(
                        G,
                        pos,
                        ax=ax,
                        edgelist=highlight_edges,
                        arrows=False,
                        width=float(edge_width) * 2.0,
                        edge_color="#111111",
                        alpha=0.95,
                        arrowsize=10,
                    )
                    highlight_edge_artists["artist"] = edge_coll

                # Highlight węzłów (tylko obrys, bez wypełnienia; nie zasłania etykiet)
                if visited_list:
                    xs = [pos[v][0] for v in visited_list]
                    ys = [pos[v][1] for v in visited_list]
                    node_coll = ax.scatter(
                        xs,
                        ys,
                        s=float(node_size) * 1.25,
                        facecolors="none",
                        edgecolors="#111111",
                        linewidths=1.8,
                        zorder=9,
                    )
                    highlight_node_artists["artist"] = node_coll
            except Exception:
                # Podświetlenie ścieżki ma charakter “UX”, nie krytyczny.
                pass

            ax.set_title(f"Zaznaczono osobnika: {nid}", fontsize=11.75, fontweight="semibold", pad=10)
            fig.canvas.draw_idle()

            if on_node_click is not None:
                try:
                    dbl = bool(getattr(event, "dblclick", False))
                    on_node_click(nid, dbl)
                except Exception:
                    pass

        fig.canvas.mpl_connect("button_press_event", _on_click)

    return fig


def plot_ancestor_pedigree(
    person_id: str,
    levels: Dict[str, int],
    edges: List[Tuple[str, str]],
    people: Dict[str, Person],
    *,
    max_nodes_for_layout_warning: int = 250,
    readable_mode: bool = True,
    full_labels_limit: int = 220,
    readable_label_depth: int = 2,
    enable_click_highlight: bool = False,
    on_node_click: Optional[Callable[[str, bool], None]] = None,
) -> plt.Figure:
    """Warstwowy graf przodków — jak dotąd: `levels` (0 = start), oś Y = −pokolenie w górę."""
    vertical = {nid: -int(lvl) for nid, lvl in levels.items()}
    return plot_layered_pedigree(
        person_id,
        vertical,
        edges,
        people,
        max_nodes_for_layout_warning=max_nodes_for_layout_warning,
        readable_mode=readable_mode,
        full_labels_limit=full_labels_limit,
        readable_label_depth=readable_label_depth,
        enable_click_highlight=enable_click_highlight,
        on_node_click=on_node_click,
    )

