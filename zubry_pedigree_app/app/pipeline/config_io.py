"""Kompatybilność wsteczna: konfiguracja projektu = format HUBA."""

from __future__ import annotations

from app.huba.config_io import load_project_config
from app.huba.models import HubProjectConfig

# Aliasy dla kodu importującego stare nazwy.
ProjectConfig = HubProjectConfig

__all__ = ["ProjectConfig", "load_project_config"]
