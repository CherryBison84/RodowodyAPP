"""Modele konfiguracji pipeline analitycznego (porównanie wariantów metryk)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VariantConfig:
    """Jeden wariant obliczeń (np. głębokość rodowodu, zestaw metryk)."""

    name: str
    max_generations_back: int | None
    calc_founders: bool = True
    calc_completeness: bool = True


@dataclass(frozen=True)
class DatasetConfig:
    """Pojedyncza baza wejściowa w projekcie analitycznym."""

    name: str
    path: Path


@dataclass(frozen=True)
class ProjectConfig:
    """Konfiguracja uruchomienia porównawczego (wiele zbiorów × wariantów)."""

    project_name: str
    output_dir: Path
    stages: tuple[str, ...]
    datasets: tuple[DatasetConfig, ...]
    variants: tuple[VariantConfig, ...]
