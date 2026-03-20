from __future__ import annotations

import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from app.data.dataset_loader import load_dataset_from_path
from app.data.dataset_loader import load_default_bison_report
from app.pedigree.ancestor_pedigree import (
    build_people_map,
    ensure_people_for_nodes,
    get_ancestor_levels_and_edges,
)
from app.visualizations.ancestor_plot import plot_ancestor_pedigree
from app.analytics.inbreeding_wright import wright_inbreeding_F


def run_tk() -> None:
    # Nowy layout GUI (MENU + sidebar + main area + status bar).
    # Stary kod pozostał poniżej, ale nie jest wykonywany.
    from app.ui.tk.gui_pro import run_tk_pro

    run_tk_pro()
    return

    root = tk.Tk()
    root.title("WisentPedigree Pro+ - Tkinter")
    root.geometry("1100x750")

    # --- Motyw kolorystyczny (las + beż, pastelowo, tło białe) ---
    APP_BG = "#ffffff"  # tło aplikacji
    PANEL_BG = "#f4fbf5"
    PANEL_BG2 = "#eaf7ec"
    TEXT = "#0f3b2a"  # ciemny las (czytelny na jasno)
    MUTED = "#2c6a4e"
    ACCENT = "#caa86e"  # beż/sand
    BUTTON_BG = "#dff4e3"
    BUTTON_BG2 = "#c8ead4"
    ENTRY_BG = "#ffffff"

    root.configure(bg=APP_BG)
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TFrame", background=PANEL_BG)
    style.configure("TLabel", background=PANEL_BG, foreground=TEXT)
    style.configure("TNotebook", background=PANEL_BG)
    style.configure("TNotebook.Tab", background=BUTTON_BG2, foreground=ACCENT, padding=(10, 6))

    style.configure("TButton", background=BUTTON_BG, foreground=TEXT, padding=(10, 6))
    style.map("TButton", background=[("active", BUTTON_BG2)])

    style.configure(
        "TEntry",
        fieldbackground=ENTRY_BG,
        background=ENTRY_BG,
        foreground=TEXT,
        bordercolor=ACCENT,
    )
    style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT)

    style.configure(
        "Treeview",
        background=PANEL_BG,
        fieldbackground=PANEL_BG,
        foreground=TEXT,
        rowheight=22,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=BUTTON_BG2,
        foreground=ACCENT,
        borderwidth=0,
        relief="flat",
        padding=(6, 4),
    )
    style.map("Treeview", background=[("selected", BUTTON_BG)], foreground=[("selected", TEXT)])

    # --- Logo (ikonka + element w UI) ---
    _logo_path = Path(__file__).resolve().parents[2] / "logo.png"
    _tk_logo_img = None
    if _logo_path.exists():
        try:
            _tk_logo_img = tk.PhotoImage(file=str(_logo_path))

            # Tk bez PIL: robimy proste zmniejszenie przez subsampling.
            # Docelowo: małe logo w nagłówku, nie rozjeżdża layoutu.
            try:
                orig_w = _tk_logo_img.width()
            except Exception:
                orig_w = 0
            target_w = 90
            if orig_w and orig_w > target_w:
                factor = max(2, int(round(orig_w / target_w)))
                _tk_logo_img = _tk_logo_img.subsample(factor, factor)

            root.iconphoto(True, _tk_logo_img)
        except Exception:
            _tk_logo_img = None

    container = ttk.Frame(root, padding=12)
    container.pack(fill=tk.BOTH, expand=True)

    if _tk_logo_img is not None:
        header = ttk.Frame(container)
        header.pack(side=tk.TOP, fill=tk.X, pady=(0, 8))
        ttk.Label(header, image=_tk_logo_img).pack(side=tk.LEFT, padx=(0, 10))

    state: dict[str, object] = {
        "df_std": None,
        "people": None,
    }

    status_var = tk.StringVar(value="Gotowe. Wybierz plik.")

    # --- Import pliku ---
    ttk.Button(
        container,
        text="Wybierz plik (CSV/XLSX)",
        command=lambda: on_choose_file(),
    ).pack(side=tk.TOP, fill=tk.X)
    ttk.Label(container, textvariable=status_var).pack(side=tk.TOP, pady=(10, 0))
    minmax_var = tk.StringVar(value="")
    ttk.Label(container, textvariable=minmax_var, foreground=MUTED).pack(side=tk.TOP, pady=(4, 0))

    # --- Zakładki: funkcjonalności ---
    notebook = ttk.Notebook(container)
    notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=False, pady=(12, 0))

    tab_anc = ttk.Frame(notebook)
    tab_inb = ttk.Frame(notebook)
    notebook.add(tab_anc, text="Przodkowie")
    notebook.add(tab_inb, text="Inbred (F)")

    # --- Sterowanie wykresem (zakładka Przodkowie) ---
    controls = ttk.Frame(tab_anc)
    controls.pack(side=tk.TOP, fill=tk.X, pady=(12, 0))

    ttk.Label(controls, text="ID (Number):").grid(row=0, column=0, sticky="w")
    id_var = tk.StringVar(value="")
    id_entry = ttk.Entry(controls, textvariable=id_var, width=20, state="disabled")
    id_entry.grid(row=0, column=1, sticky="w", padx=(8, 20))

    ttk.Label(controls, text="Max pokoleń:").grid(row=0, column=2, sticky="w")
    depth_var = tk.StringVar(value="4")
    depth_entry = ttk.Entry(controls, textvariable=depth_var, width=10, state="disabled")
    depth_entry.grid(row=0, column=3, sticky="w", padx=(8, 20))

    readable_anc_var = tk.BooleanVar(value=True)
    readable_anc_cb = ttk.Checkbutton(
        controls,
        text="Tryb czytelny (mniej etykiet)",
        variable=readable_anc_var,
        state="disabled",
    )
    readable_anc_cb.grid(row=1, column=0, columnspan=5, sticky="w", pady=(10, 0))

    generate_btn = ttk.Button(
        controls, text="Generuj przodków", state="disabled", command=lambda: on_generate()
    )
    generate_btn.grid(row=0, column=4, sticky="w")

    anc_hint = tk.Label(
        tab_anc,
        text="Wybierz wiersz w podglądzie (double-click), aby uzupełnić ID.",
        foreground=MUTED,
        background=PANEL_BG,
    )
    anc_hint.pack(side=tk.TOP, anchor="w", pady=(10, 0), padx=6)

    # --- Sterowanie inbredem (zakładka Inbred) ---
    ttk.Label(tab_inb, text="ID (Number):").grid(row=0, column=0, sticky="w")
    id_inb_var = tk.StringVar(value="")
    id_inb_entry = ttk.Entry(tab_inb, textvariable=id_inb_var, width=22, state="disabled")
    id_inb_entry.grid(row=0, column=1, sticky="w", padx=(8, 20))

    ttk.Label(tab_inb, text="Max pokoleń:").grid(row=0, column=2, sticky="w")
    depth_inb_var = tk.StringVar(value="4")
    depth_inb_entry = ttk.Entry(tab_inb, textvariable=depth_inb_var, width=10, state="disabled")
    depth_inb_entry.grid(row=0, column=3, sticky="w", padx=(8, 20))

    unbounded_inb_var = tk.BooleanVar(value=False)
    unbounded_inb_cb = ttk.Checkbutton(
        tab_inb,
        text="Bez ograniczenia (do founderów)",
        variable=unbounded_inb_var,
        state="disabled",
    )
    unbounded_inb_cb.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

    calc_inb_btn = ttk.Button(tab_inb, text="Policz F (Wright)", state="disabled", command=lambda: on_calc_inbreeding())
    calc_inb_btn.grid(row=0, column=4, sticky="w")

    inb_result_var = tk.StringVar(value="F = -")
    ttk.Label(tab_inb, textvariable=inb_result_var, font=("TkDefaultFont", 12, "bold")).grid(
        row=2, column=0, columnspan=5, sticky="w", pady=(14, 0)
    )
    inb_method_var = tk.StringVar(
        value="Jak liczony jest inbred Wrighta (F): F(i)=Phi(sire(i), dam(i)). Phi liczymy rekurencyjnie po ścieżkach rodowodowych; brak rodziców traktujemy jako founder (Phi=0 dla par)."
    )
    ttk.Label(
        tab_inb,
        textvariable=inb_method_var,
        foreground=MUTED,
        justify="left",
        wraplength=650,
    ).grid(row=3, column=0, columnspan=5, sticky="w", pady=(6, 0))

    inb_note_var = tk.StringVar(value="Wynik liczony z ograniczeniem liczby pokoleń.")
    ttk.Label(tab_inb, textvariable=inb_note_var, foreground=MUTED).grid(
        row=4, column=0, columnspan=5, sticky="w", pady=(4, 0)
    )

    inb_plot_frame = ttk.Frame(tab_inb)
    inb_plot_frame.grid(row=5, column=0, columnspan=5, sticky="nsew", pady=(10, 0))

    # --- Podgląd danych (żeby łatwo skopiować ID) ---
    preview_frame = ttk.LabelFrame(container, text="Podgląd wierszy (pierwsze 250)")
    preview_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, pady=(14, 0))

    columns = ("id", "name", "sex", "birth_year", "father_id", "mother_id")
    tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=7)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="w")

    vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
    vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def set_controls_enabled(enabled: bool) -> None:
        next_state = "normal" if enabled else "disabled"
        id_entry.configure(state=next_state)
        depth_entry.configure(state=next_state)
        readable_anc_cb.configure(state=next_state)
        generate_btn.configure(state=next_state)

    def set_inb_controls_enabled(enabled: bool) -> None:
        next_state = "normal" if enabled else "disabled"
        id_inb_entry.configure(state=next_state)
        depth_inb_entry.configure(state=next_state)
        unbounded_inb_cb.configure(state=next_state)
        calc_inb_btn.configure(state=next_state)

    def clear_tree() -> None:
        for item in tree.get_children():
            tree.delete(item)

    def on_choose_file() -> None:
        path = filedialog.askopenfilename(
            title="Wybierz plik",
            filetypes=[("CSV", "*.csv"), ("Excel", "*.xlsx *.xls"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            df_std, info = load_dataset_from_path(path)
        except Exception as e:
            messagebox.showerror("Błąd", str(e))
            status_var.set("Błąd wczytywania.")
            return

        _apply_loaded_dataset(df_std=df_std, info=info)

    def on_tree_double_click(_event: tk.Event) -> None:
        selection = tree.selection()
        if not selection:
            return
        values = tree.item(selection[0], "values")
        if not values:
            return
        # values[0] = id (zgodnie z kolejnością kolumn)
        picked_id = str(values[0])
        id_var.set(picked_id)
        id_inb_var.set(picked_id)

    def on_generate() -> None:
        people = state.get("people")
        if not people:
            messagebox.showinfo("Info", "Najpierw wczytaj plik.")
            return

        person_id = str(id_var.get()).strip()
        if not person_id:
            messagebox.showerror("Błąd", "Podaj ID (Number).")
            return
        if person_id not in people:  # type: ignore[operator]
            messagebox.showerror("Błąd", "Nie ma takiego ID w wczytanych danych.")
            return

        try:
            depth = int(str(depth_var.get()).strip())
        except Exception:
            messagebox.showerror("Błąd", "Max pokoleń musi być liczbą całkowitą.")
            return
        if depth < 0:
            messagebox.showerror("Błąd", "Max pokoleń nie może być ujemne.")
            return
        depth = min(depth, 10)

        levels, edges = get_ancestor_levels_and_edges(person_id=person_id, depth=depth, people=people)  # type: ignore[arg-type]
        if not levels:
            messagebox.showerror("Błąd", "Nie znaleziono wiersza dla podanego ID (lub brak rodziców w limicie).")
            return

        people_all = ensure_people_for_nodes(levels=levels, people=people)  # type: ignore[arg-type]
        fig = plot_ancestor_pedigree(
            person_id=person_id,
            levels=levels,
            edges=edges,
            people=people_all,
            readable_mode=bool(readable_anc_var.get()),
        )  # type: ignore[arg-type]

        if len(levels) <= 1 or len(edges) == 0:
            person = people.get(person_id)  # type: ignore[union-attr]
            father = getattr(person, "father_id", None) if person else None
            mother = getattr(person, "mother_id", None) if person else None
            messagebox.showinfo(
                "Informacja",
                "Dla tego ID nie znaleziono przodków (brak krawędzi) w podanym limicie.\n"
                "Jeśli `Father` i `Mother` są nieznane (brak ID rodziców), traktujemy osobnika jako founder i w wykresie pojawia się tylko on.\n"
                f"Father: {father}\n"
                f"Mother: {mother}\n"
                f"Węzły: {len(levels)}, krawędzie: {len(edges)}.",
            )

        # --- Otwieramy nowe okno z wykresem ---
        graph_win = tk.Toplevel(root)
        graph_win.title(f"Przodkowie: {person_id} (max pokoleń: {depth})")
        graph_win.geometry("1150x650")

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie mogę osadzić wykresu w Tk: {e}")
            return

        canvas = FigureCanvasTkAgg(fig, master=graph_win)
        canvas.draw()
        try:
            toolbar = NavigationToolbar2Tk(canvas, graph_win)
            toolbar.update()
            toolbar.pack(side=tk.TOP, fill=tk.X)
        except Exception:
            # Jeśli toolbar nie jest dostępny (np. minimalna instalacja Matplotlib), wykres i tak będzie działał.
            pass
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def on_calc_inbreeding() -> None:
        people = state.get("people")
        if not people:
            messagebox.showinfo("Info", "Najpierw wczytaj plik.")
            return

        person_id = str(id_inb_var.get()).strip()
        if not person_id:
            messagebox.showerror("Błąd", "Podaj ID (Number).")
            return
        if person_id not in people:  # type: ignore[operator]
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
            depth = min(depth, 10)
            f_res = wright_inbreeding_F(person_id=person_id, people=people, max_generations_back=depth)

        inb_result_var.set(f"F = {f_res.F:.6f}")

        if abs(f_res.F) < 1e-12:
            father_id = f_res.father_id
            mother_id = f_res.mother_id
            father_name = f_res.father_name
            mother_name = f_res.mother_name
            inb_note_var.set(
                "F=0 dla max pokoleń (ścieżki n1+n2) ="
                f"{f_res.used_generations}. "
                f"Father={father_id} ({father_name}); Mother={mother_id} ({mother_name})."
            )
        else:
            inb_note_var.set(
                "Wynik liczony dla max pokoleń (ścieżki n1+n2) ="
                f"{f_res.used_generations}. "
                f"Father={f_res.father_id} ({f_res.father_name}); Mother={f_res.mother_id} ({f_res.mother_name})."
            )

        # --- Wizualizacja: przebieg F w funkcji głębokości rodowodu ---
        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie mogę przygotować wykresu inbredu: {e}")
            return

        # Czyścimy poprzedni wykres.
        for child in inb_plot_frame.winfo_children():
            child.destroy()

        # Zakres głębokości do wykresu (diagnostyka, ograniczamy aby UI nie zwolniło).
        if bool(unbounded_inb_var.get()):
            # Wykres jest diagnostyczny; ograniczamy zakres dla wydajności GUI.
            max_trace_depth = min(20, int(f_res.used_generations))
        else:
            # W trybie ograniczonym suwak już był ograniczony do max 10.
            max_trace_depth = int(depth)

        depths = list(range(0, max_trace_depth + 1))
        Fs: list[float] = []
        for d in depths:
            Fs.append(
                wright_inbreeding_F(
                    person_id=person_id,
                    people=people,
                    max_generations_back=int(d),
                ).F
            )

        fig, ax = plt.subplots(figsize=(7.5, 3.6))
        ax.plot(depths, Fs, marker="o", linewidth=2, color="#2c6a4e")
        ax.set_title(f"Inbred (Wright F) - diagnostyka (ID {person_id})")
        ax.set_xlabel("max pokoleń")
        ax.set_ylabel("F")
        ax.grid(True, alpha=0.25)

        if bool(unbounded_inb_var.get()) and int(f_res.used_generations) > max_trace_depth:
            ax.annotate(
                f"F unbounded={f_res.F:.3f}\n(dopóki do founderów: {f_res.used_generations})",
                xy=(max_trace_depth, Fs[-1] if Fs else 0.0),
                xytext=(10, 10),
                textcoords="offset points",
                fontsize=9,
                ha="left",
                va="bottom",
            )

        canvas = FigureCanvasTkAgg(fig, master=inb_plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    tree.bind("<Double-1>", on_tree_double_click)

    set_controls_enabled(False)
    set_inb_controls_enabled(False)

    def _apply_loaded_dataset(*, df_std, info) -> None:
        state["df_std"] = df_std
        state["people"] = build_people_map(df_std)

        status_var.set(
            f"Wczytano: {info.rows} wierszy, {info.columns} kolumn. (Podgląd odświeżony)"
        )

        # Info o zakresie ID (Number) w wczytanej bazie.
        ids = df_std["id"].dropna().astype(str)
        if not ids.empty:
            def _id_sort_key(s: str) -> tuple[int, str]:
                m = re.match(r"^(\\d+)([A-Za-z]*)$", s)
                if not m:
                    return (10**30, s)
                return (int(m.group(1)), m.group(2) or "")

            min_id = min(ids.tolist(), key=_id_sort_key)
            max_id = max(ids.tolist(), key=_id_sort_key)
            minmax_var.set(f"Zakres ID: min {min_id} / max {max_id}")
        else:
            minmax_var.set("Zakres ID: brak prawidłowych wartości.")

        clear_tree()
        df_preview = df_std.head(250)
        for _, row in df_preview.iterrows():
            tree.insert(
                "",
                "end",
                values=(
                    row.get("id"),
                    row.get("name"),
                    row.get("sex"),
                    row.get("birth_year"),
                    row.get("father_id"),
                    row.get("mother_id"),
                ),
            )

        # Default ID: pierwsza osoba z przynajmniej jednym rodzicem.
        if not df_std.empty:
            with_parents = df_std[df_std["father_id"].notna() | df_std["mother_id"].notna()]
            first_row = with_parents.iloc[0] if not with_parents.empty else df_std.iloc[0]
            first_id = first_row["id"]
        else:
            first_id = ""
        id_var.set(str(first_id))
        id_inb_var.set(str(first_id))
        inb_result_var.set("F = -")
        inb_note_var.set("Wynik liczony z ograniczeniem liczby pokoleń.")
        set_controls_enabled(True)
        set_inb_controls_enabled(True)

    # --- Auto-wczytanie domyślnej bazy (bez uploadu) ---
    try:
        df_std, info = load_default_bison_report()
        _apply_loaded_dataset(df_std=df_std, info=info)
    except Exception as e:
        # Jeśli pliku nie ma, wracamy do trybu "wybierz plik".
        status_var.set(f"Nie udało się wczytać domyślnej bazy: {e}")

    root.mainloop()

