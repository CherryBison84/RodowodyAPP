"""
Wykresy zakładki Populacja w GUI Tk (Tkinter + matplotlib).

Obejmuje m.in.: urodzenia w dekadach, trendy F/RIA, top p_i założycieli,
średnie GI, trend GI po dekadach, histogram rodzin pełnego rodzeństwa.

Wyodrębnione z gui_pro.py, aby zmniejszyć rozmiar pliku głównego.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import tkinter as tk
from tkinter import ttk

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.pedigree.ancestor_pedigree import get_ancestor_levels_unbounded


def _clear_frame(area: ttk.Frame) -> None:
    for w in area.winfo_children():
        w.destroy()


def render_birth_decade_charts(
    df_use: Any,
    *,
    state: dict[str, Any],
    colors: Any,
    save_figure_fn: Callable[..., None],
    pop_birth_sex_plot_area: ttk.Frame,
    pop_birth_line_plot_area: ttk.Frame,
    pop_birth_ratio_plot_area: ttk.Frame,
    pop_comp_sex_plot_area: ttk.Frame,
    pop_comp_line_plot_area: ttk.Frame,
) -> None:
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from datetime import datetime

        from pandas import isna  # type: ignore[import-not-found]

        now_year = datetime.now().year
        min_dec = (1881 // 10) * 10  # 1880
        max_dec = (now_year // 10) * 10
        decades = list(range(min_dec, max_dec + 1, 10))
        decade_labels = [f"{d}-{d+9}" for d in decades]

        if df_use is None or getattr(df_use, "empty", True):
            return
        if "birth_year" not in df_use.columns:
            return

        def _parse_birth_year(v: object) -> int | None:
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
            if y_int < 1881 or y_int > now_year:
                return None
            return y_int

        birth_int = df_use["birth_year"].apply(_parse_birth_year)
        dfc = df_use.copy()
        dfc["_birth_int"] = birth_int
        dfc = dfc.dropna(subset=["_birth_int"])
        if dfc.empty:
            return
        dfc["_birth_int"] = dfc["_birth_int"].astype(int)
        dfc["decade"] = (dfc["_birth_int"] // 10) * 10

        # --- Sex split ---
        def _norm_sex(v: object) -> str | None:
            if v is None:
                return None
            s = str(v).strip().upper()
            if s == "M":
                return "M"
            if s == "F":
                return "F"
            return None

        sex_norm = dfc["sex"].apply(_norm_sex) if "sex" in dfc.columns else None
        m_counts: dict[int, int] = {}
        f_counts: dict[int, int] = {}
        if sex_norm is not None:
            vc_m = (
                dfc[sex_norm == "M"].groupby("decade").size().to_dict()
                if not dfc.empty
                else {}
            )
            vc_f = (
                dfc[sex_norm == "F"].groupby("decade").size().to_dict()
                if not dfc.empty
                else {}
            )
            m_counts = vc_m
            f_counts = vc_f

        _clear_frame(pop_birth_sex_plot_area)
        fig1 = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax1 = fig1.add_subplot(1, 1, 1)
        x = list(range(len(decades)))
        w = 0.38
        m_vals = [m_counts.get(d, 0) for d in decades]
        f_vals = [f_counts.get(d, 0) for d in decades]
        ax1.bar([i - w / 2 for i in x], m_vals, width=w, color="#9ecbff", edgecolor=colors.ACCENT, label="M")
        ax1.bar([i + w / 2 for i in x], f_vals, width=w, color="#ffb4c1", edgecolor=colors.ACCENT, label="F")
        ax1.set_title("Urodzenia w dekadach (płeć)")
        ax1.set_xlabel("dekada")
        ax1.set_ylabel("liczba urodzeń")
        ax1.set_xticks(x)
        ax1.set_xticklabels(decade_labels, rotation=45, ha="right", fontsize=8)
        ax1.legend(fontsize=8)
        fig1.tight_layout()
        ttk.Button(
            pop_birth_sex_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig1: save_figure_fn(f, default_basename="pop_urodzenia_plec"),
        ).pack(anchor="w", pady=(0, 6))
        canvas1 = FigureCanvasTkAgg(fig1, master=pop_birth_sex_plot_area)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Line split (LB vs LC) ---
        def _norm_line(v: object) -> str | None:
            if v is None:
                return None
            s = str(v).strip().upper()
            if s == "LB":
                return "LB"
            if s == "LC":
                return "LC"
            return None

        line_norm = dfc["line"].apply(_norm_line) if "line" in dfc.columns else None
        lb_counts: dict[int, int] = {}
        lc_counts: dict[int, int] = {}
        if line_norm is not None:
            vc_lb = (
                dfc[line_norm == "LB"].groupby("decade").size().to_dict()
                if not dfc.empty
                else {}
            )
            vc_lc = (
                dfc[line_norm == "LC"].groupby("decade").size().to_dict()
                if not dfc.empty
                else {}
            )
            lb_counts = vc_lb
            lc_counts = vc_lc

        _clear_frame(pop_birth_line_plot_area)
        fig2 = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax2 = fig2.add_subplot(1, 1, 1)
        lb_vals = [lb_counts.get(d, 0) for d in decades]
        lc_vals = [lc_counts.get(d, 0) for d in decades]
        ax2.bar([i - w / 2 for i in x], lc_vals, width=w, color="#2e8b57", edgecolor=colors.ACCENT, label="LC")
        ax2.bar([i + w / 2 for i in x], lb_vals, width=w, color="#d64545", edgecolor=colors.ACCENT, label="LB")
        ax2.set_title("Urodzenia w dekadach (LC vs LB)")
        ax2.set_xlabel("dekada")
        ax2.set_ylabel("liczba urodzeń")
        ax2.set_xticks(x)
        ax2.set_xticklabels(decade_labels, rotation=45, ha="right", fontsize=8)
        ax2.legend(fontsize=8)
        fig2.tight_layout()
        ttk.Button(
            pop_birth_line_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig2: save_figure_fn(f, default_basename="pop_urodzenia_linie"),
        ).pack(anchor="w", pady=(0, 6))
        canvas2 = FigureCanvasTkAgg(fig2, master=pop_birth_line_plot_area)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Ratio F/M od 1900 (po dekadach) ---
        ratio_decades = [d for d in decades if d >= 1900]
        ratio_labels = [f"{d}-{d+9}" for d in ratio_decades]

        ratio_m = m_counts
        ratio_f = f_counts

        ratio_vals: list[float] = []
        for d in ratio_decades:
            m = ratio_m.get(d, 0)
            f = ratio_f.get(d, 0)
            if m <= 0:
                ratio_vals.append(float("nan"))
            else:
                ratio_vals.append(float(f) / float(m))

        _clear_frame(pop_birth_ratio_plot_area)
        fig3 = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax3 = fig3.add_subplot(1, 1, 1)
        xs3 = list(range(len(ratio_decades)))
        ax3.plot(xs3, ratio_vals, marker="o", linewidth=2, color=colors.MUTED)
        ax3.axhline(1.0, color=colors.ACCENT, linewidth=1, alpha=0.8)
        ax3.set_title("Female/Male ratio w dekadach (F/M) od 1900")
        ax3.set_xlabel("dekada")
        ax3.set_ylabel("F/M")
        ax3.set_xticks(xs3)
        ax3.set_xticklabels(ratio_labels, rotation=45, ha="right", fontsize=8)
        fig3.tight_layout()
        ttk.Button(
            pop_birth_ratio_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig3: save_figure_fn(f, default_basename="pop_urodzenia_ratio_FM"),
        ).pack(anchor="w", pady=(0, 6))
        canvas3 = FigureCanvasTkAgg(fig3, master=pop_birth_ratio_plot_area)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Kompletnosc rodowodu (MG/CG/EG) wg płci oraz linii ---
        people = state.get("people")
        if people:
            # bierzemy tylko rekordy, które istnieją w `people`
            dfc = df_use.copy()
            dfc["id"] = dfc["id"].astype(str)
            dfc = dfc[dfc["id"].isin(set(people.keys()))].reset_index(drop=True)

            # liczymy MG/CG/EG per osobnik (memo)
            pid_list = dfc["id"].tolist() if "id" in dfc.columns else []
            unique_pids = sorted(set(pid_list))

            comp_memo: dict[str, tuple[int, int, float]] = {}

            for pid in unique_pids:
                levels = get_ancestor_levels_unbounded(person_id=pid, people=people)
                by_gen: dict[int, int] = {}
                for _, lvl in levels.items():
                    if lvl is None or lvl <= 0:
                        continue
                    by_gen[lvl] = by_gen.get(lvl, 0) + 1

                if not by_gen:
                    comp_memo[pid] = (0, 0, 0.0)
                    continue

                MG = int(max(by_gen.keys()))
                CG = 0
                EG = 0.0
                for g, a_g in by_gen.items():
                    pcl_g = float(a_g) / float(2**g)
                    EG += pcl_g
                    if pcl_g >= 0.999999:
                        CG += 1
                comp_memo[pid] = (MG, CG, EG)

            def _norm_sex_comp(v: object) -> str:
                if v is None:
                    return "NA"
                s = str(v).strip().upper()
                return s if s in {"M", "F"} else "NA"

            def _norm_line_comp(v: object) -> str:
                if v is None:
                    return "NA"
                s = str(v).strip().upper()
                return s if s in {"LB", "LC"} else "NA"

            dfc["sex_norm"] = dfc["sex"].apply(_norm_sex_comp) if "sex" in dfc.columns else "NA"
            dfc["line_norm"] = dfc["line"].apply(_norm_line_comp) if "line" in dfc.columns else "NA"

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
                        float(sum(MGs)) / float(len(MGs)),
                        float(sum(CGs)) / float(len(CGs)),
                        float(sum(EGs)) / float(len(EGs)),
                    )
                return out

            sex_means = _group_means("sex_norm", ["M", "F"])
            line_means = _group_means("line_norm", ["LB", "LC", "NA"])

            # --- wykres płci ---
            _clear_frame(pop_comp_sex_plot_area)
            cats = ["M", "F"]
            MGv = [sex_means[c][0] for c in cats]
            CGv = [sex_means[c][1] for c in cats]
            EGv = [sex_means[c][2] for c in cats]

            fig_c = plt.Figure(figsize=(8.6, 3.4), dpi=100)
            ax_c = fig_c.add_subplot(1, 1, 1)
            xs = list(range(len(cats)))
            ww = 0.26
            ax_c.bar([i - ww for i in xs], MGv, width=ww, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT, label="MG (max)")
            ax_c.bar([i for i in xs], CGv, width=ww, color=colors.BUTTON_BG, edgecolor=colors.ACCENT, label="CG (kompletne)")
            ax_c.bar([i + ww for i in xs], EGv, width=ww, color="#6b5b4d", edgecolor=colors.ACCENT, label="EG (równoważne)")
            ax_c.set_title("Kompletność: MG/CG/EG wg płci")
            ax_c.set_xlabel("płeć")
            ax_c.set_ylabel("wartość (średnia)")
            ax_c.set_xticks(xs)
            ax_c.set_xticklabels(cats, fontsize=9)
            ax_c.legend(fontsize=8)
            fig_c.tight_layout()
            ttk.Button(
                pop_comp_sex_plot_area,
                text="Zapis wykresu (jpeg)",
                command=lambda f=fig_c: save_figure_fn(f, default_basename="pop_kompletnosc_plec"),
            ).pack(anchor="w", pady=(0, 6))
            canvas_c = FigureCanvasTkAgg(fig_c, master=pop_comp_sex_plot_area)
            canvas_c.draw()
            canvas_c.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # --- wykres linii ---
            _clear_frame(pop_comp_line_plot_area)
            cats2 = ["LB", "LC", "NA"]
            MGv2 = [line_means[c][0] for c in cats2]
            CGv2 = [line_means[c][1] for c in cats2]
            EGv2 = [line_means[c][2] for c in cats2]

            fig_l = plt.Figure(figsize=(8.6, 3.4), dpi=100)
            ax_l = fig_l.add_subplot(1, 1, 1)
            xs2 = list(range(len(cats2)))
            ww2 = 0.22
            ax_l.bar([i - ww2 for i in xs2], MGv2, width=ww2, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT, label="MG (max)")
            ax_l.bar([i for i in xs2], CGv2, width=ww2, color=colors.BUTTON_BG, edgecolor=colors.ACCENT, label="CG (kompletne)")
            ax_l.bar([i + ww2 for i in xs2], EGv2, width=ww2, color="#6b5b4d", edgecolor=colors.ACCENT, label="EG (równoważne)")
            ax_l.set_title("Kompletność: MG/CG/EG wg linii")
            ax_l.set_xlabel("linia")
            ax_l.set_ylabel("wartość (średnia)")
            ax_l.set_xticks(xs2)
            ax_l.set_xticklabels(cats2, fontsize=9)
            ax_l.legend(fontsize=8)
            fig_l.tight_layout()
            ttk.Button(
                pop_comp_line_plot_area,
                text="Zapis wykresu (jpeg)",
                command=lambda f=fig_l: save_figure_fn(f, default_basename="pop_kompletnosc_linie"),
            ).pack(anchor="w", pady=(0, 6))
            canvas_l = FigureCanvasTkAgg(fig_l, master=pop_comp_line_plot_area)
            canvas_l.draw()
            canvas_l.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception:
        return


def render_inbreeding_year_trends(
    df_use: Any,
    *,
    state: dict[str, Any],
    pop_depth_inb_var: tk.StringVar,
    pop_unbounded_inb_var: tk.BooleanVar | tk.StringVar,
    pop_inb_year_sex_plot_area: ttk.Frame,
    pop_inb_year_line_plot_area: ttk.Frame,
    pop_ria_overall_var: tk.StringVar,
    pop_ne_var: tk.StringVar,
    save_figure_fn: Callable[..., None],
) -> None:
    """
    Average F oraz Rate of Inbred Animals (RIA, %) w czasie (TP),
    osobno dla:
    - płci (M/F)
    - linii (LB/LC)
    """
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from datetime import datetime

        people = state.get("people")
        if not people:
            return

        if df_use is None or getattr(df_use, "empty", True):
            return
        if "birth_year" not in df_use.columns:
            return

        now_year = datetime.now().year

        def _parse_birth_year(v: object) -> int | None:
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

        dfc = df_use.copy()
        dfc["id"] = dfc["id"].astype(str)
        dfc["birth_year_int"] = dfc["birth_year"].apply(_parse_birth_year)
        dfc = dfc.dropna(subset=["birth_year_int"]).reset_index(drop=True)
        if dfc.empty:
            return
        dfc["birth_year_int"] = dfc["birth_year_int"].astype(int)

        # Limit pokoleń dla obliczeń F:
        try:
            depth = int(str(pop_depth_inb_var.get()).strip())
        except Exception:
            depth = 4
        if depth < 0:
            depth = 0
        depth = min(depth, 30)
        max_generations_back = None if bool(pop_unbounded_inb_var.get()) else depth

        unique_ids = sorted(set(dfc["id"].tolist()))
        f_map: dict[str, float] = {}
        for pid in unique_ids:
            if pid not in people:
                continue
            try:
                f_map[pid] = float(
                    wright_inbreeding_F(
                        person_id=pid,
                        people=people,  # type: ignore[arg-type]
                        max_generations_back=max_generations_back,
                    ).F
                )
            except Exception:
                f_map[pid] = float("nan")

        dfc["_F"] = dfc["id"].apply(lambda pid: f_map.get(str(pid), float("nan")))
        dfc = dfc.dropna(subset=["_F"]).reset_index(drop=True)
        if dfc.empty:
            return

        years = sorted(set(dfc["birth_year_int"].tolist()))

        eps_inbred = 1e-15  # F>0 (w sensie numerycznym)

        try:
            f_vals = dfc["_F"].tolist() if "_F" in dfc.columns else []
            if f_vals:
                ria_overall = 100.0 * float(sum(1 for v in f_vals if v > eps_inbred)) / float(len(f_vals))
                pop_ria_overall_var.set(f"- RIA ogółem (F>0): {ria_overall:.1f}%")
        except Exception:
            pass

        # --- Wykres wg płci ---
        _clear_frame(pop_inb_year_sex_plot_area)
        cats_sex = ["M", "F"]
        colors_sex = {"M": "#9ecbff", "F": "#ffb4c1"}

        fig = plt.Figure(figsize=(9, 6), dpi=100)
        ax_avg = fig.add_subplot(2, 1, 1)
        ax_ria = fig.add_subplot(2, 1, 2)

        for cat in cats_sex:
            dfc_cat = dfc.copy()
            sex_col = dfc_cat["sex"] if "sex" in dfc_cat.columns else None
            if sex_col is None:
                continue
            mask_cat = dfc_cat["sex"].astype(str).str.strip().str.upper() == cat
            avgF: list[float] = []
            ria: list[float] = []
            for y in years:
                g = dfc_cat[(dfc_cat["birth_year_int"] == y) & mask_cat]
                if g.empty:
                    avgF.append(float("nan"))
                    ria.append(float("nan"))
                    continue
                vals = g["_F"].tolist()
                avgF.append(float(sum(vals)) / float(len(vals)))
                ria.append(100.0 * float(sum(1 for v in vals if v > eps_inbred)) / float(len(vals)))
            ax_avg.plot(years, avgF, marker="o", markersize=2, linewidth=2, color=colors_sex[cat], label=f"{cat}")
            ax_ria.plot(years, ria, marker="o", markersize=2, linewidth=2, color=colors_sex[cat], label=f"{cat}")

        ax_avg.set_title("Average Inbreeding Coefficient (F) w TP — wg płci")
        ax_avg.set_xlabel("rok urodzenia")
        ax_avg.set_ylabel("średnie F")
        ax_avg.grid(True, alpha=0.25)
        ax_avg.legend(fontsize=8)

        ax_ria.set_title("Rate of Inbred Animals (RIA) w TP — wg płci")
        ax_ria.set_xlabel("rok urodzenia")
        ax_ria.set_ylabel("RIA (%) — F>0")
        ax_ria.grid(True, alpha=0.25)
        ax_ria.legend(fontsize=8)

        if len(years) > 15:
            step = 5
            ticks = [y for i, y in enumerate(years) if i % step == 0]
            ax_avg.set_xticks(ticks)
            ax_ria.set_xticks(ticks)
        fig.tight_layout()

        ttk.Button(
            pop_inb_year_sex_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig: save_figure_fn(f, default_basename="pop_inbred_trend_plec"),
        ).pack(anchor="w", pady=(0, 6))

        canvas = FigureCanvasTkAgg(fig, master=pop_inb_year_sex_plot_area)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- Wykres wg linii ---
        _clear_frame(pop_inb_year_line_plot_area)
        cats_line = ["LB", "LC", "NA"]
        colors_line = {"LB": "#d64545", "LC": "#2e8b57", "NA": "#d6d0c4"}

        fig2 = plt.Figure(figsize=(9, 6), dpi=100)
        ax_avg2 = fig2.add_subplot(2, 1, 1)
        ax_ria2 = fig2.add_subplot(2, 1, 2)

        line_col = dfc["line"] if "line" in dfc.columns else None
        if line_col is None:
            return

        line_norm = dfc["line"].astype(str).str.strip().str.upper()
        for cat in cats_line:
            mask_cat = line_norm == cat
            avgF2: list[float] = []
            ria2: list[float] = []
            for y in years:
                g = dfc[(dfc["birth_year_int"] == y) & mask_cat]
                if g.empty:
                    avgF2.append(float("nan"))
                    ria2.append(float("nan"))
                    continue
                vals = g["_F"].tolist()
                avgF2.append(float(sum(vals)) / float(len(vals)))
                ria2.append(100.0 * float(sum(1 for v in vals if v > eps_inbred)) / float(len(vals)))
            ax_avg2.plot(years, avgF2, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=f"{cat}")
            ax_ria2.plot(years, ria2, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=f"{cat}")

        ax_avg2.set_title("Average Inbreeding Coefficient (F) w TP — wg linii")
        ax_avg2.set_xlabel("rok urodzenia")
        ax_avg2.set_ylabel("średnie F")
        ax_avg2.grid(True, alpha=0.25)
        ax_avg2.legend(fontsize=8)

        ax_ria2.set_title("Rate of Inbred Animals (RIA) w TP — wg linii")
        ax_ria2.set_xlabel("rok urodzenia")
        ax_ria2.set_ylabel("RIA (%) — F>0")
        ax_ria2.grid(True, alpha=0.25)
        ax_ria2.legend(fontsize=8)

        if len(years) > 15:
            step = 5
            ticks2 = [y for i, y in enumerate(years) if i % step == 0]
            ax_avg2.set_xticks(ticks2)
            ax_ria2.set_xticks(ticks2)
        fig2.tight_layout()

        ttk.Button(
            pop_inb_year_line_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig2: save_figure_fn(f, default_basename="pop_inbred_trend_linie"),
        ).pack(anchor="w", pady=(0, 6))

        canvas2 = FigureCanvasTkAgg(fig2, master=pop_inb_year_line_plot_area)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- N_e (efektywna wielkość populacji) z trendu F ---
        try:
            import numpy as np

            avgF_all: list[float] = []
            for y in years:
                g_all = dfc[dfc["birth_year_int"] == y]
                if g_all.empty:
                    avgF_all.append(float("nan"))
                else:
                    vals_all = g_all["_F"].tolist()
                    avgF_all.append(float(sum(vals_all)) / float(len(vals_all)))

            xs: list[float] = []
            ys: list[float] = []
            for y, v in zip(years, avgF_all):
                if v == v and y == y:  # nan-safe
                    xs.append(float(y))
                    ys.append(float(v))

            if len(xs) >= 2:
                slope_per_year = float(np.polyfit(xs, ys, 1)[0])  # dF/dyear
                gi_mean = state.get("population_gi_mean")
                if gi_mean is not None and gi_mean > 0 and slope_per_year == slope_per_year:
                    deltaF_per_gen = slope_per_year * float(gi_mean)
                    if deltaF_per_gen > 0:
                        ne = 1.0 / (2.0 * deltaF_per_gen)
                        pop_ne_var.set(f"- N_e (efektywna wielkość populacji, z trendu F): {ne:.1f}")
                    else:
                        pop_ne_var.set("- N_e: brak wzrostu F (ΔF<=0)")
        except Exception:
            pass

    except Exception:
        return


def render_founders_pi_chart(
    *,
    state: dict[str, Any],
    colors: Any,
    people: dict[str, Any] | None,
    save_figure_fn: Callable[..., None],
    pop_founders_plot_area: ttk.Frame,
) -> None:
    """Top założycieli (p_i) w zakładce populacji."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        _clear_frame(pop_founders_plot_area)

        contribs = state.get("population_founder_contributions") or {}
        founder_items: list[tuple[Any, Any]] = []
        if isinstance(contribs, dict):
            try:
                founder_items = sorted(contribs.items(), key=lambda kv: kv[1], reverse=True)
            except Exception:
                founder_items = []

        top_k = min(10, len(founder_items))
        fig_fe = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax_fe = fig_fe.add_subplot(1, 1, 1)

        if top_k > 0:
            top_items = founder_items[:top_k]
            vals = [float(v) for _, v in top_items]
            ids = [str(fid) for fid, _ in top_items]

            ax_fe.bar(range(len(top_items)), vals, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
            ax_fe.set_title(f"Top {top_k} założycieli (p_i)")
            ax_fe.set_xlabel("założyciel (ID + imię)")
            ax_fe.set_ylabel("p_i (udział)")
            ax_fe.set_xticks(range(len(top_items)))

            labels: list[str] = []
            for fid in ids:
                p = people.get(fid) if people else None
                nm = getattr(p, "name", None) if p else None
                labels.append(f"{fid} ({nm})" if nm else fid)
            ax_fe.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
        else:
            ax_fe.text(0.5, 0.5, "Brak danych founder contributions", ha="center", va="center")
            ax_fe.axis("off")

        fig_fe.tight_layout()
        ttk.Button(
            pop_founders_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig_fe: save_figure_fn(f, default_basename="pop_founders_pi"),
        ).pack(anchor="w", pady=(0, 6))
        canvas_fe = FigureCanvasTkAgg(fig_fe, master=pop_founders_plot_area)
        canvas_fe.draw()
        canvas_fe.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception:
        pass


def render_gi_and_family_charts(
    *,
    colors: Any,
    save_figure_fn: Callable[..., None],
    people: dict[str, Any] | None,
    gi_data: dict[str, Any],
    pop_gi_plot_area: ttk.Frame,
    pop_gi_trend_plot_area: ttk.Frame,
    pop_family_plot_area: ttk.Frame,
) -> None:
    """Średnie GI, trend GI po dekadach, histogram wielkości rodzin pełnego rodzeństwa."""
    if not people:
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from collections import Counter

        gi_decades: dict[str, dict[int, list[float]]] = gi_data.get("gi_decades") or {
            "FS": {},
            "FD": {},
            "MS": {},
            "MD": {},
        }

        # GI bar chart
        _clear_frame(pop_gi_plot_area)
        gi_vals = [
            gi_data.get("gi_fs"),
            gi_data.get("gi_fd"),
            gi_data.get("gi_ms"),
            gi_data.get("gi_md"),
        ]
        gi_labels = ["Ojciec→Syn", "Ojciec→Córka", "Matka→Syn", "Matka→Córka"]
        fig_gi = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax_gi = fig_gi.add_subplot(1, 1, 1)
        x = list(range(len(gi_labels)))
        bar_colors = [colors.BUTTON_BG2, colors.BUTTON_BG2, colors.BUTTON_BG, colors.BUTTON_BG]
        shown = [(i, v) for i, v in enumerate(gi_vals) if v is not None]
        if shown:
            means = [v if v is not None else 0.0 for v in gi_vals]
            ax_gi.bar(x, means, color=bar_colors, edgecolor=colors.ACCENT)
            ax_gi.set_xticks(x)
            ax_gi.set_xticklabels(gi_labels, rotation=20, ha="right", fontsize=8)
        else:
            ax_gi.text(0.5, 0.5, "Brak danych GI", ha="center", va="center")
            ax_gi.axis("off")
        ax_gi.set_title("Odstęp międzypokoleniowy (GI)")
        ax_gi.set_ylabel("GI (lata)")
        fig_gi.tight_layout()
        ttk.Button(
            pop_gi_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig_gi: save_figure_fn(f, default_basename="pop_gi_mean"),
        ).pack(anchor="w", pady=(0, 6))
        canvas_gi = FigureCanvasTkAgg(fig_gi, master=pop_gi_plot_area)
        canvas_gi.draw()
        canvas_gi.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # --- GI trend (w dekadach) ---
        _clear_frame(pop_gi_trend_plot_area)
        all_decades = sorted(set().union(*[set(gi_decades[k].keys()) for k in gi_decades.keys()]))
        if all_decades:
            decade_labels = [f"{d}-{d+9}" for d in all_decades]

            def _decade_mean(path_key: str, d: int) -> float | None:
                xs = gi_decades.get(path_key, {}).get(d, [])
                if not xs:
                    return None
                return float(sum(xs)) / float(len(xs))

            gi_fs = [_decade_mean("FS", d) for d in all_decades]
            gi_fd = [_decade_mean("FD", d) for d in all_decades]
            gi_ms = [_decade_mean("MS", d) for d in all_decades]
            gi_md = [_decade_mean("MD", d) for d in all_decades]

            fig_t = plt.Figure(figsize=(8.6, 3.4), dpi=100)
            ax_t = fig_t.add_subplot(1, 1, 1)
            x_t = list(range(len(all_decades)))

            def _to_plot(arr: list[float | None]) -> list[float]:
                return [float(v) if v is not None else float("nan") for v in arr]

            ax_t.plot(x_t, _to_plot(gi_fs), marker="o", linewidth=2, color="#9ecbff", label="Ojciec→Syn")
            ax_t.plot(x_t, _to_plot(gi_fd), marker="o", linewidth=2, color="#ffb4c1", label="Ojciec→Córka")
            ax_t.plot(x_t, _to_plot(gi_ms), marker="o", linewidth=2, color="#2e8b57", label="Matka→Syn")
            ax_t.plot(x_t, _to_plot(gi_md), marker="o", linewidth=2, color="#d64545", label="Matka→Córka")

            ax_t.set_title("GI (trend) — Ojciec/Mak x płeć potomstwa (dekady)")
            ax_t.set_xlabel("dekada urodzenia potomstwa")
            ax_t.set_ylabel("średni GI (lata)")
            ax_t.grid(True, alpha=0.25)
            ax_t.legend(fontsize=8)

            if len(x_t) > 15:
                step = 2
            else:
                step = 1
            ticks = [i for i in x_t if i % step == 0]
            ax_t.set_xticks(ticks)
            ax_t.set_xticklabels(
                [decade_labels[i] for i in ticks],
                rotation=35,
                ha="right",
                fontsize=8,
            )
            fig_t.tight_layout()
            ttk.Button(
                pop_gi_trend_plot_area,
                text="Zapis wykresu (jpeg)",
                command=lambda f=fig_t: save_figure_fn(f, default_basename="pop_gi_trend"),
            ).pack(anchor="w", pady=(0, 6))
            canvas_t = FigureCanvasTkAgg(fig_t, master=pop_gi_trend_plot_area)
            canvas_t.draw()
            canvas_t.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            fig_t = plt.Figure(figsize=(8.6, 3.4), dpi=100)
            ax_t = fig_t.add_subplot(1, 1, 1)
            ax_t.text(0.5, 0.5, "Brak danych GI w dekadach", ha="center", va="center")
            ax_t.axis("off")
            fig_t.tight_layout()
            ttk.Button(
                pop_gi_trend_plot_area,
                text="Zapis wykresu (jpeg)",
                command=lambda f=fig_t: save_figure_fn(f, default_basename="pop_gi_trend"),
            ).pack(anchor="w", pady=(0, 6))
            canvas_t = FigureCanvasTkAgg(fig_t, master=pop_gi_trend_plot_area)
            canvas_t.draw()
            canvas_t.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Family size histogram
        _clear_frame(pop_family_plot_area)
        fam_sizes = gi_data.get("family_sizes") or []
        fig_f = plt.Figure(figsize=(8.6, 3.4), dpi=100)
        ax_f = fig_f.add_subplot(1, 1, 1)
        if fam_sizes:
            c = Counter(int(s) for s in fam_sizes)
            max_show = 10
            labels: list[str] = []
            counts: list[int] = []
            for s in range(1, max_show + 1):
                labels.append(str(s))
                counts.append(int(c.get(s, 0)))
            labels.append(f"{max_show}+")
            counts.append(int(sum(v for k, v in c.items() if k > max_show)))

            x2 = list(range(len(labels)))
            ax_f.bar(x2, counts, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
            ax_f.set_xticks(x2)
            ax_f.set_xticklabels(labels, fontsize=8)
            ax_f.set_title("Rozkład wielkości rodzin pełnego rodzeństwa")
            ax_f.set_xlabel("wielkość rodziny (liczba rodzeństwa pełnego)")
            ax_f.set_ylabel("liczba rodzin")
        else:
            ax_f.text(0.5, 0.5, "Brak danych rodzin", ha="center", va="center")
            ax_f.axis("off")
        fig_f.tight_layout()
        ttk.Button(
            pop_family_plot_area,
            text="Zapis wykresu (jpeg)",
            command=lambda f=fig_f: save_figure_fn(f, default_basename="pop_family_sizes"),
        ).pack(anchor="w", pady=(0, 6))
        canvas_f = FigureCanvasTkAgg(fig_f, master=pop_family_plot_area)
        canvas_f.draw()
        canvas_f.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    except Exception:
        pass
