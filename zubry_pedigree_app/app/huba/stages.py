"""Etapy przetwarzania pojedynczego wejścia (rejestr rozszerzalny)."""

from __future__ import annotations

import hashlib
from typing import Callable

import pandas as pd

from app.config import get_config
from app.data.auto_fix import apply_auto_fixes, default_year_max
from app.data.dataset_loader import (
    dataframe_app_schema_columns,
    load_dataset_from_bytes,
    load_dataset_from_path,
)
from app.data.validator import validate_loaded_dataset
from app.huba.context import DatasetContext
from app.huba import layout as out_layout
from app.pedigree.ancestor_pedigree import build_people_map


def _exclude_test_rows(df: pd.DataFrame, test_id: str) -> pd.DataFrame:
    """Usuwa wiersze testowe (domyślnie id=99999) przed eksportem."""
    if "id" not in df.columns or not test_id:
        return df
    try:
        return df[df["id"].astype(str) != str(test_id)].reset_index(drop=True)
    except Exception:
        return df[df["id"] != test_id].reset_index(drop=True)


def stage_load(
    ctx: DatasetContext,
    *,
    file_bytes: bytes | None = None,
    filename: str = "",
    df_preloaded: pd.DataFrame | None = None,
) -> DatasetContext:
    """
    Wczytuje dane z gotowej ramki, bajtów pliku lub ścieżki na dysku.

    Na końcu ogranicza kolumny do schematu aplikacji (``dataframe_app_schema_columns``).
    """
    if df_preloaded is not None:
        df_raw = df_preloaded.copy()
        ctx.source_label = ctx.source.name
        hashed = pd.util.hash_pandas_object(df_raw, index=True).values.tobytes()
        ctx.input_sha256 = hashlib.sha256(hashed).hexdigest()
        ctx.input_size_bytes = int(df_raw.memory_usage(index=True, deep=True).sum())
    elif file_bytes is not None and filename:
        df_raw, _info = load_dataset_from_bytes(file_bytes, filename)
        ctx.source_label = filename
        ctx.input_sha256 = hashlib.sha256(file_bytes).hexdigest()
        ctx.input_size_bytes = len(file_bytes)
    elif ctx.source.path is not None:
        df_raw, _info = load_dataset_from_path(ctx.source.path)
        ctx.source_label = str(ctx.source.path.name)
        digest = hashlib.sha256()
        with ctx.source.path.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        ctx.input_sha256 = digest.hexdigest()
        ctx.input_size_bytes = ctx.source.path.stat().st_size
    else:
        raise ValueError(f"Brak danych wejściowych dla „{ctx.source.name}”.")

    ctx.df_std = dataframe_app_schema_columns(df_raw)
    ctx.rows_in = len(ctx.df_std)
    ctx.rows_out = len(ctx.df_std)
    return ctx


def stage_validate(ctx: DatasetContext) -> DatasetContext:
    """Buduje mapę osobników i uruchamia walidator rodowodu."""
    if ctx.df_std is None:
        raise RuntimeError("stage_validate wymaga danych z etapu load.")
    people = build_people_map(ctx.df_std)
    ctx.people = people
    ctx.validation_report = validate_loaded_dataset(df_std=ctx.df_std, people=people)
    if ctx.initial_validation_report is None:
        ctx.initial_validation_report = ctx.validation_report
    return ctx


def stage_transform(ctx: DatasetContext) -> DatasetContext:
    """Auto-fix, opcjonalne wykluczenie rekordów testowych; ponowna walidacja."""
    if ctx.df_std is None:
        raise RuntimeError("stage_transform wymaga danych z etapu load.")
    df = ctx.df_std
    rules = ctx.rules
    cfg = get_config()

    if rules.apply_auto_fix:
        df, log = apply_auto_fixes(
            df,
            rules.auto_fix,
            year_min=int(cfg.validation_min_year),
            year_max=default_year_max(cfg),
            parent_min_age_at_birth=int(cfg.auto_fix_parent_min_age_at_birth),
            parent_max_age_at_birth=int(cfg.auto_fix_parent_max_age_at_birth),
        )
        ctx.fix_log = list(log)

    if rules.exclude_test_records:
        before = len(df)
        df = _exclude_test_rows(df, rules.test_record_id)
        dropped = before - len(df)
        if dropped:
            ctx.fix_log.append(
                f"Pominięto {dropped} rekord(ów) testowych (id={rules.test_record_id})."
            )

    ctx.df_std = df
    ctx.rows_out = len(df)
    if ctx.people is not None:
        ctx.people = build_people_map(df)
        ctx.validation_report = validate_loaded_dataset(df_std=df, people=ctx.people)
    return ctx


def stage_export(ctx: DatasetContext) -> DatasetContext:
    """Zapisuje oczyszczoną bazę, raport walidacji i log auto-fix do ``run_dir``."""
    if ctx.df_std is None:
        raise RuntimeError("stage_export wymaga ramki danych.")
    run_dir = ctx.run_dir
    out = ctx.output
    cleaned = out_layout.write_cleaned(ctx.df_std, run_dir, out)
    ctx.artifacts["Oczyszczona baza"] = cleaned
    if ctx.validation_report is not None:
        issues = out_layout.write_validation_issues(ctx.validation_report, run_dir, out)
        if issues is not None:
            ctx.artifacts["Problemy walidacji"] = issues
        summary = out_layout.write_validation_summary(ctx, run_dir, out)
        if summary is not None:
            ctx.artifacts["Podsumowanie walidacji"] = summary
    fix_log = out_layout.write_fix_log(ctx, run_dir, out)
    if fix_log is not None:
        ctx.artifacts["Log auto-poprawek"] = fix_log
    return ctx


StageFn = Callable[[DatasetContext], DatasetContext]

STAGE_REGISTRY: dict[str, StageFn] = {
    "load": stage_load,
    "validate": stage_validate,
    "transform": stage_transform,
    "export": stage_export,
}


def run_stages(
    ctx: DatasetContext,
    stage_names: tuple[str, ...],
    *,
    file_bytes: bytes | None = None,
    filename: str = "",
    df_preloaded: pd.DataFrame | None = None,
) -> DatasetContext:
    """
    Wykonuje etapy w podanej kolejności.

    Etap ``load`` przyjmuje opcjonalne ``file_bytes`` / ``df_preloaded`` (pozostałe etapy — nie).
    """
    for name in stage_names:
        fn = STAGE_REGISTRY.get(name)
        if fn is None:
            raise ValueError(f"Nieznany etap HUBA: {name}")
        if name == "load":
            ctx = stage_load(
                ctx,
                file_bytes=file_bytes,
                filename=filename,
                df_preloaded=df_preloaded,
            )
        else:
            ctx = fn(ctx)
    return ctx
