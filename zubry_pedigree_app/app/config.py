"""
Domyślne ustawienia programu, np. gdzie szukać folderu z plikami danych.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    dataset_dir: Path

    default_max_inbreeding_depth: int = 20
    default_pci_max_generations: int = 4
    default_tree_generations: int = 4


def get_config() -> AppConfig:
    # Default to project's `data/` directory inside this repo.
    base_dir = Path(__file__).resolve().parents[2]
    return AppConfig(dataset_dir=base_dir / "data")

