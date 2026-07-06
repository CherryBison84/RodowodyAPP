"""Wspólne ustawianie sys.path dla skryptów uruchomieniowych w katalogu projektu."""

from __future__ import annotations

import sys
from pathlib import Path


def project_root() -> Path:
    """Katalog ``zubry_pedigree_app/`` (nad pakietem ``app``)."""
    return Path(__file__).resolve().parent.parent


def app_package_dir() -> Path:
    """Katalog pakietu ``app/``."""
    return Path(__file__).resolve().parent


def assets_dir() -> Path:
    """Statyczne zasoby UI, np. logo, ikona i grafiki pomocnicze."""
    return app_package_dir() / "assets"


def data_dir() -> Path:
    """Przykładowe bazy i pliki wejściowe projektu."""
    return project_root() / "data"


EBPB_SAMPLE_FILENAMES: tuple[str, ...] = (
    "EBPB_bison_report.xlsx",
    "EBPB_register.xlsx",
)


def list_ebpb_sample_paths() -> list[Path]:
    """Przykładowe bazy EBPB z ``data/`` (raport i rejestr), jeśli pliki istnieją."""
    root = data_dir()
    return [root / name for name in EBPB_SAMPLE_FILENAMES if (root / name).is_file()]


def ensure_package_root_on_path() -> Path:
    """Dodaje katalog nadrzędny nad `app/` (np. `zubry_pedigree_app/`) na początek sys.path."""
    root = project_root()
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root
