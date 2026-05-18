"""Wczytywanie konfiguracji projektu HUBA z JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.huba.models import ExportFormat, HubProjectConfig, InputSource, OutputSpec
from app.huba.rules import processing_rules_from_mapping


def repo_root() -> Path:
    """Katalog główny paczki ``zubry_pedigree_app`` (baza ścieżek względnych w JSON)."""
    return Path(__file__).resolve().parents[2]


def _resolve_path(raw: str, *, base: Path) -> Path:
    p = Path(raw.strip())
    return p if p.is_absolute() else base / p


def _parse_stages(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list) or not raw:
        return ("load", "validate", "transform", "export")
    stages = tuple(str(s).strip() for s in raw if str(s).strip())
    return stages or ("load", "validate", "transform", "export")


def _output_from_mapping(raw: dict[str, Any] | None) -> OutputSpec:
    if not raw:
        return OutputSpec()
    fmt = str(raw.get("export_format", "xlsx")).strip().lower()
    export_format: ExportFormat = "csv" if fmt == "csv" else "xlsx"
    return OutputSpec(
        datasets_subdir=str(raw.get("datasets_subdir", "datasets")).strip() or "datasets",
        cleaned_basename=str(raw.get("cleaned_basename", "cleaned")).strip() or "cleaned",
        issues_basename=str(raw.get("issues_basename", "validation_issues")).strip() or "validation_issues",
        summary_basename=str(raw.get("summary_basename", "validation_summary")).strip()
        or "validation_summary",
        fix_log_basename=str(raw.get("fix_log_basename", "auto_fix_log")).strip() or "auto_fix_log",
        export_format=export_format,
        write_validation_issues=bool(raw.get("write_validation_issues", True)),
        write_summary=bool(raw.get("write_summary", True)),
        write_fix_log=bool(raw.get("write_fix_log", True)),
        csv_delimiter=str(raw.get("csv_delimiter", ";"))[:1] or ";",
    )


def _inputs_from_mapping(raw: object, *, base: Path) -> tuple[InputSource, ...]:
    if not isinstance(raw, list) or not raw:
        raise ValueError("`inputs` musi zawierać co najmniej jeden wpis.")
    out: list[InputSource] = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"inputs[{i}] musi być obiektem.")
        name = str(item.get("name", f"input_{i+1}")).strip() or f"input_{i+1}"
        path_raw = str(item.get("path", "")).strip()
        path = _resolve_path(path_raw, base=base) if path_raw else None
        out.append(InputSource(name=name, path=path))
    return tuple(out)


def load_project_config(path: str | Path) -> HubProjectConfig:
    """
    Wczytuje plik JSON projektu HUBA.

    Ścieżki względne w ``inputs`` i ``output_dir`` są rozwiązywane względem ``repo_root()``.
    """
    cfg_path = Path(path)
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Plik konfiguracyjny musi być obiektem JSON.")

    base = repo_root()
    project_name = str(raw.get("project_name", "huba_run")).strip() or "huba_run"
    output_dir = _resolve_path(str(raw.get("output_dir", "outputs")).strip() or "outputs", base=base)

    rules_raw = raw.get("rules")
    rules = processing_rules_from_mapping(rules_raw if isinstance(rules_raw, dict) else None)

    output_raw = raw.get("output")
    output = _output_from_mapping(output_raw if isinstance(output_raw, dict) else None)

    inputs = _inputs_from_mapping(raw.get("inputs"), base=base)

    return HubProjectConfig(
        project_name=project_name,
        output_dir=output_dir,
        stages=_parse_stages(raw.get("stages")),  # type: ignore[arg-type]
        inputs=inputs,
        rules=rules,
        output=output,
    )


def project_config_to_dict(project: HubProjectConfig) -> dict[str, Any]:
    """Serializacja do podglądu w UI (bez ścieżek bezwzględnych)."""
    return {
        "project_name": project.project_name,
        "output_dir": "outputs",
        "stages": list(project.stages),
        "rules": {
            "apply_auto_fix": project.rules.apply_auto_fix,
            "exclude_test_records": project.rules.exclude_test_records,
            "test_record_id": project.rules.test_record_id,
            "auto_fix": {
                "dedupe_ids": project.rules.auto_fix.dedupe_ids,
                "drop_rows_without_id": project.rules.auto_fix.drop_rows_without_id,
                "clear_birth_year_out_of_range": project.rules.auto_fix.clear_birth_year_out_of_range,
                "clear_death_date_on_conflict": project.rules.auto_fix.clear_death_date_on_conflict,
                "remove_self_parent": project.rules.auto_fix.remove_self_parent,
                "cut_missing_parent_record": project.rules.auto_fix.cut_missing_parent_record,
                "cut_parent_sex_collision": project.rules.auto_fix.cut_parent_sex_collision,
                "cut_parent_too_young": project.rules.auto_fix.cut_parent_too_young,
                "cut_parent_too_old": project.rules.auto_fix.cut_parent_too_old,
            },
        },
        "output": {
            "export_format": project.output.export_format,
            "datasets_subdir": project.output.datasets_subdir,
        },
        "inputs": [{"name": i.name, "path": str(i.path) if i.path else ""} for i in project.inputs],
    }
