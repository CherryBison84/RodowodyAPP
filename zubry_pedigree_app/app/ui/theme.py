"""Paleta kolorystyczna interfejsu (Streamlit, matplotlib) — motyw „leśny”."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Mgła, mech, kora — spójnie z CSS Streamlit i wykresami Matplotlib."""

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
    COMPLETENESS_ACCENT: str = "#5d7a66"
    TABLE_TEXT: str = "#1e2b24"
    TABLE_HEADER_TEXT: str = "#243529"
    BORDER_SUBTLE: str = "#9aaa9e"
    LINK: str = "#355d47"
