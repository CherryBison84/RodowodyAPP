"""
Domyślne ustawienia programu, np. gdzie szukać folderu z plikami danych.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


@dataclass(frozen=True)
class AppConfig:
    dataset_dir: Path

    default_max_inbreeding_depth: int = 20
    default_pci_max_generations: int = 4
    default_tree_generations: int = 4

    # Mating / ranking defaults (Tk + Streamlit)
    mating_age_limit_years: int = 15
    mating_ranking_top_n: int = 36
    mating_default_male_limit: int = 200
    mating_default_female_limit: int = 200

    # Plot/report defaults
    f_ria_smooth_window: int = 7
    gi_smooth_window: int = 3
    report_founders_top_n: int = 20
    report_birth_location_top_n: int = 12


def get_config() -> AppConfig:
    # Default to project's `data/` directory inside this repo.
    base_dir = Path(__file__).resolve().parents[2]
    return AppConfig(dataset_dir=base_dir / "data")


def resolve_app_icon_ico() -> Path | None:
    """
    Ikona okna / favicon: `ikona.ico` w `app/`, w `zubry_pedigree_app/` lub w katalogu
    nadrzędnym repozytorium (np. folder projektu obok `zubry_pedigree_app/`).
    """
    app_dir = Path(__file__).resolve().parent
    for base in (app_dir, app_dir.parent, app_dir.parent.parent):
        p = base / "ikona.ico"
        if p.is_file():
            return p
    return None


def _ico_largest_frame_rgba(im: "PILImage") -> "PILImage":
    """Z wieloklatkowego ICO wybiera największą bitmapę (czytelna ikona w Tk / Streamlit)."""
    from PIL import Image

    frames: list[Image.Image] = []
    n = int(getattr(im, "n_frames", 1) or 1)
    try:
        for i in range(n):
            im.seek(i)
            frames.append(im.copy())
    except EOFError:
        pass
    if not frames:
        return im.convert("RGBA")
    best = max(frames, key=lambda x: x.size[0] * x.size[1])
    return best.convert("RGBA")


def app_icon_pil_best() -> "PILImage | None":
    """
    Ikona jako obraz PIL (najlepsza klatka `ikona.ico`).
    Używane przez Streamlit (`page_icon`) i Tk (`iconphoto`).
    """
    try:
        from PIL import Image
    except ImportError:
        return None
    path = resolve_app_icon_ico()
    if path is None:
        return None
    try:
        return _ico_largest_frame_rgba(Image.open(path))
    except Exception:
        return None

