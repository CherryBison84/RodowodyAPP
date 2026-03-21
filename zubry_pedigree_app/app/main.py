"""
Punkt startowy z linii poleceń: wybór, czy pokazać program w oknie na pulpicie,
czy w wersji otwieranej w przeglądarce.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Umożliwia uruchamianie jako skrypt: `python zubry_pedigree_app/app/main.py`
# (bez konieczności odpalenia przez `-m` z katalogu projektu).
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def main() -> None:
    parser = argparse.ArgumentParser(description="WisentPedigree Pro+")
    parser.add_argument("--ui", choices=["tk", "streamlit"], default="tk")
    args = parser.parse_args()

    if args.ui == "tk":
        from app.ui.tk.main import run_tk

        run_tk()
    else:
        # Streamlit jest uruchamiany jako osobny proces.
        # Ta ściezka jest tylko dla wygody uruchomienia.
        from app.ui.streamlit.streamlit_app import run_streamlit_direct

        run_streamlit_direct()


if __name__ == "__main__":
    main()

