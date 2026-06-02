"""Wczytanie i inspekcja błędów w bazie (bez transformacji wsadowej)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from app.data.validator import ValidationReport, validate_loaded_dataset
from app.huba.validation_utils import count_validation_issues
from app.pedigree.ancestor_pedigree import build_people_map

__all__ = [
    "InspectedDataset",
    "entry_kind_label",
    "inspect_dataframe",
    "inspect_dataset_from_bytes",
    "inspect_dataset_from_path",
]


def entry_kind_label(d: object) -> str:
    """Etykieta typu wpisu (działa też po podniesieniu starych obiektów z sesji Streamlit)."""
    merged = getattr(d, "merged_from", None)
    if merged:
        return "Połączenie"
    source = getattr(d, "source_label", "")
    if isinstance(source, str) and source.startswith("Połączenie:"):
        return "Połączenie"
    return "Plik"


def _merged_from_for(d: object) -> tuple[str, ...]:
    """Odczytuje listę baz źródłowych dla wpisu będącego połączeniem."""
    merged = getattr(d, "merged_from", None)
    if merged:
        return tuple(merged)
    source = getattr(d, "source_label", "")
    if isinstance(source, str) and source.startswith("Połączenie:"):
        body = source.replace("Połączenie:", "", 1).strip()
        if body:
            return tuple(part.strip() for part in body.split("+") if part.strip())
    return ()


@dataclass(frozen=True)
class InspectedDataset:
    """Wynik etapu „wczytaj + zwaliduj” dla jednego pliku lub połączenia."""

    name: str
    source_label: str
    df_std: pd.DataFrame
    validation_report: ValidationReport
    rows: int
    error_count: int
    warning_count: int
    merged_from: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status_label(self) -> str:
        if self.error_count:
            return f"Błędy ({self.error_count})"
        if self.warning_count:
            return f"Ostrzeżenia ({self.warning_count})"
        return "OK"

    @property
    def entry_kind(self) -> str:
        return entry_kind_label(self)


def inspect_dataframe(
    name: str,
    df_std: pd.DataFrame,
    source_label: str,
    *,
    merged_from: tuple[str, ...] = (),
) -> InspectedDataset:
    """Waliduje standaryzowaną ramkę i zwraca obiekt do katalogu w UI."""
    people = build_people_map(df_std)
    rep = validate_loaded_dataset(df_std=df_std, people=people)
    err, warn = count_validation_issues(rep)
    return InspectedDataset(
        name=name,
        source_label=source_label,
        df_std=df_std,
        validation_report=rep,
        rows=len(df_std),
        error_count=err,
        warning_count=warn,
        merged_from=merged_from,
    )


def inspect_dataset_from_bytes(name: str, data: bytes, filename: str) -> InspectedDataset:
    """Wczytuje plik z pamięci (upload UI), standaryzuje i waliduje."""
    from app.data.dataset_loader import load_dataset_from_bytes
    from app.data.ebpb_formats import ebpb_format_label

    df_std, info = load_dataset_from_bytes(data, filename)
    kind = getattr(info, "ebpb_format", "ebpb_report")
    source_label = f"{filename} ({ebpb_format_label(kind)})"
    return inspect_dataframe(name, df_std, source_label)


def inspect_dataset_from_path(name: str, path: str | Path) -> InspectedDataset:
    """Wczytuje plik z dysku (np. przykładowa baza z ``data/``)."""
    from app.data.dataset_loader import load_dataset_from_path
    from app.data.ebpb_formats import ebpb_format_label

    path = Path(path)
    df_std, info = load_dataset_from_path(path)
    kind = getattr(info, "ebpb_format", "ebpb_report")
    source_label = f"{path.name} ({ebpb_format_label(kind)})"
    return inspect_dataframe(name, df_std, source_label)
