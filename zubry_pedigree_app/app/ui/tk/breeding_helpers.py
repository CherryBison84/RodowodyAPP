"""
Propozycje par hodowlanych z uwzględnieniem pokrewieństwa i prostych ograniczeń.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from app.analytics.inbreeding_wright import batch_offspring_inbreeding_F_from_parent_pairs
from app.pedigree.ancestor_pedigree import Person


@dataclass(frozen=True)
class PairSuggestion:
    offspring_F: float
    dam_id: str
    dam_line: str
    dam_age: int
    sire_id: str
    sire_line: str
    sire_age: int


@dataclass(frozen=True)
class PairSuggestionResult:
    suggestions: list[PairSuggestion]
    female_candidates: int
    male_candidates: int

    @property
    def mean_F(self) -> float:
        if not self.suggestions:
            return 0.0
        return float(sum(s.offspring_F for s in self.suggestions)) / float(len(self.suggestions))

    @property
    def max_F(self) -> float:
        if not self.suggestions:
            return 0.0
        return max(s.offspring_F for s in self.suggestions)


def normalize_line(v: object) -> str:
    if v is None:
        return "NA"
    if isinstance(v, float) and v != v:
        return "NA"
    s = str(v).strip().upper()
    return s if s in {"LB", "LC"} else "NA"


def _filter_candidates(
    df_std: pd.DataFrame,
    *,
    sex: str,
    min_age: int,
    max_age: int,
    line_mode: str,
    candidate_limit: int,
    current_year: Optional[int] = None,
) -> list[str]:
    current_year = int(current_year or datetime.now().year)
    dfc = df_std.copy()
    dfc = dfc[dfc["sex"].astype(str).str.upper() == sex]
    if dfc.empty:
        return []

    dfc["_birth_int"] = pd.to_numeric(dfc["birth_year"], errors="coerce")
    dfc = dfc.dropna(subset=["_birth_int"])
    if dfc.empty:
        return []
    dfc["_birth_int"] = dfc["_birth_int"].astype(int)
    dfc["_age"] = current_year - dfc["_birth_int"]
    dfc = dfc[(dfc["_age"] >= min_age) & (dfc["_age"] <= max_age)]
    if dfc.empty:
        return []

    lmode = str(line_mode).strip().upper()
    dfc["_line_norm"] = dfc["line"].map(normalize_line)
    if lmode == "LB":
        dfc = dfc[dfc["_line_norm"] == "LB"]
    elif lmode == "LC":
        dfc = dfc[dfc["_line_norm"] == "LC"]
    elif lmode == "LB+LC":
        dfc = dfc[dfc["_line_norm"].isin(["LB", "LC"])]
    elif lmode == "NA":
        dfc = dfc[dfc["_line_norm"] == "NA"]
    # else: bez filtra

    if dfc.empty:
        return []

    limit = max(1, int(candidate_limit))
    mid_age = 0.5 * (float(min_age) + float(max_age))
    dfc["_age_dist"] = (dfc["_age"] - mid_age).abs()
    dfc = dfc.sort_values(by=["_age_dist", "_birth_int"], ascending=[True, True])
    return [str(x) for x in dfc["id"].astype(str).tolist()[:limit]]


def suggest_pairs_with_constraints(
    df_std: pd.DataFrame,
    people: Dict[str, Person],
    *,
    min_age: int,
    max_age: int,
    line_mode: str,
    candidate_limit: int,
    top_n: int,
    max_generations_back: int | None,
    max_dam_uses: int,
    max_sire_uses: int,
    goal_max_enabled: bool,
    goal_max_F: float,
    current_year: Optional[int] = None,
) -> PairSuggestionResult:
    current_year = int(current_year or datetime.now().year)
    min_age = int(min_age)
    max_age = int(max_age)
    if min_age > max_age:
        min_age, max_age = max_age, min_age

    women = _filter_candidates(
        df_std,
        sex="F",
        min_age=min_age,
        max_age=max_age,
        line_mode=line_mode,
        candidate_limit=candidate_limit,
        current_year=current_year,
    )
    men = _filter_candidates(
        df_std,
        sex="M",
        min_age=min_age,
        max_age=max_age,
        line_mode=line_mode,
        candidate_limit=candidate_limit,
        current_year=current_year,
    )

    if not women or not men:
        return PairSuggestionResult(suggestions=[], female_candidates=len(women), male_candidates=len(men))

    pair_meta: list[tuple[str, str]] = []
    for sire in men:
        for dam in women:
            pair_meta.append((sire, dam))

    F_vals = batch_offspring_inbreeding_F_from_parent_pairs(
        pair_meta,
        people,
        max_generations_back=max_generations_back,
    )

    # id -> age/line map
    dfc = df_std.copy()
    dfc["_birth_int"] = pd.to_numeric(dfc["birth_year"], errors="coerce")
    dfc = dfc.dropna(subset=["_birth_int"])
    dfc["_birth_int"] = dfc["_birth_int"].astype(int)
    dfc["_age"] = current_year - dfc["_birth_int"]

    line_map: dict[str, str] = {}
    age_map: dict[str, int] = {}
    for _, r in dfc.iterrows():
        pid = str(r.get("id"))
        line_map[pid] = normalize_line(r.get("line"))
        try:
            age_map[pid] = int(r.get("_age"))
        except Exception:
            age_map[pid] = -1

    rows: list[PairSuggestion] = []
    for (sire, dam), F_off in zip(pair_meta, F_vals):
        rows.append(
            PairSuggestion(
                offspring_F=float(F_off),
                dam_id=str(dam),
                dam_line=line_map.get(str(dam), "NA"),
                dam_age=age_map.get(str(dam), -1),
                sire_id=str(sire),
                sire_line=line_map.get(str(sire), "NA"),
                sire_age=age_map.get(str(sire), -1),
            )
        )

    rows.sort(key=lambda r: r.offspring_F)
    limit_top = max(1, int(top_n))
    dam_limit = max(1, int(max_dam_uses))
    sire_limit = max(1, int(max_sire_uses))

    accepted: list[PairSuggestion] = []
    dam_used: dict[str, int] = {}
    sire_used: dict[str, int] = {}

    for row in rows:
        if len(accepted) >= limit_top:
            break
        if dam_used.get(row.dam_id, 0) >= dam_limit:
            continue
        if sire_used.get(row.sire_id, 0) >= sire_limit:
            continue
        if goal_max_enabled and float(row.offspring_F) > float(goal_max_F):
            continue
        accepted.append(row)
        dam_used[row.dam_id] = dam_used.get(row.dam_id, 0) + 1
        sire_used[row.sire_id] = sire_used.get(row.sire_id, 0) + 1

    return PairSuggestionResult(
        suggestions=accepted,
        female_candidates=len(women),
        male_candidates=len(men),
    )

