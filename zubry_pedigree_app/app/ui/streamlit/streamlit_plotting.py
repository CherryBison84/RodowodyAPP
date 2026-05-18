"""Wykresy walidacji (matplotlib) i wyświetlanie w Streamlit."""

from __future__ import annotations

from collections import Counter
import textwrap
from typing import Sequence

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.patches import Rectangle

from app.data.dataset_loader import dataframe_app_schema_columns
from app.data.validator import ValidationReport
from app.ui.theme import Theme
from app.ui.typography import apply_matplotlib_fonts

PLOT_THEME = Theme()
ACCENT = PLOT_THEME.ACCENT
MUTED = PLOT_THEME.MUTED
BUTTON_BG = PLOT_THEME.BUTTON_BG
BUTTON_BG2 = PLOT_THEME.BUTTON_BG2
PLOT_BAR_3RD = PLOT_THEME.TAB_TEXT

# Czcionki i figury dopasowane do wyższego DPI — czytelność w UI (st.image „stretch”) i w PNG.
ST_FS_TITLE = 11.75
ST_FS_AXIS = 10.25
ST_FS_TICK = 9.15
ST_FS_DENSE = 8.35
ST_FS_MISS_HEAD = 11.25
ST_XTICK_ROT = 47.0
# Wyższe DPI = więcej pikseli przy tym samym rozmiarze figury — ostrzejszy tekst po skalowaniu w przeglądarce.
ST_DPI_EXPORT = 200
ST_DPI_MISSING_MAP = 420
ST_FIG_VALIDATION_W, ST_FIG_VALIDATION_H = 12.2, 5.25
ST_FIG_EMPTY = (6.35, 2.65)
# Opcjonalna stała szerokość podglądu (px), gdy przy wywołaniu podasz width=ST_CHART_DISPLAY_WIDTH_PX
ST_CHART_DISPLAY_WIDTH_PX = 1280
# Linie z markerami (trendy roku / GI): grubsze = lepiej widać po skalowaniu UI.
ST_LINE_MARKERSIZE = 4.45
ST_LINE_WIDTH = 2.35
# Siatka osi — nieco wyższy kontrast na jasnym tle strony / przezroczystym PNG.
ST_GRID_ALPHA = 0.38
ST_GRID_AXIS_WIDTH = 0.95

apply_matplotlib_fonts()


def _slant_xlabels(ax: plt.Axes, *, rotation: float | None = None, tick_fs: float | None = None) -> None:
    """Etykiety osi X pod kątem (domyślnie ST_XTICK_ROT), żeby się nie nakładały."""
    rot = float(ST_XTICK_ROT if rotation is None else rotation)
    fs = float(ST_FS_TICK if tick_fs is None else tick_fs)
    for t in ax.get_xticklabels():
        t.set_rotation(rot)
        t.set_horizontalalignment("right")
        t.set_fontsize(fs)


def _legend_style(**extra: object) -> dict[str, object]:
    """Ramka legendy — czytelna na przezroczystym podglądzie w Streamlit."""
    kw: dict[str, object] = {
        "fontsize": ST_FS_TICK,
        "framealpha": 0.94,
        "fancybox": True,
        "edgecolor": PLOT_THEME.BORDER_SUBTLE,
    }
    kw.update(extra)
    return kw


# Przezroczyste tło figury i osi — podgląd i PNG są spójne z tłem strony (zielonkawy APP_BG).
mpl.rcParams.update(
    {
        "figure.facecolor": "none",
        "axes.facecolor": "none",
        "savefig.facecolor": "none",
        "axes.linewidth": ST_GRID_AXIS_WIDTH,
        "xtick.major.width": ST_GRID_AXIS_WIDTH * 0.88,
        "ytick.major.width": ST_GRID_AXIS_WIDTH * 0.88,
        "xtick.major.size": 4.5,
        "ytick.major.size": 4.5,
        "lines.antialiased": True,
        "patch.linewidth": 1.12,
    }
)


def _figsize_for_n_x_categories(
    n: int,
    *,
    min_w: float = 9.35,
    max_w: float = 17.2,
    min_h: float = 4.85,
    max_h: float = 7.35,
) -> tuple[float, float]:
    """Przy wielu dekadach na osi X: szersza i wyższa figura, żeby etykiety nie były mikroskopijne."""
    if n <= 1:
        return min_w, min_h
    w = min(max_w, max(min_w, 5.85 + 0.44 * float(n)))
    h = min(max_h, max(min_h, 3.75 + 0.12 * float(n)))
    return w, h

