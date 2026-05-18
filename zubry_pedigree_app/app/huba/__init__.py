"""
HUBA — Hybrid Unified Batch Analyzer.

Jednolity silnik wsadowy: wiele plików wejściowych → uporządkowane katalogi wyjściowe
zgodnie z regułami walidacji, transformacji i eksportu.
"""

from app.huba.config_io import load_project_config
from app.huba.engine import run_project
from app.huba.models import HubProjectConfig, HubRunResult

__all__ = [
    "HubProjectConfig",
    "HubRunResult",
    "load_project_config",
    "run_project",
]
