"""Walidacja danych po imporcie: duplikaty ID, rodzice w bazie, lata, płeć, cykle w grafie."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.pedigree.ancestor_pedigree import Person


@dataclass(frozen=True)
class ValidationIssue:
    severity: str  # "OK" | "WARN" | "ERROR"
    title: str
    details: str = ""


@dataclass(frozen=True)
class ValidationExportRow:
    """Wiersz eksportu CSV (id, priorytet, typ, opis) do poprawy w arkuszu."""

    record_id: str
    severity: str  # ERROR | WARN
    problem_type: str
    details: str = ""


@dataclass(frozen=True)
class ValidationReport:
    total_rows: int
    issues: List[ValidationIssue]
    export_rows: Tuple[ValidationExportRow, ...] = ()

    @property
    def ok(self) -> bool:
        return all(i.severity in {"OK"} for i in self.issues)

    def short_status(self) -> str:
        n_errors = sum(1 for i in self.issues if i.severity == "ERROR")
        n_warns = sum(1 for i in self.issues if i.severity == "WARN")
        if n_errors > 0:
            return f"Walidacja: Błędy ({n_errors})"
        if n_warns > 0:
            return f"Walidacja: Ostrzeżenia ({n_warns})"
        return "Walidacja: OK"

    def ui_summary(self, *, max_issues: int = 30) -> str:
        """Krótki opis + lista problemów (ERROR/WARN) do podglądu w UI."""
        head = self.short_status()
        problems = [i for i in self.issues if i.severity in ("ERROR", "WARN")]
        if not problems:
            return head
        lines = [head]
        for issue in problems[:max_issues]:
            if issue.details:
                lines.append(f"• {issue.title} — {issue.details}")
            else:
                lines.append(f"• {issue.title}")
        if len(problems) > max_issues:
            lines.append(f"• … (+{len(problems) - max_issues} więcej — pełna lista w eksporcie raportu walidacji)")
        return "\n".join(lines)

    def to_text(self) -> str:
        lines: List[str] = []
        lines.append(self.short_status())
        lines.append(f"- wiersze w df_std: {self.total_rows}")
        for issue in self.issues:
            if issue.details:
                lines.append(f"- {issue.severity}: {issue.title} • {issue.details}")
            else:
                lines.append(f"- {issue.severity}: {issue.title}")
        return "\n".join(lines)

    def to_csv_string(self, *, delimiter: str = ";") -> str:
        """Nagłówek + wiersze (id, waga, typ_problemu, szczegoly) — np. do Excela (CSV UTF-8)."""
        buf = StringIO()
        w = csv.writer(buf, delimiter=delimiter)
        w.writerow(["id", "waga", "typ_problemu", "szczegoly"])
        for r in self.export_rows:
            w.writerow([r.record_id, r.severity, r.problem_type, r.details])
        return buf.getvalue()

    @property
    def has_export_rows(self) -> bool:
        return len(self.export_rows) > 0


def _norm_sex(v: object) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, float) and v != v:
        return None
    s = str(v).strip().upper()
    if s == "M":
        return "M"
    if s == "F":
        return "F"
    return None


def _norm_line(v: object) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float) and v != v:
        return "NA"
    s = str(v).strip().upper()
    return s if s in {"LB", "LC"} else "NA"


def _parse_year(v: object) -> Optional[int]:
    if v is None:
        return None
    try:
        if isinstance(v, float) and v != v:
            return None
    except Exception:
        pass
    try:
        return int(float(v))
    except Exception:
        return None


def validate_loaded_dataset(
    df_std: pd.DataFrame,
    people: Dict[str, Person],
    *,
    current_year: Optional[int] = None,
    min_year: int = 1800,
    max_year_buffer: int = 2,
) -> ValidationReport:
    """Zbiorcza walidacja ramki po standaryzacji (wymagane i opcjonalne kolumny jak w `Person`)."""
    issues: List[ValidationIssue] = []
    export_rows: List[ValidationExportRow] = []
    total_rows = int(len(df_std.index))

    if df_std is None or getattr(df_std, "empty", True):
        return ValidationReport(
            total_rows=0,
            issues=[ValidationIssue("ERROR", "Brak danych do walidacji")],
            export_rows=(),
        )

    if current_year is None:
        from datetime import datetime

        current_year = int(datetime.now().year)

    # 1) Duplikaty ID
    if "id" in df_std.columns:
        try:
            dup_count = int(df_std["id"].duplicated().sum())
            if dup_count > 0:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "Duplikaty ID",
                        details=f"duplikaty={dup_count} (id powinno być unikalne w bazie)",
                    )
                )
                dup_mask = df_std.duplicated(subset=["id"], keep=False)
                for _, row in df_std.loc[dup_mask].iterrows():
                    rid = str(row.get("id", "")).strip()
                    if rid:
                        export_rows.append(
                            ValidationExportRow(
                                rid,
                                "ERROR",
                                "Duplikat ID",
                                "To samo id w wielu wierszach — zostaw jeden rekord lub zmień id.",
                            )
                        )
            else:
                issues.append(ValidationIssue("OK", "Unikalność ID (duplikaty=0)"))
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić duplikatów ID"))

    # 2) Referencje rodziców (brak rekordów w `people`)
    father_missing = 0
    mother_missing = 0
    if "father_id" in df_std.columns and "mother_id" in df_std.columns and people:
        try:
            for _, row in df_std.iterrows():
                cid = str(row.get("id"))
                fa = row.get("father_id")
                mo = row.get("mother_id")

                if fa is not None and fa == fa:  # nan-safe
                    fa_s = str(fa).strip()
                    if fa_s and fa_s != "None" and fa_s not in people:
                        father_missing += 1
                        export_rows.append(
                            ValidationExportRow(
                                cid,
                                "WARN",
                                "Brak rekordu ojca w bazie",
                                f"father_id={fa_s} (brak tego id w people)",
                            )
                        )
                if mo is not None and mo == mo:
                    mo_s = str(mo).strip()
                    if mo_s and mo_s != "None" and mo_s not in people:
                        mother_missing += 1
                        export_rows.append(
                            ValidationExportRow(
                                cid,
                                "WARN",
                                "Brak rekordu matki w bazie",
                                f"mother_id={mo_s} (brak tego id w people)",
                            )
                        )
        except Exception:
            # walidacja nie może wywalić aplikacji
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić braków rodziców"))
        else:
            if father_missing > 0 or mother_missing > 0:
                issues.append(
                    ValidationIssue(
                        "WARN",
                        "Brak rekordów rodziców (founder-stop w metrykach)",
                        details=f"missing_father_records={father_missing}, missing_mother_records={mother_missing}",
                    )
                )
            else:
                issues.append(ValidationIssue("OK", "Rodzice: wszystkie rekordy istnieją w `people`"))

    # 3) Cykl w relacji rodzic->dziecko (w praktyce: cykl w relacji child->parent)
    try:
        import networkx as nx

        G = nx.DiGraph()
        G.add_nodes_from(people.keys())
        if "father_id" in df_std.columns and "mother_id" in df_std.columns:
            for _, row in df_std.iterrows():
                child_id = row.get("id")
                if child_id is None or (isinstance(child_id, float) and child_id != child_id):
                    continue
                child_s = str(child_id)
                if child_s not in people:
                    continue
                fa = row.get("father_id")
                mo = row.get("mother_id")
                if fa is not None and fa == fa:
                    fa_s = str(fa).strip()
                    if fa_s and fa_s in people:
                        # edge child -> parent
                        G.add_edge(child_s, fa_s)
                if mo is not None and mo == mo:
                    mo_s = str(mo).strip()
                    if mo_s and mo_s in people:
                        G.add_edge(child_s, mo_s)

        cycle_nodes = None
        try:
            cyc = nx.find_cycle(G, orientation="original")
            # cyc: list of edges (u,v)
            cycle_nodes = [cyc[0][0], cyc[0][1]] if cyc else None
        except Exception:
            cycle_nodes = None

        if cycle_nodes:
            issues.append(ValidationIssue("ERROR", "Wykryto cykl w rodowodzie", details=f"sample_nodes={cycle_nodes}"))
            export_rows.append(
                ValidationExportRow(
                    "_GLOBAL_",
                    "ERROR",
                    "Cykl w rodowodzie",
                    f"Dotyczy całej bazy — przykładowe węzły na cyklu: {cycle_nodes}",
                )
            )
        else:
            issues.append(ValidationIssue("OK", "Rodowód: brak cykli"))
    except Exception:
        issues.append(ValidationIssue("WARN", "Nie udało się wykryć cykli (networkx)"))

    # 4) Samorodzicielstwo / self-parent
    self_parent = 0
    if "id" in df_std.columns and "father_id" in df_std.columns and "mother_id" in df_std.columns:
        try:
            for _, row in df_std.iterrows():
                cid = row.get("id")
                if cid is None or (isinstance(cid, float) and cid != cid):
                    continue
                cid_s = str(cid).strip()
                fa = row.get("father_id")
                mo = row.get("mother_id")

                if fa is not None and fa == fa and str(fa).strip() == cid_s:
                    self_parent += 1
                    export_rows.append(
                        ValidationExportRow(
                            cid_s,
                            "ERROR",
                            "Self-parent (ojciec)",
                            "father_id wskazuje na ten sam id co osobnik",
                        )
                    )
                if mo is not None and mo == mo and str(mo).strip() == cid_s:
                    self_parent += 1
                    export_rows.append(
                        ValidationExportRow(
                            cid_s,
                            "ERROR",
                            "Self-parent (matka)",
                            "mother_id wskazuje na ten sam id co osobnik",
                        )
                    )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić self-parent"))
        else:
            if self_parent > 0:
                issues.append(ValidationIssue("ERROR", "Self-parent (osobnik ma samego siebie jako rodzica)", details=f"count={self_parent}"))
            else:
                issues.append(ValidationIssue("OK", "Self-parent: brak"))

    # 5) Sanity: płeć
    if "sex" in df_std.columns:
        try:
            invalid_sex = int(df_std["sex"].apply(_norm_sex).isna().sum() - df_std["sex"].isna().sum())
            # if sex was something unexpected, norm becomes None but original wasn't NaN
            if invalid_sex > 0:
                issues.append(ValidationIssue("WARN", "Niepoprawne wartości `sex` w pliku (zestandaryzowano do None)", details=f"count={invalid_sex}"))
                for _, row in df_std.iterrows():
                    raw = row.get("sex")
                    if raw is None or (isinstance(raw, float) and raw != raw):
                        continue
                    if _norm_sex(raw) is None:
                        rid = str(row.get("id", "")).strip()
                        if rid:
                            export_rows.append(
                                ValidationExportRow(
                                    rid,
                                    "WARN",
                                    "Niepoprawna płeć (sex)",
                                    f"Oczekiwane M/F lub puste; wartość={raw!r}",
                                )
                            )
            else:
                issues.append(ValidationIssue("OK", "Płeć: wartości w M/F lub puste"))
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić poprawności `sex`"))

    # 6) Sanity: birth_year zakres + wiek rodziców
    out_of_range_birth = 0
    parent_age_outliers = 0
    year_min = min_year
    year_max = int(current_year) + int(max_year_buffer)
    if "birth_year" in df_std.columns:
        try:
            # Map id->year dla szybkiego sprawdzania rodziców.
            id_to_year: Dict[str, Optional[int]] = {}
            for pid, p in people.items():
                id_to_year[pid] = _parse_year(getattr(p, "birth_year", None))

            for _, row in df_std.iterrows():
                child_id = row.get("id")
                child_s = str(child_id).strip() if child_id is not None else ""
                child_year = _parse_year(row.get("birth_year"))
                if child_year is not None and (child_year < year_min or child_year > year_max):
                    out_of_range_birth += 1
                    if child_s:
                        export_rows.append(
                            ValidationExportRow(
                                child_s,
                                "WARN",
                                "birth_year poza zakresem",
                                f"rok={child_year}, dopuszczalnie {year_min}–{year_max}",
                            )
                        )

                fa = row.get("father_id")
                mo = row.get("mother_id")
                if child_year is None:
                    continue

                if fa is not None and fa == fa:
                    fa_s = str(fa).strip()
                    fa_y = id_to_year.get(fa_s)
                    if fa_y is not None:
                        age = child_year - fa_y
                        if age < 0 or age > 80:
                            parent_age_outliers += 1
                            if child_s:
                                export_rows.append(
                                    ValidationExportRow(
                                        child_s,
                                        "WARN",
                                        "Wiek ojca przy urodzeniu potomka poza 0–80 lat",
                                        f"różnica lat potomek–ojciec={age}, father_id={fa_s}",
                                    )
                                )

                if mo is not None and mo == mo:
                    mo_s = str(mo).strip()
                    mo_y = id_to_year.get(mo_s)
                    if mo_y is not None:
                        age = child_year - mo_y
                        if age < 0 or age > 80:
                            parent_age_outliers += 1
                            if child_s:
                                export_rows.append(
                                    ValidationExportRow(
                                        child_s,
                                        "WARN",
                                        "Wiek matki przy urodzeniu potomka poza 0–80 lat",
                                        f"różnica lat potomek–matka={age}, mother_id={mo_s}",
                                    )
                                )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się wykonać sanity lat/age dla rodziców"))
        else:
            if out_of_range_birth > 0:
                issues.append(ValidationIssue("WARN", "birth_year poza zakresem", details=f"count={out_of_range_birth} (min={year_min}, max={year_max})"))
            else:
                issues.append(ValidationIssue("OK", "birth_year: zakres OK"))
            if parent_age_outliers > 0:
                issues.append(ValidationIssue("WARN", "Wiek rodziców (birth_year różnica) — outliery", details=f"count={parent_age_outliers} (poza 0..80 lat)"))
            else:
                issues.append(ValidationIssue("OK", "Wiek rodziców: bez outlierów (0..80)"))

    # 7) Cross-check linii: father_line/mother_line vs recordy rodziców
    mismatch_f = 0
    mismatch_m = 0
    compared_f = 0
    compared_m = 0
    if "father_line" in df_std.columns and "mother_line" in df_std.columns and "father_id" in df_std.columns and "mother_id" in df_std.columns:
        try:
            for _, row in df_std.iterrows():
                fa = row.get("father_id")
                fa_line = row.get("father_line")
                cid = row.get("id")
                if fa is not None and fa == fa:
                    fa_s = str(fa).strip()
                    fa_rec = people.get(fa_s)
                    if fa_rec is not None and _norm_line(fa_line) in {"LB", "LC"}:
                        compared_f += 1
                        if _norm_line(getattr(fa_rec, "line", None)) != _norm_line(fa_line):
                            mismatch_f += 1
                            cid_s = str(cid).strip() if cid is not None else ""
                            if cid_s:
                                export_rows.append(
                                    ValidationExportRow(
                                        cid_s,
                                        "WARN",
                                        "Niespójność father_line z linią ojca w bazie",
                                        f"wiersz father_line={_norm_line(fa_line)}, rekord ojca line={_norm_line(getattr(fa_rec, 'line', None))}, father_id={fa_s}",
                                    )
                                )

                mo = row.get("mother_id")
                mo_line = row.get("mother_line")
                if mo is not None and mo == mo:
                    mo_s = str(mo).strip()
                    mo_rec = people.get(mo_s)
                    if mo_rec is not None and _norm_line(mo_line) in {"LB", "LC"}:
                        compared_m += 1
                        if _norm_line(getattr(mo_rec, "line", None)) != _norm_line(mo_line):
                            mismatch_m += 1
                            cid_s = str(cid).strip() if cid is not None else ""
                            if cid_s:
                                export_rows.append(
                                    ValidationExportRow(
                                        cid_s,
                                        "WARN",
                                        "Niespójność mother_line z linią matki w bazie",
                                        f"wiersz mother_line={_norm_line(mo_line)}, rekord matki line={_norm_line(getattr(mo_rec, 'line', None))}, mother_id={mo_s}",
                                    )
                                )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić spójności `father_line/mother_line`"))
        else:
            if compared_f > 0:
                if mismatch_f > 0:
                    issues.append(
                        ValidationIssue(
                            "WARN",
                            "Niespójność father_line vs line rodzica",
                            details=f"mismatch={mismatch_f} / compared={compared_f}",
                        )
                    )
                else:
                    issues.append(ValidationIssue("OK", "father_line vs line rodzica: spójne"))
            if compared_m > 0:
                if mismatch_m > 0:
                    issues.append(
                        ValidationIssue(
                            "WARN",
                            "Niespójność mother_line vs line rodzica",
                            details=f"mismatch={mismatch_m} / compared={compared_m}",
                        )
                    )
                else:
                    issues.append(ValidationIssue("OK", "mother_line vs line rodzica: spójne"))

    return ValidationReport(total_rows=total_rows, issues=issues, export_rows=tuple(export_rows))

