"""Metryki zbiorcze: F, EG, PCI, założyciele (f_e, f_a), linie; oraz GI i rodziny pełnego rodzeństwa."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pandas as pd

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.pedigree.ancestor_pedigree import Person, get_ancestor_levels_unbounded


TEST_ID = "99999"


class FounderContributionComputer:
    """Udział genów od przodków przy founder-stop (jak przy F); suma udziałów = 1 dla pełnej gałęzi."""

    def __init__(self, people: Mapping[str, Person]):
        self._people = people
        self._memo: Dict[str, Dict[str, float]] = {}

    def contributions_for(self, person_id: str) -> Dict[str, float]:
        pid = _safe_str_id(person_id)
        if pid is None or pid not in self._people:
            return {}
        if pid in self._memo:
            return self._memo[pid]

        p = self._people.get(pid)
        if p is None:
            out = {pid: 1.0}
        elif p.father_id is None or p.mother_id is None:
            out = {pid: 1.0}
        else:
            fa = p.father_id
            mo = p.mother_id
            if fa not in self._people:
                fa_contrib = {fa: 1.0}
            else:
                fa_contrib = self.contributions_for(fa)
            if mo not in self._people:
                mo_contrib = {mo: 1.0}
            else:
                mo_contrib = self.contributions_for(mo)
            out: Dict[str, float] = {}
            for k, v in fa_contrib.items():
                out[k] = out.get(k, 0.0) + 0.5 * float(v)
            for k, v in mo_contrib.items():
                out[k] = out.get(k, 0.0) + 0.5 * float(v)

        self._memo[pid] = out
        return out


def compute_individual_founder_contributions(person_id: str, people: Mapping[str, Person]) -> Dict[str, float]:
    """Słownik założyciel_id → udział (0–1), suma = 1.0 przy pełnej rozwiązywalności gałęzi."""
    return FounderContributionComputer(people).contributions_for(person_id)


@dataclass(frozen=True)
class PopulationInbreedingSummary:
    n: int
    mean_F: float
    median_F: float
    min_F: float
    max_F: float
    zeros: int


@dataclass(frozen=True)
class PopulationCompletenessSummary:
    # EG — równoważne pełne pokolenia; PCI — średnia „pełności” poziomów (0–1).
    mean_EG: float
    mean_PCI: float


@dataclass(frozen=True)
class PopulationFounderSummary:
    # f_e — efektywna liczba założycieli z p_i; f_a — druga miara w tej samej logice founder-stop.
    f_e: float
    f_a: float


@dataclass(frozen=True)
class PopulationGeneticsStats:
    n: int
    n_founders_any_missing_parent: int
    inbreeding: PopulationInbreedingSummary
    completeness: PopulationCompletenessSummary
    founders: PopulationFounderSummary
    line_counts: Dict[str, int]
    # Serie do wykresów (F, EG, PCI na osobnika).
    f_values: List[float]
    eg_values: List[float]
    pci_values: List[float]
    founder_contributions: Dict[str, float]  # p_i (znormalizowane do 1)


def _safe_str_id(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _normalize_line(v: object) -> str:
    s = "" if v is None else str(v).strip().upper()
    if s in {"LB", "LC"}:
        return s
    return "NA"


def compute_population_genetics_stats(
    df_std: pd.DataFrame,
    people: Dict[str, Person],
    *,
    max_generations_back: int | None,
    calc_f: bool = True,
    calc_completeness: bool = True,
    calc_founders: bool = True,
    calc_lines: bool = True,
) -> PopulationGeneticsStats:
    """
    Zbiór F, kompletności, f_e/f_a i linii dla wierszy `df_std` (limit głębokości jak przy F).
    Founder-stop: brak ojca lub matki kończy gałąź — spójnie z `wright_inbreeding_F`.
    """

    if df_std is None or df_std.empty:
        raise ValueError("Brak danych (df_std).")

    df_use = df_std.copy()
    df_use["id"] = df_use["id"].astype(str)
    df_use = df_use[df_use["id"] != TEST_ID].reset_index(drop=True)

    ids: List[str] = [str(x) for x in df_use["id"].tolist() if str(x) in people]
    n = int(len(ids))
    if n == 0:
        raise ValueError("Po odfiltrowaniu `99999` i brakach rekordów nie ma osób do policzenia.")

    Fs: List[float] = []
    EG_values: List[float] = []
    PCI_values: List[float] = []

    # --- Inbreeding F (populacyjnie) ---
    if calc_f:
        for pid in ids:
            res = wright_inbreeding_F(
                person_id=pid,
                people=people,
                max_generations_back=max_generations_back,
            )
            Fs.append(float(res.F))

        zeros = int(sum(1 for f in Fs if abs(f) < 1e-15))
        inb = PopulationInbreedingSummary(
            n=n,
            mean_F=float(mean(Fs)),
            median_F=float(median(Fs)),
            min_F=float(min(Fs)),
            max_F=float(max(Fs)),
            zeros=zeros,
        )
    else:
        inb = PopulationInbreedingSummary(n=n, mean_F=0.0, median_F=0.0, min_F=0.0, max_F=0.0, zeros=0)

    # --- Founder-like stop (dowolny brak rodzica) ---
    # founder_any_missing_parent:
    # ojciec lub matka jest nieznana
    n_founders_any_missing_parent = int(
        df_use["father_id"].isna().values.sum() + df_use["mother_id"].isna().values.sum()  # noqa: PLR2004
    )
    # powyższe sumuje ojciec+matka, więc przeliczmy prawidłowo:
    n_founders_any_missing_parent = int(
        (df_use["father_id"].isna() | df_use["mother_id"].isna()).values.sum()
    )

    # --- Kompletnosć rodowodu (EG + PCI) ---
    if calc_completeness:
        for pid in ids:
            levels = get_ancestor_levels_unbounded(person_id=pid, people=people)
            # Pomijamy poziom 0 (sam osobnik).
            by_gen: Dict[int, int] = {}
            for _aid, lvl in levels.items():
                if lvl is None:
                    continue
                if lvl <= 0:
                    continue
                by_gen[lvl] = by_gen.get(lvl, 0) + 1

            if not by_gen:
                EG_values.append(0.0)
                PCI_values.append(0.0)
                continue

            G = max(by_gen.keys())
            pcl_values: List[float] = []
            eg = 0.0
            for g in range(1, G + 1):
                a_g = by_gen.get(g, 0)
                pcl_g = float(a_g) / float(2**g)
                pcl_values.append(pcl_g)
                eg += pcl_g  # bo pcl_g = a_g/2^g

            EG_values.append(eg)
            PCI_values.append(float(sum(pcl_values)) / float(G))

        completeness = PopulationCompletenessSummary(
            mean_EG=float(mean(EG_values)),
            mean_PCI=float(mean(PCI_values)),
        )
    else:
        completeness = PopulationCompletenessSummary(mean_EG=0.0, mean_PCI=0.0)

    # --- Wkład założycieli (f_e) ---
    founder_contributions: Dict[str, float] = {}
    f_e = 0.0

    if calc_founders:
        # f_e = 1 / sum_i p_i^2, gdzie p_i to średni wkład genów założyciela i do populacji.
        #
        # Zakładamy, że wkład dla osobnika traktuje brak ojca lub matki jak founder stop,
        # analogicznie do F: cała gałąź kończy się i nie schodzimy dalej.

        fc = FounderContributionComputer(people)
        founder_totals: Dict[str, float] = {}
        for pid in ids:
            contribs = fc.contributions_for(pid)
            for founder_id, v in contribs.items():
                founder_totals[founder_id] = founder_totals.get(founder_id, 0.0) + float(v)

        # p_i = avg over individuals of contributions.
        denom = float(n)
        sum_sq = 0.0
        for founder_id, total in founder_totals.items():
            p_i = float(total) / denom
            founder_contributions[founder_id] = p_i
            sum_sq += p_i * p_i
        f_e = float("inf") if sum_sq <= 0 else 1.0 / sum_sq

    # --- Rozkład linii (LB/LC) ---
    line_counts: Dict[str, int] = {"LB": 0, "LC": 0, "NA": 0}
    if calc_lines and "line" in df_use.columns:
        for v in df_use["line"].tolist():
            line_counts[_normalize_line(v)] = line_counts.get(_normalize_line(v), 0) + 1

    return PopulationGeneticsStats(
        n=n,
        n_founders_any_missing_parent=n_founders_any_missing_parent,
        inbreeding=inb,
        completeness=completeness,
        founders=PopulationFounderSummary(f_e=f_e, f_a=f_e),
        line_counts=line_counts,
        f_values=Fs,
        eg_values=EG_values,
        pci_values=PCI_values,
        founder_contributions=founder_contributions,
    )


# --- GI i rodziny pełnego rodzeństwa (wspólne UI) ---


def _gi_norm_id(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _gi_parse_year(v: object) -> Optional[int]:
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


def _gi_norm_sex(v: object) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip().upper()
    return s if s in {"M", "F"} else None


def _gi_mean(xs: list[float]) -> Optional[float]:
    return float(sum(xs)) / float(len(xs)) if xs else None


def compute_gi_and_family_data(
    df_use: Any,
    people: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """GI (cztery ścieżki + średnia), zgrupowanie po dekadach, listy wielkości rodzin pełnego rodzeństwa."""
    out: dict[str, Any] = {
        "gi_fs": None,
        "gi_fd": None,
        "gi_ms": None,
        "gi_md": None,
        "gi_all": None,
        "gi_decades": {"FS": {}, "FD": {}, "MS": {}, "MD": {}},
        "family_sizes": [],
    }
    if df_use is None or getattr(df_use, "empty", True) or not people:
        return out

    father_son_ages: list[float] = []
    father_daughter_ages: list[float] = []
    mother_son_ages: list[float] = []
    mother_daughter_ages: list[float] = []
    gi_decades: dict[str, dict[int, list[float]]] = {"FS": {}, "FD": {}, "MS": {}, "MD": {}}

    try:
        for _, row in df_use.iterrows():
            off_year = _gi_parse_year(row.get("birth_year"))
            if off_year is None:
                continue
            sex = _gi_norm_sex(row.get("sex"))
            if sex not in {"M", "F"}:
                continue
            fa_id = _gi_norm_id(row.get("father_id"))
            mo_id = _gi_norm_id(row.get("mother_id"))
            decade = (off_year // 10) * 10

            if sex == "M":
                if fa_id and fa_id in people and _gi_parse_year(people[fa_id].birth_year) is not None:
                    parent_year = _gi_parse_year(people[fa_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            father_son_ages.append(age)
                            gi_decades["FS"].setdefault(decade, []).append(age)
                if mo_id and mo_id in people and _gi_parse_year(people[mo_id].birth_year) is not None:
                    parent_year = _gi_parse_year(people[mo_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            mother_son_ages.append(age)
                            gi_decades["MS"].setdefault(decade, []).append(age)
            else:
                if fa_id and fa_id in people and _gi_parse_year(people[fa_id].birth_year) is not None:
                    parent_year = _gi_parse_year(people[fa_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            father_daughter_ages.append(age)
                            gi_decades["FD"].setdefault(decade, []).append(age)
                if mo_id and mo_id in people and _gi_parse_year(people[mo_id].birth_year) is not None:
                    parent_year = _gi_parse_year(people[mo_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            mother_daughter_ages.append(age)
                            gi_decades["MD"].setdefault(decade, []).append(age)
    except Exception:
        pass

    out["gi_fs"] = _gi_mean(father_son_ages)
    out["gi_fd"] = _gi_mean(father_daughter_ages)
    out["gi_ms"] = _gi_mean(mother_son_ages)
    out["gi_md"] = _gi_mean(mother_daughter_ages)
    all_gi = father_son_ages + father_daughter_ages + mother_son_ages + mother_daughter_ages
    out["gi_all"] = _gi_mean(all_gi)
    out["gi_decades"] = gi_decades

    try:
        if "father_id" in df_use.columns and "mother_id" in df_use.columns:
            df_fam = df_use[df_use["father_id"].notna() & df_use["mother_id"].notna()].copy()
            if not df_fam.empty:
                df_fam["father_id"] = df_fam["father_id"].apply(_gi_norm_id)
                df_fam["mother_id"] = df_fam["mother_id"].apply(_gi_norm_id)
                df_fam = df_fam.dropna(subset=["father_id", "mother_id"])
                fam_sizes = df_fam.groupby(["father_id", "mother_id"]).size()
                if len(fam_sizes) > 0:
                    out["family_sizes"] = fam_sizes.astype(int).tolist()
    except Exception:
        pass

    return out

