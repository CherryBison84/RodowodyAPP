"""Wspólne ustawianie sys.path dla skryptów uruchomieniowych w katalogu projektu."""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_package_root_on_path() -> Path:
    """Dodaje katalog nadrzędny nad `app/` (np. `zubry_pedigree_app/`) na początek sys.path."""
    root = Path(__file__).resolve().parent.parent
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root
