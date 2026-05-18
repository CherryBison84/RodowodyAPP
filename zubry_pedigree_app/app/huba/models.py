"""Modele konfiguracji i wyników uruchomienia HUBA."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Tuple

from app.data.auto_fix import AutoFixOptions

StageName = Literal["load", "validate", "transform", "export"]
ExportFormat = Literal["csv", "xlsx"]


@dataclass(frozen=True)
class InputSource:
    """Jeden plik wejściowy w projekcie wsadowym."""

    name: str
    path: Path | None = None  # ścieżka na dysku (CLI / JSON); None przy uploadzie z UI

    @property
    def safe_name(self) -> str:
        """Nazwa bezpieczna dla systemu plików (znaki specjalne → ``_``)."""
        raw = (self.name or "dataset").strip()
        return "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in raw) or "dataset"


@dataclass(frozen=True)
class OutputSpec:
    """Struktura katalogów i nazewnictwo plików wynikowych."""

    datasets_subdir: str = "datasets"
    cleaned_basename: str = "cleaned"
    issues_basename: str = "validation_issues"
    summary_basename: str = "validation_summary"
    fix_log_basename: str = "auto_fix_log"
    export_format: ExportFormat = "xlsx"
    write_validation_issues: bool = True
    write_summary: bool = True
    write_fix_log: bool = True
    csv_delimiter: str = ";"


@dataclass(frozen=True)
class ProcessingRules:
    """Reguły transformacji po walidacji."""

    apply_auto_fix: bool = True
    auto_fix: AutoFixOptions = field(default_factory=AutoFixOptions)
    exclude_test_records: bool = True
    test_record_id: str = "99999"


@dataclass(frozen=True)
class HubProjectConfig:
    """Pełna konfiguracja jednego uruchomienia wsadowego."""

    project_name: str
    output_dir: Path
    stages: Tuple[StageName, ...] = ("load", "validate", "transform", "export")
    inputs: Tuple[InputSource, ...] = ()
    rules: ProcessingRules = field(default_factory=ProcessingRules)
    output: OutputSpec = field(default_factory=OutputSpec)


@dataclass(frozen=True)
class DatasetRunResult:
    """Wynik przetworzenia pojedynczego wejścia."""

    input_name: str
    run_dir: Path
    rows_in: int
    rows_out: int
    validation_errors: int
    validation_warnings: int
    fix_steps: int
    status: str  # ok | warn | error | skipped


@dataclass(frozen=True)
class HubRunResult:
    """Manifest całego uruchomienia."""

    project_dir: Path
    manifest_path: Path
    comparison_path: Path | None
    datasets: Tuple[DatasetRunResult, ...]
