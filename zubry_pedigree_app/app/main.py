"""CLI: domyślnie Qt (na macOS + Python 3.14 — fallback do Streamlit w przeglądarce)."""

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
    parser = argparse.ArgumentParser(description="WisentPedigree Pro+ — analiza rodowodów żubrów")
    parser.add_argument(
        "--ui",
        choices=["qt", "tk", "streamlit", "web"],
        default="qt",
        help="qt — PySide6 (Mac+3.14→ Streamlit w przeglądarce); web — jak wyżej jawnie; tk; streamlit — ten sam skrypt w tym procesie",
    )
    args = parser.parse_args()

    if args.ui == "qt":
        from app.ui.qt.main import run_qt

        run_qt()
    elif args.ui == "web":
        from app.ui.web_launcher import run_streamlit_in_browser

        run_streamlit_in_browser()
    elif args.ui == "tk":
        from app.ui.tk.main import run_tk

        run_tk()
    else:
        # Streamlit jest uruchamiany jako osobny proces.
        # Ta ścieżka jest tylko dla wygody uruchomienia.
        from app.ui.streamlit.streamlit_app import run_streamlit_direct

        run_streamlit_direct()


if __name__ == "__main__":
    main()

