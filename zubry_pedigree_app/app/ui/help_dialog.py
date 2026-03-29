"""
Małe okno z przewijanym tekstem pomocy — wyświetlane z poziomu wersji na pulpicie.
Treść w UTF-8 (polskie znaki); czcionka z ui/typography (większa, spójna z resztą okna).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, scrolledtext

from app.ui.tk.theme import Theme
from app.ui.typography import TK_PT_HELP_BODY, ensure_tk_font_resolved, tk_font


def show_help_window(
    parent: tk.Misc,
    title: str,
    body: str,
    *,
    width: int = 860,
    height: int = 640,
) -> None:
    """Wyświetla niemodalne okno z treścią pomocy (UTF-8)."""
    ensure_tk_font_resolved(parent)
    colors = Theme()

    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry(f"{width}x{height}")
    win.minsize(520, 360)
    win.configure(bg=colors.APP_BG)

    txt = scrolledtext.ScrolledText(
        win,
        wrap="word",
        font=tk_font(TK_PT_HELP_BODY),
        padx=14,
        pady=14,
        bg=colors.ENTRY_BG,
        fg=colors.TEXT,
        insertbackground=colors.TEXT,
        selectbackground=colors.BUTTON_BG2,
        selectforeground=colors.TEXT,
        relief="flat",
        borderwidth=1,
        highlightthickness=1,
        highlightbackground=colors.ACCENT,
        highlightcolor=colors.ACCENT,
        spacing1=2,
        spacing3=4,
    )
    txt.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 0))
    txt.insert("1.0", body)
    txt.configure(state="disabled")

    btn_row = ttk.Frame(win)
    btn_row.pack(fill=tk.X, pady=(0, 10))
    ttk.Button(btn_row, text="Zamknij", command=win.destroy).pack()