# Kolejność jak w tabeli „Rejestr osobniczy populacji”, potem pozostałe pola schematu alfabetycznie.
_REGISTRY_TREE_ORDER: tuple[str, ...] = (
    "id",
    "name",
    "sex",
    "birth_year",
    "birth_location",
    "father_id",
    "mother_id",
    "line",
    "father_line",
    "mother_line",
)
_REGISTRY_EXTRA_ORDER: tuple[str, ...] = (
    "alt_name",
    "status",
    "father_name",
    "mother_name",
    "birth_date",
    "death_date",
    "birth_location",
)


def registry_like_column_order(df_columns: pd.Index | list[str]) -> list[str]:
    """Kolumny w tej samej kolejności co widok rejestru (najpierw główne pola tabeli), potem pozostałe alfabetycznie."""
    names = [str(c) for c in df_columns]
    colset = set(names)
    preferred = _REGISTRY_TREE_ORDER + _REGISTRY_EXTRA_ORDER
    ordered: list[str] = []
    seen: set[str] = set()
    for c in preferred:
        if c in colset and c not in seen:
            ordered.append(c)
            seen.add(c)
    rest = sorted(c for c in colset if c not in seen)
    return ordered + rest


def show_matplotlib_figure_in_streamlit(
    fig: plt.Figure,
    *,
    download_filename: str,
    download_key: str,
    width: str | int = "stretch",
    export_dpi: int | None = None,
    save_pad_inches: float = 0.16,
) -> None:
    """
    Wyświetla wykres jako PNG (`st.image`, stabilniej niż `st.pyplot` w części przeglądarek)
    i dodaje przycisk pobrania pliku. Figura jest zamykana po zapisie.
    Podgląd: tło przezroczyste (spójne ze stroną). Pobierany plik PNG: **białe tło**.
    `width`: domyślnie `"stretch"`; albo `"content"` albo szerokość w px (np. `ST_CHART_DISPLAY_WIDTH_PX`).
    `export_dpi`: opcjonalnie inne DPI niż `ST_DPI_EXPORT` (np. gęsty wykres dwupanelowy).
    `save_pad_inches`: margines `bbox_inches='tight'` — większy przy gęstym tekście (mapa braków).
    """
    import io

    import streamlit as st

    buf_ui = io.BytesIO()
    buf_dl = io.BytesIO()
    _dpi = int(export_dpi) if export_dpi is not None else ST_DPI_EXPORT
    _save_kw = dict(
        format="png",
        dpi=_dpi,
        bbox_inches="tight",
        pad_inches=float(save_pad_inches),
    )
    try:
        fig.savefig(
            buf_ui,
            **_save_kw,
            transparent=True,
            facecolor="none",
            edgecolor="none",
        )
        fig.savefig(
            buf_dl,
            **_save_kw,
            transparent=False,
            facecolor="white",
            edgecolor="white",
        )
    finally:
        plt.close(fig)
    png_ui = buf_ui.getvalue()
    png_dl = buf_dl.getvalue()
    st.image(io.BytesIO(png_ui), width=width)
    st.download_button(
        "Pobierz wykres (PNG)",
        data=png_dl,
        file_name=download_filename,
        mime="image/png",
        key=download_key,
        width="content",
    )


def column_missing_percentages(df: pd.DataFrame) -> pd.Series:
    """
    Dla każdej kolumny: % wierszy z brakiem (NaN / puste / „nan” w tekście).
    Zdublowane nazwy kolumn — jak w rejestrze: pierwsza kopia (spójnie z widokiem Streamlit).
    """
    if df is None or df.empty:
        return pd.Series(dtype=float)
    work = df.loc[:, ~df.columns.duplicated(keep="first")] if df.columns.duplicated().any() else df
    n = len(work)
    if n == 0:
        return pd.Series(dtype=float)
    out: dict[str, float] = {}
    for col in work.columns:
        s = work[col]
        if pd.api.types.is_bool_dtype(s):
            miss = s.isna()
        elif pd.api.types.is_numeric_dtype(s):
            miss = s.isna()
        else:
            sn = s.isna()
            ss = s.astype(str)
            miss = sn | (ss.str.strip() == "") | ss.str.lower().isin(("nan", "none", "<na>"))
        out[str(col)] = 100.0 * float(miss.sum()) / float(n)
    return pd.Series(out)


def _col_label_missing_map_rotated(name: str, ncol: int) -> str:
    """Jedna linia pod mapą (ukośna etykieta); przy bardzo długich nazwach delikatne skrócenie."""
    s = str(name).replace("\n", " ")
    cap = max(16, min(42, int(220 / max(ncol, 1)) + 10))
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "…"


