"""Treść eksportowanego raportu zbiorczego (wspólna dla .txt / .docx / .pdf)."""

from __future__ import annotations

from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional

import pandas as pd

from app.analytics.mean_kinship import mean_kinship_pairwise
from app.analytics.population_dashboard import (
    global_ria_percent,
    pct_individuals_incomplete_parents,
    pct_missing_parent_slots,
)
from app.analytics.population_genetics import (
    TEST_ID,
    compute_gi_and_family_data,
    compute_population_genetics_stats,
)
from app.config import get_config
from app.data.dataset_loader import dataframe_app_schema_columns
from app.data.validator import ValidationReport
from app.ui.metric_copy import RIA_PLAIN_SHORT

# W UI trendy populacji używają 4 pokoleń — raport jest spójny z tym ustawieniem.
REPORT_POP_MAX_GENERATIONS_BACK = 4


def build_export_report_text(
    *,
    source: object,
    df_std: Optional[pd.DataFrame],
    people: Optional[Dict[str, Any]],
    rep: Optional[ValidationReport],
    max_generations_back: int = REPORT_POP_MAX_GENERATIONS_BACK,
) -> str:
    lines: List[str] = [
        "WisentPedigree Pro+ — raport zbiorczy",
        "",
        f"Wygenerowano: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Źródło danych: {source if source is not None else '-'}",
        "",
        "=== Parametry obliczeń w tym raporcie ===",
        f"- F (Wright), EG i PCI dla zbioru: maks. {max_generations_back} pokoleń wstecz od każdego osobnika "
        "(zatrzymanie przy founder-stop / braku rodzica w drzewie, jak w module analiz).",
        "- Mean kinship (Φ̄, R): losowa próba par wśród wczytanych ID, max 4 pokolenia wstecz od obu osobników.",
        "- GI i rodziny pełnego rodzeństwa: na podstawie lat urodzenia i powiązań ojciec–matka w wczytanym zbiorze.",
        "",
    ]

    df_s: Optional[pd.DataFrame] = None
    if df_std is not None and not df_std.empty:
        try:
            df_s = dataframe_app_schema_columns(df_std)
        except Exception:
            df_s = df_std.copy()

    if df_s is not None and not df_s.empty:
        lines.append("=== Zbiór danych (model aplikacji) ===")
        lines.append(f"- liczba rekordów: {len(df_s)}")
        cols = [str(c) for c in df_s.columns.tolist()]
        lines.append(f"- kolumny ({len(cols)}): {', '.join(cols)}")
        try:
            lines.append(f"- rekordów z brakiem ojca lub matki: {pct_individuals_incomplete_parents(df_s):.2f}%")
            lines.append(f"- puste sloty rodzicielskie względem 2n: {pct_missing_parent_slots(df_s):.2f}%")
        except Exception:
            pass
        if "sex" in df_s.columns:
            try:
                sx = df_s["sex"].astype(str).str.strip().str.upper()
                nm = int((sx == "M").sum())
                nf = int((sx == "F").sum())
                no = int(len(sx) - nm - nf)
                lines.append(f"- płeć: M={nm}, F={nf}, inne/brak={no}")
            except Exception:
                pass
        if "birth_year" in df_s.columns:
            try:
                yrs = pd.to_numeric(df_s["birth_year"], errors="coerce").dropna()
                if len(yrs) > 0:
                    lines.append(f"- rok urodzenia (min–max): {int(yrs.min())} – {int(yrs.max())} (n={len(yrs)})")
            except Exception:
                pass
        lines.append("")

    if rep is not None:
        lines.append("=== Walidacja spójności (tylko skrót) ===")
        lines.append(f"- {rep.short_status()}")
        lines.append(f"- wiersze w df_std: {rep.total_rows}")
        n_err = sum(1 for i in rep.issues if i.severity == "ERROR")
        n_warn = sum(1 for i in rep.issues if i.severity == "WARN")
        n_other = len(rep.issues) - n_err - n_warn
        lines.append(f"- komunikaty: ERROR={n_err}, WARN={n_warn}, pozostałe={n_other} (łącznie wpisów: {len(rep.issues)})")
        if rep.has_export_rows:
            lines.append(f"- rekordy do śledzenia w arkuszu (CSV w UI): {len(rep.export_rows)}")
        lines.append("- Pełny opis problemów, lista i plik CSV: sekcja „Walidacja spójności zbioru” w aplikacji.")
        lines.append("")
    else:
        lines.append("=== Walidacja spójności (tylko skrót) ===")
        lines.append("(brak zapisanego raportu walidacji — uruchom walidację po imporcie danych.)")
        lines.append("")

    if df_s is not None and people:
        cfg = get_config()
        try:
            stats = compute_population_genetics_stats(
                df_std=df_s,
                people=people,  # type: ignore[arg-type]
                max_generations_back=max_generations_back,
                calc_f=True,
                calc_completeness=True,
                calc_founders=True,
                calc_lines=True,
            )
            lines.append("=== Populacja — metryki genetyczne i struktura ===")
            lines.append(f"n={stats.n} (pominięto rekord testowy ID={TEST_ID} zgodnie z modułem metryk)")
            lines.append(
                f"F: średnia={stats.inbreeding.mean_F:.6f}, mediana={stats.inbreeding.median_F:.6f}, "
                f"min={stats.inbreeding.min_F:.6f}, max={stats.inbreeding.max_F:.6f}, "
                f"F≈0 dla {stats.inbreeding.zeros} osobników"
            )
            lines.append(f"RIA — {RIA_PLAIN_SHORT}: {global_ria_percent(stats.f_values):.2f}%")
            med_eg = median(stats.eg_values) if stats.eg_values else 0.0
            med_pci = median(stats.pci_values) if stats.pci_values else 0.0
            lines.append(
                f"Kompletność: średnie EG={stats.completeness.mean_EG:.4f}, średnie PCI={stats.completeness.mean_PCI:.4f}; "
                f"mediana EG={med_eg:.4f}, mediana PCI={med_pci:.4f}"
            )
            lines.append(
                f"Założyciele (founder-stop): f_e={stats.founders.f_e:.4f}, f_a={stats.founders.f_a:.4f}; "
                f"osobnicy z brakiem ojca lub matki w rekordzie: {stats.n_founders_any_missing_parent}"
            )
            lines.append(
                f"Linie (rekord): LB={stats.line_counts.get('LB', 0)}, LC={stats.line_counts.get('LC', 0)}, "
                f"NA={stats.line_counts.get('NA', 0)}"
            )
            top_n = max(1, int(cfg.report_founders_top_n))
            if stats.founder_contributions:
                ranked = sorted(stats.founder_contributions.items(), key=lambda kv: kv[1], reverse=True)[:top_n]
                lines.append(f"Top {min(top_n, len(ranked))} założycieli wg średniego wkładu p_i (%):")
                for fid, pi in ranked:
                    lines.append(f"  - {fid}: {100.0 * float(pi):.4f}%")
            lines.append("")

            try:
                id_list = [str(x) for x in df_s["id"].tolist()]
                mk_phi, mk_r, mk_note = mean_kinship_pairwise(
                    people,  # type: ignore[arg-type]
                    id_list,
                    max_generations_back=4,
                )
                if mk_phi is not None and mk_r is not None:
                    lines.append("=== Pokrewieństwo średnie (próba par) ===")
                    lines.append(f"Φ̄={mk_phi:.6f}, R̄={mk_r:.6f}")
                    if mk_note:
                        lines.append(f"Uwaga: {mk_note}")
                    lines.append("")
            except Exception:
                pass

            try:
                gi_data = compute_gi_and_family_data(df_s, people)
                gi_bits: List[str] = []
                if gi_data.get("gi_all") is not None:
                    gi_bits.append(f"GI średnie={float(gi_data['gi_all']):.2f} lat")
                if gi_data.get("gi_fs") is not None:
                    gi_bits.append(f"O→S={float(gi_data['gi_fs']):.2f}")
                if gi_data.get("gi_fd") is not None:
                    gi_bits.append(f"O→C={float(gi_data['gi_fd']):.2f}")
                if gi_data.get("gi_ms") is not None:
                    gi_bits.append(f"M→S={float(gi_data['gi_ms']):.2f}")
                if gi_data.get("gi_md") is not None:
                    gi_bits.append(f"M→C={float(gi_data['gi_md']):.2f}")
                if gi_bits:
                    lines.append("=== Generational interval (GI) ===")
                    lines.append(", ".join(gi_bits))
                    fam = gi_data.get("family_sizes") or []
                    if fam:
                        lines.append(
                            f"Rodziny pełnego rodzeństwa: {len(fam)} grup, średnia wielkość "
                            f"{float(sum(fam)) / float(len(fam)):.2f}"
                        )
                    lines.append("")
            except Exception:
                pass

            try:
                if "birth_location" in df_s.columns:
                    loc = df_s["birth_location"].astype(str).str.strip()
                    loc = loc.replace({"": "NA", "nan": "NA", "None": "NA", "NaN": "NA"})
                    top = loc.value_counts(dropna=False).head(int(cfg.report_birth_location_top_n)).to_dict()
                    lines.append(
                        "=== Miejsce urodzenia (najczęstsze) ==="
                    )
                    lines.append(" | ".join([f"{k}={int(v)}" for k, v in top.items()]))
                    lines.append("")
            except Exception:
                pass
        except Exception as e:
            lines.append(f"=== Populacja ===\n(błąd metryk: {e})\n")

    lines.append("=== Uwagi do eksportu ===")
    lines.append(
        "Wykresy z modułu Populacja oraz PNG rodowodów należy dołączyć osobno (przyciski pobierania w aplikacji). "
        "Walidacja w tym pliku jest tylko skrótem — pełne wyniki i CSV w sekcji walidacji w aplikacji."
    )
    return "\n".join(lines)
