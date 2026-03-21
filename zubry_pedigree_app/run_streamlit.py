"""
Uruchamianie aplikacji Streamlit.

Zawsze używaj tego skryptu jako zwykłego Pythona (PyCharm „Run”):
    python run_streamlit.py

Wewnętrznie wywołuje: python -m streamlit run .../streamlit_app.py

Nie importuj tutaj modułów Streamlit — unikniesz ostrzeżeń „missing ScriptRunContext”.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    app = root / "app" / "ui" / "streamlit" / "streamlit_app.py"
    if not app.is_file():
        print(f"Nie znaleziono pliku aplikacji: {app}", file=sys.stderr)
        return 1
    return subprocess.call([sys.executable, "-m", "streamlit", "run", str(app)])


if __name__ == "__main__":
    raise SystemExit(main())
