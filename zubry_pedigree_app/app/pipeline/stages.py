from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from app.analytics.population_genetics import compute_population_genetics_stats
from app.data.dataset_loader import load_dataset_from_path
from app.data.validator import validate_loaded_dataset
from app.pedigree.ancestor_pedigree import build_people_map
from app.pipeline.models import DatasetConfig, VariantConfig


@dataclass
class PipelineContext:
    dataset: DatasetConfig
    variant: VariantConfig
    run_dir: Path
    df_std: pd.DataFrame | None = None
    people: dict | None = None
    validation_summary: dict[str, int] | None = None
    metrics_row: dict[str, object] | None = None


def stage_load(ctx: PipelineContext) -> PipelineContext:
    df_std, _ = load_dataset_from_path(ctx.dataset.path)
    people = build_people_map(df_std)
    rep = validate_loaded_dataset(df_std=df_std, people=people)
    ctx.df_std = df_std
    ctx.people = people
    ctx.validation_summary = {
        "errors": sum(1 for i in rep.issues if i.severity == "ERROR"),
        "warnings": sum(1 for i in rep.issues if i.severity == "WARN"),
    }
    return ctx


def stage_analyze(ctx: PipelineContext) -> PipelineContext:
    if ctx.df_std is None or ctx.people is None:
        raise RuntimeError("stage_analyze wymaga danych z stage_load.")
    stats = compute_population_genetics_stats(
        df_std=ctx.df_std,
        people=ctx.people,  # type: ignore[arg-type]
        max_generations_back=ctx.variant.max_generations_back,
        calc_f=True,
        calc_completeness=ctx.variant.calc_completeness,
        calc_founders=ctx.variant.calc_founders,
        calc_lines=True,
    )
    errs = int((ctx.validation_summary or {}).get("errors", 0))
    warns = int((ctx.validation_summary or {}).get("warnings", 0))
    ctx.metrics_row = {
        "dataset": ctx.dataset.name,
        "variant": ctx.variant.name,
        "n": int(stats.n),
        "mean_F": float(stats.inbreeding.mean_F),
        "median_F": float(stats.inbreeding.median_F),
        "max_F": float(stats.inbreeding.max_F),
        "mean_EG": float(stats.completeness.mean_EG),
        "f_e": float(stats.founders.f_e),
        "f_a": float(stats.founders.f_a),
        "validation_errors": errs,
        "validation_warnings": warns,
        "max_generations_back": ctx.variant.max_generations_back if ctx.variant.max_generations_back is not None else "unbounded",
    }
    return ctx


def stage_report(ctx: PipelineContext) -> PipelineContext:
    if ctx.metrics_row is None:
        raise RuntimeError("stage_report wymaga danych z stage_analyze.")
    ctx.run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = ctx.run_dir / "summary.json"
    summary_path.write_text(json.dumps(ctx.metrics_row, ensure_ascii=False, indent=2), encoding="utf-8")

    if ctx.df_std is not None:
        (ctx.run_dir / "dataset_preview.csv").write_text(ctx.df_std.head(200).to_csv(index=False), encoding="utf-8")

    # Prosty wykres rozkładu roczników - szybka kontrola wejścia dla batch.
    if ctx.df_std is not None and "birth_year" in ctx.df_std.columns:
        yrs = pd.to_numeric(ctx.df_std["birth_year"], errors="coerce").dropna()
        if not yrs.empty:
            fig, ax = plt.subplots(figsize=(8.0, 4.2))
            ax.hist(yrs.tolist(), bins=24, color="#4f6f52", edgecolor="#1f3325")
            ax.set_title(f"Rozkład birth_year: {ctx.dataset.name}")
            ax.set_xlabel("birth_year")
            ax.set_ylabel("liczba rekordów")
            fig.tight_layout()
            fig.savefig(ctx.run_dir / "birth_year_hist.png", dpi=170)
            plt.close(fig)
    return ctx


STAGE_REGISTRY = {
    "load": stage_load,
    "analyze": stage_analyze,
    "report": stage_report,
}

