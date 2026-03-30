"""Uruchomienie pełnego GUI (moduł `gui_pro`)."""

from __future__ import annotations


def run_tk() -> None:
    from app.ui.tk.gui_pro import run_tk_pro

    run_tk_pro()
