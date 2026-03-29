"""
Wejście na pulpit: pełne GUI w `gui_pro` (wszystkie zakładki, populacja, raporty).
"""

from __future__ import annotations


def run_tk() -> None:
    from app.ui.tk.gui_pro import run_tk_pro

    run_tk_pro()
