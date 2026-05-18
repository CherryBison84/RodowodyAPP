"""Zapis artefaktów do ustalonej struktury katalogów."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from app.data.validator import ValidationReport
from app.huba.context import DatasetContext
from app.huba.models import OutputSpec
from app.huba.validation_utils import count_validation_issues, dataset_status_from_report


def dataset_run_dir(project_dir: Path, output: OutputSpec, safe_name: str) -> Path:
    """Ścieżka katalogu wyników dla jednego wejścia (np. ``outputs/run/datasets/plik_a``)."""
    return project_dir / output.datasets_subdir / safe_name


def write_cleaned(df: pd.DataFrame, run_dir: Path, output: OutputSpec) -> Path:
    """Zapisuje oczyszczoną ramkę jako CSV lub XLSX zgodnie z ``OutputSpec``."""
    run_dir.mkdir(parents=True, exist_ok=True)
    if output.export_format == "xlsx":
        path = run_dir / f"{output.cleaned_basename}.xlsx"
        df.to_excel(path, index=False)
    else:
        path = run_dir / f"{output.cleaned_basename}.csv"
        df.to_csv(path, index=False, sep=output.csv_delimiter, encoding="utf-8-sig")
    return path


def write_validation_issues(report: ValidationReport, run_dir: Path, output: OutputSpec) -> Path | None:
    """Eksportuje wiersze problemów walidacji do CSV (gdy włączone w konfiguracji)."""
    if not output.write_validation_issues or not report.has_export_rows:
        return None
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{output.issues_basename}.csv"
    path.write_text(report.to_csv_string(delimiter=output.csv_delimiter), encoding="utf-8-sig")
    return path


def write_validation_summary(ctx: DatasetContext, run_dir: Path, output: OutputSpec) -> Path | None:
    """Zapisuje skrócony JSON ze statusem walidacji i liczbą wierszy."""
    if not output.write_summary or ctx.validation_report is None:
        return None
    n_err, n_warn = count_validation_issues(ctx.validation_report)
    payload = {
        "input_name": ctx.source.name,
        "source_label": ctx.source_label,
        "rows_in": ctx.rows_in,
        "rows_out": ctx.rows_out,
        "validation_errors": n_err,
        "validation_warnings": n_warn,
        "export_issue_rows": len(ctx.validation_report.export_rows),
        "status": dataset_status_from_report(ctx.validation_report),
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{output.summary_basename}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_fix_log(ctx: DatasetContext, run_dir: Path, output: OutputSpec) -> Path | None:
    """Zapisuje tekstowy log kroków auto-fix (pusty log — brak pliku)."""
    if not output.write_fix_log or not ctx.fix_log:
        return None
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / f"{output.fix_log_basename}.txt"
    path.write_text("\n".join(ctx.fix_log), encoding="utf-8")
    return path
