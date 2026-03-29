"""
Rysunek drzewa przodków (schemat pokoleń) dla wybranego osobnika.
"""

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

matplotlib.use("Agg")  # UI-klient decyduje gdzie rysujemy; dla Tk/Streamlit i tak użyjemy pyplot/fig.

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from matplotlib.lines import Line2D

from app.pedigree.ancestor_pedigree import Person
from app.ui.typography import apply_matplotlib_fonts

apply_matplotlib_fonts()


def _node_color(sex: Optional[str]) -> str:
    if sex == "M":
        # pastel blue (ojciec)
        return "#9ecbff"
    if sex == "F":
        # pastel pink (matka)
        return "#ffb4c1"
    # brak danych
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
        return "LB", "#d64545"  # czerwień dla LB (jak na screenie)
    if line == "LC":
        return "LC", "#2e8b57"  # zieleń dla LC (jak na screenie)
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
            arrowsize=12,
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
        arrowsize=10,
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
    badge_font_size = max(5, label_font_size - 2)
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
            linewidths=0.6,
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
        fontsize=8,
        borderpad=0.25,
        labelspacing=0.25,
        handletextpad=0.5,
        ncol=2,
    )


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
    # event_doubleclick=True oznacza podwójne kliknięcie na węzeł.
    on_node_click: Optional[Callable[[str, bool], None]] = None,
) -> plt.Figure:
    """
    Generuje prosty, warstwowy wykres przodków (parent -> child).
    """
    if not levels:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig

    if len(levels) > max_nodes_for_layout_warning:
        # Layout warstwowy nadal działa, ale może być czytelność słaba.
        pass

    # Budujemy graf.
    G = nx.DiGraph()
    for nid in levels.keys():
        G.add_node(nid)
    for parent, child in edges:
        if parent in levels and child in levels:
            G.add_edge(parent, child)

    # Warstwowanie: y = -generation.
    # Zamiast sortowania po ID, robimy prostą redukcję crossingów:
    # przestawiamy kolejność węzłów w każdej warstwie tak, aby węzły były
    # ułożone “bliżej” barycentru ich sąsiadów z sąsiedniej warstwy.
    by_level: Dict[int, List[str]] = {}
    for nid, lvl in levels.items():
        by_level.setdefault(lvl, []).append(nid)
    for lvl in by_level:
        by_level[lvl].sort()

    max_level = max(by_level.keys())
    total_nodes = len(levels)

    in_neighbors: Dict[str, List[str]] = {}
    out_neighbors: Dict[str, List[str]] = {}
    for parent, child in edges:
        if parent not in levels or child not in levels:
            continue
        out_neighbors.setdefault(parent, []).append(child)
        in_neighbors.setdefault(child, []).append(parent)

    def _reorder_levels(iterations: int = 4) -> None:
        # In-place: modyfikuje `by_level`.
        for _ in range(iterations):
            # Forward: porządkujemy warstwę lvl na podstawie rodziców w lvl-1.
            for lvl in range(1, max_level + 1):
                prev_nodes = by_level.get(lvl - 1, [])
                idx_prev = {nid: i for i, nid in enumerate(prev_nodes)}

                cur_nodes = by_level.get(lvl, [])
                if not cur_nodes:
                    continue

                def score(nid: str) -> float:
                    parents = [p for p in in_neighbors.get(nid, []) if levels.get(p) == (lvl - 1)]
                    if not parents:
                        # Brak rodziców w tej warstwie -> zostaw kolejność (score = inf).
                        return float("inf")
                    return float(sum(idx_prev.get(p, 0) for p in parents)) / float(len(parents))

                cur_nodes_sorted = sorted(cur_nodes, key=lambda nid: (score(nid), str(nid)))
                by_level[lvl] = cur_nodes_sorted

            # Backward: porządkujemy warstwę lvl na podstawie dzieci w lvl+1.
            for lvl in range(max_level - 1, -1, -1):
                next_nodes = by_level.get(lvl + 1, [])
                idx_next = {nid: i for i, nid in enumerate(next_nodes)}

                cur_nodes = by_level.get(lvl, [])
                if not cur_nodes:
                    continue

                def score(nid: str) -> float:
                    children = [c for c in out_neighbors.get(nid, []) if levels.get(c) == (lvl + 1)]
                    if not children:
                        return float("inf")
                    return float(sum(idx_next.get(c, 0) for c in children)) / float(len(children))

                cur_nodes_sorted = sorted(cur_nodes, key=lambda nid: (score(nid), str(nid)))
                by_level[lvl] = cur_nodes_sorted

    # Heurystyka działa najlepiej na małych/średnich grafach (typu ancestor depth 4-8),
    # ale nawet dla większych zmniejsza “losowość” układu.
    _reorder_levels(iterations=4)

    pos: Dict[str, Tuple[float, float]] = {}
    for lvl in range(0, max_level + 1):
        nodes = by_level.get(lvl, [])
        if not nodes:
            continue

        # Estymacja rozstawu w poziomie (bez dokładnego liczenia szerokości fontu).
        max_chars = 0
        for nid in nodes:
            person = people.get(nid)
            name = getattr(person, "name", None) if person else None
            year_str = _birth_year_label(person)
            name_part = ""
            if not readable_mode or total_nodes <= full_labels_limit:
                name_part = str(name) if name else ""
            else:
                # W trybie czytelnym nazwy pokazujemy tylko w płytszych pokoleniach.
                if lvl in (0, 1) and name:
                    name_part = str(name)
            est = len(str(nid)) + len(name_part) + len(year_str)
            max_chars = max(max_chars, est)

        # Przy wielu węzłach na jednej warstwie limit x_span=3.0 powodował zbyt
        # małe rozstawienie etykiet. Zwiększamy span proporcjonalnie do liczby węzłów.
        x_span = float(1.2 + max_chars / 90.0 + 0.25 * float(len(nodes)))

        if len(nodes) == 1:
            xs = [0.0]
        else:
            xs = np.linspace(-x_span, x_span, num=len(nodes))

        y = -float(lvl)
        for i, nid in enumerate(nodes):
            pos[nid] = (float(xs[i]), y)

    max_nodes_in_level = max((len(v) for v in by_level.values()), default=1)
    # Przy wielu węzłach na poziomie etykiety zaczynają się nakładać.
    # Zwiększamy szerokość proporcjonalnie do gęstości.
    fig_width = min(34.0, 10.0 + 0.6 * float(max_nodes_in_level))
    # Więcej miejsca pionowego, żeby “piętra” hierarchii były wyraźne.
    fig_height = max(6.0, 4.8 + 0.55 * float(max_level))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_title(f"Osobnik numer: {person_id}")
    ax.axis("off")

    total_nodes = len(levels)
    # Gdy użytkownik klika w węzły, podświetlimy też ścieżkę do przodków,
    # więc bazowe krawędzie przyciemnimy, aby highlight był bardziej widoczny.
    base_edge_alpha = 0.55 if total_nodes <= 200 else 0.22
    edge_alpha = float(base_edge_alpha) * (0.45 if enable_click_highlight else 1.0)
    edge_width = 1.1 if total_nodes <= 200 else 0.75
    if total_nodes > 320:
        # Przy bardzo gęstych wykresach grubsze linie potęgują “spaghetti”.
        edge_alpha = min(edge_alpha, 0.18)
        edge_width = 0.55

    _draw_pedigree_edges(
        G=G,
        pos=pos,
        ax=ax,
        readable_mode=readable_mode,
        max_level=max_level,
        edge_width=edge_width,
        edge_alpha=edge_alpha,
    )

    node_ids = list(G.nodes())
    node_colors = [_node_color(people.get(nid).sex if nid in people else None) for nid in node_ids]
    # node_size jest polem (area) w punktach, więc daje wyraźnie większe kółka.
    base_node_size = 2600 if readable_mode else 1900
    node_size = int(max(260, base_node_size / np.sqrt(max(1.0, total_nodes / 160.0))))
    node_artist = nx.draw_networkx_nodes(
        G,
        pos,
        ax=ax,
        nodelist=node_ids,
        node_color=node_colors,
        node_size=node_size,
        linewidths=0.8,
        edgecolors="#333333",
    )

    labels: Dict[str, str] = {}
    # Pomocnicze struktury do nakładania LB/LC pod rokiem.
    label_line_counts: Dict[str, int] = {}
    line_text_map: Dict[str, str] = {}
    line_color_map: Dict[str, str] = {}
    dense_mode = bool(readable_mode and total_nodes > full_labels_limit)
    for nid in G.nodes():
        lvl = levels.get(nid)
        person = people.get(nid)
        name = person.name if person and person.name else None
        year_str = _birth_year_label(person)
        line_text, line_color = _line_text_and_color(person.line if person else None)

        if not readable_mode or total_nodes <= full_labels_limit:
            # Pełne etykiety (dużo tekstu) - tylko gdy wykres nie jest zbyt gęsty.
            if name:
                name = str(name)
                if len(name) > 18:
                    name = name[:18] + "…"
                labels[nid] = f"{nid}\n{name}\n{year_str}"
                # 3 linie: nid + imię + rok
                label_line_counts[nid] = 3
            else:
                labels[nid] = f"{nid}\n{year_str}"
                # 2 linie: nid + rok
                label_line_counts[nid] = 2
        else:
            # Tryb czytelny: wciąż pokazujemy birth year, żeby rysunek był jednoznaczny.
            if lvl is None:
                labels[nid] = f"{nid}\n{year_str}"
                label_line_counts[nid] = 2
            elif lvl in (0, 1):
                if dense_mode and lvl >= 1:
                    # W trybie gęstym (dużo węzłów) ograniczamy opis do samego ID,
                    # żeby uniknąć nakładania się etykiet na wyższych piętrach.
                    labels[nid] = f"{nid}"
                    label_line_counts[nid] = 1
                elif dense_mode and lvl == 0:
                    # Top (lvl=0) jest mały — pokazujemy tylko ID (bez roku), nadal czytelnie.
                    labels[nid] = f"{nid}"
                    label_line_counts[nid] = 1
                else:
                # W pierwszych pokoleniach dodatkowo krótka nazwa.
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
                # Dla głębszych pokoleń: skrót (ID + rok).
                if dense_mode:
                    # Gdy graf jest gęsty, rok powoduje nakładanie się etykiet.
                    # Zostawiamy tylko ID (1 linia).
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
            label_font_size = 8 if max_nodes_in_level <= 6 else (7 if max_nodes_in_level <= 10 else 6)
        else:
            label_font_size = 7 if max_nodes_in_level <= 8 else 6
        font_color = "#0b2f22" if readable_mode else "white"
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=label_font_size, font_color=font_color)

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
    for lvl in range(0, max_level + 1):
        ax.axhline(-float(lvl), color="#ede7d8", linewidth=0.8, alpha=0.55, zorder=0)

    _add_combined_legend(ax)

    # --- Interakcja: klik w węzeł -> podświetlenie ---
    if enable_click_highlight and len(levels) > 0:
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

            ax.set_title(f"Zaznaczono osobnika: {nid}")
            fig.canvas.draw_idle()

            if on_node_click is not None:
                try:
                    dbl = bool(getattr(event, "dblclick", False))
                    on_node_click(nid, dbl)
                except Exception:
                    pass

        fig.canvas.mpl_connect("button_press_event", _on_click)

    return fig

