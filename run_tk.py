"""
Zastąpione: aplikacja działa w przeglądarce (Streamlit).

Uruchomienie z katalogu RodowodyAPP:
  python run_streamlit.py
lub:
  python zubry_pedigree_app/run_web.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    pkg = Path(__file__).resolve().parent / "zubry_pedigree_app"
    if str(pkg) not in sys.path:
        sys.path.insert(0, str(pkg))
    from app.ui.web_launcher import run_streamlit_in_browser

    run_streamlit_in_browser()


if __name__ == "__main__":
    main()
