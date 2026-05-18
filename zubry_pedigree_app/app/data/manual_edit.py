"""Ręczna korekta pól w ``df_std`` (pojedynczy rekord, walidacja przed zapisem)."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from app.data.dataset_loader import STANDARD_BISON_REPORT_COLUMNS, dataframe_app_schema_columns
from app.data.validator import id_cell_string, parse_year_field

__all__ = [
    "FieldPatch",
    "PROBLEM_TYPE_FIELD_HINTS",
    "apply_field_patch",
    "apply_record_patches",
    "editable_columns",
    "find_row_indices",
    "normalize_field_value",
    "parse_cycle_nodes_from_details",
    "suggest_fields_for_problem",
    "validate_patch",
]

_EMPTY_MARKERS: Final[frozenset[str]] = frozenset({"", "—", "(puste)", "nan", "none"})

PROBLEM_TYPE_FIELD_HINTS: Final[dict[str, tuple[str, ...]]] = {
    "Duplikat ID": ("id",),
    "Pusty lub niepoprawny identyfikator": ("id",),
    "Niepoprawna płeć (sex)": ("sex",),
    "Brak birth_year": ("birth_year",),
    "birth_year poza zakresem": ("birth_year",),
    "Brak rekordu ojca w bazie": ("father_id",),
    "Brak rekordu matki w bazie": ("mother_id",),
    "Self-parent (ojciec)": ("father_id",),
    "Self-parent (matka)": ("mother_id",),
    "Ten sam ID jako ojciec i matka": ("father_id", "mother_id"),
    "Ojciec ma płeć F w rekordzie osobnika": ("father_id", "mother_id", "sex"),
    "Matka ma płeć M w rekordzie osobnika": ("father_id", "mother_id", "sex"),
    "Wiek ojca przy urodzeniu potomka poza 0–80 lat": ("birth_year", "father_id"),
    "Wiek matki przy urodzeniu potomka poza 0–80 lat": ("birth_year", "mother_id"),
    "Daty: podejrzenie śmierci przed urodzeniem": ("birth_date", "death_date", "birth_year"),
    "Cykl w rodowodzie": ("father_id", "mother_id"),
    "Niespójność father_line z linią ojca w bazie": ("father_line", "father_id"),
    "Niespójność mother_line z linią matki w bazie": ("mother_line", "mother_id"),
}

_DEFAULT_EDIT_FIELDS: Final[tuple[str, ...]] = (
    "id",
    "name",
    "sex",
    "birth_year",
    "father_id",
    "mother_id",
    "father_line",
    "mother_line",
    "birth_date",
    "death_date",
)


@dataclass(frozen=True)
class FieldPatch:
    record_id: str
    column: str
    new_value: object
    row_index: Optional[int] = None


def suggest_fields_for_problem(problem_type: str) -> tuple[str, ...]:
    return PROBLEM_TYPE_FIELD_HINTS.get(problem_type, _DEFAULT_EDIT_FIELDS)


def editable_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in STANDARD_BISON_REPORT_COLUMNS if c in df.columns]


def find_row_indices(df: pd.DataFrame, record_id: str) -> list[Any]:
    rid = str(record_id).strip()
    if not rid or rid == "_GLOBAL_":
        return []
    if "id" not in df.columns:
        return []
    mask = df["id"].map(lambda v: id_cell_string(v) == rid)
    return list(df.index[mask])


def _norm_sex(v: object) -> Optional[str]:
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip().upper()
    return s if s in {"M", "F"} else None


def _norm_line(v: object) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return "NA"
    s = str(v).strip().upper()
    return s if s in {"LB", "LC"} else "NA"


def normalize_field_value(column: str, value: object) -> object:
    """Wartość do zapisu w komórce (None / pd.NA = wyczyść)."""
    if value is None:
        return pd.NA
    if isinstance(value, float) and np.isnan(value):
        return pd.NA
    if isinstance(value, str):
        s = value.strip()
        if s.lower() in _EMPTY_MARKERS:
            return pd.NA

    if column == "sex":
        return _norm_sex(value)
    if column == "birth_year":
        if value == "" or value is pd.NA:
            return pd.NA
        y = parse_year_field(value)
        return y if y is not None else pd.NA
    if column in {"father_line", "mother_line", "line"}:
        return _norm_line(value)
    if column in {"id", "father_id", "mother_id"}:
        s = id_cell_string(value)
        return s if s else pd.NA
    if isinstance(value, str):
        return value.strip() if value.strip() else pd.NA
    return value


def validate_patch(
    df: pd.DataFrame,
    patch: FieldPatch,
    *,
    year_min: int = 1800,
    year_max: int | None = None,
) -> list[str]:
    """Ostrzeżenia (nie blokują zapisu) przed zastosowaniem patcha."""
    notes: list[str] = []
    col = patch.column
    if col not in editable_columns(df):
        notes.append(f"Kolumna `{col}` nie jest w schemacie aplikacji.")
        return notes

    val = normalize_field_value(col, patch.new_value)
    if col == "sex":
        raw = patch.new_value
        if raw is not None and not (isinstance(raw, float) and np.isnan(raw)):
            s = str(raw).strip()
            if s.lower() not in _EMPTY_MARKERS and _norm_sex(raw) is None:
                notes.append("Płeć: dozwolone M, F lub puste.")

    if col == "birth_year" and val is not pd.NA and val is not None:
        try:
            y = int(val)
        except (TypeError, ValueError):
            notes.append("Rok urodzenia musi być liczbą całkowitą.")
        else:
            ymax = year_max if year_max is not None else datetime.now().year + 2
            if y < year_min or y > ymax:
                notes.append(f"Rok {y} poza zakresem {year_min}–{ymax} (walidacja po zapisie też to zgłosi).")

    if col in {"father_id", "mother_id"} and val is not pd.NA and val is not None:
        pid = id_cell_string(val)
        if pid and "id" in df.columns:
            known = {id_cell_string(x) for x in df["id"] if id_cell_string(x)}
            if pid not in known:
                notes.append(f"ID `{pid}` nie występuje jeszcze w kolumnie `id` (ostrzeżenie walidacji).")

    indices = find_row_indices(df, patch.record_id)
    if len(indices) > 1 and patch.row_index is None:
        notes.append(f"W bazie jest {len(indices)} wierszy z tym samym `id` — wybierz wiersz.")

    return notes


def apply_field_patch(
    df_in: pd.DataFrame,
    patch: FieldPatch,
) -> tuple[pd.DataFrame, list[str]]:
    """Zwraca nową ramkę i komunikaty (błędy blokujące zapis)."""
    messages: list[str] = []
    df = df_in.copy()
    indices = find_row_indices(df, patch.record_id)
    if not indices:
        return df_in, [f"Nie znaleziono rekordu o id={patch.record_id!r}."]

    if len(indices) > 1:
        if patch.row_index is None:
            return df_in, [
                f"Duplikat id={patch.record_id!r}: {len(indices)} wierszy — wskaż numer wiersza w formularzu."
            ]
        if patch.row_index not in indices:
            return df_in, [f"Indeks wiersza {patch.row_index} nie pasuje do id={patch.record_id!r}."]
        idx = patch.row_index
    else:
        idx = indices[0]

    if patch.column not in df.columns:
        return df_in, [f"Brak kolumny `{patch.column}` w bazie."]

    new_val = normalize_field_value(patch.column, patch.new_value)
    old_val = df.at[idx, patch.column]
    df.at[idx, patch.column] = new_val
    messages.append(
        f"`{patch.column}`: {old_val!r} → {new_val!r} (wiersz {idx}, id={patch.record_id})"
    )
    return dataframe_app_schema_columns(df), messages


def apply_record_patches(
    df_in: pd.DataFrame,
    record_id: str,
    fields: dict[str, object],
    *,
    row_index: int | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """Atomowy zapis wielu pól jednego rekordu (jeden wiersz przy duplikacie id)."""
    indices = find_row_indices(df_in, record_id)
    if not indices:
        return df_in, [f"Nie znaleziono rekordu o id={record_id!r}."]
    if len(indices) > 1 and row_index is None:
        return df_in, [
            f"Duplikat id={record_id!r}: {len(indices)} wierszy — wskaż numer wiersza w formularzu."
        ]
    idx = row_index if row_index is not None and row_index in indices else indices[0]

    df = df_in.copy()
    messages: list[str] = []
    for col, val in fields.items():
        if col not in df.columns:
            return df_in, [f"Brak kolumny `{col}` w bazie."]
        new_val = normalize_field_value(col, val)
        old_val = df.at[idx, col]
        df.at[idx, col] = new_val
        messages.append(f"`{col}`: {old_val!r} → {new_val!r} (wiersz {idx})")
    return dataframe_app_schema_columns(df), messages


def parse_cycle_nodes_from_details(details: str) -> list[str]:
    """Wyciąga przykładowe ID węzłów z opisu problemu cyklu."""
    if not details:
        return []
    m = re.search(r"\[[^\]]+\]", details)
    if m:
        try:
            parsed = ast.literal_eval(m.group(0))
            if isinstance(parsed, (list, tuple)):
                return [id_cell_string(x) for x in parsed if id_cell_string(x)]
        except (SyntaxError, ValueError):
            pass
    return [id_cell_string(x) for x in re.findall(r"\b\d+[A-Za-z]*\b", details) if id_cell_string(x)]
