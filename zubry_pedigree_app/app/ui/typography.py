"""
Wspólna czcionka interfejsu: to samo „pismo” w oknie na pulpicie, w przeglądarce i na wykresach.
Priorytet: sans-serif z pełnym zestawem znaków łacińskich (polskie ogonki) na danej platformie.
"""

from __future__ import annotations

import sys
from typing import Any, Tuple, Union

# Rozmiary (pt) — jeden zestaw dla Tk / ttk
TK_PT_LABEL = 13
TK_PT_BUTTON = 12
TK_PT_ENTRY = 12
TK_PT_TREE = 12
TK_PT_NOTEBOOK_TAB = 12
TK_PT_SMALL = 11
TK_PT_HELP_BODY = 16

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

# Preferencja dla Tk: pierwsza nazwa faktycznie zwrócona przez font.families() (UTF-8 / PL).
_TK_FAMILY_PRIORITY: tuple[str, ...] = (
    "SF Pro Text",
    ".SF NS Text",
    "Helvetica Neue",
    "Lucida Grande",
    "Segoe UI",
    "Arial",
    "DejaVu Sans",
    "Liberation Sans",
    "Noto Sans",
    "Cantarell",
    "Ubuntu",
    "Helvetica",
)

_resolved_tk_family: str | None = None


def _platform_fallback_family() -> str:
    if sys.platform == "darwin":
        return "Helvetica Neue"
    if sys.platform == "win32":
        return "Segoe UI"
    return "DejaVu Sans"


def set_tk_font_family_from_root(widget: Any) -> None:
    """Wybiera pierwszą dostępną czcionkę z listy (lepsze pokrycie PL niż sztywna nazwa)."""
    global _resolved_tk_family
    if _resolved_tk_family is not None:
        return
    try:
        import tkinter.font as tkfont
    except Exception:
        _resolved_tk_family = _platform_fallback_family()
        return
    try:
        fams = set(tkfont.families(widget))
    except Exception:
        _resolved_tk_family = _platform_fallback_family()
        return
    for name in _TK_FAMILY_PRIORITY:
        if name in fams:
            _resolved_tk_family = name
            return
    _resolved_tk_family = _platform_fallback_family()


def ensure_tk_font_resolved(widget: Any) -> None:
    """Wywołaj np. przed pierwszym oknem pomocy, jeśli motyw jeszcze nie zainicjował rodziny."""
    set_tk_font_family_from_root(widget)


def ui_font_family() -> str:
    return _resolved_tk_family or _platform_fallback_family()


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
