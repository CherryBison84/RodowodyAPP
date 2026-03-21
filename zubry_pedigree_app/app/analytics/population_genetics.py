"""
Zestawienia dla całej populacji: średnie pokrewieństwo, założyciele, linie,
kompletność rodowodu — to, co widać w podsumowaniach i raportach zbiorczych.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.analytics.inbreeding_wright import wright_inbreeding_F
from app.pedigree.ancestor_pedigree import Person, get_ancestor_levels_unbounded


TEST_ID = "99999"


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
    # EG (Equivalent Complete Generations) wprost wg definicji z metrics_definition:
    # EG = sum_{ancestor at generation n} (1/2)^n = sum_g a_g / 2^g
    mean_EG: float
    mean_PCI: float


@dataclass(frozen=True)
class PopulationFounderSummary:
    # f_e policzone na wkładach genów założycieli (founder-like stop),
    # gdzie brak ojca lub matki traktujemy jak "founder stop", spójnie z logiką w F.
    f_e: float
    # W tym podejściu (founder-stop spójny z `wright_inbreeding_F`) efektywna
    # liczba przodków wychodzi równoważna f_e.
    f_a: float


@dataclass(frozen=True)
class PopulationGeneticsStats:
    n: int
    n_founders_any_missing_parent: int
    inbreeding: PopulationInbreedingSummary
    completeness: PopulationCompletenessSummary
    founders: PopulationFounderSummary
    line_counts: Dict[str, int]
    # Surowe dane do wizualizacji
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
    Liczy zestaw metryk genetyki populacyjnej możliwych do wyliczenia z rodowodu:
    - Wright inbreeding F (dla całej populacji w trybie unbounded/bounded)
    - kompletność rodowodu (EG + PCI w uproszczeniu jako średnia PCL po pokoleniach)
    - efektywna liczba założycieli (f_e) z wkładów genów
    - rozkład linii (LB/LC z kolumny `line`)

    Uwaga dot. definicji founder stop:
    - tu spójnie z `wright_inbreeding_F` uznajemy, że brak ojca lub matki
      kończy ścieżkę i traktujemy osobnika jako źródło founder-like.
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

        @lru_cache(maxsize=None)
        def contributions_to_founders(pid: str) -> Dict[str, float]:
            p = people.get(pid)
            if p is None:
                return {pid: 1.0}
            if p.father_id is None or p.mother_id is None:
                return {pid: 1.0}

            fa = p.father_id
            mo = p.mother_id

            if fa not in people:
                fa_contrib = {fa: 1.0}
            else:
                fa_contrib = contributions_to_founders(fa)

            if mo not in people:
                mo_contrib = {mo: 1.0}
            else:
                mo_contrib = contributions_to_founders(mo)

            out: Dict[str, float] = {}
            for k, v in fa_contrib.items():
                out[k] = out.get(k, 0.0) + 0.5 * float(v)
            for k, v in mo_contrib.items():
                out[k] = out.get(k, 0.0) + 0.5 * float(v)
            return out

        founder_totals: Dict[str, float] = {}
        for pid in ids:
            contribs = contributions_to_founders(pid)
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

