"""Walidacja danych po imporcie: jakość drzewa rodowego (ID, rodzice, płeć, daty, cykle, braki)."""

from __future__ import annotations

import csv
import re
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


_YEAR_TOKEN_RE = re.compile(r"\b(18\d{2}|19\d{2}|20[0-3]\d)\b")


def _years_from_date_cell(v: object) -> List[int]:
    """Wyciąga lata z luźnych napisów (np. „12.5.1891”, „ca. 1881”) — do porównania ur./zg."""
    if v is None:
        return []
    if isinstance(v, float) and v != v:
        return []
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", ""}:
        return []
    return [int(m.group(0)) for m in _YEAR_TOKEN_RE.finditer(s)]


def _is_nonempty_parent(val: object) -> bool:
    if val is None:
        return False
    if isinstance(val, float) and val != val:
        return False
    s = str(val).strip()
    return bool(s) and s.lower() not in {"none", "nan"}


def _str_id_cell(v: object) -> str:
    if v is None or (isinstance(v, float) and v != v):
        return ""
    return str(v).strip()


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

    # 8) Puste / nieważne ID wierszy (spójność z modelem drzewa)
    if "id" in df_std.columns:
        try:
            bad_id = 0
            for _, row in df_std.iterrows():
                sid = _str_id_cell(row.get("id"))
                if not sid or sid.lower() == "nan":
                    bad_id += 1
            if bad_id > 0:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "Wiersze z brakującym lub niepoprawnym `id`",
                        details=f"count={bad_id}",
                    )
                )
                export_rows.append(
                    ValidationExportRow(
                        "_GLOBAL_",
                        "ERROR",
                        "Pusty lub niepoprawny identyfikator",
                        f"{bad_id} wierszy bez czytelnego `id` — usuń lub uzupełnij numery osobników.",
                    )
                )
            else:
                issues.append(ValidationIssue("OK", "Identyfikatory: każdy wiersz ma niepuste `id`"))
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić poprawności `id` w wierszach"))

    # 9) Brak roku urodzenia (utrudnia analizy kohort, wiek rodziców)
    if "birth_year" in df_std.columns:
        try:
            ser_y = df_std["birth_year"].map(_parse_year)
            n_miss_y = int(ser_y.isna().sum())
            if n_miss_y > 0:
                issues.append(
                    ValidationIssue(
                        "WARN",
                        "Brak roku urodzenia (birth_year) w części rekordów",
                        details=f"count={n_miss_y} / {total_rows}",
                    )
                )
                shown = 0
                for _, row in df_std.iterrows():
                    if shown >= 100:
                        break
                    if _parse_year(row.get("birth_year")) is None:
                        rid = _str_id_cell(row.get("id"))
                        if rid:
                            export_rows.append(
                                ValidationExportRow(
                                    rid,
                                    "WARN",
                                    "Brak birth_year",
                                    "Uzupełnij rok urodzenia lub popraw format pola.",
                                )
                            )
                            shown += 1
            else:
                issues.append(ValidationIssue("OK", "birth_year: brak luk w rekordach"))
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się policzyć braków `birth_year`"))

    # 10) Ta sama osoba jako ojciec i matka
    same_parent_pair = 0
    if "father_id" in df_std.columns and "mother_id" in df_std.columns and "id" in df_std.columns:
        try:
            for _, row in df_std.iterrows():
                if not _is_nonempty_parent(row.get("father_id")) or not _is_nonempty_parent(row.get("mother_id")):
                    continue
                fa_s = _str_id_cell(row.get("father_id"))
                mo_s = _str_id_cell(row.get("mother_id"))
                if fa_s == mo_s:
                    same_parent_pair += 1
                    cid = _str_id_cell(row.get("id"))
                    if cid:
                        export_rows.append(
                            ValidationExportRow(
                                cid,
                                "ERROR",
                                "Ten sam ID jako ojciec i matka",
                                f"father_id=mother_id={fa_s} — niemożliwe biologicznie; sprawdź zamianę kolumn lub literówkę.",
                            )
                        )
            if same_parent_pair > 0:
                issues.append(
                    ValidationIssue(
                        "ERROR",
                        "Powiązania rodzinne: ten sam osobnik jako oba rodzice",
                        details=f"count={same_parent_pair}",
                    )
                )
            else:
                issues.append(ValidationIssue("OK", "Para rodziców: ojciec i matka to różne ID"))
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić father_id == mother_id"))

    # 11) Płeć rodzica vs rola (ojciec = M, matka = F) — wykrywa pomyłki / zamianę kolumn
    wrong_father_sex = 0
    wrong_mother_sex = 0
    if "father_id" in df_std.columns and "mother_id" in df_std.columns and people:
        try:
            for _, row in df_std.iterrows():
                cid = _str_id_cell(row.get("id"))
                fa = row.get("father_id")
                mo = row.get("mother_id")
                if _is_nonempty_parent(fa):
                    fa_s = _str_id_cell(fa)
                    pfa = people.get(fa_s)
                    if pfa is not None and pfa.sex in {"M", "F"} and pfa.sex != "M":
                        wrong_father_sex += 1
                        if cid:
                            export_rows.append(
                                ValidationExportRow(
                                    cid,
                                    "WARN",
                                    "Ojciec ma płeć F w rekordzie osobnika",
                                    f"father_id={fa_s} — w drzewie ojciec powinien być M; możliwa zamiana z matką lub błąd płci u rodzica.",
                                )
                            )
                if _is_nonempty_parent(mo):
                    mo_s = _str_id_cell(mo)
                    pmo = people.get(mo_s)
                    if pmo is not None and pmo.sex in {"M", "F"} and pmo.sex != "F":
                        wrong_mother_sex += 1
                        if cid:
                            export_rows.append(
                                ValidationExportRow(
                                    cid,
                                    "WARN",
                                    "Matka ma płeć M w rekordzie osobnika",
                                    f"mother_id={mo_s} — w drzewie matka powinna być F; możliwa zamiana z ojcem lub błąd płci u rodzica.",
                                )
                            )
            if wrong_father_sex > 0 or wrong_mother_sex > 0:
                issues.append(
                    ValidationIssue(
                        "WARN",
                        "Niespójność płci z rolą rodzica (sprawdź zamianę kolumn lub dane źródłowe)",
                        details=f"ojciec z płcią F: {wrong_father_sex}, matka z płcią M: {wrong_mother_sex}",
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        "OK",
                        "Płeć rodziców zgodna z rolą (ojciec M / matka F), gdzie płeć jest podana",
                    )
                )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się zweryfikować płci rodziców względem roli"))

    # 12) Kompletność wpisów o przodkach bezpośrednich (braki w danych — nie zawsze błąd)
    if "father_id" in df_std.columns and "mother_id" in df_std.columns:
        try:
            n_full = n_no_f = n_no_m = n_no_both = 0
            for _, row in df_std.iterrows():
                hf = _is_nonempty_parent(row.get("father_id"))
                hm = _is_nonempty_parent(row.get("mother_id"))
                if hf and hm:
                    n_full += 1
                elif not hf and not hm:
                    n_no_both += 1
                elif not hf:
                    n_no_f += 1
                else:
                    n_no_m += 1
            pct_full = 100.0 * n_full / total_rows if total_rows else 0.0
            issues.append(
                ValidationIssue(
                    "OK",
                    "Kompletność danych o rodzicach (struktura rekordów)",
                    details=(
                        f"pełna para (ojciec+matka): {n_full} ({pct_full:.1f}%), "
                        f"tylko brak ojca: {n_no_f}, tylko brak matki: {n_no_m}, brak obojga: {n_no_both}"
                    ),
                )
            )
            if n_no_both > 0 and n_no_both == total_rows:
                issues.append(
                    ValidationIssue(
                        "WARN",
                        "Wszystkie rekordy bez wskazania rodziców",
                        details="Drzewo nie ma krawędzi rodzic–dziecko — analizy rodowodowe będą ograniczone.",
                    )
                )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się policzyć kompletności rodziców"))

    # 13) Spójność lat w birth_date vs death_date (heurystyka po latach w tekście)
    if "birth_date" in df_std.columns and "death_date" in df_std.columns and "id" in df_std.columns:
        try:
            illogical = 0
            for _, row in df_std.iterrows():
                bys = _years_from_date_cell(row.get("birth_date"))
                dys = _years_from_date_cell(row.get("death_date"))
                if len(bys) < 1 or len(dys) < 1:
                    continue
                # Jeśli najpóźniejszy rok z pola „ur.” jest po najwcześniejszym roku ze „zg.” — podejrzenie błędu.
                if max(bys) > min(dys):
                    illogical += 1
                    rid = _str_id_cell(row.get("id"))
                    if rid:
                        export_rows.append(
                            ValidationExportRow(
                                rid,
                                "WARN",
                                "Daty: podejrzenie śmierci przed urodzeniem",
                                f"birth_date={row.get('birth_date')!r}, death_date={row.get('death_date')!r} "
                                f"(porównanie po wyciągniętych latach: max(ur.)={max(bys)}, min(zg.)={min(dys)})",
                            )
                        )
            if illogical > 0:
                issues.append(
                    ValidationIssue(
                        "WARN",
                        "Nielogiczna kolejność dat ur./zg. (wg lat w polach tekstowych)",
                        details=f"count={illogical} (heurystyka — sprawdź ręcznie nietypowe zapisy)",
                    )
                )
            else:
                issues.append(
                    ValidationIssue(
                        "OK",
                        "Daty ur./zg.: brak oczywistych sprzeczności (heurystyka lat w tekście)",
                    )
                )
        except Exception:
            issues.append(ValidationIssue("WARN", "Nie udało się sprawdzić spójności birth_date/death_date"))

    return ValidationReport(total_rows=total_rows, issues=issues, export_rows=tuple(export_rows))

