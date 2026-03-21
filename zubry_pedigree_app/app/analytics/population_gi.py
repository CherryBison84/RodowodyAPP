"""
Generation interval (GI), dekady GI oraz rozmiary rodzin pełnego rodzeństwa.

Wspólna logika dla GUI Tk i Streamlit (bez zależności od warstwy UI).
"""

from __future__ import annotations

from typing import Any, Mapping


def _norm_id(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() == "nan":
        return None
    return s


def _parse_year(v: object) -> int | None:
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


def _norm_sex(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip().upper()
    return s if s in {"M", "F"} else None


def _mean(xs: list[float]) -> float | None:
    return float(sum(xs)) / float(len(xs)) if xs else None


def compute_gi_and_family_data(
    df_use: Any,
    people: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Zwraca statystyki GI (4 ścieżki + średnia łączna), dekady dla trendu
    oraz rozmiary rodzin pełnego rodzeństwa (liczba potomków na parę rodziców).

    Klucze wyniku:
        gi_fs, gi_fd, gi_ms, gi_md, gi_all — float | None
        gi_decades — {"FS"|"FD"|"MS"|"MD": {dekada_start: [wiek, ...]}}
        family_sizes — list[int]
    """
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
            off_year = _parse_year(row.get("birth_year"))
            if off_year is None:
                continue
            sex = _norm_sex(row.get("sex"))
            if sex not in {"M", "F"}:
                continue
            fa_id = _norm_id(row.get("father_id"))
            mo_id = _norm_id(row.get("mother_id"))
            decade = (off_year // 10) * 10

            if sex == "M":
                if fa_id and fa_id in people and _parse_year(people[fa_id].birth_year) is not None:
                    parent_year = _parse_year(people[fa_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            father_son_ages.append(age)
                            gi_decades["FS"].setdefault(decade, []).append(age)
                if mo_id and mo_id in people and _parse_year(people[mo_id].birth_year) is not None:
                    parent_year = _parse_year(people[mo_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            mother_son_ages.append(age)
                            gi_decades["MS"].setdefault(decade, []).append(age)
            else:
                if fa_id and fa_id in people and _parse_year(people[fa_id].birth_year) is not None:
                    parent_year = _parse_year(people[fa_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            father_daughter_ages.append(age)
                            gi_decades["FD"].setdefault(decade, []).append(age)
                if mo_id and mo_id in people and _parse_year(people[mo_id].birth_year) is not None:
                    parent_year = _parse_year(people[mo_id].birth_year)
                    if parent_year is not None:
                        age = float(off_year) - float(parent_year)
                        if 0 <= age <= 80:
                            mother_daughter_ages.append(age)
                            gi_decades["MD"].setdefault(decade, []).append(age)
    except Exception:
        pass

    out["gi_fs"] = _mean(father_son_ages)
    out["gi_fd"] = _mean(father_daughter_ages)
    out["gi_ms"] = _mean(mother_son_ages)
    out["gi_md"] = _mean(mother_daughter_ages)
    all_gi = father_son_ages + father_daughter_ages + mother_son_ages + mother_daughter_ages
    out["gi_all"] = _mean(all_gi)
    out["gi_decades"] = gi_decades

    try:
        if "father_id" in df_use.columns and "mother_id" in df_use.columns:
            df_fam = df_use[df_use["father_id"].notna() & df_use["mother_id"].notna()].copy()
            if not df_fam.empty:
                df_fam["father_id"] = df_fam["father_id"].apply(_norm_id)
                df_fam["mother_id"] = df_fam["mother_id"].apply(_norm_id)
                df_fam = df_fam.dropna(subset=["father_id", "mother_id"])
                fam_sizes = df_fam.groupby(["father_id", "mother_id"]).size()
                if len(fam_sizes) > 0:
                    out["family_sizes"] = fam_sizes.astype(int).tolist()
    except Exception:
        pass

    return out
