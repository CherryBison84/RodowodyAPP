"""Kontekst wykonania dla pojedynczego pliku wejściowego."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.data.validator import ValidationReport
from app.huba.models import InputSource, OutputSpec, ProcessingRules
from app.pedigree.ancestor_pedigree import Person


@dataclass
class DatasetContext:
    """
    Stan przetwarzania jednego wejścia w trakcie przebiegu etapów HUBA.

    Pola ``df_std``, ``people`` i ``validation_report`` są uzupełniane kolejno
    przez etapy ``load``, ``validate`` i ``transform``.
    """

    source: InputSource
    run_dir: Path
    rules: ProcessingRules
    output: OutputSpec
    source_label: str = ""
    df_std: pd.DataFrame | None = None
    people: dict[str, Person] | None = None
    initial_validation_report: ValidationReport | None = None
    validation_report: ValidationReport | None = None
    fix_log: list[str] = field(default_factory=list)
    artifacts: dict[str, Path] = field(default_factory=dict)
    input_sha256: str = ""
    input_size_bytes: int | None = None
    rows_in: int = 0
    rows_out: int = 0
