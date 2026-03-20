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
    by_level: Dict[int, List[str]] = {}
    for nid, lvl in levels.items():
        by_level.setdefault(lvl, []).append(nid)
    for lvl in by_level:
        by_level[lvl].sort()

    pos: Dict[str, Tuple[float, float]] = {}
    max_level = max(by_level.keys())
    total_nodes = len(levels)
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

        x_span = float(min(3.0, 1.2 + max_chars / 90.0))

        if len(nodes) == 1:
            xs = [0.0]
        else:
            xs = np.linspace(-x_span, x_span, num=len(nodes))

        y = -float(lvl)
        for i, nid in enumerate(nodes):
            pos[nid] = (float(xs[i]), y)

    max_nodes_in_level = max((len(v) for v in by_level.values()), default=1)
    fig_width = min(22.0, 10.0 + 0.25 * float(max_nodes_in_level))
    fig_height = 6.0
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    ax.set_title(f"Przodkowie: {person_id}")
    ax.axis("off")

    total_nodes = len(levels)
    edge_alpha = 0.55 if total_nodes <= 200 else 0.22
    edge_width = 1.1 if total_nodes <= 200 else 0.75

    # Rysujemy krawędzie.
    if readable_mode:
        # W trybie czytelnym chcesz większą czytelność, więc zostawiamy strzałki,
        # ale bez nadmiarowej geometrii połączeń.
        arrows = True
        arrowstyle = "-|>"
        arrowsize = 12
        nx.draw_networkx_edges(
            G,
            pos,
            ax=ax,
            arrows=arrows,
            arrowstyle=arrowstyle,
            arrowsize=arrowsize,
            width=edge_width,
            edge_color="#6b5b4d",
            alpha=edge_alpha,
        )
    else:
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
                labels[nid] = f"{nid}\n{year_str}"
                label_line_counts[nid] = 2

        # Zapis do późniejszego nakładania LB/LC.
        line_text_map[nid] = line_text
        line_color_map[nid] = line_color

    if labels:
        label_font_size = 8 if readable_mode else 7
        font_color = "#0b2f22" if readable_mode else "white"
        nx.draw_networkx_labels(G, pos, ax=ax, labels=labels, font_size=label_font_size, font_color=font_color)

        # Nakładamy osobno LB/LC pod rokiem, żeby kolor działał bez `\color` w mathtext.
        #
        # `va='center'` oznacza, że label jest wycentrowany, więc przesuwamy tekst w dół
        # zależnie od liczby linii w labelu (2 vs 3).
        line_dy = 0.09
        # Większe przesunięcie w dół, żeby etykiety LB/LC nie nachodziły na rok urodzenia.
        extra_below_year = 1.15
        for nid, (x, y) in pos.items():
            if nid not in line_text_map:
                continue
            n_lines = label_line_counts.get(nid, 2)
            y_line = float(y) - ((n_lines - 1) / 2.0) * line_dy - extra_below_year * line_dy
            ax.text(
                float(x),
                y_line,
                line_text_map[nid],
                ha="center",
                va="center",
                fontsize=label_font_size,
                fontweight="bold",
                color=line_color_map.get(nid, "#9aa3a2"),
            )

    # --- Jedna legenda: płeć (M/F) + linie (LB/LC) ---
    sex_line_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=10,
            markerfacecolor=_node_color("M"),
            markeredgecolor="#333333",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            linestyle="None",
            markersize=10,
            markerfacecolor=_node_color("F"),
            markeredgecolor="#333333",
        ),
        Line2D([0], [0], marker="s", linestyle="None", markersize=10, markerfacecolor="#d64545", markeredgecolor="#d64545"),
        Line2D([0], [0], marker="s", linestyle="None", markersize=10, markerfacecolor="#2e8b57", markeredgecolor="#2e8b57"),
    ]
    ax.legend(
        sex_line_handles,
        ["Ojciec (M)", "Matka (F)", "LB", "LC"],
        loc="upper right",
        frameon=True,
        fontsize=8,
        borderpad=0.3,
        labelspacing=0.3,
    )

    # --- Interakcja: klik w węzeł -> podświetlenie ---
    if enable_click_highlight and len(levels) > 0:
        selected_marker: dict[str, object] = {"artist": None}
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

            sx, sy = pos[nid]
            selected_marker["artist"] = ax.scatter(
                [sx],
                [sy],
                s=selected_size,
                facecolors="none",
                edgecolors=selected_edge,
                linewidths=2.0,
            )

            ax.set_title(f"Przodkowie: {person_id} | klik: {nid}")
            fig.canvas.draw_idle()

            if on_node_click is not None:
                try:
                    dbl = bool(getattr(event, "dblclick", False))
                    on_node_click(nid, dbl)
                except Exception:
                    pass

        fig.canvas.mpl_connect("button_press_event", _on_click)

    return fig

