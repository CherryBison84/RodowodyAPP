"""Łączenie wielu standaryzowanych ramek w jedną bazę (HUBA)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from app.data.dataset_loader import dataframe_app_schema_columns

DuplicateIdPolicy = Literal["keep_first", "keep_last", "keep_all"]


@dataclass(frozen=True)
class MergeResult:
    """Wynik operacji łączenia (przed walidacją)."""

    df_std: pd.DataFrame
    log: tuple[str, ...]
    source_names: tuple[str, ...]
    rows_per_source: tuple[int, ...]
    rows_before_dedupe: int
    rows_after_dedupe: int
    duplicate_rows_removed: int


def merge_standardized_frames(
    parts: list[tuple[str, pd.DataFrame]],
    *,
    on_duplicate_id: DuplicateIdPolicy = "keep_first",
) -> MergeResult:
    """
    Łączy ramki w jedną (kolejność ``parts``).

    Przy ``keep_first`` / ``keep_last`` usuwa powtórzone ``id`` (pierwszy / ostatni wiersz w kolejności plików).
    Przy ``keep_all`` pozostawia wszystkie wiersze — duplikaty wykryje walidacja.
    """
    if len(parts) < 2:
        raise ValueError("Łączenie wymaga co najmniej dwóch baz.")

    log: list[str] = []
    frames: list[pd.DataFrame] = []
    source_names: list[str] = []
    rows_per_source: list[int] = []

    for name, df in parts:
        clean = dataframe_app_schema_columns(df)
        frames.append(clean)
        source_names.append(name)
        n = len(clean)
        rows_per_source.append(n)
        log.append(f"• {name}: {n} wierszy")

    combined = pd.concat(frames, ignore_index=True)
    rows_before = len(combined)
    removed = 0

    if on_duplicate_id != "keep_all" and "id" in combined.columns and not combined.empty:
        keep = "first" if on_duplicate_id == "keep_first" else "last"
        before = len(combined)
        combined = combined.drop_duplicates(subset=["id"], keep=keep).reset_index(drop=True)
        removed = before - len(combined)
        if removed:
            policy_pl = "pierwszy wiersz" if on_duplicate_id == "keep_first" else "ostatni wiersz"
            log.append(
                f"Duplikaty `id`: usunięto {removed} wierszy "
                f"(zostawiono {policy_pl} wg kolejności plików)."
            )

    log.append(f"Razem: {len(combined)} wierszy (przed deduplikacją: {rows_before}).")

    return MergeResult(
        df_std=combined,
        log=tuple(log),
        source_names=tuple(source_names),
        rows_per_source=tuple(rows_per_source),
        rows_before_dedupe=rows_before,
        rows_after_dedupe=len(combined),
        duplicate_rows_removed=removed,
    )
