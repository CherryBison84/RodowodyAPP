"""Czcionki: CSS (Streamlit) i matplotlib — spójnie, z obsługą polskich znaków."""

from __future__ import annotations

# Kolejność dla CSS / matplotlib (pierwsza dostępna w systemie)
FONT_STACK_SANS: list[str] = [
    "SF Pro Text",
    ".SF NS Text",
    "Helvetica Neue",
    "Lucida Grande",
    "Segoe UI",
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
    "Noto Sans",
    "Helvetica",
    "sans-serif",
]

_mpl_configured = False


def css_font_family() -> str:
    """Łańcuch font-family do wstrzyknięcia w CSS (Streamlit)."""
    return ", ".join(f"'{n}'" if " " in n else n for n in FONT_STACK_SANS[:-1]) + ", sans-serif"


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
            "font.size": 12,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 11,
            "figure.titlesize": 14,
        }
    )
    _mpl_configured = True
