"""
Najprostsze uruchomienie programu w postaci okna na pulpicie (bez przeglądarki).
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.ui.tk.main import run_tk

if __name__ == "__main__":
    run_tk()
