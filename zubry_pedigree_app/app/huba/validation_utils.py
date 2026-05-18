"""Liczniki i statusy raportu walidacji (silnik wsadowy, layout, inspekcja)."""

from __future__ import annotations

from app.data.validator import ValidationReport

DatasetStatus = str  # ok | warn | error | skipped


def count_validation_issues(report: ValidationReport | None) -> tuple[int, int]:
    """Zwraca parę (liczba błędów ERROR, liczba ostrzeżeń WARN)."""
    if report is None:
        return 0, 0
    n_err = sum(1 for i in report.issues if i.severity == "ERROR")
    n_warn = sum(1 for i in report.issues if i.severity == "WARN")
    return n_err, n_warn


def dataset_status_from_report(report: ValidationReport | None) -> DatasetStatus:
    """Mapuje raport walidacji na status zbioru: ok, warn, error lub skipped."""
    if report is None:
        return "skipped"
    n_err, n_warn = count_validation_issues(report)
    if n_err:
        return "error"
    if n_warn:
        return "warn"
    return "ok"
