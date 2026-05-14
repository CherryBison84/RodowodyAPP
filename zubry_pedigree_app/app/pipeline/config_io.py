from __future__ import annotations

import json
from pathlib import Path

from app.pipeline.models import DatasetConfig, ProjectConfig, VariantConfig


def _root_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def load_project_config(path: str | Path) -> ProjectConfig:
    cfg_path = Path(path)
    raw = json.loads(cfg_path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Plik konfiguracyjny musi być obiektem JSON.")

    project_name = str(raw.get("project_name", "pedigree_project")).strip() or "pedigree_project"
    output_dir_raw = str(raw.get("output_dir", "outputs")).strip() or "outputs"
    output_dir = Path(output_dir_raw)
    if not output_dir.is_absolute():
        output_dir = _root_dir() / output_dir

    stages_raw = raw.get("stages", ["load", "analyze", "report"])
    if not isinstance(stages_raw, list) or not stages_raw:
        raise ValueError("`stages` musi być niepustą listą.")
    stages = tuple(str(s).strip() for s in stages_raw if str(s).strip())
    if not stages:
        raise ValueError("`stages` po oczyszczeniu nie może być puste.")

    datasets_raw = raw.get("datasets", [])
    if not isinstance(datasets_raw, list) or not datasets_raw:
        raise ValueError("`datasets` musi zawierać przynajmniej jeden wpis.")
    datasets: list[DatasetConfig] = []
    for i, d in enumerate(datasets_raw):
        if not isinstance(d, dict):
            raise ValueError(f"datasets[{i}] musi być obiektem.")
        name = str(d.get("name", f"dataset_{i+1}")).strip() or f"dataset_{i+1}"
        path_raw = str(d.get("path", "")).strip()
        if not path_raw:
            raise ValueError(f"datasets[{i}].path jest wymagane.")
        p = Path(path_raw)
        if not p.is_absolute():
            p = _root_dir() / p
        datasets.append(DatasetConfig(name=name, path=p))

    variants_raw = raw.get("variants", [])
    if not isinstance(variants_raw, list) or not variants_raw:
        raise ValueError("`variants` musi zawierać przynajmniej jeden wpis.")
    variants: list[VariantConfig] = []
    for i, v in enumerate(variants_raw):
        if not isinstance(v, dict):
            raise ValueError(f"variants[{i}] musi być obiektem.")
        name = str(v.get("name", f"variant_{i+1}")).strip() or f"variant_{i+1}"
        mgb = v.get("max_generations_back", 4)
        if mgb is None:
            max_generations_back = None
        else:
            max_generations_back = int(mgb)
        variants.append(
            VariantConfig(
                name=name,
                max_generations_back=max_generations_back,
                calc_founders=bool(v.get("calc_founders", True)),
                calc_completeness=bool(v.get("calc_completeness", True)),
            )
        )

    return ProjectConfig(
        project_name=project_name,
        output_dir=output_dir,
        stages=stages,
        datasets=tuple(datasets),
        variants=tuple(variants),
    )

