"""Uruchomienie UI w przeglądarce (Streamlit): wolny port, start serwera, otwarcie domyślnej przeglądarki."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


def _pkg_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _pick_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = int(s.getsockname()[1])
    s.close()
    return port


def _wait_for_http(url: str, *, attempts: int = 40, delay_s: float = 0.25) -> bool:
    for _ in range(attempts):
        try:
            urllib.request.urlopen(url, timeout=1.0)
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(delay_s)
    return False


def run_streamlit_in_browser() -> None:
    """
    Startuje `streamlit run` na wolnym porcie i otwiera domyślną przeglądarkę.
    Zamknięcie terminala (Ctrl+C) kończy serwer.
    """
    root = _pkg_root()
    script = root / "app" / "ui" / "streamlit" / "streamlit_app.py"
    if not script.is_file():
        print(f"Brak pliku Streamlit: {script}", file=sys.stderr)
        raise SystemExit(1)

    port = _pick_port()
    url = f"http://127.0.0.1:{port}"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script),
        "--server.port",
        str(port),
        "--server.address",
        "127.0.0.1",
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]
    proc = subprocess.Popen(cmd, cwd=str(root))
    try:
        if not _wait_for_http(url):
            print("Streamlit nie odpowiada — sprawdź konsolę.", file=sys.stderr)
        webbrowser.open(url)
        code = proc.wait()
        raise SystemExit(code)
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        raise SystemExit(0) from None
