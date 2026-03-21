"""
Małe okno z przewijanym tekstem pomocy — wyświetlane z poziomu wersji na pulpicie.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext


def show_help_window(
    parent: tk.Misc,
    title: str,
    body: str,
    *,
    width: int = 760,
    height: int = 560,
) -> None:
    """Wyświetla niemodalne okno z treścią pomocy (UTF-8)."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry(f"{width}x{height}")
    win.minsize(480, 320)

    txt = scrolledtext.ScrolledText(
        win,
        wrap="word",
        font=("TkDefaultFont", 10),
        padx=10,
        pady=10,
    )
    txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 0))
    txt.insert("1.0", body)
    txt.configure(state="disabled")

    btn_row = ttk.Frame(win)
    btn_row.pack(fill=tk.X, pady=(0, 8))
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack()
