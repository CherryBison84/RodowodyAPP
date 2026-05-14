from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.pipeline.models import ProjectConfig
from app.pipeline.stages import PipelineContext, STAGE_REGISTRY


def _safe_name(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in s.strip()) or "run"


def run_project(project: ProjectConfig) -> Path:
    project_out = project.output_dir / _safe_name(project.project_name)
    project_out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, object]] = []
    for ds in project.datasets:
        for var in project.variants:
            run_dir = project_out / _safe_name(ds.name) / _safe_name(var.name)
            ctx = PipelineContext(dataset=ds, variant=var, run_dir=run_dir)
            for stage_name in project.stages:
                stage = STAGE_REGISTRY.get(stage_name)
                if stage is None:
                    raise ValueError(f"Nieznany etap pipeline: {stage_name}")
                ctx = stage(ctx)
            if ctx.metrics_row is not None:
                rows.append(ctx.metrics_row)

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(project_out / "comparison.csv", index=False)
    return project_out

