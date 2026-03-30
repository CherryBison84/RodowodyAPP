"""Motyw kolorystyczny i style ttk (clam lub ttkbootstrap + paleta „leśna”)."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from app.ui.typography import (
    TK_PT_BUTTON,
    TK_PT_ENTRY,
    TK_PT_LABEL,
    TK_PT_NOTEBOOK_TAB,
    TK_PT_SMALL,
    TK_PT_TREE,
    set_tk_font_family_from_root,
    tk_font,
)


@dataclass(frozen=True)
class Theme:
    """Leśna kolorystyka: mgła, mech, kora, ściółka — spójnie Tk, Streamlit i Matplotlib."""

    # --- Interfejs ---
    APP_BG: str = "#e8f0eb"
    PANEL_BG: str = "#dce8df"
    PANEL_BG2: str = "#c5d6c9"
    TEXT: str = "#1e2b24"
    MUTED: str = "#4a5d52"
    ACCENT: str = "#8a6b58"
    TAB_BG: str = "#d4cdc2"
    TAB_ACTIVE_BG: str = "#b8cab8"
    TAB_TEXT: str = "#2a221c"
    BUTTON_BG: str = "#c8d9cc"
    BUTTON_BG2: str = "#a8bfa8"
    ENTRY_BG: str = "#f4f8f4"
    EDGE_PLOT: str = "#3d634d"
    TREE_BG: str = "#e4efe6"
    TABLE_TEXT: str = "#1e2b24"
    TABLE_HEADER_TEXT: str = "#243529"
    # Obramowania / akcent drugorzędny (jak spękana kora)
    BORDER_SUBTLE: str = "#9aaa9e"
    LINK: str = "#355d47"


def _setup_theme_ttkbootstrap(root: tk.Misc) -> Theme:
    """ttkbootstrap + nasza paleta leśna (tekst, pola, drzewo, tło okna)."""
    colors = Theme()
    set_tk_font_family_from_root(root)
    style = root.style
    try:
        root.configure(background=colors.APP_BG)
    except Exception:
        pass
    # Nadpisania spójne z Theme (bootstrap zostawia kontrolki, tło/ramy jak las)
    for w in ("TFrame", "TLabelframe", "TNotebook"):
        try:
            style.configure(w, background=colors.PANEL_BG)
        except Exception:
            pass
    try:
        style.configure("TLabelframe.Label", background=colors.PANEL_BG, foreground=colors.MUTED)
    except Exception:
        pass
    try:
        style.configure(
            "TLabel",
            background=colors.PANEL_BG,
            foreground=colors.TEXT,
            font=tk_font(TK_PT_LABEL),
        )
    except Exception:
        pass
    try:
        style.configure(
            "Treeview",
            background=colors.TREE_BG,
            fieldbackground=colors.TREE_BG,
            foreground=colors.TABLE_TEXT,
            rowheight=28,
            font=tk_font(TK_PT_TREE),
        )
        style.configure(
            "Treeview.Heading",
            background=colors.BUTTON_BG2,
            foreground=colors.TABLE_HEADER_TEXT,
            font=tk_font(TK_PT_TREE, bold=True),
        )
        style.map(
            "Treeview",
            background=[("selected", colors.TAB_ACTIVE_BG)],
            foreground=[("selected", colors.TABLE_TEXT)],
        )
    except Exception:
        pass
    # Leśna paleta na całym UI (ttkbootstrap tylko jako silnik stylów).
    try:
        style.configure("TNotebook", background=colors.PANEL_BG)
        style.configure(
            "TNotebook.Tab",
            background=colors.TAB_BG,
            foreground=colors.TAB_TEXT,
            padding=(10, 6),
            font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", colors.TAB_ACTIVE_BG), ("active", colors.PANEL_BG2)],
            foreground=[("selected", colors.TAB_TEXT), ("active", colors.TAB_TEXT)],
        )
    except Exception:
        pass
    # Przyciski nawigacji głównej (jak karty notebooka — ta sama paleta co TNotebook.Tab).
    try:
        style.configure(
            "NavTab.TButton",
            background=colors.TAB_BG,
            foreground=colors.TAB_TEXT,
            padding=(10, 6),
            font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
        )
        style.map(
            "NavTab.TButton",
            background=[("active", colors.PANEL_BG2), ("pressed", colors.TAB_ACTIVE_BG)],
            foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
        )
        style.configure(
            "NavTabActive.TButton",
            background=colors.TAB_ACTIVE_BG,
            foreground=colors.TAB_TEXT,
            padding=(10, 6),
            font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
        )
        style.map(
            "NavTabActive.TButton",
            background=[("active", colors.PANEL_BG2), ("pressed", colors.TAB_BG)],
            foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
        )
    except Exception:
        pass
    try:
        style.configure(
            "TButton",
            background=colors.BUTTON_BG,
            foreground=colors.TEXT,
            padding=(10, 6),
            font=tk_font(TK_PT_BUTTON),
        )
        style.map(
            "TButton",
            background=[("active", colors.BUTTON_BG2), ("pressed", colors.TAB_BG)],
            foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
        )
    except Exception:
        pass
    try:
        style.configure(
            "TCheckbutton",
            background=colors.PANEL_BG,
            foreground=colors.TEXT,
            font=tk_font(TK_PT_ENTRY),
        )
        style.configure(
            "TRadiobutton",
            background=colors.PANEL_BG,
            foreground=colors.TEXT,
            font=tk_font(TK_PT_ENTRY),
        )
    except Exception:
        pass
    try:
        style.configure(
            "TEntry",
            fieldbackground=colors.ENTRY_BG,
            background=colors.ENTRY_BG,
            foreground=colors.TEXT,
            insertcolor=colors.TEXT,
            bordercolor=colors.ACCENT,
            lightcolor=colors.BORDER_SUBTLE,
            darkcolor=colors.BORDER_SUBTLE,
            font=tk_font(TK_PT_ENTRY),
        )
        style.configure(
            "TCombobox",
            fieldbackground=colors.ENTRY_BG,
            background=colors.ENTRY_BG,
            foreground=colors.TEXT,
            arrowcolor=colors.TEXT,
            font=tk_font(TK_PT_ENTRY),
        )
        style.map("TCombobox", fieldbackground=[("readonly", colors.ENTRY_BG)])
    except Exception:
        pass
    try:
        style.configure(
            "Vertical.TScrollbar",
            background=colors.PANEL_BG2,
            troughcolor=colors.PANEL_BG,
            bordercolor=colors.BORDER_SUBTLE,
            arrowcolor=colors.MUTED,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=colors.PANEL_BG2,
            troughcolor=colors.PANEL_BG,
            bordercolor=colors.BORDER_SUBTLE,
            arrowcolor=colors.MUTED,
        )
    except Exception:
        pass
    return colors


def setup_theme(root: tk.Misc) -> Theme:
    try:
        from ttkbootstrap import Window

        if isinstance(root, Window):
            return _setup_theme_ttkbootstrap(root)
    except ImportError:
        pass

    colors = Theme()
    root.configure(bg=colors.APP_BG)
    set_tk_font_family_from_root(root)

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure("TFrame", background=colors.PANEL_BG)
    style.configure("TLabel", background=colors.PANEL_BG, foreground=colors.TEXT, font=tk_font(TK_PT_LABEL))
    style.configure("TNotebook", background=colors.PANEL_BG)
    style.configure(
        "TNotebook.Tab",
        background=colors.TAB_BG,
        foreground=colors.TAB_TEXT,
        padding=(10, 6),
        font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors.TAB_ACTIVE_BG), ("active", colors.PANEL_BG2)],
        foreground=[("selected", colors.TAB_TEXT), ("active", colors.TAB_TEXT)],
    )

    style.configure(
        "NavTab.TButton",
        background=colors.TAB_BG,
        foreground=colors.TAB_TEXT,
        padding=(10, 6),
        font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
    )
    style.map(
        "NavTab.TButton",
        background=[("active", colors.PANEL_BG2), ("pressed", colors.TAB_ACTIVE_BG)],
        foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
    )
    style.configure(
        "NavTabActive.TButton",
        background=colors.TAB_ACTIVE_BG,
        foreground=colors.TAB_TEXT,
        padding=(10, 6),
        font=tk_font(TK_PT_NOTEBOOK_TAB, bold=True),
    )
    style.map(
        "NavTabActive.TButton",
        background=[("active", colors.PANEL_BG2), ("pressed", colors.TAB_BG)],
        foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
    )

    style.configure(
        "TButton", background=colors.BUTTON_BG, foreground=colors.TEXT, padding=(10, 6), font=tk_font(TK_PT_BUTTON)
    )
    style.map(
        "TButton",
        background=[("active", colors.BUTTON_BG2), ("pressed", colors.TAB_BG)],
        foreground=[("active", colors.TAB_TEXT), ("pressed", colors.TAB_TEXT)],
    )

    style.configure(
        "TEntry",
        fieldbackground=colors.ENTRY_BG,
        background=colors.ENTRY_BG,
        foreground=colors.TEXT,
        insertcolor=colors.TEXT,
        bordercolor=colors.ACCENT,
        lightcolor=colors.BORDER_SUBTLE,
        darkcolor=colors.BORDER_SUBTLE,
        font=tk_font(TK_PT_ENTRY),
    )
    style.configure("TCheckbutton", background=colors.PANEL_BG, foreground=colors.TEXT, font=tk_font(TK_PT_ENTRY))
    style.configure("TRadiobutton", background=colors.PANEL_BG, foreground=colors.TEXT, font=tk_font(TK_PT_ENTRY))

    style.configure("TLabelframe", background=colors.PANEL_BG)
    style.configure("TLabelframe.Label", background=colors.PANEL_BG, foreground=colors.MUTED, font=tk_font(TK_PT_SMALL))

    style.configure(
        "TCombobox",
        fieldbackground=colors.ENTRY_BG,
        background=colors.ENTRY_BG,
        foreground=colors.TEXT,
        font=tk_font(TK_PT_ENTRY),
    )
    style.map("TCombobox", fieldbackground=[("readonly", colors.ENTRY_BG)])

    style.configure(
        "Treeview",
        background=colors.TREE_BG,
        fieldbackground=colors.TREE_BG,
        foreground=colors.TABLE_TEXT,
        rowheight=24,
        borderwidth=0,
        font=tk_font(TK_PT_TREE),
    )
    style.configure(
        "Treeview.Heading",
        background=colors.BUTTON_BG2,
        foreground=colors.TABLE_HEADER_TEXT,
        borderwidth=0,
        relief="flat",
        padding=(6, 4),
        font=tk_font(TK_PT_TREE, bold=True),
    )
    style.map("Treeview", background=[("selected", colors.BUTTON_BG)], foreground=[("selected", colors.TABLE_TEXT)])

    try:
        style.configure(
            "Vertical.TScrollbar",
            background=colors.PANEL_BG2,
            troughcolor=colors.PANEL_BG,
            bordercolor=colors.BORDER_SUBTLE,
            arrowcolor=colors.MUTED,
        )
        style.configure(
            "Horizontal.TScrollbar",
            background=colors.PANEL_BG2,
            troughcolor=colors.PANEL_BG,
            bordercolor=colors.BORDER_SUBTLE,
            arrowcolor=colors.MUTED,
        )
    except Exception:
        pass

    return colors

