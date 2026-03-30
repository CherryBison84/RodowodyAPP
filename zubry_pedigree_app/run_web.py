"""Start UI w przeglądarce (Streamlit): wybór portu, otwarcie przeglądarki."""

from __future__ import annotations

from app.runtime_path import ensure_package_root_on_path

ensure_package_root_on_path()

from app.ui.web_launcher import run_streamlit_in_browser

if __name__ == "__main__":
    run_streamlit_in_browser()
