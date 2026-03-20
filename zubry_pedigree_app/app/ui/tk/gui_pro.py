from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.data.dataset_loader import load_dataset_from_path, load_default_bison_report
from app.pedigree.ancestor_pedigree import (
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
    get_ancestor_levels_unbounded,
)
from app.pedigree.ancestor_pedigree import build_people_map as _build_people_map
from app.visualizations.ancestor_plot import plot_ancestor_pedigree
from app.analytics.line_membership import (
    compute_all_line_memberships,
    get_line_membership,
)
from app.analytics.population_genetics import TEST_ID, compute_population_genetics_stats


def _clear_frame(frame: ttk.Frame) -> None:
    for w in frame.winfo_children():
        w.destroy()


@dataclass(frozen=True)
class Theme:
    APP_BG: str = "#ffffff"
    PANEL_BG: str = "#f4fbf5"
    PANEL_BG2: str = "#eaf7ec"
    TEXT: str = "#0f3b2a"
    MUTED: str = "#2c6a4e"
    ACCENT: str = "#caa86e"
    BUTTON_BG: str = "#dff4e3"
    BUTTON_BG2: str = "#c8ead4"
    ENTRY_BG: str = "#ffffff"
    EDGE_PLOT: str = "#2c6a4e"
    TREE_BG: str = "#f4fbf5"


def _setup_theme(root: tk.Tk) -> Theme:
    colors = Theme()
    root.configure(bg=colors.APP_BG)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TFrame", background=colors.PANEL_BG)
    style.configure("TLabel", background=colors.PANEL_BG, foreground=colors.TEXT)
    style.configure("TNotebook", background=colors.PANEL_BG)
    style.configure(
        "TNotebook.Tab",
        background=colors.BUTTON_BG2,
        foreground=colors.MUTED,
        padding=(10, 6),
        font=("TkDefaultFont", 11, "bold"),
    )

    style.configure("TButton", background=colors.BUTTON_BG, foreground=colors.TEXT, padding=(10, 6))
    style.map("TButton", background=[("active", colors.BUTTON_BG2)])

    style.configure(
        "TEntry",
        fieldbackground=colors.ENTRY_BG,
        background=colors.ENTRY_BG,
        foreground=colors.TEXT,
        bordercolor=colors.ACCENT,
    )
    style.configure("TCheckbutton", background=colors.PANEL_BG, foreground=colors.TEXT)

    style.configure(
        "Treeview",
        background=colors.TREE_BG,
        fieldbackground=colors.TREE_BG,
        foreground=colors.TEXT,
        rowheight=22,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=colors.BUTTON_BG2,
        foreground=colors.ACCENT,
        borderwidth=0,
        relief="flat",
        padding=(6, 4),
    )
    style.map("Treeview", background=[("selected", colors.BUTTON_BG)], foreground=[("selected", colors.TEXT)])
    return colors


