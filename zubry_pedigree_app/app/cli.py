"""Terminalowy DataCleaner bez interfejsu Streamlit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from app.huba.config_io import load_project_config, repo_root
from app.huba.engine import run_project
from app.huba.models import HubProjectConfig, InputSource, OutputSpec, ProcessingRules


STATUS_LABELS = {
    "ok": "gotowe",
    "warn": "gotowe warunkowo",
    "error": "wymaga poprawy",
    "skipped": "nie oceniono",
}


def _resolve_cli_path(raw: str | Path) -> Path:
    """Rozwiązuje ścieżkę podaną w terminalu względem bieżącego katalogu."""
    path = Path(raw).expanduser()
    return path if path.is_absolute() else Path.cwd() / path


def _default_project_name(inputs: Sequence[Path]) -> str:
    """Buduje nazwę projektu, gdy użytkownik jej nie poda."""
    if len(inputs) == 1:
        return inputs[0].stem or "datacleaner"
    return "datacleaner_batch"


def _project_from_args(args: argparse.Namespace) -> HubProjectConfig:
    """Buduje konfigurację uruchomienia z argumentów terminalowych."""
    input_paths = tuple(_resolve_cli_path(path) for path in args.input)
    missing = [str(path) for path in input_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Nie znaleziono plików wejściowych: " + ", ".join(missing))

    project_name = args.project_name.strip() or _default_project_name(input_paths)
    output_dir = _resolve_cli_path(args.output_dir)
    inputs = tuple(InputSource(name=path.stem or f"input_{i + 1}", path=path) for i, path in enumerate(input_paths))
    rules = ProcessingRules(
        apply_auto_fix=not args.no_auto_fix,
        exclude_test_records=not args.keep_test_records,
        test_record_id=args.test_record_id,
    )
    output = OutputSpec(export_format=args.format)
    return HubProjectConfig(
        project_name=project_name,
        output_dir=output_dir,
        inputs=inputs,
        rules=rules,
        output=output,
    )


def _print_result(result) -> None:
    """Wypisuje krótkie, terminalowe podsumowanie wyniku."""
    print("\nWisentPedigree DataCleaner zakończył pracę.")
    print(f"Wyniki: {result.project_dir}")
    if result.comparison_path:
        print(f"Porównanie CSV: {result.comparison_path}")
    print(f"Raport HTML: {result.final_report_html_path}")
    print(f"Manifest techniczny: {result.manifest_path}")
    print("\nPodsumowanie baz:")
    for dataset in result.datasets:
        status = STATUS_LABELS.get(dataset.status, dataset.status)
        print(
            " - "
            f"{dataset.input_name}: {dataset.rows_in} -> {dataset.rows_out} wierszy, "
            f"błędy: {dataset.validation_errors}, ostrzeżenia: {dataset.validation_warnings}, "
            f"status: {status}"
        )


def _write_example_config(path: Path) -> None:
    """Zapisuje przykład konfiguracji dla pracy wsadowej."""
    example = {
        "project_name": "datacleaner_terminal",
        "output_dir": "outputs",
        "stages": ["load", "validate", "transform", "export"],
        "inputs": [
            {
                "name": "EBPB_bison_report",
                "path": "data/EBPB_bison_report.xlsx",
            }
        ],
        "rules": {
            "apply_auto_fix": True,
            "exclude_test_records": True,
            "test_record_id": "99999",
            "auto_fix": {
                "dedupe_ids": True,
                "drop_rows_without_id": False,
                "clear_birth_year_out_of_range": True,
                "clear_death_date_on_conflict": True,
                "remove_self_parent": True,
                "cut_missing_parent_record": True,
                "cut_parent_sex_collision": True,
                "cut_parent_too_young": True,
                "cut_parent_too_old": False,
            },
        },
        "output": {
            "export_format": "xlsx",
            "write_validation_issues": True,
            "write_summary": True,
            "write_fix_log": True,
            "csv_delimiter": ";",
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(example, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    """Tworzy parser argumentów terminalowych."""
    parser = argparse.ArgumentParser(
        prog="datacleaner",
        description="WisentPedigree DataCleaner - przygotowanie baz do analizy rodowodowej bez GUI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = subparsers.add_parser("run", help="Uruchom DataCleaner na plikach albo konfiguracji JSON.")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--config", help="Plik JSON projektu DataCleaner.")
    source.add_argument(
        "--input",
        nargs="+",
        help="Jeden lub kilka plików wejściowych CSV/XLSX przetwarzanych bez konfiguracji JSON.",
    )
    run.add_argument("--project-name", default="", help="Nazwa uruchomienia w katalogu wyników.")
    run.add_argument("--output-dir", default=str(repo_root() / "outputs"), help="Katalog wyników.")
    run.add_argument("--format", choices=["xlsx", "csv"], default="xlsx", help="Format oczyszczonej bazy.")
    run.add_argument("--no-auto-fix", action="store_true", help="Wyłącz automatyczne poprawki.")
    run.add_argument("--keep-test-records", action="store_true", help="Nie usuwaj rekordów testowych.")
    run.add_argument("--test-record-id", default="99999", help="Identyfikator rekordu testowego.")
    run.add_argument(
        "--fail-on-validation-error",
        action="store_true",
        help="Zwróć kod błędu, jeśli walidacja znajdzie błędy typu ERROR.",
    )

    init = subparsers.add_parser("init-config", help="Zapisz przykładowy plik konfiguracji JSON.")
    init.add_argument(
        "path",
        nargs="?",
        default="config/datacleaner_cli.example.json",
        help="Gdzie zapisać przykład konfiguracji.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Punkt wejścia terminalowej wersji aplikacji."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-config":
        path = _resolve_cli_path(args.path)
        _write_example_config(path)
        print(f"Zapisano przykładową konfigurację: {path}")
        return 0

    if args.command != "run":
        parser.print_help()
        return 0

    try:
        project = load_project_config(args.config) if args.config else _project_from_args(args)
        result = run_project(project)
    except Exception as exc:
        print(f"Błąd DataCleanera: {exc}", file=sys.stderr)
        return 1

    _print_result(result)
    has_errors = any(dataset.validation_errors > 0 for dataset in result.datasets)
    if args.fail_on_validation_error and has_errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
