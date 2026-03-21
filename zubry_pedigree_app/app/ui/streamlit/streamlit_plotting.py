"""
Wykresy Matplotlib współdzielone z logiką zbliżoną do gui_pro (Tk).
Używane wyłącznie przez Streamlit.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pandas import isna

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.pedigree.ancestor_pedigree import get_ancestor_levels_unbounded

# Kolory zbliżone do theme.py / gui_pro
ACCENT = "#caa86e"
MUTED = "#2c6a4e"
BUTTON_BG = "#dff4e3"
BUTTON_BG2 = "#c8ead4"


def _parse_birth_year(v: object, *, lo: int = 1881, hi: int | None = None) -> int | None:
    hi = hi or datetime.now().year
    if v is None:
        return None
    try:
        if isinstance(v, float) and v != v:
            return None
    except Exception:
        pass
    if isna(v):
        return None
    try:
        y_int = int(float(v))
    except Exception:
        return None
    if y_int < lo or y_int > hi:
        return None
    return y_int


def fig_birth_decades_sex(df: pd.DataFrame) -> plt.Figure:
    now_year = datetime.now().year
    min_dec = (1881 // 10) * 10
    max_dec = (now_year // 10) * 10
    decades = list(range(min_dec, max_dec + 1, 10))
    decade_labels = [f"{d}-{d+9}" for d in decades]
    x = list(range(len(decades)))
    w = 0.38

    if df is None or df.empty or "birth_year" not in df.columns:
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig

    birth_int = df["birth_year"].apply(lambda v: _parse_birth_year(v, lo=1881))
    dfc = df.copy()
    dfc["_birth_int"] = birth_int
    dfc = dfc.dropna(subset=["_birth_int"])
    if dfc.empty:
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        ax.text(0.5, 0.5, "Brak prawidłowych lat urodzenia", ha="center", va="center")
        ax.axis("off")
        return fig
    dfc["_birth_int"] = dfc["_birth_int"].astype(int)
    dfc["decade"] = (dfc["_birth_int"] // 10) * 10

    def _norm_sex(v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s in {"M", "F"} else None

    sex_norm = dfc["sex"].apply(_norm_sex) if "sex" in dfc.columns else None
    m_counts: dict[int, int] = {}
    f_counts: dict[int, int] = {}
    if sex_norm is not None:
        vc_m = dfc[sex_norm == "M"].groupby("decade").size().to_dict()
        vc_f = dfc[sex_norm == "F"].groupby("decade").size().to_dict()
        m_counts = {int(k): int(v) for k, v in vc_m.items()}
        f_counts = {int(k): int(v) for k, v in vc_f.items()}

    m_vals = [m_counts.get(d, 0) for d in decades]
    f_vals = [f_counts.get(d, 0) for d in decades]

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.bar([i - w / 2 for i in x], m_vals, width=w, color="#9ecbff", edgecolor=ACCENT, label="M")
    ax.bar([i + w / 2 for i in x], f_vals, width=w, color="#ffb4c1", edgecolor=ACCENT, label="F")
    ax.set_title("Urodzenia w dekadach (płeć)")
    ax.set_xlabel("dekada")
    ax.set_ylabel("liczba urodzeń")
    ax.set_xticks(x)
    ax.set_xticklabels(decade_labels, rotation=45, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def fig_birth_decades_line(df: pd.DataFrame) -> plt.Figure:
    now_year = datetime.now().year
    min_dec = (1881 // 10) * 10
    max_dec = (now_year // 10) * 10
    decades = list(range(min_dec, max_dec + 1, 10))
    decade_labels = [f"{d}-{d+9}" for d in decades]
    x = list(range(len(decades)))
    w = 0.38

    if df is None or df.empty or "birth_year" not in df.columns:
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig

    birth_int = df["birth_year"].apply(lambda v: _parse_birth_year(v, lo=1881))
    dfc = df.copy()
    dfc["_birth_int"] = birth_int
    dfc = dfc.dropna(subset=["_birth_int"])
    if dfc.empty:
        fig, ax = plt.subplots(figsize=(8.6, 3.4))
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig
    dfc["_birth_int"] = dfc["_birth_int"].astype(int)
    dfc["decade"] = (dfc["_birth_int"] // 10) * 10

    def _norm_line(v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s in {"LB", "LC"} else None

    line_norm = dfc["line"].apply(_norm_line) if "line" in dfc.columns else None
    lb_counts: dict[int, int] = {}
    lc_counts: dict[int, int] = {}
    if line_norm is not None:
        vc_lb = dfc[line_norm == "LB"].groupby("decade").size().to_dict()
        vc_lc = dfc[line_norm == "LC"].groupby("decade").size().to_dict()
        lb_counts = {int(k): int(v) for k, v in vc_lb.items()}
        lc_counts = {int(k): int(v) for k, v in vc_lc.items()}

    lb_vals = [lb_counts.get(d, 0) for d in decades]
    lc_vals = [lc_counts.get(d, 0) for d in decades]

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    ax.bar([i - w / 2 for i in x], lc_vals, width=w, color="#2e8b57", edgecolor=ACCENT, label="LC")
    ax.bar([i + w / 2 for i in x], lb_vals, width=w, color="#d64545", edgecolor=ACCENT, label="LB")
    ax.set_title("Urodzenia w dekadach (LC vs LB)")
    ax.set_xlabel("dekada")
    ax.set_ylabel("liczba urodzeń")
    ax.set_xticks(x)
    ax.set_xticklabels(decade_labels, rotation=45, ha="right", fontsize=8)
    ax.legend(fontsize=8)
    fig.tight_layout()
    return fig


def fig_female_male_ratio(df: pd.DataFrame) -> plt.Figure:
    now_year = datetime.now().year
    min_dec = (1881 // 10) * 10
    max_dec = (now_year // 10) * 10
    decades = list(range(min_dec, max_dec + 1, 10))

    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    if df is None or df.empty:
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig

    birth_int = df["birth_year"].apply(lambda v: _parse_birth_year(v, lo=1881))
    dfc = df.copy()
    dfc["_birth_int"] = birth_int
    dfc = dfc.dropna(subset=["_birth_int"])
    if dfc.empty:
        ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
        ax.axis("off")
        return fig
    dfc["_birth_int"] = dfc["_birth_int"].astype(int)
    dfc["decade"] = (dfc["_birth_int"] // 10) * 10

    def _norm_sex(v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s in {"M", "F"} else None

    sex_norm = dfc["sex"].apply(_norm_sex) if "sex" in dfc.columns else None
    m_counts: dict[int, int] = {}
    f_counts: dict[int, int] = {}
    if sex_norm is not None:
        m_counts = {int(k): int(v) for k, v in dfc[sex_norm == "M"].groupby("decade").size().to_dict().items()}
        f_counts = {int(k): int(v) for k, v in dfc[sex_norm == "F"].groupby("decade").size().to_dict().items()}

    ratio_decades = [d for d in decades if d >= 1900]
    ratio_labels = [f"{d}-{d+9}" for d in ratio_decades]
    ratio_vals: list[float] = []
    for d in ratio_decades:
        m = m_counts.get(d, 0)
        f = f_counts.get(d, 0)
        ratio_vals.append(float("nan") if m <= 0 else float(f) / float(m))

    xs3 = list(range(len(ratio_decades)))
    ax.plot(xs3, ratio_vals, marker="o", linewidth=2, color=MUTED)
    ax.axhline(1.0, color=ACCENT, linewidth=1, alpha=0.8)
    ax.set_title("Female/Male ratio w dekadach (F/M) od 1900")
    ax.set_xlabel("dekada")
    ax.set_ylabel("F/M")
    ax.set_xticks(xs3)
    ax.set_xticklabels(ratio_labels, rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    return fig


def _comp_per_individual(pid: str, people: dict) -> tuple[int, int, float]:
    levels = get_ancestor_levels_unbounded(person_id=pid, people=people)
    by_gen: dict[int, int] = {}
    for _, lvl in levels.items():
        try:
            g = int(lvl)
        except Exception:
            continue
        if g <= 0:
            continue
        by_gen[g] = by_gen.get(g, 0) + 1
    if not by_gen:
        return 0, 0, 0.0
    MG = int(max(by_gen.keys()))
    CG = 0
    EG = 0.0
    for g, a_g in by_gen.items():
        pcl_g = float(a_g) / float(2**g)
        EG += pcl_g
        if pcl_g >= 0.999999:
            CG += 1
    return MG, CG, EG


def fig_completeness_sex_line(df: pd.DataFrame, people: dict) -> Tuple[plt.Figure, plt.Figure]:
    fig_c, ax_c = plt.subplots(figsize=(8.6, 3.4))
    fig_l, ax_l = plt.subplots(figsize=(8.6, 3.4))

    if df is None or df.empty or not people:
        for ax in (ax_c, ax_l):
            ax.text(0.5, 0.5, "Brak danych", ha="center", va="center")
            ax.axis("off")
        return fig_c, fig_l

    dfc = df.copy()
    dfc["id"] = dfc["id"].astype(str)
    dfc = dfc[dfc["id"].isin(set(people.keys()))].reset_index(drop=True)
    if dfc.empty:
        for ax in (ax_c, ax_l):
            ax.text(0.5, 0.5, "Brak dopasowania ID", ha="center", va="center")
            ax.axis("off")
        return fig_c, fig_l

    comp_memo: dict[str, tuple[int, int, float]] = {}
    for pid in dfc["id"].unique().tolist():
        comp_memo[str(pid)] = _comp_per_individual(str(pid), people)

    def _norm_sex(v: object) -> str:
        if v is None:
            return "NA"
        s = str(v).strip().upper()
        return s if s in {"M", "F"} else "NA"

    def _norm_line(v: object) -> str:
        if v is None:
            return "NA"
        s = str(v).strip().upper()
        return s if s in {"LB", "LC"} else "NA"

    dfc["sex_norm"] = dfc["sex"].apply(_norm_sex) if "sex" in dfc.columns else "NA"
    dfc["line_norm"] = dfc["line"].apply(_norm_line) if "line" in dfc.columns else "NA"

    def _group_means(group_col: str, categories: list[str]) -> dict[str, tuple[float, float, float]]:
        out: dict[str, tuple[float, float, float]] = {}
        for cat in categories:
            pids = dfc[dfc[group_col] == cat]["id"].tolist()
            if not pids:
                out[cat] = (0.0, 0.0, 0.0)
                continue
            MGs = [float(comp_memo[pid][0]) for pid in pids if pid in comp_memo]
            CGs = [float(comp_memo[pid][1]) for pid in pids if pid in comp_memo]
            EGs = [float(comp_memo[pid][2]) for pid in pids if pid in comp_memo]
            if not MGs:
                out[cat] = (0.0, 0.0, 0.0)
                continue
            out[cat] = (
                sum(MGs) / len(MGs),
                sum(CGs) / len(CGs),
                sum(EGs) / len(EGs),
            )
        return out

    sex_means = _group_means("sex_norm", ["M", "F"])
    line_means = _group_means("line_norm", ["LB", "LC", "NA"])

    cats = ["M", "F"]
    MGv = [sex_means[c][0] for c in cats]
    CGv = [sex_means[c][1] for c in cats]
    EGv = [sex_means[c][2] for c in cats]
    xs = list(range(len(cats)))
    ww = 0.26
    ax_c.bar([i - ww for i in xs], MGv, width=ww, color=BUTTON_BG2, edgecolor=ACCENT, label="MG")
    ax_c.bar([i for i in xs], CGv, width=ww, color=BUTTON_BG, edgecolor=ACCENT, label="CG")
    ax_c.bar([i + ww for i in xs], EGv, width=ww, color="#6b5b4d", edgecolor=ACCENT, label="EG")
    ax_c.set_title("Kompletność: MG/CG/EG wg płci")
    ax_c.set_xticks(xs)
    ax_c.set_xticklabels(cats)
    ax_c.legend(fontsize=8)
    fig_c.tight_layout()

    cats2 = ["LB", "LC", "NA"]
    MGv2 = [line_means[c][0] for c in cats2]
    CGv2 = [line_means[c][1] for c in cats2]
    EGv2 = [line_means[c][2] for c in cats2]
    xs2 = list(range(len(cats2)))
    ww2 = 0.22
    ax_l.bar([i - ww2 for i in xs2], MGv2, width=ww2, color=BUTTON_BG2, edgecolor=ACCENT, label="MG")
    ax_l.bar([i for i in xs2], CGv2, width=ww2, color=BUTTON_BG, edgecolor=ACCENT, label="CG")
    ax_l.bar([i + ww2 for i in xs2], EGv2, width=ww2, color="#6b5b4d", edgecolor=ACCENT, label="EG")
    ax_l.set_title("Kompletność: MG/CG/EG wg linii")
    ax_l.set_xticks(xs2)
    ax_l.set_xticklabels(cats2)
    ax_l.legend(fontsize=8)
    fig_l.tight_layout()
    return fig_c, fig_l


def fig_founder_contributions(contributions: Dict[str, float], people: dict) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    if not contributions:
        ax.text(0.5, 0.5, "Brak danych founder contributions", ha="center", va="center")
        ax.axis("off")
        return fig
    items = sorted(contributions.items(), key=lambda kv: kv[1], reverse=True)[:10]
    vals = [float(v) for _, v in items]
    ids = [str(fid) for fid, _ in items]
    labels: list[str] = []
    for fid in ids:
        p = people.get(fid)
        nm = getattr(p, "name", None) if p else None
        labels.append(f"{fid} ({nm})" if nm else fid)
    ax.bar(range(len(items)), vals, color=BUTTON_BG2, edgecolor=ACCENT)
    ax.set_title("Top 10 założycieli (p_i)")
    ax.set_xticks(range(len(items)))
    ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("p_i")
    fig.tight_layout()
    return fig


def fig_histogram_f(f_values: List[float]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(7.5, 3.5))
    if not f_values:
        ax.text(0.5, 0.5, "Brak danych F", ha="center", va="center")
        ax.axis("off")
        return fig
    ax.hist(f_values, bins=30, color="#d5c4ae", edgecolor="#4b3a2a")
    ax.set_title("Rozkład F (Wright) w populacji")
    ax.set_xlabel("F")
    ax.set_ylabel("liczba osobników")
    fig.tight_layout()
    return fig


# --- GI, rodziny, trendy F (jak w gui_pro) ---
# compute_gi_and_family_data: app.analytics.population_gi


def fig_gi_mean_bar(gi_data: Dict[str, Any]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    labels = ["Ojciec→Syn", "Ojciec→Córka", "Matka→Syn", "Matka→Córka"]
    vals = [
        gi_data.get("gi_fs"),
        gi_data.get("gi_fd"),
        gi_data.get("gi_ms"),
        gi_data.get("gi_md"),
    ]
    x = list(range(4))
    bar_colors = [BUTTON_BG2, BUTTON_BG2, BUTTON_BG, BUTTON_BG]
    means = [float(v) if v is not None else 0.0 for v in vals]
    shown = any(v is not None for v in vals)
    if not shown:
        ax.text(0.5, 0.5, "Brak danych GI", ha="center", va="center")
        ax.axis("off")
        return fig
    ax.bar(x, means, color=bar_colors, edgecolor=ACCENT)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
    ax.set_title("Odstęp międzypokoleniowy (GI) — średni wiek rodziców")
    ax.set_ylabel("GI (lata)")
    fig.tight_layout()
    return fig


def fig_gi_trend_decades(gi_data: Dict[str, Any]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    gi_decades: dict[str, dict[int, list[float]]] = gi_data.get("gi_decades") or {}
    all_decades = sorted(
        set().union(*[set(gi_decades.get(k, {}).keys()) for k in ("FS", "FD", "MS", "MD")])
    )
    if not all_decades:
        ax.text(0.5, 0.5, "Brak danych GI w dekadach", ha="center", va="center")
        ax.axis("off")
        return fig

    decade_labels = [f"{d}-{d+9}" for d in all_decades]
    x = list(range(len(all_decades)))
    colors = {"FS": "#9ecbff", "FD": "#ffb4c1", "MS": "#2e8b57", "MD": "#d64545"}
    labels_map = {"FS": "Ojciec→Syn", "FD": "Ojciec→Córka", "MS": "Matka→Syn", "MD": "Matka→Córka"}

    def _dec_mean(path_key: str, d: int) -> Optional[float]:
        xs = gi_decades.get(path_key, {}).get(d, [])
        if not xs:
            return None
        return float(sum(xs)) / float(len(xs))

    for path_key in ("FS", "FD", "MS", "MD"):
        ys = [_dec_mean(path_key, d) for d in all_decades]
        ys_plot = [float(v) if v is not None else float("nan") for v in ys]
        ax.plot(x, ys_plot, marker="o", linewidth=2, color=colors[path_key], label=labels_map[path_key])
    ax.set_title("GI (trend) — dekady urodzenia potomstwa")
    ax.set_xlabel("dekada")
    ax.set_ylabel("średni GI (lata)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    if len(x) > 15:
        step = 2
        ticks = [i for i in x if i % step == 0]
    else:
        ticks = x
    ax.set_xticks(ticks)
    ax.set_xticklabels([decade_labels[i] for i in ticks], rotation=35, ha="right", fontsize=8)
    fig.tight_layout()
    return fig


def fig_family_full_siblings(family_sizes: List[int]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    if not family_sizes:
        ax.text(0.5, 0.5, "Brak danych rodzin", ha="center", va="center")
        ax.axis("off")
        return fig
    c = Counter(int(s) for s in family_sizes)
    max_show = 10
    labels: list[str] = []
    counts: list[int] = []
    for s in range(1, max_show + 1):
        labels.append(str(s))
        counts.append(int(c.get(s, 0)))
    labels.append(f"{max_show}+")
    counts.append(int(sum(v for k, v in c.items() if k > max_show)))
    x2 = list(range(len(labels)))
    ax.bar(x2, counts, color=BUTTON_BG2, edgecolor=ACCENT)
    ax.set_xticks(x2)
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title("Rozkład wielkości rodzin pełnego rodzeństwa")
    ax.set_xlabel("wielkość rodziny (liczba rodzeństwa)")
    ax.set_ylabel("liczba rodzin")
    fig.tight_layout()
    return fig


def prepare_inbreeding_trends_dataframe(
    df: pd.DataFrame,
    people: dict,
    max_generations_back: Optional[int],
    *,
    max_ids: int = 5000,
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """
    Jedno liczenie F (Wright) per ID — wspólne dla wykresów płeć/linie i N_e.
    Zwraca ramkę z kolumnami: id, birth_year_int, _F, (+ sex, line jeśli były).
    """
    warn: Optional[str] = None
    if df is None or df.empty or not people:
        return None, None

    now_year = datetime.now().year

    def _parse_by(v: object) -> Optional[int]:
        if v is None:
            return None
        try:
            if isinstance(v, float) and v != v:
                return None
        except Exception:
            pass
        try:
            y_int = int(float(v))
        except Exception:
            return None
        if y_int < 1900 or y_int > now_year:
            return None
        return y_int

    dfc = df.copy()
    dfc["id"] = dfc["id"].astype(str)
    dfc["birth_year_int"] = dfc["birth_year"].apply(_parse_by)
    dfc = dfc.dropna(subset=["birth_year_int"]).reset_index(drop=True)
    if dfc.empty:
        return None, None

    unique_ids = sorted(set(dfc["id"].tolist()))
    if len(unique_ids) > max_ids:
        unique_ids = unique_ids[:max_ids]
        warn = f"Ograniczono liczenie F do pierwszych {max_ids} ID (wydajność)."
        dfc = dfc[dfc["id"].isin(unique_ids)].reset_index(drop=True)

    f_map: dict[str, float] = {}
    for pid in unique_ids:
        if pid not in people:
            continue
        try:
            f_map[pid] = float(
                wright_inbreeding_F(
                    person_id=pid,
                    people=people,
                    max_generations_back=max_generations_back,
                ).F
            )
        except Exception:
            f_map[pid] = float("nan")

    dfc["_F"] = dfc["id"].apply(lambda pid: f_map.get(str(pid), float("nan")))
    dfc = dfc.dropna(subset=["_F"]).reset_index(drop=True)
    if dfc.empty:
        return None, warn
    return dfc, warn


def fig_inbreeding_year_trends_sex(
    df: pd.DataFrame,
    people: dict,
    max_generations_back: Optional[int],
    *,
    max_ids: int = 5000,
    dfc_precomputed: Optional[pd.DataFrame] = None,
    trend_warn: Optional[str] = None,
) -> Tuple[plt.Figure, Optional[str]]:
    """Średnie F i RIA (%) wg roku urodzenia i płci."""
    warn: Optional[str] = None
    fig, (ax_avg, ax_ria) = plt.subplots(2, 1, figsize=(9, 6))
    if dfc_precomputed is not None:
        dfc = dfc_precomputed.copy()
        warn = trend_warn
    else:
        dfc, warn = prepare_inbreeding_trends_dataframe(
            df, people, max_generations_back, max_ids=max_ids
        )
    if dfc is None or dfc.empty:
        for a in (ax_avg, ax_ria):
            a.text(0.5, 0.5, "Brak danych (rok urodzenia / F)", ha="center", va="center")
            a.axis("off")
        return fig, warn
    if "sex" not in dfc.columns:
        for a in (ax_avg, ax_ria):
            a.text(0.5, 0.5, "Brak kolumny sex", ha="center", va="center")
            a.axis("off")
        return fig, warn

    years = sorted(set(dfc["birth_year_int"].tolist()))
    eps_inbred = 1e-15
    cats_sex = ["M", "F"]
    colors_sex = {"M": "#9ecbff", "F": "#ffb4c1"}

    for cat in cats_sex:
        mask_cat = dfc["sex"].astype(str).str.strip().str.upper() == cat
        avg_f: list[float] = []
        ria: list[float] = []
        for y in years:
            g = dfc[(dfc["birth_year_int"] == y) & mask_cat]
            if g.empty:
                avg_f.append(float("nan"))
                ria.append(float("nan"))
                continue
            vals = g["_F"].tolist()
            avg_f.append(float(sum(vals)) / float(len(vals)))
            ria.append(100.0 * float(sum(1 for v in vals if v > eps_inbred)) / float(len(vals)))
        ax_avg.plot(years, avg_f, marker="o", markersize=2, linewidth=2, color=colors_sex[cat], label=cat)
        ax_ria.plot(years, ria, marker="o", markersize=2, linewidth=2, color=colors_sex[cat], label=cat)

    ax_avg.set_title("Średnie F w populacji — wg płci (rok urodzenia)")
    ax_avg.set_xlabel("rok urodzenia")
    ax_avg.set_ylabel("średnie F")
    ax_avg.grid(True, alpha=0.25)
    ax_avg.legend(fontsize=8)

    ax_ria.set_title("RIA (%) — odsetek z F>0 — wg płci")
    ax_ria.set_xlabel("rok urodzenia")
    ax_ria.set_ylabel("RIA (%)")
    ax_ria.grid(True, alpha=0.25)
    ax_ria.legend(fontsize=8)

    if len(years) > 15:
        step = 5
        ticks = [y for i, y in enumerate(years) if i % step == 0]
        ax_avg.set_xticks(ticks)
        ax_ria.set_xticks(ticks)
    fig.tight_layout()
    return fig, warn


def fig_inbreeding_year_trends_line(
    df: pd.DataFrame,
    people: dict,
    max_generations_back: Optional[int],
    *,
    max_ids: int = 5000,
    dfc_precomputed: Optional[pd.DataFrame] = None,
    trend_warn: Optional[str] = None,
) -> Tuple[plt.Figure, Optional[str]]:
    """Średnie F i RIA wg roku urodzenia i linii LB/LC/NA."""
    warn: Optional[str] = None
    fig, (ax_avg, ax_ria) = plt.subplots(2, 1, figsize=(9, 6))
    if dfc_precomputed is not None:
        dfc = dfc_precomputed.copy()
        warn = trend_warn
    else:
        dfc, warn = prepare_inbreeding_trends_dataframe(
            df, people, max_generations_back, max_ids=max_ids
        )
    if dfc is None or dfc.empty:
        for a in (ax_avg, ax_ria):
            a.text(0.5, 0.5, "Brak danych (rok urodzenia / F)", ha="center", va="center")
            a.axis("off")
        return fig, warn
    if "line" not in dfc.columns:
        for a in (ax_avg, ax_ria):
            a.text(0.5, 0.5, "Brak kolumny line", ha="center", va="center")
            a.axis("off")
        return fig, warn

    years = sorted(set(dfc["birth_year_int"].tolist()))
    eps_inbred = 1e-15
    cats_line = ["LB", "LC", "NA"]
    colors_line = {"LB": "#d64545", "LC": "#2e8b57", "NA": "#d6d0c4"}

    line_norm = dfc["line"].astype(str).str.strip().str.upper()
    line_norm = line_norm.where(line_norm.isin(["LB", "LC"]), other="NA")

    for cat in cats_line:
        mask_cat = line_norm == cat
        avg_f: list[float] = []
        ria: list[float] = []
        for y in years:
            g = dfc[(dfc["birth_year_int"] == y) & mask_cat]
            if g.empty:
                avg_f.append(float("nan"))
                ria.append(float("nan"))
                continue
            vals = g["_F"].tolist()
            avg_f.append(float(sum(vals)) / float(len(vals)))
            ria.append(100.0 * float(sum(1 for v in vals if v > eps_inbred)) / float(len(vals)))
        ax_avg.plot(years, avg_f, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=cat)
        ax_ria.plot(years, ria, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=cat)

    ax_avg.set_title("Średnie F w populacji — wg linii (LB/LC/NA)")
    ax_avg.set_xlabel("rok urodzenia")
    ax_avg.set_ylabel("średnie F")
    ax_avg.grid(True, alpha=0.25)
    ax_avg.legend(fontsize=8)

    ax_ria.set_title("RIA (%) — wg linii")
    ax_ria.set_xlabel("rok urodzenia")
    ax_ria.set_ylabel("RIA (%)")
    ax_ria.grid(True, alpha=0.25)
    ax_ria.legend(fontsize=8)

    if len(years) > 15:
        step = 5
        ticks = [y for i, y in enumerate(years) if i % step == 0]
        ax_avg.set_xticks(ticks)
        ax_ria.set_xticks(ticks)
    fig.tight_layout()
    return fig, warn


def estimate_ne_from_f_trend(
    df: pd.DataFrame,
    people: dict,
    gi_mean: Optional[float],
    max_generations_back: Optional[int],
    *,
    max_ids: int = 5000,
    dfc_precomputed: Optional[pd.DataFrame] = None,
) -> Optional[float]:
    """N_e ~ 1/(2*ΔF_na_pokolenie), ΔF_na_pokolenie = slope_rok * GI."""
    if gi_mean is None or gi_mean <= 0:
        return None
    if dfc_precomputed is not None and not dfc_precomputed.empty:
        dfc = dfc_precomputed.dropna(subset=["_F"]).copy()
        if dfc.empty:
            return None
    elif df is None or df.empty:
        return None
    else:
        dfc, _ = prepare_inbreeding_trends_dataframe(df, people, max_generations_back, max_ids=max_ids)
        if dfc is None or dfc.empty:
            return None
    years = sorted(set(dfc["birth_year_int"].tolist()))
    avg_f_all: list[float] = []
    for y in years:
        g_all = dfc[dfc["birth_year_int"] == y]
        if g_all.empty:
            avg_f_all.append(float("nan"))
        else:
            vals = g_all["_F"].tolist()
            avg_f_all.append(float(sum(vals)) / float(len(vals)))
    xs: list[float] = []
    ys: list[float] = []
    for y, v in zip(years, avg_f_all):
        if v == v:
            xs.append(float(y))
            ys.append(float(v))
    if len(xs) < 2:
        return None
    slope_per_year = float(np.polyfit(xs, ys, 1)[0])
    delta_f_gen = slope_per_year * float(gi_mean)
    if delta_f_gen <= 0:
        return None
    return 1.0 / (2.0 * delta_f_gen)
