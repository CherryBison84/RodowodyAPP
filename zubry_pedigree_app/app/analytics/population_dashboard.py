"""Tabele pomocnicze: kohorta aktywna, reproduktory, koncentracja ojców, ryzyko linii, porównanie okresów."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.analytics.population_genetics import TEST_ID, compute_population_genetics_stats
from app.pedigree.ancestor_pedigree import Person


def _parse_year(v: object) -> Optional[int]:
    if v is None:
        return None
    try:
        if isinstance(v, float) and v != v:
            return None
    except Exception:
        pass
    try:
        y = int(float(v))
    except Exception:
        return None
    if y < 1800 or y > datetime.now().year + 1:
        return None
    return y


def _norm_line(v: object) -> str:
    s = "" if v is None else str(v).strip().upper()
    return s if s in {"LB", "LC"} else "NA"


def global_ria_percent(f_values: List[float], *, eps: float = 1e-12) -> float:
    """% osobników z F > 0 (RIA w sensie z trendów F w aplikacji)."""
    if not f_values:
        return 0.0
    nz = sum(1 for f in f_values if float(f) > eps)
    return 100.0 * float(nz) / float(len(f_values))


def pct_missing_parent_slots(df: pd.DataFrame) -> float:
    """% „slotów” rodzicielskich pustych: (braki ojca + braki matki) / (2*n)."""
    if df is None or df.empty:
        return 0.0
    n = len(df)
    if n == 0:
        return 0.0
    mf = df["father_id"].isna().sum() if "father_id" in df.columns else 0
    mm = df["mother_id"].isna().sum() if "mother_id" in df.columns else 0
    return 100.0 * float(mf + mm) / float(2 * n)


def pct_individuals_incomplete_parents(df: pd.DataFrame) -> float:
    """% rekordów z brakiem ojca lub matki."""
    if df is None or df.empty or "father_id" not in df.columns:
        return 0.0
    m = df["father_id"].isna() | df["mother_id"].isna()
    return 100.0 * float(m.sum()) / float(len(df))


@dataclass(frozen=True)
class ActiveCohortSummary:
    """
    Kohorta „aktywna”: urodzeni w ostatnich `window_years` latach.
    Reproduktorzy: unikalne ID ojca/matki przy urodzeniach potomstwa w tym samym oknie.
    """

    window_years: int
    reference_year: int
    birth_year_min: int
    n_total: int
    n_males: int
    n_females: int
    n_reproducer_males: int
    n_reproducer_females: int
    n_reproducer_males_in_cohort: int
    n_reproducer_females_in_cohort: int


def summarize_active_cohort(
    df_std: pd.DataFrame,
    *,
    window_years: int = 20,
    reference_year: Optional[int] = None,
) -> ActiveCohortSummary:
    cy = int(reference_year or datetime.now().year)
    lo = cy - max(1, int(window_years))
    d = df_std.copy()
    d["id"] = d["id"].astype(str)
    d = d[d["id"] != TEST_ID]
    if d.empty:
        return ActiveCohortSummary(window_years, cy, lo, 0, 0, 0, 0, 0, 0, 0)
    y = d["birth_year"].map(_parse_year) if "birth_year" in d.columns else pd.Series([None] * len(d))
    d = d.assign(_by=y)
    d = d[d["_by"].notna() & (d["_by"] >= lo)]
    n = len(d)
    sex = d["sex"].astype(str).str.upper() if "sex" in d.columns else pd.Series([""] * len(d))
    nm = int((sex == "M").sum())
    nf = int((sex == "F").sum())

    # Potomstwo urodzone w oknie [lo, cy]
    d_all = df_std.copy()
    d_all["id"] = d_all["id"].astype(str)
    d_all = d_all[d_all["id"] != TEST_ID]
    yo = d_all["birth_year"].map(_parse_year) if "birth_year" in d_all.columns else pd.Series([None] * len(d_all))
    off = d_all[yo.notna() & (yo >= lo) & (yo <= cy)]

    sires = set()
    dams = set()
    if "father_id" in off.columns:
        for v in off["father_id"].dropna().astype(str).tolist():
            sires.add(v.strip())
    if "mother_id" in off.columns:
        for v in off["mother_id"].dropna().astype(str).tolist():
            dams.add(v.strip())

    active_ids = set(d["id"].astype(str).tolist())
    male_ids = set(d.loc[sex == "M", "id"].astype(str).tolist())
    female_ids = set(d.loc[sex == "F", "id"].astype(str).tolist())
    n_rm = len(sires)
    n_rf = len(dams)
    n_rm_cohort = len(sires & male_ids)
    n_rf_cohort = len(dams & female_ids)

    return ActiveCohortSummary(
        window_years=max(1, int(window_years)),
        reference_year=cy,
        birth_year_min=lo,
        n_total=n,
        n_males=nm,
        n_females=nf,
        n_reproducer_males=n_rm,
        n_reproducer_females=n_rf,
        n_reproducer_males_in_cohort=n_rm_cohort,
        n_reproducer_females_in_cohort=n_rf_cohort,
    )


def sire_offspring_concentration(df_std: pd.DataFrame, *, top_k: int = 5) -> Tuple[float, float, int]:
    """
    Zwraca (pct_top5, pct_top10, n_z_ojcem) — % potomstwa z znanym ojcem przypisanym do top 5 / 10 ojców wg liczby dzieci.
    """
    d = df_std.copy()
    d["id"] = d["id"].astype(str)
    d = d[d["id"] != TEST_ID]
    if d.empty or "father_id" not in d.columns:
        return 0.0, 0.0, 0
    fa = d["father_id"].dropna().astype(str).str.strip()
    fa = fa[fa != ""]
    n = int(len(fa))
    if n == 0:
        return 0.0, 0.0, 0
    vc = fa.value_counts()
    top5 = int(vc.head(5).sum())
    top10 = int(vc.head(10).sum())
    return 100.0 * top5 / n, 100.0 * top10 / n, n


def reproducers_by_offspring_decade(df_std: pd.DataFrame) -> pd.DataFrame:
    """Dla każdej dekady urodzenia potomka: liczba unikalnych ojców i matek."""
    d = df_std.copy()
    d["id"] = d["id"].astype(str)
    d = d[d["id"] != TEST_ID]
    if d.empty or "birth_year" not in d.columns:
        return pd.DataFrame(columns=["decade", "unikalni_ojcowie", "unikalne_matki", "urodzenia"])
    y = d["birth_year"].map(_parse_year)
    d = d.assign(_y=y)
    d = d[d["_y"].notna()]
    if d.empty:
        return pd.DataFrame(columns=["decade", "unikalni_ojcowie", "unikalne_matki", "urodzenia"])
    d["decade"] = (d["_y"] // 10) * 10
    rows = []
    for dec, g in d.groupby("decade"):
        n_b = len(g)
        us = 0
        ud = 0
        if "father_id" in g.columns:
            us = g["father_id"].dropna().astype(str).str.strip().nunique()
        if "mother_id" in g.columns:
            ud = g["mother_id"].dropna().astype(str).str.strip().nunique()
        rows.append({"decade": int(dec), "unikalni_ojcowie": int(us), "unikalne_matki": int(ud), "urodzenia": int(n_b)})
    return pd.DataFrame(rows).sort_values("decade")


def line_vulnerability_table(
    df_std: pd.DataFrame,
    *,
    recent_years: int = 30,
    active_window: int = 20,
    reference_year: Optional[int] = None,
) -> pd.DataFrame:
    """
    LB/LC: liczba urodzeń w ostatnich `recent_years`, liczba osobników w kohortcie `active_window`,
    wskaźnik „zagrożenia” (im mniej urodzeń, tym wyższy score).
    """
    cy = int(reference_year or datetime.now().year)
    lo_r = cy - max(1, int(recent_years))
    lo_a = cy - max(1, int(active_window))
    d = df_std.copy()
    d["id"] = d["id"].astype(str)
    d = d[d["id"] != TEST_ID]
    if d.empty or "birth_year" not in d.columns or "line" not in d.columns:
        return pd.DataFrame()
    y = d["birth_year"].map(_parse_year)
    d = d.assign(_y=y)
    d = d[d["_y"].notna()]
    d["line_n"] = d["line"].map(_norm_line)
    rows = []
    for line in ("LB", "LC"):
        dl = d[d["line_n"] == line]
        n_rec = int(dl[dl["_y"] >= lo_r].shape[0])
        n_act = int(dl[dl["_y"] >= lo_a].shape[0])
        n_dist_act = int(dl[dl["_y"] >= lo_a]["id"].nunique())
        # score: odwrotność „zdrowia”; +1 żeby uniknąć dzielenia przez zero
        risk = 1000.0 / float(n_rec + 1) + 50.0 / float(n_dist_act + 1)
        rows.append(
            {
                "Linia": line,
                f"Urodzenia {recent_years} lat": n_rec,
                f"Osobnicy {active_window} lat (n)": n_act,
                f"Unikalne ID {active_window} lat": n_dist_act,
                "Score ryzyka": round(risk, 4),
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty and "Score ryzyka" in out.columns:
        out = out.sort_values("Score ryzyka", ascending=False).reset_index(drop=True)
        out.insert(0, "Ranking ryzyka", range(1, len(out) + 1))
    return out


def compare_birth_periods(
    df_std: pd.DataFrame,
    people: Dict[str, Person],
    *,
    periods: Tuple[Tuple[int, int], ...] = ((1950, 1980), (1981, 2000), (2001, 9999)),
    max_generations_back: Optional[int] = 4,
) -> pd.DataFrame:
    """
    Dla każdego przedziału [od, do] lat urodzenia: n, średnie F, RIA%, % LB, % LC, f_e, średni EG.
    Rok 9999 = do bieżącego roku.
    """
    cy = datetime.now().year
    out_rows = []
    for y0, y1 in periods:
        hi = min(y1, cy) if y1 < 9000 else cy
        d = df_std.copy()
        d["id"] = d["id"].astype(str)
        d = d[d["id"] != TEST_ID]
        y = d["birth_year"].map(_parse_year) if "birth_year" in d.columns else pd.Series([None] * len(d))
        d = d.assign(_y=y)
        d = d[d["_y"].notna() & (d["_y"] >= y0) & (d["_y"] <= hi)]
        if d.empty:
            out_rows.append(
                {
                    "Okres": f"{y0}–{hi}",
                    "n": 0,
                    "śr. F": None,
                    "RIA %": None,
                    "% LB": None,
                    "% LC": None,
                    "f_e": None,
                    "śr. EG": None,
                }
            )
            continue
        try:
            st = compute_population_genetics_stats(
                d,
                people,
                max_generations_back=max_generations_back,
                calc_f=True,
                calc_completeness=True,
                calc_founders=True,
                calc_lines=True,
            )
            ria = global_ria_percent(st.f_values)
            lc = st.line_counts
            ntot = sum(lc.values()) or 1
            pct_lb = 100.0 * lc.get("LB", 0) / ntot
            pct_lc = 100.0 * lc.get("LC", 0) / ntot
            fe = st.founders.f_e if st.founders.f_e != float("inf") else None
            out_rows.append(
                {
                    "Okres": f"{y0}–{hi}",
                    "n": st.n,
                    "śr. F": round(st.inbreeding.mean_F, 6),
                    "RIA %": round(ria, 2),
                    "% LB": round(pct_lb, 2),
                    "% LC": round(pct_lc, 2),
                    "f_e": None if fe is None else round(float(fe), 4),
                    "śr. EG": round(st.completeness.mean_EG, 4),
                }
            )
        except Exception:
            out_rows.append(
                {
                    "Okres": f"{y0}–{hi}",
                    "n": len(d),
                    "śr. F": None,
                    "RIA %": None,
                    "% LB": None,
                    "% LC": None,
                    "f_e": None,
                    "śr. EG": None,
                }
            )
    return pd.DataFrame(out_rows)
