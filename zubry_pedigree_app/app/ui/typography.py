"""
Wspólna czcionka interfejsu: to samo „pismo” w oknie na pulpicie, w przeglądarce i na wykresach.
Na Macu domyślnie Helvetica Neue, na Windows Segoe UI, na Linuxie DejaVu Sans.
"""

from __future__ import annotations

import sys
from typing import Tuple, Union

# Kolejność dla CSS / matplotlib (pierwsza dostępna w systemie)
FONT_STACK_SANS: list[str] = [
    "Helvetica Neue",
    "Segoe UI",
    "DejaVu Sans",
    "Liberation Sans",
    "Arial",
    "sans-serif",
]

# Jedna nazwa dla Tk (ttk nie obsługuje listy zapasowej)
def ui_font_family() -> str:
    if sys.platform == "darwin":
        return "Helvetica Neue"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def tk_font(size: int, *, bold: bool = False) -> Union[Tuple[str, int], Tuple[str, int, str]]:
    """Krotka czcionki dla Tkinter / ttk (np. ttk.Label(..., font=tk_font(12, bold=True)))."""
    fam = ui_font_family()
    if bold:
        return (fam, size, "bold")
    return (fam, size)


def css_font_family() -> str:
    """Łańcuch font-family do wstrzyknięcia w CSS (Streamlit)."""
    return ", ".join(f"'{n}'" if " " in n else n for n in FONT_STACK_SANS[:-1]) + ", sans-serif"


_mpl_configured = False


def apply_matplotlib_fonts() -> None:
    """Ustawia rodzinę czcionki i bazowe rozmiary dla wszystkich wykresów Matplotlib."""
    global _mpl_configured
    if _mpl_configured:
        return
    import matplotlib

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": FONT_STACK_SANS[:-1],
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
            "legend.fontsize": 9,
            "figure.titlesize": 12,
        }
    )
    _mpl_configured = True
