"""Orkiestracja uruchomień wsadowych HUBA."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from html import escape
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


def _status_label(status: str) -> str:
    """Czytelna etykieta statusu walidacji do raportu HTML."""
    return {
        "ok": "Gotowe do analizy",
        "warn": "Gotowe warunkowo",
        "error": "Wymaga poprawy",
        "skipped": "Nie oceniono",
    }.get(status, status)


def _status_class(status: str) -> str:
    """Klasa CSS statusu walidacji."""
    return status if status in {"ok", "warn", "error", "skipped"} else "skipped"


def _html_table(headers: list[str], rows: list[list[object]]) -> str:
    """Buduje prostą tabelę HTML z escapowaniem danych."""
    head = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _write_final_report_html(
    project: HubProjectConfig,
    project_dir: Path,
    contexts: list[DatasetContext],
) -> Path:
    """Generuje czytelny raport HTML dla użytkownika końcowego."""
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary_rows: list[list[object]] = []
    sections: list[str] = []
    for ctx in contexts:
        n_err, n_warn = count_validation_issues(ctx.validation_report)
        status = dataset_status_from_report(ctx.validation_report)
        export_rows = len(ctx.validation_report.export_rows) if ctx.validation_report else 0
        summary_rows.append(
            [
                ctx.source.name,
                ctx.source_label,
                ctx.rows_in,
                ctx.rows_out,
                n_err,
                n_warn,
                export_rows,
                _status_label(status),
            ]
        )

        issue_rows: list[list[object]] = []
        if ctx.validation_report is not None:
            for issue in ctx.validation_report.issues:
                issue_rows.append([issue.severity, issue.title, issue.details])
        export_issue_rows: list[list[object]] = []
        if ctx.validation_report is not None:
            for row in ctx.validation_report.export_rows[:300]:
                export_issue_rows.append([row.record_id, row.severity, row.problem_type, row.details])

        run_dir_rel = ctx.run_dir.relative_to(project_dir)
        artifacts = [
            ["Oczyszczona baza", f"{run_dir_rel}/{project.output.cleaned_basename}.{project.output.export_format}"],
            ["Problemy walidacji", f"{run_dir_rel}/{project.output.issues_basename}.csv"],
            ["Podsumowanie walidacji", f"{run_dir_rel}/{project.output.summary_basename}.json"],
            ["Log auto-poprawek", f"{run_dir_rel}/{project.output.fix_log_basename}.txt"],
        ]

        status_badge = (
            f'<span class="badge {_status_class(status)}">{escape(_status_label(status))}</span>'
        )
        sections.append(
            f"""
            <section class="dataset">
              <div class="dataset-title">
                <h2>{escape(ctx.source.name)}</h2>
                {status_badge}
              </div>
              <p class="muted">Źródło: {escape(ctx.source_label or ctx.source.name)}</p>
              <div class="metrics">
                <div><strong>{ctx.rows_in}</strong><span>wiersze wejściowe</span></div>
                <div><strong>{ctx.rows_out}</strong><span>wiersze wynikowe</span></div>
                <div><strong>{n_err}</strong><span>błędy</span></div>
                <div><strong>{n_warn}</strong><span>ostrzeżenia</span></div>
              </div>
              <h3>Artefakty</h3>
              {_html_table(["Artefakt", "Ścieżka"], artifacts)}
              <h3>Komunikaty walidacji</h3>
              {_html_table(["Poziom", "Komunikat", "Szczegóły"], issue_rows) if issue_rows else "<p>Brak komunikatów.</p>"}
              <h3>Rekordy do korekty</h3>
              {_html_table(["ID", "Waga", "Typ problemu", "Szczegóły"], export_issue_rows) if export_issue_rows else "<p>Brak rekordów do korekty.</p>"}
              {'<p class="muted">Pokazano pierwsze 300 wpisów. Pełna lista jest w CSV.</p>' if ctx.validation_report and len(ctx.validation_report.export_rows) > 300 else ''}
              <h3>Log auto-poprawek</h3>
              {"<ul>" + "".join(f"<li>{escape(line)}</li>" for line in ctx.fix_log) + "</ul>" if ctx.fix_log else "<p>Brak zmian automatycznych.</p>"}
            </section>
            """
        )

    html = f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Raport DataCleaner — {escape(project.project_name)}</title>
  <style>
    :root {{
      --ink:#1f2d25; --muted:#66786d; --bg:#eef6f0; --paper:#ffffff;
      --line:#bccdc2; --green:#2f6b4f; --amber:#8a6817; --red:#9b3434;
    }}
    body {{ margin:0; padding:36px; background:var(--bg); color:var(--ink);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.5; }}
    main {{ max-width:1180px; margin:0 auto; }}
    header, section.dataset {{ background:var(--paper); border:1px solid var(--line);
      border-radius:10px; padding:24px; margin-bottom:18px; box-shadow:0 1px 8px rgba(31,45,37,.05); }}
    h1 {{ margin:0 0 8px; font-size:30px; }}
    h2 {{ margin:0; font-size:22px; }}
    h3 {{ margin:24px 0 8px; font-size:16px; }}
    .muted {{ color:var(--muted); }}
    .summary {{ margin-top:18px; }}
    table {{ width:100%; border-collapse:collapse; font-size:14px; background:#fff; }}
    th, td {{ border:1px solid var(--line); padding:8px 10px; text-align:left; vertical-align:top; }}
    th {{ background:#e5efe8; font-weight:700; }}
    tr:nth-child(even) td {{ background:#f8fbf9; }}
    .dataset-title {{ display:flex; align-items:center; justify-content:space-between; gap:16px; }}
    .badge {{ display:inline-block; padding:6px 10px; border-radius:999px; color:#fff; font-weight:700; font-size:13px; }}
    .badge.ok {{ background:var(--green); }}
    .badge.warn {{ background:var(--amber); }}
    .badge.error {{ background:var(--red); }}
    .badge.skipped {{ background:var(--muted); }}
    .metrics {{ display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px; margin:16px 0; }}
    .metrics div {{ border:1px solid var(--line); background:#f4faf6; border-radius:8px; padding:12px; }}
    .metrics strong {{ display:block; font-size:24px; }}
    .metrics span {{ color:var(--muted); font-size:13px; }}
    @media print {{ body {{ background:#fff; padding:0; }} header, section.dataset {{ box-shadow:none; break-inside:avoid; }} }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>Raport DataCleaner</h1>
    <p class="muted">Projekt: <strong>{escape(project.project_name)}</strong> · wygenerowano: {escape(generated)}</p>
    <p>Raport podsumowuje jakość danych, status gotowości oraz artefakty wygenerowane przed właściwą analizą rodowodową.</p>
    <div class="summary">
      {_html_table(["Baza", "Źródło", "Wiersze wejściowe", "Wiersze wynikowe", "Błędy", "Ostrzeżenia", "Wpisy CSV", "Status"], summary_rows)}
    </div>
  </header>
  {''.join(sections)}
</main>
</body>
</html>
"""
    path = project_dir / "final_report.html"
    path.write_text(html, encoding="utf-8")
    return path


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
    contexts: list[DatasetContext] = []

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
        contexts.append(ctx)

    comparison_path: Path | None = None
    if comparison_rows:
        comparison_path = project_dir / "comparison.csv"
        pd.DataFrame(comparison_rows).to_csv(comparison_path, index=False)

    final_report_html_path = _write_final_report_html(project, project_dir, contexts)

    manifest = {
        "project_name": project.project_name,
        "project_dir": str(project_dir),
        "final_report_html": str(final_report_html_path),
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
        final_report_html_path=final_report_html_path,
        comparison_path=comparison_path,
        datasets=tuple(results),
    )
