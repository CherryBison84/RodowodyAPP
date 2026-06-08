"""Start aplikacji: GUI albo terminalowy DataCleaner."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Uruchamianie jako skrypt: `python zubry_pedigree_app/app/main.py`
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))


def main() -> None:
    """Punkt wejścia CLI: UI Streamlit lub tryb terminalowy."""
    parser = argparse.ArgumentParser(
        description="WisentPedigree DataCleaner - przygotowanie baz do analizy rodowodowej."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["gui", "cli"],
        default="gui",
        help="gui - interfejs Streamlit; cli - wersja terminalowa bez GUI.",
    )
    parser.add_argument(
        "--project-config",
        default="",
        help="Ścieżka do pliku JSON projektu DataCleaner (skrót dla trybu terminalowego).",
    )
    parser.add_argument(
        "--ui",
        choices=["web", "streamlit"],
        default="web",
        help="web — Streamlit + przeglądarka (domyślnie); streamlit — ten sam proces",
    )
    args, remaining = parser.parse_known_args()

    if str(args.project_config).strip():
        from app.cli import main as cli_main

        raise SystemExit(cli_main(["run", "--config", args.project_config]))

    if args.mode == "cli":
        from app.cli import main as cli_main

        raise SystemExit(cli_main(remaining))

    if args.ui == "web":
        from app.ui.web_launcher import run_streamlit_in_browser

        run_streamlit_in_browser()
    else:
        from app.ui.streamlit.streamlit_app import run_streamlit_direct

        run_streamlit_direct()


if __name__ == "__main__":
    main()