def run_tk_pro() -> None:
    root = tk.Tk()
    root.title("WisentPedigree Pro+")
    root.geometry("1280x860")

    colors = _setup_theme(root)

    # -------------------------
    # Logo + header
    # -------------------------
    header = ttk.Frame(root, padding=(12, 10), style="TFrame")
    header.pack(side=tk.TOP, fill=tk.X)

    logo_path = Path(__file__).resolve().parents[2] / "logo.png"
    logo_img = None
    if logo_path.exists():
        try:
            logo_img = tk.PhotoImage(file=str(logo_path))
            # quick downscale (Tk PhotoImage can be heavy; subsample is OK).
            try:
                w = logo_img.width()
            except Exception:
                w = 0
            # Docelowa szerokość logo w nagłówku (Tk PhotoImage sub-sampling).
            target_w = 150
            if w and w > target_w:
                factor = max(2, int(round(w / target_w)))
                logo_img = logo_img.subsample(factor, factor)
        except Exception:
            logo_img = None

    if logo_img is not None:
        ttk.Label(header, image=logo_img).pack(side=tk.LEFT, padx=(0, 12))

    ttk.Label(header, text="WisentPedigree Pro+", font=("TkDefaultFont", 18, "bold")).pack(side=tk.LEFT)
    subtitle = ttk.Label(header, text="Rodowody żubrów • Inbreeding • Wizualizacja", foreground=colors.MUTED)
    subtitle.pack(side=tk.LEFT, padx=(16, 0))

    # -------------------------
    # Main: Notebook tabs
    # -------------------------
    status_var = tk.StringVar(value="Gotowe.")
    status_bar = tk.Label(
        root,
        textvariable=status_var,
        bd=1,
        relief=tk.SUNKEN,
        anchor="w",
        bg=colors.APP_BG,
        fg=colors.TEXT,
    )
    status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    notebook = ttk.Notebook(root)
    notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    tab_persons = ttk.Frame(notebook, padding=14)
    tab_pedigree = ttk.Frame(notebook, padding=14)
    tab_analysis = ttk.Frame(notebook, padding=14)
    tab_population = ttk.Frame(notebook, padding=14)
    tab_reports = ttk.Frame(notebook, padding=14)
    tab_settings = ttk.Frame(notebook, padding=14)

    notebook.add(tab_persons, text="Osobniki")
    notebook.add(tab_pedigree, text="Rodowód")
    notebook.add(tab_analysis, text="Analizy")
    notebook.add(tab_population, text="Populacja")
    notebook.add(tab_reports, text="Raporty")
    notebook.add(tab_settings, text="Ustawienia")

    def _placeholder(tab: ttk.Frame, title: str) -> None:
        ttk.Label(tab, text=title, font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(tab, text="Sekcja w przygotowaniu.", foreground=colors.MUTED).pack(anchor="w", pady=(8, 0))

    _placeholder(tab_reports, "Raporty")
    _placeholder(tab_settings, "Ustawienia")

    # -------------------------
    # Shared app state
    # -------------------------
    state: dict[str, object] = {"df_std": None, "people": None, "line_memberships": {}}

    # -------------------------
    # Populacja tab (podstawowe metryki)
    # -------------------------
    pop_frame = ttk.Frame(tab_population)
    pop_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(14, 0))

    pop_total_var = tk.StringVar(value="-")
    pop_founders_count_var = tk.StringVar(value="-")
    pop_known_parents_var = tk.StringVar(value="-")
    pop_known_father_var = tk.StringVar(value="-")
    pop_known_mother_var = tk.StringVar(value="-")
    pop_lines_var = tk.StringVar(value="-")

    # Parametry liczenia inbredu (F) dla metryk populacyjnych (bez wpływu na "Analizy").
    pop_depth_inb_var = tk.StringVar(value="4")
    pop_unbounded_inb_var = tk.BooleanVar(value=False)

    # Genetyka populacyjna (TP/RP — zależnie od implementacji).
    pop_f_e_var = tk.StringVar(value="-")
    pop_f_a_var = tk.StringVar(value="-")
    pop_bottleneck_var = tk.StringVar(value="-")
    pop_ne_var = tk.StringVar(value="-")
    pop_drift_var = tk.StringVar(value="-")
    pop_ria_overall_var = tk.StringVar(value="-")

    # Demografia / rodowód.
    pop_gi_mean_var = tk.StringVar(value="-")
    pop_gi_father_son_var = tk.StringVar(value="-")
    pop_gi_father_daughter_var = tk.StringVar(value="-")
    pop_gi_mother_son_var = tk.StringVar(value="-")
    pop_gi_mother_daughter_var = tk.StringVar(value="-")

    pop_family_count_var = tk.StringVar(value="-")
    pop_family_mean_size_var = tk.StringVar(value="-")

    ttk.Label(pop_frame, text="Podstawowe statystyki:", foreground=colors.TEXT, font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    pop_basic_grid = ttk.Frame(pop_frame)
    pop_basic_grid.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))
    pop_basic_grid.columnconfigure(0, weight=1)
    pop_basic_grid.columnconfigure(1, weight=1)

    ttk.Label(pop_basic_grid, textvariable=pop_total_var, foreground=colors.TEXT).grid(row=0, column=0, sticky="w")
    ttk.Label(pop_basic_grid, textvariable=pop_founders_count_var, foreground=colors.TEXT).grid(row=1, column=0, sticky="w")
    ttk.Label(pop_basic_grid, textvariable=pop_known_parents_var, foreground=colors.TEXT).grid(row=2, column=0, sticky="w")

    ttk.Label(pop_basic_grid, textvariable=pop_known_father_var, foreground=colors.TEXT).grid(row=0, column=1, sticky="w")
    ttk.Label(pop_basic_grid, textvariable=pop_known_mother_var, foreground=colors.TEXT).grid(row=1, column=1, sticky="w")
    ttk.Label(pop_basic_grid, textvariable=pop_lines_var, foreground=colors.TEXT).grid(row=2, column=1, sticky="w", pady=(10, 0))

    # --- Parametry liczenia F (dla wykresów populacyjnych) ---
    pop_inb_param_frame = ttk.Frame(pop_frame)
    pop_inb_param_frame.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))
    ttk.Label(
        pop_inb_param_frame,
        text="Parametry F (dla wykresów populacyjnych):",
        foreground=colors.TEXT,
        font=("TkDefaultFont", 12, "bold"),
    ).pack(anchor="w")

    pop_unbounded_inb_cb = ttk.Checkbutton(
        pop_inb_param_frame,
        text="Bez ograniczenia (do founderów)",
        variable=pop_unbounded_inb_var,
    )
    pop_unbounded_inb_cb.pack(anchor="w", pady=(6, 0))

    pop_depth_inb_row = ttk.Frame(pop_inb_param_frame)
    pop_depth_inb_row.pack(anchor="w", pady=(6, 0))
    ttk.Label(pop_depth_inb_row, text="Max pokoleń:").pack(side=tk.LEFT)
    pop_depth_inb_entry = ttk.Entry(pop_depth_inb_row, textvariable=pop_depth_inb_var, width=10)
    pop_depth_inb_entry.pack(side=tk.LEFT, padx=(8, 0))

    def _sync_pop_inb_depth_state() -> None:
        st = "disabled" if bool(pop_unbounded_inb_var.get()) else "normal"
        pop_depth_inb_entry.configure(state=st)

    _sync_pop_inb_depth_state()
    pop_unbounded_inb_var.trace_add("write", lambda *_args: _sync_pop_inb_depth_state())

    # --- Genetyka i demografia populacji (skrót) ---
    ttk.Label(
        pop_frame,
        text="Wskaźniki genetyczne i demograficzne:",
        foreground=colors.TEXT,
        font=("TkDefaultFont", 12, "bold"),
    ).pack(anchor="w", pady=(12, 0))

    pop_meta_grid = ttk.Frame(pop_frame)
    pop_meta_grid.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))
    pop_meta_grid.columnconfigure(0, weight=1)
    pop_meta_grid.columnconfigure(1, weight=1)

    ttk.Label(pop_meta_grid, textvariable=pop_f_e_var, foreground=colors.TEXT).grid(row=0, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_f_a_var, foreground=colors.TEXT).grid(row=0, column=1, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_bottleneck_var, foreground=colors.TEXT).grid(row=1, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_ne_var, foreground=colors.TEXT).grid(row=1, column=1, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_drift_var, foreground=colors.TEXT).grid(row=2, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_ria_overall_var, foreground=colors.TEXT).grid(row=2, column=1, sticky="w")

    ttk.Label(pop_meta_grid, textvariable=pop_gi_mean_var, foreground=colors.TEXT).grid(row=3, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_family_count_var, foreground=colors.TEXT).grid(row=3, column=1, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_gi_father_son_var, foreground=colors.TEXT).grid(row=4, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_gi_father_daughter_var, foreground=colors.TEXT).grid(row=4, column=1, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_gi_mother_son_var, foreground=colors.TEXT).grid(row=5, column=0, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_gi_mother_daughter_var, foreground=colors.TEXT).grid(row=5, column=1, sticky="w")
    ttk.Label(pop_meta_grid, textvariable=pop_family_mean_size_var, foreground=colors.TEXT).grid(row=6, column=0, sticky="w")

    # -------------------------
    # Wykresy: każdy wykres = 1 zakładka
    # -------------------------
    pop_charts_frame = ttk.Frame(pop_frame)
    pop_charts_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(14, 0))

    pop_plots_nb = ttk.Notebook(pop_charts_frame)
    pop_plots_nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def _plot_tab(title: str) -> ttk.Frame:
        tab = ttk.Frame(pop_plots_nb, padding=10)
        pop_plots_nb.add(tab, text=title)
        return tab

    # Urodzenia (płeć)
    tab_birth_sex = _plot_tab("Urodzenia: płeć")
    ttk.Label(tab_birth_sex, text="Liczba osobników urodzonych w dekadach (płeć)", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_birth_sex,
        text="Interpretacja: słupki pokazują liczbę urodzeń w dekadzie (np. 1880–1889). M/F to płeć z bazy.",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_birth_sex_plot_area = ttk.Frame(tab_birth_sex)
    pop_birth_sex_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Urodzenia (linie)
    tab_birth_line = _plot_tab("Urodzenia: LB/LC")
    ttk.Label(tab_birth_line, text="Liczba osobników urodzonych w dekadach (LB vs LC)", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_birth_line,
        text="Interpretacja: słupki pokazują liczbę urodzeń w dekadzie podzielone wg linii `line` (LB/LC).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_birth_line_plot_area = ttk.Frame(tab_birth_line)
    pop_birth_line_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Female/Male ratio
    tab_birth_ratio = _plot_tab("Female/Male (1900+)")
    ttk.Label(tab_birth_ratio, text="Female/Male ratio urodzeń od 1900 roku", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_birth_ratio,
        text="Interpretacja: ratio = liczba samic (F) / liczba samców (M) w dekadzie. Jeśli M=0 dla dekady, punkt nie jest pokazywany.",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_birth_ratio_plot_area = ttk.Frame(tab_birth_ratio)
    pop_birth_ratio_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # GI (bar)
    tab_gi = _plot_tab("GI (średni)")
    ttk.Label(tab_gi, text="Odstęp międzypokoleniowy (GI) — średni wiek rodziców", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_gi,
        text="Interpretacja: GI = (rok urodzenia potomstwa) - (rok urodzenia rodzica). Liczymy średnio dla par: Ojciec→Syn, Ojciec→Córka, Matka→Syn, Matka→Córka (tylko gdy znane są obie daty).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_gi_plot_area = ttk.Frame(tab_gi)
    pop_gi_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # GI trend
    tab_gi_trend = _plot_tab("GI trend (dekady)")
    ttk.Label(tab_gi_trend, text="GI w czasie (trend) — dekady i 4 ścieżki", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_gi_trend,
        text="Interpretacja: wartości dla kolejnych dekad liczone jako średni GI w tej dekadzie (dla każdej ścieżki osobno).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_gi_trend_plot_area = ttk.Frame(tab_gi_trend)
    pop_gi_trend_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Rodziny pełne
    tab_family = _plot_tab("Rodziny pełne")
    ttk.Label(tab_family, text="Struktura rodzin pełnego rodzeństwa", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
    ttk.Label(
        tab_family,
        text="Interpretacja: rodzina pełnego rodzeństwa = osobniki z tym samym ojcem i tą samą matką (tylko gdy oboje rodzice są znani).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_family_plot_area = ttk.Frame(tab_family)
    pop_family_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Kompletność (płeć)
    tab_comp_sex = _plot_tab("Kompletność: płeć")
    ttk.Label(tab_comp_sex, text="Kompletność rodowodu: MG / CG / EG wg płci", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_comp_sex,
        text="Interpretacja: MG = maksymalna generacja; CG = liczba kompletnych pokoleń (PCL=1); EG = równoważne kompletne pokolenia.",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_comp_sex_plot_area = ttk.Frame(tab_comp_sex)
    pop_comp_sex_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Kompletność (linie)
    tab_comp_line = _plot_tab("Kompletność: LB/LC")
    ttk.Label(tab_comp_line, text="Kompletność rodowodu: MG / CG / EG wg linii LB / LC", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_comp_line,
        text="Interpretacja: jak wyżej, ale kategorie wynikają z kolumny `line` (LB/LC/NA).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_comp_line_plot_area = ttk.Frame(tab_comp_line)
    pop_comp_line_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Inbred TP (płeć)
    tab_inb_year_sex = _plot_tab("Inbred TP: płeć")
    ttk.Label(tab_inb_year_sex, text="Average F i RIA (%) w czasie — wg płci", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_inb_year_sex,
        text="Interpretacja: średnie F w roku urodzenia oraz RIA (%) = odsetek osobników z F>0 w tym roku (w TP).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_inb_year_sex_plot_area = ttk.Frame(tab_inb_year_sex)
    pop_inb_year_sex_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Inbred TP (linie)
    tab_inb_year_line = _plot_tab("Inbred TP: LB/LC")
    ttk.Label(tab_inb_year_line, text="Average F i RIA (%) w czasie — wg linii LB/LC", font=("TkDefaultFont", 12, "bold")).pack(
        anchor="w"
    )
    ttk.Label(
        tab_inb_year_line,
        text="Interpretacja: jak wyżej, ale kategorie wynikają z kolumny `line` (LB vs LC).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_inb_year_line_plot_area = ttk.Frame(tab_inb_year_line)
    pop_inb_year_line_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    # Founder contributions
    tab_founders = _plot_tab("Założyciele: p_i")
    ttk.Label(tab_founders, text="Wkład genetyczny założycieli (top p_i)", font=("TkDefaultFont", 12, "bold")).pack(anchor="w")
    ttk.Label(
        tab_founders,
        text="Interpretacja: p_i to znormalizowany udział genetyczny przodków (founder-like zgodnie z logiką founder-stop).",
        font=("TkDefaultFont", 8),
        foreground=colors.MUTED,
        wraplength=900,
        justify="left",
    ).pack(anchor="w", pady=(6, 0))
    pop_founders_plot_area = ttk.Frame(tab_founders)
    pop_founders_plot_area.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

    def _render_birth_decade_charts(df_use) -> None:
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
            m_counts = {}
            f_counts = {}
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
            lb_counts = {}
            lc_counts = {}
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
            canvas2 = FigureCanvasTkAgg(fig2, master=pop_birth_line_plot_area)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # --- Ratio F/M od 1900 (po dekadach) ---
            # Używamy tych samych rozkładów co dla wykresu płci.
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
                        out[cat] = (float(sum(MGs)) / float(len(MGs)), float(sum(CGs)) / float(len(CGs)), float(sum(EGs)) / float(len(EGs)))
                    return out

                sex_means = _group_means("sex_norm", ["M", "F"])
                line_means = _group_means("line_norm", ["LB", "LC", "NA"])

                def _clear_plot(area: ttk.Frame) -> None:
                    for w in area.winfo_children():
                        w.destroy()

                # --- wykres płci ---
                _clear_plot(pop_comp_sex_plot_area)
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
                canvas_c = FigureCanvasTkAgg(fig_c, master=pop_comp_sex_plot_area)
                canvas_c.draw()
                canvas_c.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                # --- wykres linii ---
                _clear_plot(pop_comp_line_plot_area)
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
                canvas_l = FigureCanvasTkAgg(fig_l, master=pop_comp_line_plot_area)
                canvas_l.draw()
                canvas_l.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception:
            return

    def _render_inbreeding_year_trends(df_use) -> None:
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
            # Domyślnie bierzemy to, co jest w polu „Max pokoleń” z sekcji F
            # w zakładce „Populacja”.
            try:
                depth = int(str(pop_depth_inb_var.get()).strip())
            except Exception:
                depth = 4
            if depth < 0:
                depth = 0
            depth = min(depth, 30)
            max_generations_back = None if bool(pop_unbounded_inb_var.get()) else depth

            # Liczymy F dla każdego ID (cache w pętli na czas tej funkcji).
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
            # Wygodna funkcja do przygotowania tablic z nan-ami.
            def _make_series(cond, value_field: str, eps: float | None = None) -> list[float]:
                arr: list[float] = []
                for y in years:
                    g = dfc[(dfc["birth_year_int"] == y) & cond]
                    if g.empty:
                        arr.append(float("nan"))
                        continue
                    vals = g[value_field].tolist()
                    if eps is not None:
                        arr.append(100.0 * float(sum(1 for v in vals if v > eps)) / float(len(vals)))
                    else:
                        arr.append(float(sum(vals)) / float(len(vals)))
                return arr

            eps_inbred = 1e-15  # F>0 (w sensie numerycznym)

            try:
                # Udział zinbredowanych (F>0) w TP — liczony na podstawie obliczonego _F.
                f_vals = dfc["_F"].tolist() if "_F" in dfc.columns else []
                if f_vals:
                    ria_overall = 100.0 * float(sum(1 for v in f_vals if v > eps_inbred)) / float(len(f_vals))
                    pop_ria_overall_var.set(f"- RIA ogółem (F>0): {ria_overall:.1f}%")
            except Exception:
                pass

            def _clear_plot_area(area: ttk.Frame) -> None:
                for w in area.winfo_children():
                    w.destroy()

            # --- Wykres wg płci ---
            _clear_plot_area(pop_inb_year_sex_plot_area)
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
                avgF = []
                ria = []
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

            # gęsty wykres -> pokazujemy co np. 5 lat
            if len(years) > 15:
                step = 5
                ticks = [y for i, y in enumerate(years) if i % step == 0]
                ax_avg.set_xticks(ticks)
                ax_ria.set_xticks(ticks)
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=pop_inb_year_sex_plot_area)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # --- Wykres wg linii ---
            _clear_plot_area(pop_inb_year_line_plot_area)
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
                avgF = []
                ria = []
                for y in years:
                    g = dfc[(dfc["birth_year_int"] == y) & mask_cat]
                    if g.empty:
                        avgF.append(float("nan"))
                        ria.append(float("nan"))
                        continue
                    vals = g["_F"].tolist()
                    avgF.append(float(sum(vals)) / float(len(vals)))
                    ria.append(100.0 * float(sum(1 for v in vals if v > eps_inbred)) / float(len(vals)))
                ax_avg2.plot(years, avgF, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=f"{cat}")
                ax_ria2.plot(years, ria, marker="o", markersize=2, linewidth=2, color=colors_line[cat], label=f"{cat}")

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
                ticks = [y for i, y in enumerate(years) if i % step == 0]
                ax_avg2.set_xticks(ticks)
                ax_ria2.set_xticks(ticks)
            fig2.tight_layout()

            canvas2 = FigureCanvasTkAgg(fig2, master=pop_inb_year_line_plot_area)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            # --- N_e (efektywna wielkość populacji) z trendu F ---
            # Szacujemy szybkość wzrostu średniego F na rok przez regresję liniową,
            # a następnie przeliczamy ją na przyrost na pokolenie mnożąc przez średnie GI.
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
                # Nie psujemy wykresów, jeśli regresja się nie uda.
                pass

        except Exception:
            return

    def _update_population_metrics(df_std) -> None:
        TEST_ID = "99999"
        if df_std is None or getattr(df_std, "empty", True):
            pop_total_var.set("-")
            pop_founders_count_var.set("-")
            pop_known_parents_var.set("-")
            pop_known_father_var.set("-")
            pop_known_mother_var.set("-")
            pop_lines_var.set("-")
            return

        try:
            df_use = df_std.copy()
            df_use["id"] = df_use["id"].astype(str)
            df_use = df_use[df_use["id"] != TEST_ID]
        except Exception:
            df_use = df_std

        total = int(len(df_use))
        if total == 0:
            pop_total_var.set("0 osób (po odfiltrowaniu test ID)")
            pop_founders_count_var.set("-")
            pop_known_parents_var.set("-")
            pop_known_father_var.set("-")
            pop_known_mother_var.set("-")
            pop_lines_var.set("-")
            return

        father_known = df_use["father_id"].notna()
        mother_known = df_use["mother_id"].notna()

        founders_mask = (~father_known) & (~mother_known)
        founders = int(founders_mask.sum())

        both_known = father_known & mother_known
        both_known_count = int(both_known.sum())
        at_least_one = int((father_known | mother_known).sum())

        def _pct(n: int) -> float:
            return round(100.0 * float(n) / float(total), 1)

        pop_total_var.set(f"- Liczba osobników: {total}")
        pop_founders_count_var.set(f"- Założyciele (brak ojca i matki): {founders} ({_pct(founders)}%)")
        pop_known_parents_var.set(
            f"- Znane oboje rodziców: {both_known_count} ({_pct(both_known_count)}%) • "
            f"- Znany przynajmniej jeden rodzic: {at_least_one} ({_pct(at_least_one)}%)"
        )
        pop_known_father_var.set(f"- Znany ojciec: {int(father_known.sum())} ({_pct(int(father_known.sum()))}%)")
        pop_known_mother_var.set(f"- Znana matka: {int(mother_known.sum())} ({_pct(int(mother_known.sum()))}%)")

        # Rozkład linii dla osobników (E w Excelu: line).
        if "line" in df_use.columns:
            line_vals = df_use["line"].astype(str).str.strip().str.upper().fillna("NA")
            lb = int((line_vals == "LB").sum())
            lc = int((line_vals == "LC").sum())
            c_other = int((~line_vals.isin(["LB", "LC"])).sum())
            pop_lines_var.set(f"- Linie: LB={lb} • LC={lc} • reszta={c_other}")
        else:
            pop_lines_var.set("- Linie: brak kolumny `line`")

        # --- Wkład założycieli / bottleneck (na podstawie p_i i founder-stop) ---
        pop_f_e_var.set("-")
        pop_f_a_var.set("-")
        pop_bottleneck_var.set("-")
        pop_ne_var.set("-")

        try:
            people_for_stats = state.get("people")
            if people_for_stats:
                depth_val: int = 4
                try:
                    depth_val = int(str(pop_depth_inb_var.get()).strip())
                except Exception:
                    depth_val = 4
                if depth_val < 0:
                    depth_val = 0
                depth_val = min(depth_val, 30)
                max_gen_back = None if bool(pop_unbounded_inb_var.get()) else depth_val

                stats_founders = compute_population_genetics_stats(
                    df_std=df_use,  # type: ignore[arg-type]
                    people=people_for_stats,  # type: ignore[arg-type]
                    max_generations_back=max_gen_back,
                    calc_f=False,
                    calc_completeness=False,
                    calc_founders=True,
                    calc_lines=False,
                )
                state["population_founder_contributions"] = stats_founders.founder_contributions
                f_e = float(stats_founders.founders.f_e)
                f_a = float(stats_founders.founders.f_a)
                pop_f_e_var.set(f"- f_e (efektywna liczba założycieli): {f_e:.4f}")
                pop_f_a_var.set(f"- f_a (efektywna liczba przodków): {f_a:.4f}")
                if f_a > 0:
                    pop_bottleneck_var.set(f"- Bottleneck f_e/f_a: {f_e / f_a:.3f}")
                # W aktualnej implementacji `f_a` jest policzone spójnie z founder-stop,
                # a brak osobnej wersji `f_ge` — przyjmujemy więc przybliżenie f_ge = f_e.
                pop_drift_var.set("- Dryf f_e/f_ge (f_ge=f_e, aproksymacja): 1.000")
        except Exception:
            # Jeśli założyciele policzyć się nie uda, reszta metryk może działać.
            pass

        # --- GI (Generation Interval) oraz struktura rodzin ---
        people = state.get("people")
        state["population_gi_mean"] = None
        pop_gi_mean_var.set("-")
        pop_gi_father_son_var.set("-")
        pop_gi_father_daughter_var.set("-")
        pop_gi_mother_son_var.set("-")
        pop_gi_mother_daughter_var.set("-")
        pop_family_count_var.set("-")
        pop_family_mean_size_var.set("-")

        def _norm_sex(v: object) -> str | None:
            if v is None:
                return None
            s = str(v).strip().upper()
            if s == "M":
                return "M"
            if s == "F":
                return "F"
            return None

        def _norm_id(v: object) -> str | None:
            if v is None:
                return None
            s = str(v).strip()
            if not s or s.lower() == "nan":
                return None
            return s

        def _parse_year(v: object) -> int | None:
            if v is None:
                return None
            try:
                if isinstance(v, float) and v != v:
                    return None
            except Exception:
                pass
            try:
                y = int(float(v))
            except Exception:
                return None
            return y

        father_son_ages: list[float] = []
        father_daughter_ages: list[float] = []
        mother_son_ages: list[float] = []
        mother_daughter_ages: list[float] = []

        gi_decades: dict[str, dict[int, list[float]]] = {
            "FS": {},
            "FD": {},
            "MS": {},
            "MD": {},
        }

        if people:
            try:
                for _, row in df_use.iterrows():
                    off_year = _parse_year(row.get("birth_year"))
                    if off_year is None:
                        continue
                    sex = _norm_sex(row.get("sex"))
                    if sex not in {"M", "F"}:
                        continue

                    fa_id = _norm_id(row.get("father_id"))
                    mo_id = _norm_id(row.get("mother_id"))
                    decade = (off_year // 10) * 10

                    if sex == "M":
                        # ojciec -> syn
                        if fa_id and fa_id in people and _parse_year(people[fa_id].birth_year) is not None:
                            parent_year = _parse_year(people[fa_id].birth_year)
                            if parent_year is None:
                                continue
                            age = float(off_year) - float(parent_year)
                            if 0 <= age <= 80:
                                father_son_ages.append(age)
                                gi_decades["FS"].setdefault(decade, []).append(age)
                        # matka -> syn
                        if mo_id and mo_id in people and _parse_year(people[mo_id].birth_year) is not None:
                            parent_year = _parse_year(people[mo_id].birth_year)
                            if parent_year is None:
                                continue
                            age = float(off_year) - float(parent_year)
                            if 0 <= age <= 80:
                                mother_son_ages.append(age)
                                gi_decades["MS"].setdefault(decade, []).append(age)
                    else:
                        # ojciec -> córka
                        if fa_id and fa_id in people and _parse_year(people[fa_id].birth_year) is not None:
                            parent_year = _parse_year(people[fa_id].birth_year)
                            if parent_year is None:
                                continue
                            age = float(off_year) - float(parent_year)
                            if 0 <= age <= 80:
                                father_daughter_ages.append(age)
                                gi_decades["FD"].setdefault(decade, []).append(age)
                        # matka -> córka
                        if mo_id and mo_id in people and _parse_year(people[mo_id].birth_year) is not None:
                            parent_year = _parse_year(people[mo_id].birth_year)
                            if parent_year is None:
                                continue
                            age = float(off_year) - float(parent_year)
                            if 0 <= age <= 80:
                                mother_daughter_ages.append(age)
                                gi_decades["MD"].setdefault(decade, []).append(age)
            except Exception:
                # Jeśli dane są niepełne, GI zostawiamy jako "-".
                pass

            def _mean_or_none(xs: list[float]) -> float | None:
                if not xs:
                    return None
                return float(sum(xs)) / float(len(xs))

            gi_fs = _mean_or_none(father_son_ages)
            gi_fd = _mean_or_none(father_daughter_ages)
            gi_ms = _mean_or_none(mother_son_ages)
            gi_md = _mean_or_none(mother_daughter_ages)
            all_gi = father_son_ages + father_daughter_ages + mother_son_ages + mother_daughter_ages
            gi_all = _mean_or_none(all_gi)

            if gi_all is not None:
                state["population_gi_mean"] = gi_all
                pop_gi_mean_var.set(f"- GI (Generation Interval, średnio): {gi_all:.2f} lat")
            if gi_fs is not None:
                pop_gi_father_son_var.set(f"- GI Ojciec→Syn: {gi_fs:.2f} lat")
            if gi_fd is not None:
                pop_gi_father_daughter_var.set(f"- GI Ojciec→Córka: {gi_fd:.2f} lat")
            if gi_ms is not None:
                pop_gi_mother_son_var.set(f"- GI Matka→Syn: {gi_ms:.2f} lat")
            if gi_md is not None:
                pop_gi_mother_daughter_var.set(f"- GI Matka→Córka: {gi_md:.2f} lat")

            # Struktura rodzin pełnego rodzeństwa.
            try:
                if "father_id" in df_use.columns and "mother_id" in df_use.columns:
                    df_fam = df_use[df_use["father_id"].notna() & df_use["mother_id"].notna()].copy()
                    if not df_fam.empty:
                        # Normalizacja do stringów, żeby grupowanie działało stabilnie.
                        df_fam["father_id"] = df_fam["father_id"].apply(_norm_id)
                        df_fam["mother_id"] = df_fam["mother_id"].apply(_norm_id)
                        df_fam = df_fam.dropna(subset=["father_id", "mother_id"])
                        fam_sizes = df_fam.groupby(["father_id", "mother_id"]).size()
                        if len(fam_sizes) > 0:
                            pop_family_count_var.set(f"- Liczba rodzin pełnego rodzeństwa: {int(fam_sizes.shape[0])}")
                            pop_family_mean_size_var.set(f"- Średnia wielkość rodziny: {float(fam_sizes.mean()):.2f}")
                            state["population_family_sizes"] = fam_sizes.tolist()
            except Exception:
                state["population_family_sizes"] = []

        # Aktualizacja wykresów po wczytaniu danych.
        try:
            _render_birth_decade_charts(df_use)
            _render_inbreeding_year_trends(df_use)

            # --- Founder contributions: top p_i (w zakładce "Inbred TP") ---
            try:
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                def _clear_frame(area: ttk.Frame) -> None:
                    for w in area.winfo_children():
                        w.destroy()

                _clear_frame(pop_founders_plot_area)

                contribs = state.get("population_founder_contributions") or {}
                founder_items = []
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
                canvas_fe = FigureCanvasTkAgg(fig_fe, master=pop_founders_plot_area)
                canvas_fe.draw()
                canvas_fe.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            except Exception:
                pass

            # --- GI wykres + rodziny (w ramach zakładki Urodzenia) ---
            try:
                if not people:
                    return
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                def _clear_frame(area: ttk.Frame) -> None:
                    for w in area.winfo_children():
                        w.destroy()

                # GI bar chart
                _clear_frame(pop_gi_plot_area)
                gi_vals = [
                    _mean_or_none(father_son_ages),
                    _mean_or_none(father_daughter_ages),
                    _mean_or_none(mother_son_ages),
                    _mean_or_none(mother_daughter_ages),
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
                canvas_gi = FigureCanvasTkAgg(fig_gi, master=pop_gi_plot_area)
                canvas_gi.draw()
                canvas_gi.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                # --- GI trend (w dekadach) ---
                _clear_frame(pop_gi_trend_plot_area)
                all_decades = sorted(
                    set()
                    .union(*[set(gi_decades[k].keys()) for k in gi_decades.keys()])
                )
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
                    x = list(range(len(all_decades)))

                    def _to_plot(arr: list[float | None]) -> list[float]:
                        return [float(v) if v is not None else float("nan") for v in arr]

                    ax_t.plot(x, _to_plot(gi_fs), marker="o", linewidth=2, color="#9ecbff", label="Ojciec→Syn")
                    ax_t.plot(x, _to_plot(gi_fd), marker="o", linewidth=2, color="#ffb4c1", label="Ojciec→Córka")
                    ax_t.plot(x, _to_plot(gi_ms), marker="o", linewidth=2, color="#2e8b57", label="Matka→Syn")
                    ax_t.plot(x, _to_plot(gi_md), marker="o", linewidth=2, color="#d64545", label="Matka→Córka")

                    ax_t.set_title("GI (trend) — Ojciec/Mak x płeć potomstwa (dekady)")
                    ax_t.set_xlabel("dekada urodzenia potomstwa")
                    ax_t.set_ylabel("średni GI (lata)")
                    ax_t.grid(True, alpha=0.25)
                    ax_t.legend(fontsize=8)

                    # zagęszczenie etykiet
                    if len(x) > 15:
                        step = 2
                    else:
                        step = 1
                    ticks = [i for i in x if i % step == 0]
                    ax_t.set_xticks(ticks)
                    ax_t.set_xticklabels(
                        [decade_labels[i] for i in ticks],
                        rotation=35,
                        ha="right",
                        fontsize=8,
                    )
                    fig_t.tight_layout()
                    canvas_t = FigureCanvasTkAgg(fig_t, master=pop_gi_trend_plot_area)
                    canvas_t.draw()
                    canvas_t.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                else:
                    fig_t = plt.Figure(figsize=(8.6, 3.4), dpi=100)
                    ax_t = fig_t.add_subplot(1, 1, 1)
                    ax_t.text(0.5, 0.5, "Brak danych GI w dekadach", ha="center", va="center")
                    ax_t.axis("off")
                    fig_t.tight_layout()
                    canvas_t = FigureCanvasTkAgg(fig_t, master=pop_gi_trend_plot_area)
                    canvas_t.draw()
                    canvas_t.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                # Family size histogram
                _clear_frame(pop_family_plot_area)
                fam_sizes = state.get("population_family_sizes") or []
                fig_f = plt.Figure(figsize=(8.6, 3.4), dpi=100)
                ax_f = fig_f.add_subplot(1, 1, 1)
                if fam_sizes:
                    # bucketowanie do czytelnych wartości
                    from collections import Counter

                    c = Counter(int(s) for s in fam_sizes)
                    max_show = 10
                    labels = []
                    counts = []
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
                canvas_f = FigureCanvasTkAgg(fig_f, master=pop_family_plot_area)
                canvas_f.draw()
                canvas_f.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            except Exception:
                pass
        except Exception:
            pass

    state["population_metrics"] = {}

    # -------------------------
    # Persons tab (unlimited preview)
    # -------------------------
    persons_controls = ttk.Frame(tab_persons)
    persons_controls.pack(side=tk.TOP, fill=tk.X)

    def _set_status(msg: str) -> None:
        status_var.set(msg)
        root.update_idletasks()

    def on_choose_file() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            df_std, _info = load_dataset_from_path(path)
            people = _build_people_map(df_std)
            _apply_dataset(df_std=df_std, people=people, source=f"Wczytano: {Path(path).name}")
        except Exception as e:
            messagebox.showerror("Błąd wczytywania", str(e))
            _set_status(f"Błąd wczytywania: {e}")

    def on_load_default() -> None:
        try:
            df_std, _info = load_default_bison_report()
            people = _build_people_map(df_std)
            _apply_dataset(df_std=df_std, people=people, source="Wczytano domyślną bazę")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wczytać domyślnej bazy: {e}")
            _set_status(f"Błąd: {e}")

    ttk.Button(persons_controls, text="Wybierz bazę", command=on_choose_file).pack(side=tk.LEFT, padx=(0, 10))
    ttk.Button(persons_controls, text="Wczytaj domyślną bazę", command=on_load_default).pack(side=tk.LEFT)

    dataset_range_var = tk.StringVar(value="")
    ttk.Label(persons_controls, textvariable=dataset_range_var, foreground=colors.MUTED).pack(side=tk.LEFT, padx=(16, 0))

    persons_tree_frame = ttk.Frame(tab_persons)
    persons_tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(14, 0))

    tree_columns = (
        "id",
        "name",
        "sex",
        "birth_year",
        "father_id",
        "mother_id",
        "SireFounder",
        "SireSteps",
        "DamFounder",
        "DamSteps",
        "line",
        "father_line",
        "mother_line",
    )
    tree = ttk.Treeview(persons_tree_frame, columns=tree_columns, show="headings", height=18)
    tree_sort_state: dict[str, bool] = {"id": True}  # True = A->Z (ascending)

    def _update_heading(col: str) -> None:
        asc = tree_sort_state.get(col, True)
        arrow = "▲" if asc else "▼"
        if col == "id":
            base = "id (A->Z)"
        else:
            base = col
        # command utrzymujemy przez ponowne ustawienie, żeby nie gubić sortowania.
        tree.heading(col, text=f"{base} {arrow}", command=lambda c=col: on_sort_click(c))

    def _sort_value_key(col: str, val: object) -> tuple[int, object]:
        # key: (is_missing, coerced_value)
        if val is None:
            return (1, "")
        s = str(val).strip()
        if s == "":
            return (1, "")

        if col == "id":
            # _id_sort_key jest zdefiniowane niżej w kodzie; w praktyce callback wywołuje się dopiero później.
            try:
                return (0, _id_sort_key(s))
            except Exception:
                return (0, s)

        # Spróbuj traktować jako liczbę dla pól typu steps / birth_year.
        if col in {"birth_year", "SireSteps", "DamSteps"}:
            try:
                return (0, float(s))
            except Exception:
                return (0, s.lower())

        # Domyślnie: leksykograficznie (A->Z).
        return (0, s.lower())

    def _sort_tree_by(col: str) -> None:
        # Toggle kierunku.
        prev_asc = tree_sort_state.get(col, True)
        next_asc = not prev_asc
        tree_sort_state[col] = next_asc

        items = list(tree.get_children())
        items_with_keys = []
        for item in items:
            val = tree.set(item, col)
            key = _sort_value_key(col, val)
            items_with_keys.append((key, item))

        # Ascending sort uses reverse=False, descending uses reverse=True.
        reverse = not next_asc
        items_with_keys.sort(key=lambda t: t[0], reverse=reverse)

        for _, item in items_with_keys:
            tree.move(item, "", "end")

        _update_heading(col)

    def on_sort_click(col: str) -> None:
        if not tree.get_children():
            return
        _sort_tree_by(col)

    for col in tree_columns:
        _update_heading(col)
        tree.column(col, width=120, anchor="w")
    vsb = ttk.Scrollbar(persons_tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    # -------------------------
    # Rodowód tab controls
    # -------------------------
    rod_header = ttk.Frame(tab_pedigree)
    rod_header.pack(side=tk.TOP, fill=tk.X)
    ttk.Label(rod_header, text="ID (Number):").grid(row=0, column=0, sticky="w")
    id_anc_var = tk.StringVar(value="")
    id_anc_entry = ttk.Entry(rod_header, textvariable=id_anc_var, width=24, state="disabled")
    id_anc_entry.grid(row=0, column=1, sticky="w", padx=(8, 16))

    ttk.Label(rod_header, text="Max pokoleń:").grid(row=0, column=2, sticky="w")
    depth_anc_var = tk.StringVar(value="4")
    depth_anc_entry = ttk.Entry(rod_header, textvariable=depth_anc_var, width=10, state="disabled")
    depth_anc_entry.grid(row=0, column=3, sticky="w", padx=(8, 16))

    readable_anc_var = tk.BooleanVar(value=True)
    readable_anc_cb = ttk.Checkbutton(
        rod_header,
        text="Tryb czytelny (mniej etykiet)",
        variable=readable_anc_var,
        state="disabled",
    )
    readable_anc_cb.grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))

    anc_btn = ttk.Button(rod_header, text="Generuj przodków", state="disabled")
    anc_btn.grid(row=0, column=4, sticky="w", padx=(14, 0))

    rod_canvas_container = ttk.Frame(tab_pedigree)
    rod_canvas_container.pack(fill=tk.BOTH, expand=True, pady=(14, 0))
    rod_title_var = tk.StringVar(value="Wykres przodków")
    ttk.Label(rod_canvas_container, textvariable=rod_title_var, foreground=colors.MUTED).pack(anchor="w")
    rod_line_var = tk.StringVar(value="")
    ttk.Label(
        rod_canvas_container,
        textvariable=rod_line_var,
        foreground=colors.MUTED,
        justify="left",
        wraplength=1100,
    ).pack(anchor="w", pady=(4, 0))
    rod_plot_frame = ttk.Frame(rod_canvas_container)
    rod_plot_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    # -------------------------
    # Analyses tab (inbreeding)
    # -------------------------
    analyses_nb = ttk.Notebook(tab_analysis)
    analyses_nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    tab_inb = ttk.Frame(analyses_nb, padding=10)
    tab_pop = ttk.Frame(analyses_nb, padding=10)
    analyses_nb.add(tab_inb, text="Inbred (F)")
    # Ogólne parametry populacyjne pokazujemy w zakładce "Populacja" (nie w "Analizy").

    ana_header = ttk.Frame(tab_inb)
    ana_header.pack(side=tk.TOP, fill=tk.X)

    ttk.Label(ana_header, text="ID (Number):").grid(row=0, column=0, sticky="w")
    id_inb_var = tk.StringVar(value="")
    id_inb_entry = ttk.Entry(ana_header, textvariable=id_inb_var, width=24, state="disabled")
    id_inb_entry.grid(row=0, column=1, sticky="w", padx=(8, 16))

    ttk.Label(ana_header, text="Max pokoleń:").grid(row=0, column=2, sticky="w")
    depth_inb_var = tk.StringVar(value="4")
    depth_inb_entry = ttk.Entry(ana_header, textvariable=depth_inb_var, width=10, state="disabled")
    depth_inb_entry.grid(row=0, column=3, sticky="w", padx=(8, 16))

    unbounded_inb_var = tk.BooleanVar(value=True)
    unbounded_inb_cb = ttk.Checkbutton(
        ana_header,
        text="Bez ograniczenia (do founderów)",
        variable=unbounded_inb_var,
        state="disabled",
    )
    unbounded_inb_cb.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

    inb_btn = ttk.Button(ana_header, text="Policz F (Wright)", state="disabled")
    inb_btn.grid(row=0, column=4, sticky="w", padx=(14, 0))

    inb_result_var = tk.StringVar(value="F = -")
    ttk.Label(tab_inb, textvariable=inb_result_var, font=("TkDefaultFont", 16, "bold")).pack(anchor="w", pady=(14, 0))
    inb_note_var = tk.StringVar(value="")
    ttk.Label(tab_inb, textvariable=inb_note_var, foreground=colors.MUTED, wraplength=900, justify="left").pack(anchor="w", pady=(6, 0))
    inb_plot_frame = ttk.Frame(tab_inb)
    inb_plot_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

    # -------------------------
    # Population genetics: wybór metryk
    # -------------------------
    pop_f_var = tk.BooleanVar(value=False)
    pop_comp_var = tk.BooleanVar(value=False)
    pop_founders_opt_var = tk.BooleanVar(value=False)
    pop_lines_opt_var = tk.BooleanVar(value=False)

    pop_f_cb = ttk.Checkbutton(
        tab_pop,
        text="F (Wright): histogram + boxplot",
        variable=pop_f_var,
        state="disabled",
    )
    pop_f_cb.pack(anchor="w", pady=(10, 0))

    pop_comp_cb = ttk.Checkbutton(
        tab_pop,
        text="Kompletność rodowodu: EG + PCI",
        variable=pop_comp_var,
        state="disabled",
    )
    pop_comp_cb.pack(anchor="w", pady=(4, 0))

    pop_founders_cb = ttk.Checkbutton(
        tab_pop,
        text="Założyciele: f_e i top p_i",
        variable=pop_founders_opt_var,
        state="disabled",
    )
    pop_founders_cb.pack(anchor="w", pady=(4, 0))

    pop_lines_cb = ttk.Checkbutton(
        tab_pop,
        text="Linie: rozkład LB/LC/NA",
        variable=pop_lines_opt_var,
        state="disabled",
    )
    pop_lines_cb.pack(anchor="w", pady=(4, 0))

    pop_calc_btn = ttk.Button(
        tab_pop,
        text="Policz wybrane statystyki",
        state="disabled",
    )
    pop_calc_btn.pack(anchor="w", pady=(6, 0))

    pop_text = tk.Text(tab_pop, height=10, wrap="word")
    pop_text.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    pop_text.configure(state="disabled", bg=colors.ENTRY_BG, fg=colors.TEXT, insertbackground=colors.TEXT)

    # Obszar na wykresy statystyk populacyjnych (poukrywane na zakładkach).
    pop_plots_frame = ttk.Frame(tab_pop)
    pop_plots_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
    pop_plots_frame.pack_forget()

    pop_plots_nb = ttk.Notebook(pop_plots_frame)
    pop_plots_nb.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    pop_tab_f = ttk.Frame(pop_plots_nb, padding=10)
    pop_tab_comp = ttk.Frame(pop_plots_nb, padding=10)
    pop_tab_founders = ttk.Frame(pop_plots_nb, padding=10)
    pop_tab_lines = ttk.Frame(pop_plots_nb, padding=10)

    pop_plots_nb.add(pop_tab_f, text="F (Wright)")
    pop_plots_nb.add(pop_tab_comp, text="Kompletność")
    pop_plots_nb.add(pop_tab_founders, text="Założyciele")
    pop_plots_nb.add(pop_tab_lines, text="Linie (LB/LC)")

    def _sync_pop_all_btn() -> None:
        # Przycisk dostępny tylko, gdy włączono przynajmniej jedną metrykę.
        any_sel = bool(
            pop_f_var.get() or pop_comp_var.get() or pop_founders_opt_var.get() or pop_lines_opt_var.get()
        )
        if any_sel and str(pop_f_cb.cget("state")) == "normal":
            pop_calc_btn.configure(state="normal")
        else:
            pop_calc_btn.configure(state="disabled")

    pop_f_var.trace_add("write", lambda *_args: _sync_pop_all_btn())
    pop_comp_var.trace_add("write", lambda *_args: _sync_pop_all_btn())
    pop_founders_opt_var.trace_add("write", lambda *_args: _sync_pop_all_btn())
    pop_lines_opt_var.trace_add("write", lambda *_args: _sync_pop_all_btn())

    def set_controls_enabled(enabled: bool) -> None:
        st = "normal" if enabled else "disabled"
        id_anc_entry.configure(state=st)
        depth_anc_entry.configure(state=st)
        readable_anc_cb.configure(state=st)
        anc_btn.configure(state=st)

        id_inb_entry.configure(state=st)
        depth_inb_entry.configure(state=st)
        unbounded_inb_cb.configure(state=st)
        inb_btn.configure(state=st)
        pop_f_cb.configure(state=st)
        pop_comp_cb.configure(state=st)
        pop_founders_cb.configure(state=st)
        pop_lines_cb.configure(state=st)
        _sync_pop_all_btn()

    def on_calc_population_all() -> None:
        people = state.get("people")
        df_std = state.get("df_std")
        if not people or df_std is None:
            messagebox.showinfo("Info", "Najpierw wczytaj bazę.")
            return
        calc_f = bool(pop_f_var.get())
        calc_comp = bool(pop_comp_var.get())
        calc_founders = bool(pop_founders_opt_var.get())
        calc_lines = bool(pop_lines_opt_var.get())

        if not (calc_f or calc_comp or calc_founders or calc_lines):
            messagebox.showinfo("Info", "Wybierz przynajmniej jedną metrykę.")
            return

        pop_calc_btn.configure(state="disabled")
        try:
            pop_text.configure(state="normal")
            pop_text.delete("1.0", tk.END)
            pop_text.insert("1.0", "Liczenie… (może potrwać chwilę)\n")
            pop_text.configure(state="disabled")
            root.update_idletasks()

            if calc_f:
                if bool(unbounded_inb_var.get()):
                    max_generations_back = None
                else:
                    try:
                        depth = int(str(depth_inb_var.get()).strip())
                    except Exception:
                        messagebox.showerror("Błąd", "Max pokoleń musi być liczbą całkowitą.")
                        return
                    if depth < 0:
                        messagebox.showerror("Błąd", "Max pokoleń nie może być ujemne.")
                        return
                    depth = min(depth, 30)
                    max_generations_back = depth
            else:
                max_generations_back = 0

            stats = compute_population_genetics_stats(
                df_std=df_std,  # type: ignore[arg-type]
                people=people,  # type: ignore[arg-type]
                max_generations_back=max_generations_back,
                calc_f=calc_f,
                calc_completeness=calc_comp,
                calc_founders=calc_founders,
                calc_lines=calc_lines,
            )

            line_counts = stats.line_counts
            pop_text.configure(state="normal")
            pop_text.delete("1.0", tk.END)
            lines_out = [
                f"Populacja (bez test ID {TEST_ID}): n={stats.n}",
                f"Założyciele (brak ojca LUB matki): {stats.n_founders_any_missing_parent}",
                "",
            ]
            if calc_f:
                lines_out += [
                    "Inbred (Wright F) – podsumowanie:",
                    f"- mean F: {stats.inbreeding.mean_F:.6f}",
                    f"- median F: {stats.inbreeding.median_F:.6f}",
                    f"- min F: {stats.inbreeding.min_F:.6f}",
                    f"- max F: {stats.inbreeding.max_F:.6f}",
                    f"- liczba F=0: {stats.inbreeding.zeros}/{stats.inbreeding.n}",
                    "",
                ]
            if calc_comp:
                lines_out += [
                    "Kompletność rodowodu:",
                    f"- mean EG: {stats.completeness.mean_EG:.4f}",
                    f"- mean PCI: {stats.completeness.mean_PCI:.4f}",
                    "",
                ]
            if calc_founders:
                lines_out += [
                    "Wkład założycieli:",
                    f"- f_e: {stats.founders.f_e:.4f}",
                    f"- f_a: {stats.founders.f_a:.4f}",
                    "",
                ]
            if calc_lines:
                lines_out += [
                    "Rozkład linii (kolumna line):",
                    f"- LB: {line_counts.get('LB', 0)}",
                    f"- LC: {line_counts.get('LC', 0)}",
                    f"- NA: {line_counts.get('NA', 0)}",
                    "",
                ]

            pop_text.insert("1.0", "\n".join(lines_out))
            pop_text.configure(state="disabled")
            # --- Wykresy (opcjonalne, ale przydatne) ---
            try:
                import matplotlib.pyplot as plt
                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                def _clear_tab(tab: ttk.Frame) -> None:
                    for w in tab.winfo_children():
                        w.destroy()

                # F histogram + boxplot
                _clear_tab(pop_tab_f)
                fig_f = plt.Figure(figsize=(8.2, 4.8), dpi=100)
                ax_hist = fig_f.add_subplot(1, 2, 1)
                ax_box = fig_f.add_subplot(1, 2, 2)
                ax_hist.hist(stats.f_values, bins=40, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
                ax_hist.set_title("Histogram F")
                ax_hist.set_xlabel("F")
                ax_hist.set_ylabel("liczba osobników")
                if stats.f_values:
                    ax_box.boxplot(stats.f_values, vert=True, patch_artist=True)
                    ax_box.set_title("Boxplot F")
                    ax_box.set_ylabel("F")
                else:
                    ax_box.text(0.5, 0.5, "Brak danych", ha="center", va="center")
                    ax_box.axis("off")
                fig_f.tight_layout()
                canvas_f = FigureCanvasTkAgg(fig_f, master=pop_tab_f)
                canvas_f.draw()
                canvas_f.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                ttk.Label(
                    pop_tab_f,
                    text="Wykres F (Wright) dla całej populacji: pokazuje rozkład inbredu wywołanego wspólnymi przodkami.",
                    font=("TkDefaultFont", 8),
                    foreground=colors.MUTED,
                    wraplength=900,
                    justify="left",
                ).pack(anchor="w", pady=(6, 0))

                # Kompletność: EG i PCI
                _clear_tab(pop_tab_comp)
                fig_c = plt.Figure(figsize=(8.2, 4.8), dpi=100)
                ax_eg = fig_c.add_subplot(1, 2, 1)
                ax_pci = fig_c.add_subplot(1, 2, 2)
                ax_eg.hist(stats.eg_values, bins=40, color=colors.BUTTON_BG, edgecolor=colors.ACCENT)
                ax_eg.set_title("Rozkład EG")
                ax_eg.set_xlabel("EG")
                ax_eg.set_ylabel("liczba osobników")
                ax_pci.hist(stats.pci_values, bins=40, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
                ax_pci.set_title("Rozkład PCI")
                ax_pci.set_xlabel("PCI")
                ax_pci.set_ylabel("liczba osobników")
                fig_c.tight_layout()
                canvas_c = FigureCanvasTkAgg(fig_c, master=pop_tab_comp)
                canvas_c.draw()
                canvas_c.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                ttk.Label(
                    pop_tab_comp,
                    text="Kompletność rodowodu: EG to suma wkładów przodków (1/2)^pokolenie, a PCI jest uśrednioną jakością kompletności po pokoleniach.",
                    font=("TkDefaultFont", 8),
                    foreground=colors.MUTED,
                    wraplength=900,
                    justify="left",
                ).pack(anchor="w", pady=(6, 0))

                # Założyciele: top wkładów (p_i)
                _clear_tab(pop_tab_founders)
                fig_fe = plt.Figure(figsize=(8.2, 4.8), dpi=100)
                ax_fe = fig_fe.add_subplot(1, 1, 1)
                founder_items = sorted(stats.founder_contributions.items(), key=lambda kv: kv[1], reverse=True)
                top_k = min(10, len(founder_items))
                top_items = founder_items[:top_k]
                if top_items:
                    ids = [fid for fid, _ in top_items]
                    vals = [v for _, v in top_items]
                    ax_fe.bar(range(len(top_items)), vals, color=colors.BUTTON_BG2, edgecolor=colors.ACCENT)
                    ax_fe.set_title(f"Top {top_k} założycieli (p_i)")
                    ax_fe.set_xlabel("założyciel (ID + imię)")
                    ax_fe.set_ylabel("p_i (udział)")
                    ax_fe.set_xticks(range(len(top_items)))
                    labels: list[str] = []
                    for fid in ids:
                        p = people.get(str(fid))  # type: ignore[name-defined]
                        nm = p.name if p and p.name else None
                        if nm:
                            labels.append(f"{fid} ({nm})")
                        else:
                            labels.append(str(fid))
                    ax_fe.set_xticklabels(labels, rotation=60, ha="right", fontsize=8)
                else:
                    ax_fe.text(0.5, 0.5, "Brak danych o założycielach", ha="center", va="center")
                    ax_fe.axis("off")
                fig_fe.tight_layout()
                canvas_fe = FigureCanvasTkAgg(fig_fe, master=pop_tab_founders)
                canvas_fe.draw()
                canvas_fe.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                ttk.Label(
                    pop_tab_founders,
                    text="Wkład założycieli (p_i) wyliczony z founder-stop: pokazuje, którzy przodkowie odpowiadają za największą część różnorodności genetycznej.",
                    font=("TkDefaultFont", 8),
                    foreground=colors.MUTED,
                    wraplength=900,
                    justify="left",
                ).pack(anchor="w", pady=(6, 0))

                # Linie: LB/LC/NA
                _clear_tab(pop_tab_lines)
                fig_l = plt.Figure(figsize=(8.2, 4.8), dpi=100)
                ax_l = fig_l.add_subplot(1, 1, 1)
                lb = line_counts.get("LB", 0)
                lc = line_counts.get("LC", 0)
                na = line_counts.get("NA", 0)
                xs = ["LB", "LC", "NA"]
                ys = [lb, lc, na]
                ax_l.bar(xs, ys, color=[colors.BUTTON_BG2, colors.BUTTON_BG, "#d6d0c4"], edgecolor=colors.ACCENT)
                ax_l.set_title("Rozkład linii (kolumna line)")
                ax_l.set_xlabel("linia")
                ax_l.set_ylabel("liczba osobników")
                fig_l.tight_layout()
                canvas_l = FigureCanvasTkAgg(fig_l, master=pop_tab_lines)
                canvas_l.draw()
                canvas_l.get_tk_widget().pack(fill=tk.BOTH, expand=True)
                ttk.Label(
                    pop_tab_lines,
                    text="Rozkład przynależności do linii (LB/LC) dla ocenianej populacji. Kolumna `line` pochodzi z pliku Excela.",
                    font=("TkDefaultFont", 8),
                    foreground=colors.MUTED,
                    wraplength=900,
                    justify="left",
                ).pack(anchor="w", pady=(6, 0))

                pop_plots_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
            except Exception as e:
                messagebox.showwarning("Wykresy", f"Nie udało się narysować wykresów: {e}")
            _set_status("Gotowe: policzono statystyki populacyjne.")
        finally:
            _sync_pop_all_btn()

    pop_calc_btn.configure(command=on_calc_population_all)

    # Double-click w Osobniki ustawia ID do rodowodu i analiz
    def on_tree_double_click(_event: tk.Event) -> None:
        selection = tree.selection()
        if not selection:
            return
        values = tree.item(selection[0], "values")
        if not values:
            return
        picked_id = str(values[0])
        id_anc_var.set(picked_id)
        id_inb_var.set(picked_id)

    tree.bind("<Double-1>", on_tree_double_click)

    # -------------------------
    # Dataset apply
    # -------------------------
    def _id_sort_key(s: str) -> tuple[int, str]:
        import re

        m = re.match(r"^(\d+)([A-Za-z]*)$", s)
        if not m:
            return (10**30, s)
        return (int(m.group(1)), m.group(2) or "")

    def _apply_dataset(df_std, people, source: str) -> None:
        state["df_std"] = df_std
        state["people"] = people
        # Precompute line memberships for quick display in "Osobniki" and "Rodowód".
        ids = [str(x) for x in df_std["id"].tolist()]
        try:
            state["line_memberships"] = compute_all_line_memberships(people, person_ids=ids)
        except Exception:
            state["line_memberships"] = {}

        ids = df_std["id"].dropna().astype(str)
        if len(ids) > 0:
            min_id = min(ids.tolist(), key=_id_sort_key)
            max_id = max(ids.tolist(), key=_id_sort_key)
            dataset_range_var.set(f"Zakres ID (Number): min {min_id} / max {max_id}")
        else:
            dataset_range_var.set("Zakres ID: brak")

        _set_status(source + f" • {len(df_std)} wierszy")

        # Wczytujemy CAŁĄ bazę (bez limitu podglądu).
        for item in tree.get_children():
            tree.delete(item)
        # Insert all rows in A->Z order by ID.
        try:
            df_std_sorted = df_std.sort_values(
                by="id",
                key=lambda s: s.astype(str).map(_id_sort_key),
            ).reset_index(drop=True)
        except Exception:
            df_std_sorted = df_std

        for _, row in df_std_sorted.iterrows():
            pid = str(row.get("id"))
            lm = state.get("line_memberships", {}).get(pid, None)

            def _cell(v: object) -> str:
                if v is None:
                    return ""
                # NaN check (bez numpy).
                if isinstance(v, float) and v != v:
                    return ""
                return str(v)

            sire_founder = ""
            sire_steps = ""
            dam_founder = ""
            dam_steps = ""
            if lm is not None:
                sire_founder = _cell(lm.sire_founder_id) + (f" ({_cell(lm.sire_founder_name)})" if lm.sire_founder_name else "")
                sire_steps = _cell(lm.sire_steps)
                dam_founder = _cell(lm.dam_founder_id) + (f" ({_cell(lm.dam_founder_name)})" if lm.dam_founder_name else "")
                dam_steps = _cell(lm.dam_steps)

            def _norm_line(line_val: object) -> str:
                if line_val is None:
                    return "NA"
                if isinstance(line_val, float) and line_val != line_val:
                    return "NA"
                s = str(line_val).strip().upper()
                if s in {"LB", "LC"}:
                    return s
                return "NA"

            line = _norm_line(row.get("line"))

            # Rodzice mogą być poza bazą jako rekordy - wtedy "NA".
            # Wartości pochodzą bezpośrednio z kolumn Excela (E/J/M):
            father_line = _norm_line(row.get("father_line"))
            mother_line = _norm_line(row.get("mother_line"))

            tree.insert(
                "",
                "end",
                values=(
                    _cell(row.get("id")),
                    _cell(row.get("name")),
                    _cell(row.get("sex")),
                    _cell(row.get("birth_year")),
                    _cell(row.get("father_id")),
                    _cell(row.get("mother_id")),
                    sire_founder,
                    sire_steps,
                    dam_founder,
                    dam_steps,
                    line,
                    father_line,
                    mother_line,
                ),
            )

        # Default IDs: first person with at least one parent.
        if not df_std.empty:
            with_parents = df_std[df_std["father_id"].notna() | df_std["mother_id"].notna()]
            first_row = with_parents.iloc[0] if not with_parents.empty else df_std.iloc[0]
            picked = str(first_row["id"])
            id_anc_var.set(picked)
            id_inb_var.set(picked)

        _update_population_metrics(df_std)
        set_controls_enabled(True)

    # -------------------------
    # Rodowód generate
    # -------------------------
    def on_generate_pedigree() -> None:
        people = state.get("people")
        if not people:
            messagebox.showinfo("Info", "Najpierw wczytaj bazę.")
            return

        person_id = str(id_anc_var.get()).strip()
        if not person_id:
            messagebox.showerror("Błąd", "Podaj ID (Number).")
            return
        if person_id not in people:
            messagebox.showerror("Błąd", "Nie ma takiego ID w wczytanych danych.")
            return

        try:
            depth = int(str(depth_anc_var.get()).strip())
        except Exception:
            messagebox.showerror("Błąd", "Max pokoleń musi być liczbą całkowitą.")
            return
        if depth < 0:
            messagebox.showerror("Błąd", "Max pokoleń nie może być ujemne.")
            return
        depth = min(depth, 30)

        levels, edges = get_ancestor_levels_and_edges(person_id=person_id, depth=depth, people=people)
        if not levels:
            messagebox.showerror("Błąd", "Nie znaleziono przodków w podanym limicie.")
            return

        people_all = ensure_people_for_nodes(levels=levels, people=people)
        fig = plot_ancestor_pedigree(
            person_id=person_id,
            levels=levels,
            edges=edges,
            people=people_all,
            readable_mode=bool(readable_anc_var.get()),
        )
        rod_title_var.set(f"Przodkowie: {person_id}")
        lm_map = state.get("line_memberships", {}) or {}

        def _pid_to_line(pid: object) -> str:
            if pid is None:
                return "NA"
            pid_s = str(pid)
            p = people.get(pid_s)
            line_val = getattr(p, "line", None) if p else None
            if not line_val:
                return "NA"
            s = str(line_val).strip().upper()
            if s in {"LB", "LC"}:
                return s
            return "NA"

        def _norm_line_val(v: object) -> str:
            if v is None:
                return "NA"
            if isinstance(v, float) and v != v:
                return "NA"
            s = str(v).strip().upper()
            if s in {"LB", "LC"}:
                return s
            return "NA"

        # Linie dla ocenianego osobnika i jego rodziców bierzemy z kolumn Excela:
        # - osobnik: `line` (E)
        # - ojciec: `father_line` (J)
        # - matka: `mother_line` (M)
        df_std = state.get("df_std")
        df_row = None
        try:
            if df_std is not None and not df_std.empty:
                matches = df_std[df_std["id"] == person_id]
                if not matches.empty:
                    df_row = matches.iloc[0]
        except Exception:
            df_row = None

        own_line = _norm_line_val(df_row.get("line") if df_row is not None else None)
        father_line = _norm_line_val(df_row.get("father_line") if df_row is not None else None)
        mother_line = _norm_line_val(df_row.get("mother_line") if df_row is not None else None)

        # Fallback, jeśli dla jakiegoś powodu nie uda się znaleźć wiersza w df_std.
        if own_line == "NA":
            own_line = _pid_to_line(person_id)
        tmp_father_id = people.get(person_id).father_id if people.get(person_id) else None
        if father_line == "NA" and tmp_father_id:
            father_line = _pid_to_line(tmp_father_id)
        tmp_mother_id = people.get(person_id).mother_id if people.get(person_id) else None
        if mother_line == "NA" and tmp_mother_id:
            mother_line = _pid_to_line(tmp_mother_id)

        def _fmt_pid(pid: object) -> str:
            if not pid:
                return "brak danych"
            pid_s = str(pid)
            mem = lm_map.get(pid_s)
            if mem is None:
                # Brak rekordu osoby w bazie (założyciel/nieznany rodzic).
                return (
                    f"Sireline: {pid_s} (NA) [steps=0]\n"
                    f"Damline: {pid_s} (NA) [steps=0]"
                )
            return (
                f"Sireline: {mem.sire_founder_id} ({mem.sire_founder_name or 'NA'}) [steps={mem.sire_steps}]\n"
                f"Damline: {mem.dam_founder_id} ({mem.dam_founder_name or 'NA'}) [steps={mem.dam_steps}]"
            )

        father_id = people.get(person_id).father_id if people.get(person_id) else None
        mother_id = people.get(person_id).mother_id if people.get(person_id) else None

        rod_line_var.set(
            "Linie (sire/dam):\n"
            f"- Oceniany ({person_id}) | line={own_line}:\n{_fmt_pid(person_id)}\n\n"
            f"- Ojciec ({father_id or 'NA'}) | line={father_line}:\n{_fmt_pid(father_id)}\n\n"
            f"- Matka ({mother_id or 'NA'}) | line={mother_line}:\n{_fmt_pid(mother_id)}"
        )

        _clear_frame(rod_plot_frame)
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie mogę osadzić wykresu: {e}")
            return

        canvas = FigureCanvasTkAgg(fig, master=rod_plot_frame)
        canvas.draw()
        try:
            toolbar = NavigationToolbar2Tk(canvas, rod_plot_frame)  # type: ignore[arg-type]
            toolbar.update()
            toolbar.pack(side=tk.TOP, fill=tk.X)
        except Exception:
            pass
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    anc_btn.configure(command=on_generate_pedigree)

    # -------------------------
    # Analyses: inbred
    # -------------------------
    def on_calc_inbreeding() -> None:
        people = state.get("people")
        if not people:
            messagebox.showinfo("Info", "Najpierw wczytaj bazę.")
            return

        person_id = str(id_inb_var.get()).strip()
        if not person_id:
            messagebox.showerror("Błąd", "Podaj ID (Number).")
            return
        if person_id not in people:
            messagebox.showerror("Błąd", "Nie ma takiego ID w wczytanych danych.")
            return

        if bool(unbounded_inb_var.get()):
            f_res = wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=None)
        else:
            try:
                depth = int(str(depth_inb_var.get()).strip())
            except Exception:
                messagebox.showerror("Błąd", "Max pokoleń musi być liczbą całkowitą.")
                return
            if depth < 0:
                messagebox.showerror("Błąd", "Max pokoleń nie może być ujemne.")
                return
            depth = min(depth, 30)
            f_res = wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=depth)

        inb_result_var.set(f"F = {f_res.F:.6f}")

        # --- Kompletność rodowodu (MG/EG/PCI) dla wskazanego osobnika (ANC, bez limitu) ---
        MG = 0
        EG = 0.0
        PCI = 0.0
        try:
            levels = get_ancestor_levels_unbounded(person_id=person_id, people=people)
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
                MG = int(max(by_gen.keys()))
                pci_sum = 0.0
                for g in range(1, MG + 1):
                    a_g = int(by_gen.get(g, 0))
                    pcl_g = float(a_g) / float(2**g)
                    EG += pcl_g
                    pci_sum += pcl_g
                PCI = pci_sum / float(MG) if MG > 0 else 0.0
        except Exception:
            pass

        # Linia (sire/dam) dla ocenianego osobnika i jego rodziców.
        subj = get_line_membership(person_id, people)

        father_id = f_res.father_id
        mother_id = f_res.mother_id
        father_mem = get_line_membership(father_id, people) if father_id else None
        mother_mem = get_line_membership(mother_id, people) if mother_id else None

        def _pid_to_line(pid: object) -> str:
            if pid is None:
                return "NA"
            pid_s = str(pid)
            p = people.get(pid_s)
            line_val = getattr(p, "line", None) if p else None
            if not line_val:
                return "NA"
            s = str(line_val).strip().upper()
            if s in {"LB", "LC"}:
                return s
            return "NA"

        def _norm_line_val(v: object) -> str:
            if v is None:
                return "NA"
            if isinstance(v, float) and v != v:
                return "NA"
            s = str(v).strip().upper()
            if s in {"LB", "LC"}:
                return s
            return "NA"

        # Linie z kolumn Excela (E/J/M) dla wiersza ocenianego osobnika.
        df_std = state.get("df_std")
        df_row = None
        try:
            if df_std is not None and not df_std.empty:
                matches = df_std[df_std["id"] == person_id]
                if not matches.empty:
                    df_row = matches.iloc[0]
        except Exception:
            df_row = None

        own_line = _norm_line_val(df_row.get("line") if df_row is not None else None)
        father_line = _norm_line_val(df_row.get("father_line") if df_row is not None else None)
        mother_line = _norm_line_val(df_row.get("mother_line") if df_row is not None else None)

        # Fallback: jeśli wiersz nie istnieje w df_std (rzadkie), bierz z rekordów w `people`.
        if own_line == "NA":
            own_line = _pid_to_line(subj.person_id)
        if father_line == "NA" and father_id:
            father_line = _pid_to_line(father_id)
        if mother_line == "NA" and mother_id:
            mother_line = _pid_to_line(mother_id)

        def _fmt(mem) -> str:
            if mem is None or (getattr(mem, "sire_founder_id", None) is None and getattr(mem, "dam_founder_id", None) is None):
                return "brak danych"
            sire = f"{mem.sire_founder_id} ({mem.sire_founder_name})"
            dam = f"{mem.dam_founder_id} ({mem.dam_founder_name})"
            return (
                f"Sireline: {sire} [steps={mem.sire_steps}]"
                f"\nDamline: {dam} [steps={mem.dam_steps}]"
            )

        inb_note_var.set(
            "Inbred (Wright F) + przynależność do linii:\n"
            f"- max pokoleń (ścieżki n1+n2) w Phi: {f_res.used_generations}\n"
            f"- Oceniany osobnik: {subj.person_id} ({subj.person_name}) | line={own_line}\n"
            f"{_fmt(subj)}\n"
            f"- Ojciec: {father_id} ({f_res.father_name}) | line={father_line}\n"
            f"{_fmt(father_mem)}\n"
            f"- Matka: {mother_id} ({f_res.mother_name}) | line={mother_line}\n"
            f"{_fmt(mother_mem)}\n\n"
            f"Kompletność rodowodu (ANC, bez limitu pokoleń): MG={MG}, EG={EG:.4f}, PCI={PCI:.4f}\n"
            f"Inbred F (Wright) liczone jako F(i)=Phi(sire(i), dam(i)); Phi rekurencyjnie wykorzystuje wspólnych przodków,\n"
            f"a brakujący rodzic traktowany jest jak „founder-stop” (wkład do Phi dla tej ścieżki wynosi 0).\n"
        )

        # Diagnostic plot (F vs max generations)
        _clear_frame(inb_plot_frame)
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie mogę narysować wykresu: {e}")
            return

        max_trace_depth = min(20, int(f_res.used_generations) if f_res.used_generations else 0)
        depths = list(range(0, max_trace_depth + 1))
        Fs = [wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=int(d)).F for d in depths]

        fig, ax = plt.subplots(figsize=(7.5, 3.6))
        ax.plot(depths, Fs, marker="o", linewidth=2, color=colors.EDGE_PLOT)
        ax.set_title(f"Inbred (Wright F) - diagnostyka (ID {person_id})")
        ax.set_xlabel("max pokoleń")
        ax.set_ylabel("F")
        ax.grid(True, alpha=0.25)

        canvas = FigureCanvasTkAgg(fig, master=inb_plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    inb_btn.configure(command=on_calc_inbreeding)

    # Disable controls until dataset is loaded.
    set_controls_enabled(False)

    # Auto-load default dataset for convenience.
    try:
        on_load_default()
    except Exception:
        _set_status("Nie udało się wczytać domyślnej bazy.")

    root.mainloop()