def _forest_missing_segment_cmap(th: Theme) -> LinearSegmentedColormap:
    """0% braków = jasna mgła; 100% = głęboka kora (jak skala na screenie, w barwach lasu)."""
    return LinearSegmentedColormap.from_list(
        "forest_miss_segments",
        [
            to_rgb(th.ENTRY_BG),
            to_rgb(th.BUTTON_BG),
            to_rgb(th.BUTTON_BG2),
            to_rgb(th.EDGE_PLOT),
            to_rgb(th.ACCENT),
            (0.32, 0.20, 0.16),
        ],
        N=768,
    )


def fig_column_missing_heatmap(df: pd.DataFrame) -> plt.Figure:
    """
    Mapa braków: kolumny schematu importu w kolejności aplikacji.
    W pasku koloru wyłącznie **% braków**; **nazwy kolumn** pod kątem pod paskiem (mniej nachodzą). Skala kolorów leśnych bez osobnego paska legendy.
    """
    th = PLOT_THEME
    if df is not None and not df.empty:
        df = dataframe_app_schema_columns(df)
    n_rows = len(df) if df is not None and not df.empty else 0
    pct = column_missing_percentages(df)
    if pct.empty:
        fig, ax = plt.subplots(figsize=ST_FIG_EMPTY)
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center", fontsize=ST_FS_AXIS)
        ax.axis("off")
        return fig
    order = registry_like_column_order(pct.index)
    pct = pct.reindex([c for c in order if c in pct.index])
    pct = pct.dropna()
    if pct.empty:
        fig, ax = plt.subplots(figsize=ST_FIG_EMPTY)
        ax.text(0.5, 0.5, "Brak kolumn do wyświetlenia", ha="center", va="center", fontsize=ST_FS_AXIS)
        ax.axis("off")
        return fig
    ncol = len(pct)
    cmap = _forest_missing_segment_cmap(th)
    # Większa figura (cale) × wysokie ST_DPI_MISSING_MAP = dużo pikseli — tekst w komórkach nie „pływa” przy zoomie.
    fig_w = min(28.5, max(11.2, 0.92 * float(ncol) + 3.45))
    label_band = min(1.35, max(0.68, 0.52 + 0.038 * float(ncol)))
    fig_h = max(6.05, min(8.85, 2.72 + 0.13 * float(ncol) + 0.58 * label_band))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    bottom_margin = max(0.21, min(0.38, 0.16 + 0.0085 * float(ncol)))
    fig.subplots_adjust(left=0.03, right=0.97, top=0.805, bottom=bottom_margin)
    ax.set_xlim(0, ncol)
    ax.set_ylim(-label_band, 1)
    ax.axis("off")

    _miss_seg_fs = max(10.75, min(16.25, 198.0 / max(ncol, 1)))
    _miss_name_fs = max(11.0, min(15.25, 142.0 / max(ncol, 1) + 2.95))
    fig.text(
        0.03,
        0.935,
        "Mapa braków danych",
        fontsize=ST_FS_MISS_HEAD * 1.28,
        color=th.TEXT,
        ha="left",
        va="top",
        fontweight="semibold",
    )
    fig.text(
        0.03,
        0.855,
        f"n = {n_rows} wierszy  ·  jasny kolor = mniej braków",
        fontsize=ST_FS_TICK * 1.18,
        color=th.MUTED,
        ha="left",
        va="top",
    )

    for j, (col_name, v_raw) in enumerate(pct.items()):
        p = float(v_raw)
        t = np.clip(p / 100.0, 0.0, 1.0)
        rgba = cmap(t)
        r, g, b = float(rgba[0]), float(rgba[1]), float(rgba[2])
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        tcol = "#f8fcf8" if lum < 0.45 else th.TEXT
        rect = Rectangle(
            (j, 0),
            1.0,
            1.0,
            facecolor=rgba,
            edgecolor=th.EDGE_PLOT,
            linewidth=0.95,
            alpha=1.0,
            antialiased=False,
            zorder=1,
        )
        ax.add_patch(rect)
        if j > 0:
            ax.plot(
                [j, j],
                [0, 1],
                color=th.EDGE_PLOT,
                linewidth=1.05,
                alpha=0.88,
                zorder=2,
                solid_capstyle="butt",
            )
        ax.text(
            j + 0.5,
            0.5,
            f"{p:.1f}%",
            ha="center",
            va="center",
            fontsize=_miss_seg_fs,
            color=tcol,
            fontweight="semibold",
            clip_on=True,
        )
        ax.text(
            j + 0.5,
            -0.02,
            _col_label_missing_map_rotated(col_name, ncol),
            rotation=48,
            ha="right",
            va="top",
            rotation_mode="anchor",
            fontsize=_miss_name_fs,
            color=th.TEXT,
            clip_on=False,
            zorder=4,
        )

    ax.plot([0, ncol], [0, 0], color=th.EDGE_PLOT, linewidth=1.35, zorder=3, clip_on=False, solid_capstyle="butt")

    frame = Rectangle(
        (0, 0),
        ncol,
        1.0,
        fill=False,
        edgecolor=th.EDGE_PLOT,
        linewidth=1.95,
        antialiased=True,
        zorder=5,
    )
    ax.add_patch(frame)
    return fig


