"""Orkiestracja uruchomień wsadowych HUBA."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from app.huba.context import DatasetContext
from app.huba import layout as out_layout
from app.huba.models import DatasetRunResult, HubProjectConfig, HubRunResult, InputSource
from app.huba.stages import run_stages
from app.huba.validation_utils import count_validation_issues, dataset_status_from_report


def _safe_dir_name(s: str) -> str:
    """Bezpieczna nazwa podkatalogu projektu (tylko znaki alfanumeryczne, -, _)."""
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in s.strip()) or "run"


def _result_row(ctx: DatasetContext) -> dict[str, object]:
    """Jeden wiersz pliku ``comparison.csv`` dla danego wejścia."""
    n_err, n_warn = count_validation_issues(ctx.validation_report)
    return {
        "input_name": ctx.source.name,
        "source": ctx.source_label,
        "rows_in": ctx.rows_in,
        "rows_out": ctx.rows_out,
        "validation_errors": n_err,
        "validation_warnings": n_warn,
        "fix_steps": len(ctx.fix_log),
        "status": dataset_status_from_report(ctx.validation_report),
        "run_dir": str(ctx.run_dir.name),
    }


def run_project(
    project: HubProjectConfig,
    *,
    upload_payloads: dict[str, tuple[bytes, str]] | None = None,
    upload_dataframes: dict[str, pd.DataFrame] | None = None,
) -> HubRunResult:
    """
    Uruchamia projekt wsadowy.

    ``upload_payloads`` mapuje ``InputSource.name`` → (bytes, filename) dla wejść z UI
    (gdy ``path`` w konfiguracji jest puste).

    ``upload_dataframes`` — już znormalizowane ramki z katalogu UI (bez ponownego mapowania kolumn).
    Ma pierwszeństwo przed ``upload_payloads`` dla tego samego klucza.
    """
    if not project.inputs:
        raise ValueError("Projekt HUBA wymaga co najmniej jednego wejścia (`inputs`).")

    project_dir = project.output_dir / _safe_dir_name(project.project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    payloads = upload_payloads or {}
    dataframes = upload_dataframes or {}
    results: list[DatasetRunResult] = []
    comparison_rows: list[dict[str, object]] = []

    for src in project.inputs:
        run_dir = out_layout.dataset_run_dir(project_dir, project.output, src.safe_name)
        ctx = DatasetContext(
            source=src,
            run_dir=run_dir,
            rules=project.rules,
            output=project.output,
        )
        file_bytes: bytes | None = None
        filename = ""
        df_preloaded: pd.DataFrame | None = None
        if src.name in dataframes:
            df_preloaded = dataframes[src.name]
        elif src.name in payloads:
            file_bytes, filename = payloads[src.name]
        elif src.path is None:
            raise ValueError(
                f"Wejście „{src.name}” nie ma ścieżki ani danych przesłanych z UI."
            )

        ctx = run_stages(
            ctx,
            project.stages,
            file_bytes=file_bytes,
            filename=filename,
            df_preloaded=df_preloaded,
        )
        row = _result_row(ctx)
        n_err = int(row["validation_errors"])
        n_warn = int(row["validation_warnings"])

        results.append(
            DatasetRunResult(
                input_name=src.name,
                run_dir=run_dir,
                rows_in=ctx.rows_in,
                rows_out=ctx.rows_out,
                validation_errors=n_err,
                validation_warnings=n_warn,
                fix_steps=len(ctx.fix_log),
                status=str(row["status"]),
            )
        )
        comparison_rows.append(row)

    comparison_path: Path | None = None
    if comparison_rows:
        comparison_path = project_dir / "comparison.csv"
        pd.DataFrame(comparison_rows).to_csv(comparison_path, index=False)

    manifest = {
        "project_name": project.project_name,
        "project_dir": str(project_dir),
        "stages": list(project.stages),
        "datasets": [
            {**asdict(r), "run_dir": str(r.run_dir)}
            for r in results
        ],
    }
    manifest_path = project_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    return HubRunResult(
        project_dir=project_dir,
        manifest_path=manifest_path,
        comparison_path=comparison_path,
        datasets=tuple(results),
    )
