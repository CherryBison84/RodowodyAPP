"""CLI: domyślnie Streamlit w przeglądarce."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Uruchamianie jako skrypt: `python zubry_pedigree_app/app/main.py`
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def main() -> None:
    parser = argparse.ArgumentParser(description="WisentPedigree Pro+ — analiza rodowodów żubrów")
    parser.add_argument(
        "--ui",
        choices=["web", "streamlit"],
        default="web",
        help="web — Streamlit + otwarcie przeglądarki (domyślnie); streamlit — `run_streamlit_direct` w tym procesie",
    )
    args = parser.parse_args()

    if args.ui == "web":
        from app.ui.web_launcher import run_streamlit_in_browser

        run_streamlit_in_browser()
    else:
        from app.ui.streamlit.streamlit_app import run_streamlit_direct

        run_streamlit_direct()


if __name__ == "__main__":
    main()