def fig_validation_findings(rep: ValidationReport) -> plt.Figure:
    """
    Wykres podsumowania walidacji: liczba wpisów ERROR/WARN w eksporcie CSV oraz rozkład wg typu problemu.
    Gdy brak wierszy eksportu, liczy komunikaty ERROR/WARN z listy `issues`.
    """
    th = PLOT_THEME
    color_err = "#a53c3c"
    color_warn = "#8a6b58"
    color_type_bar = th.COMPLETENESS_ACCENT
    color_type_text = "#f4f8f4"

    n_err = sum(1 for r in rep.export_rows if r.severity == "ERROR")
    n_warn = sum(1 for r in rep.export_rows if r.severity == "WARN")
    type_counter: Counter[str] = Counter(r.problem_type for r in rep.export_rows)

    if not rep.export_rows:
        n_err = max(n_err, sum(1 for i in rep.issues if i.severity == "ERROR"))
        n_warn = max(n_warn, sum(1 for i in rep.issues if i.severity == "WARN"))
        if not type_counter:
            type_counter = Counter(i.title for i in rep.issues if i.severity in ("ERROR", "WARN"))

    top_types = type_counter.most_common(12)
    n_bars = len(top_types) if top_types else 1
    fig_h = max(ST_FIG_VALIDATION_H, 2.35 + 0.38 * float(n_bars))
    fig_w = max(ST_FIG_VALIDATION_W, 10.8)

    fig, (ax0, ax1) = plt.subplots(
        1,
        2,
        figsize=(fig_w, fig_h),
        gridspec_kw={"width_ratios": [1.12, 2.55], "wspace": 0.36},
        constrained_layout=True,
    )

    labels_sev = ["Błędy\n(ERROR)", "Ostrzeżenia\n(WARN)"]
    vals_sev = [float(n_err), float(n_warn)]
    bars0 = ax0.bar(
        range(2),
        vals_sev,
        color=[color_err, color_warn],
        edgecolor=th.EDGE_PLOT,
        linewidth=0.85,
        width=0.58,
    )
    ax0.set_xticks(range(2))
    ax0.set_xticklabels(labels_sev, fontsize=ST_FS_TICK + 0.25)
    ax0.set_ylabel("Liczba wpisów", fontsize=ST_FS_AXIS)
    n_txt = f"{rep.total_rows:,}".replace(",", " ")
    ax0.set_title(
        f"Waga w raporcie (CSV)\nw bazie: n = {n_txt}",
        fontsize=ST_FS_TITLE,
        pad=8,
    )
    ax0.tick_params(axis="y", labelsize=ST_FS_TICK)
    ymax = max(1.0, max(vals_sev) * 1.14) if vals_sev else 1.0
    ax0.set_ylim(0, ymax)
    for b, v in zip(bars0, vals_sev):
        if v > 0:
            ax0.text(
                b.get_x() + b.get_width() / 2.0,
                b.get_height() + ymax * 0.018,
                str(int(v)),
                ha="center",
                va="bottom",
                fontsize=ST_FS_TICK + 0.35,
                color=th.TEXT,
                fontweight="semibold",
            )
    ax0.grid(True, axis="y", alpha=0.42, linestyle="--", linewidth=0.78)

    if not top_types:
        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
        ax1.text(
            0.5,
            0.5,
            "Brak szczegółowych typów problemów\n(wszystko OK lub brak wierszy eksportu)",
            ha="center",
            va="center",
            fontsize=ST_FS_AXIS,
            color=th.MUTED,
        )
        ax1.set_xticks([])
        ax1.set_yticks([])
        for s in ax1.spines.values():
            s.set_visible(False)
    else:
        types, counts = zip(*top_types, strict=True)
        counts_f = [float(c) for c in counts]

        def _wrap_problem_label(s: str, *, width: int = 32, max_lines: int = 4) -> str:
            t = str(s).replace("\n", " ").strip()
            lines = textwrap.wrap(t, width=width, break_long_words=False, break_on_hyphens=True)
            if not lines:
                return ""
            if len(lines) <= max_lines:
                return "\n".join(lines)
            head = "\n".join(lines[: max_lines - 1])
            return f"{head}\n{lines[max_lines - 1]}…"

        labels = [_wrap_problem_label(t) for t in types]
        y = np.arange(len(labels))
        bars1 = ax1.barh(
            y,
            counts_f,
            color=color_type_bar,
            edgecolor=th.EDGE_PLOT,
            linewidth=0.9,
            height=0.72,
        )
        ax1.set_yticks(y)
        ax1.set_yticklabels(labels, fontsize=ST_FS_DENSE + 0.35)
        ax1.invert_yaxis()
        ax1.set_xlabel("Liczba wykryć (wiersze eksportu / typ)", fontsize=ST_FS_AXIS)
        ax1.set_title("Najczęstsze typy problemów", fontsize=ST_FS_TITLE, pad=8)
        ax1.tick_params(axis="x", labelsize=ST_FS_TICK)
        ax1.grid(True, axis="x", alpha=0.42, linestyle="--", linewidth=0.78)

        xmax = max(1.0, max(counts_f) * 1.22)
        ax1.set_xlim(0, xmax)

        for b, yi, c in zip(bars1, y, counts_f):
            lbl = str(int(c))
            if xmax > 0 and c >= xmax * 0.12:
                tx = max(c - xmax * 0.012, xmax * 0.02)
                ax1.text(
                    tx,
                    yi,
                    lbl,
                    va="center",
                    ha="right",
                    fontsize=ST_FS_TICK,
                    color=color_type_text,
                    fontweight="semibold",
                )
            else:
                ax1.text(
                    min(c + xmax * 0.012, xmax * 0.995),
                    yi,
                    f" {lbl}",
                    va="center",
                    ha="left",
                    fontsize=ST_FS_TICK,
                    color=th.TEXT,
                    fontweight="semibold",
                )

    return fig


