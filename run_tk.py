"""
Punkt wejścia z katalogu głównego repozytorium.
Źródło: `zubry_pedigree_app/run_tk.py`

Uruchomienie (z katalogu RodowodyAPP):
  python zubry_pedigree_app/run_tk.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_pkg = Path(__file__).resolve().parent / "zubry_pedigree_app"
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))

from app.ui.tk.main import run_tk

if __name__ == "__main__":
    run_tk()
