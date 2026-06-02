"""Konfiguracja: katalog danych, limity obliczeń i opcjonalny plik GUI JSON."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


@dataclass(frozen=True)
class AppConfig:
    """Niezmienne ustawienia wczytywane przy starcie (ścieżki, progi, okna wygładzania)."""

    dataset_dir: Path

    default_max_inbreeding_depth: int = 20
    default_pci_max_generations: int = 4
    default_tree_generations: int = 4

    # Mating / ranking defaults
    mating_age_limit_years: int = 15
    mating_ranking_top_n: int = 36
    mating_default_male_limit: int = 200
    mating_default_female_limit: int = 200

    # Plot/report defaults
    f_ria_smooth_window: int = 7
    gi_smooth_window: int = 3
    report_founders_top_n: int = 20
    report_birth_location_top_n: int = 12

    # Automatyczne poprawki (progi z config/gui.json)
    validation_min_year: int = 1800
    validation_max_year_buffer: int = 2
    auto_fix_parent_min_age_at_birth: int = 12
    auto_fix_parent_max_age_at_birth: int = 80


def _config_root_dir() -> Path:
    """Zwraca katalog paczki używany jako baza dla plików konfiguracyjnych."""
    return Path(__file__).resolve().parents[1]


def _repo_root_dir() -> Path:
    """Zwraca katalog główny repozytorium z danymi i konfiguracją."""
    return Path(__file__).resolve().parents[2]


def _gui_config_path() -> Path:
    """Zwraca ścieżkę do opcjonalnego pliku ``config/gui.json``."""
    return _config_root_dir() / "config" / "gui.json"


def _load_gui_overrides() -> dict[str, object]:
    """Wczytuje nadpisania konfiguracji GUI, ignorując brak lub błędny plik."""
    path = _gui_config_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    return raw


def get_config() -> AppConfig:
    """Zwraca konfigurację aplikacji, z opcjonalnymi nadpisaniami z `config/gui.json`."""
    defaults = AppConfig(dataset_dir=_repo_root_dir() / "data")
    overrides = _load_gui_overrides()
    if not overrides:
        return defaults

    dataset_dir = overrides.get("dataset_dir")
    if isinstance(dataset_dir, str) and dataset_dir.strip():
        ds = Path(dataset_dir.strip())
        if not ds.is_absolute():
            ds = _repo_root_dir() / ds
    else:
        ds = defaults.dataset_dir

    def _int_or(default_val: int, key: str) -> int:
        v = overrides.get(key, default_val)
        try:
            return int(v)
        except Exception:
            return int(default_val)

    return AppConfig(
        dataset_dir=ds,
        default_max_inbreeding_depth=_int_or(defaults.default_max_inbreeding_depth, "default_max_inbreeding_depth"),
        default_pci_max_generations=_int_or(defaults.default_pci_max_generations, "default_pci_max_generations"),
        default_tree_generations=_int_or(defaults.default_tree_generations, "default_tree_generations"),
        mating_age_limit_years=_int_or(defaults.mating_age_limit_years, "mating_age_limit_years"),
        mating_ranking_top_n=_int_or(defaults.mating_ranking_top_n, "mating_ranking_top_n"),
        mating_default_male_limit=_int_or(defaults.mating_default_male_limit, "mating_default_male_limit"),
        mating_default_female_limit=_int_or(defaults.mating_default_female_limit, "mating_default_female_limit"),
        f_ria_smooth_window=_int_or(defaults.f_ria_smooth_window, "f_ria_smooth_window"),
        gi_smooth_window=_int_or(defaults.gi_smooth_window, "gi_smooth_window"),
        report_founders_top_n=_int_or(defaults.report_founders_top_n, "report_founders_top_n"),
        report_birth_location_top_n=_int_or(defaults.report_birth_location_top_n, "report_birth_location_top_n"),
        validation_min_year=_int_or(defaults.validation_min_year, "validation_min_year"),
        validation_max_year_buffer=_int_or(defaults.validation_max_year_buffer, "validation_max_year_buffer"),
        auto_fix_parent_min_age_at_birth=_int_or(
            defaults.auto_fix_parent_min_age_at_birth, "auto_fix_parent_min_age_at_birth"
        ),
        auto_fix_parent_max_age_at_birth=_int_or(
            defaults.auto_fix_parent_max_age_at_birth, "auto_fix_parent_max_age_at_birth"
        ),
    )


def resolve_app_icon_ico() -> Path | None:
    """Szuka pliku `ikona.ico` w ``app/assets/`` lub starszych lokalizacjach."""
    from app.runtime_path import app_package_dir, assets_dir

    app_dir = app_package_dir()
    for base in (assets_dir(), app_dir, app_dir.parent, app_dir.parent.parent):
        p = base / "ikona.ico"
        if p.is_file():
            return p
    return None


def _ico_largest_frame_rgba(im: "PILImage") -> "PILImage":
    """Z wieloklatkowego ICO wybiera największą bitmapę (czytelna ikona)."""
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
    """Największa klatka z `ikona.ico` jako obraz PIL (np. favicon Streamlit)."""
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
