"""Kompatybilność CLI: delegacja do silnika HUBA."""

from __future__ import annotations

from pathlib import Path

from app.huba.config_io import load_project_config
from app.huba.engine import run_project as run_huba_project


def run_project(project_config_path: str | Path) -> Path:
    """
    Uruchamia projekt wsadowy z pliku JSON (stary interfejs ``pipeline``).

    Zwraca katalog główny wyników projektu.
    """
    cfg = load_project_config(project_config_path)
    result = run_huba_project(cfg)
    return result.project_dir
