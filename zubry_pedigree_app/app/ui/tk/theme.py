from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


@dataclass(frozen=True)
class Theme:
    APP_BG: str = "#ffffff"
    PANEL_BG: str = "#f4fbf5"
    PANEL_BG2: str = "#eaf7ec"
    TEXT: str = "#000000"
    MUTED: str = "#333333"
    ACCENT: str = "#caa86e"
    TAB_BG: str = "#e6ddd2"
    TAB_ACTIVE_BG: str = "#d5c4ae"
    TAB_TEXT: str = "#4b3a2a"
    BUTTON_BG: str = "#e6ddd2"
    BUTTON_BG2: str = "#d5c4ae"
    ENTRY_BG: str = "#ffffff"
    EDGE_PLOT: str = "#2c6a4e"
    TREE_BG: str = "#f4fbf5"
    TABLE_TEXT: str = "#000000"
    TABLE_HEADER_TEXT: str = "#000000"


def setup_theme(root: tk.Tk) -> Theme:
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
        background=colors.TAB_BG,
        foreground=colors.TAB_TEXT,
        padding=(10, 6),
        font=("TkDefaultFont", 11, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors.TAB_ACTIVE_BG), ("active", "#ddd0bf")],
        foreground=[("selected", colors.TAB_TEXT), ("active", colors.TAB_TEXT)],
    )

    style.configure("TButton", background=colors.BUTTON_BG, foreground=colors.TEXT, padding=(10, 6))
    style.map(
        "TButton",
        background=[("active", colors.BUTTON_BG2), ("pressed", "#c9b296")],
        foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
    )

    style.configure(
        "TEntry",
        fieldbackground=colors.ENTRY_BG,
        background=colors.ENTRY_BG,
        foreground=colors.TEXT,
        bordercolor=colors.ACCENT,
    )
    style.configure("TCheckbutton", background=colors.PANEL_BG, foreground=colors.TEXT)
    style.configure("TRadiobutton", background=colors.PANEL_BG, foreground=colors.TEXT)

    style.configure("TLabelframe", background=colors.PANEL_BG)
    style.configure("TLabelframe.Label", background=colors.PANEL_BG, foreground=colors.MUTED)

    style.configure(
        "TCombobox",
        fieldbackground=colors.ENTRY_BG,
        background=colors.ENTRY_BG,
        foreground=colors.TEXT,
    )
    style.map("TCombobox", fieldbackground=[("readonly", colors.ENTRY_BG)])

    style.configure(
        "Treeview",
        background=colors.TREE_BG,
        fieldbackground=colors.TREE_BG,
        foreground=colors.TABLE_TEXT,
        rowheight=22,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        background=colors.BUTTON_BG2,
        foreground=colors.TABLE_HEADER_TEXT,
        borderwidth=0,
        relief="flat",
        padding=(6, 4),
    )
    style.map("Treeview", background=[("selected", colors.BUTTON_BG)], foreground=[("selected", colors.TABLE_TEXT)])

    return colors