def fig_validation_by_category(
    categories: Sequence[tuple[str, int, int]],
) -> plt.Figure:
    """Poziome słupki skumulowane: ERROR + WARN wg kategorii kontroli (np. Rodzice, ID)."""
    th = PLOT_THEME
    color_err = "#a53c3c"
    color_warn = "#8a6b58"

    if not categories:
        fig, ax = plt.subplots(figsize=(8.5, 3.2), constrained_layout=True)
        ax.text(
            0.5,
            0.5,
            "Brak kategorii do wyświetlenia",
            ha="center",
            va="center",
            fontsize=ST_FS_AXIS,
            color=th.MUTED,
        )
        ax.set_axis_off()
        return fig

    labels = [str(lbl) for lbl, _e, _w in categories]
    err = [float(e) for _lbl, e, _w in categories]
    warn = [float(w) for _lbl, _e, w in categories]
    y = np.arange(len(labels))
    fig_h = max(3.4, 1.35 + 0.52 * len(labels))
    fig, ax = plt.subplots(figsize=(9.2, fig_h), constrained_layout=True)

    ax.barh(y, err, height=0.58, color=color_err, label="ERROR", edgecolor=th.EDGE_PLOT, linewidth=0.75)
    ax.barh(
        y,
        warn,
        left=err,
        height=0.58,
        color=color_warn,
        label="WARN",
        edgecolor=th.EDGE_PLOT,
        linewidth=0.75,
    )
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=ST_FS_DENSE + 0.25)
    ax.invert_yaxis()
    ax.set_xlabel("Liczba wpisów w eksporcie", fontsize=ST_FS_AXIS)
    ax.set_title("Problemy wg kategorii kontroli", fontsize=ST_FS_TITLE, pad=8)
    ax.tick_params(axis="x", labelsize=ST_FS_TICK)
    ax.grid(True, axis="x", alpha=0.42, linestyle="--", linewidth=0.78)
    ax.legend(loc="lower right", fontsize=ST_FS_TICK, framealpha=0.92)

    totals = [e + w for e, w in zip(err, warn, strict=True)]
    xmax = max(1.0, max(totals) * 1.18) if totals else 1.0
    ax.set_xlim(0, xmax)
    for yi, tot in zip(y, totals, strict=True):
        if tot > 0:
            ax.text(
                tot + xmax * 0.01,
                yi,
                str(int(tot)),
                va="center",
                ha="left",
                fontsize=ST_FS_TICK,
                color=th.TEXT,
                fontweight="semibold",
            )

    return fig
