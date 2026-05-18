"""CLI HUBA: UI w przeglądarce lub tryb wsadowy z pliku JSON."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Uruchamianie jako skrypt: `python zubry_pedigree_app/app/main.py`
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def main() -> None:
    """Punkt wejścia CLI: UI Streamlit lub wsadowe uruchomienie z pliku JSON."""
    parser = argparse.ArgumentParser(
        description="HUBA-WPB Cleaner — Hybrid Unified Batch Analyzer + Wisent Pedigree Base"
    )
    parser.add_argument(
        "--project-config",
        default="",
        help="Ścieżka do pliku JSON projektu HUBA (tryb wsadowy, bez UI).",
    )
    parser.add_argument(
        "--ui",
        choices=["web", "streamlit"],
        default="web",
        help="web — Streamlit + przeglądarka (domyślnie); streamlit — ten sam proces",
    )
    args = parser.parse_args()

    if str(args.project_config).strip():
        from app.huba.config_io import load_project_config
        from app.huba.engine import run_project

        cfg = load_project_config(args.project_config)
        result = run_project(cfg)
        print(f"[OK] HUBA zakończony. Wyniki: {result.project_dir}")
        if result.comparison_path:
            print(f"     Porównanie: {result.comparison_path}")
        return

    if args.ui == "web":
        from app.ui.web_launcher import run_streamlit_in_browser

        run_streamlit_in_browser()
    else:
        from app.ui.streamlit.streamlit_app import run_streamlit_direct

        run_streamlit_direct()


if __name__ == "__main__":
    main()
