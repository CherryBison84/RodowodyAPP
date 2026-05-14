from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VariantConfig:
    name: str
    max_generations_back: int | None
    calc_founders: bool = True
    calc_completeness: bool = True


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    path: Path


@dataclass(frozen=True)
class ProjectConfig:
    project_name: str
    output_dir: Path
    stages: tuple[str, ...]
    datasets: tuple[DatasetConfig, ...]
    variants: tuple[VariantConfig, ...]

