"""
Automatyczne poprawki ramki `df_std` w ramach modelu aplikacji (bez zapisu do pliku źródłowego).

Kolejność reguł w `apply_auto_fixes` ma znaczenie (np. najpierw deduplikacja, potem odwołania do `id`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

import numpy as np
import pandas as pd

from app.data.validator import date_cell_years, id_cell_string, parse_year_field


@dataclass(frozen=True)
class AutoFixOptions:
    """Przełączniki reguł automatycznych poprawek (UI mapuje je na checkboxy)."""

    dedupe_ids: bool = True
    drop_rows_without_id: bool = False
    clear_birth_year_out_of_range: bool = True
    clear_death_date_on_conflict: bool = True
    remove_self_parent: bool = True
    cut_missing_parent_record: bool = True
    cut_parent_sex_collision: bool = True
    cut_parent_too_young: bool = True
    cut_parent_too_old: bool = False


def _norm_sex(v: object) -> Optional[str]:
    """M / F lub None (niespójne wartości traktujemy jak brak)."""
    if v is None or (isinstance(v, float) and v != v):
        return None
    s = str(v).strip().upper()
    return s if s in {"M", "F"} else None


def _valid_row_id(v: object) -> bool:
    """Czy wiersz ma identyfikator nadający się do klucza w drzewie."""
    s = id_cell_string(v)
    return bool(s) and s.lower() not in {"nan", "none"}


def apply_auto_fixes(
    df_in: pd.DataFrame,
    options: AutoFixOptions,
    *,
    year_min: int = 1800,
    year_max: int,
    parent_min_age_at_birth: int = 12,
    parent_max_age_at_birth: int = 80,
) -> tuple[pd.DataFrame, List[str]]:
    """
    Zwraca kopię ramki po sekwencyjnym zastosowaniu włączonych reguł oraz listę komunikatów (log).

    Parametry roku i wieku rodzica powinny być zgodne z walidacją / `config/gui.json`.
    """
    log: List[str] = []
    df = df_in.copy()

    if options.drop_rows_without_id and "id" in df.columns:
        before = len(df)
        mask = df["id"].map(_valid_row_id)
        df = df.loc[mask].reset_index(drop=True)
        removed = before - len(df)
        if removed:
            log.append(f"Usunięto {removed} wierszy bez poprawnego numeru osobnika.")

    if options.dedupe_ids and "id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
        dup = before - len(df)
        if dup:
            log.append(f"Usunięto {dup} duplikatów `id` (zostawiono pierwszy wiersz wg kolejności w pliku).")

    if df.empty:
        log.append("Zbiór jest pusty po wstępnych krokach — dalsze kroki pominięto.")
        return df, log

    ids = set(df["id"].astype(str).str.strip()) if "id" in df.columns else set()

    if options.clear_birth_year_out_of_range and "birth_year" in df.columns:
        n = 0
        for i in df.index:
            y = parse_year_field(df.at[i, "birth_year"])
            if y is not None and (y < year_min or y > year_max):
                df.at[i, "birth_year"] = np.nan
                n += 1
        if n:
            log.append(f"Wyczyszczono {n} wartości `birth_year` poza zakresem {year_min}–{year_max}.")

    if options.clear_death_date_on_conflict and "birth_date" in df.columns and "death_date" in df.columns:
        n = 0
        for i in df.index:
            bys = date_cell_years(df.at[i, "birth_date"])
            dys = date_cell_years(df.at[i, "death_date"])
            if len(bys) < 1 or len(dys) < 1:
                continue
            if max(bys) > min(dys):
                df.at[i, "death_date"] = None
                n += 1
        if n:
            log.append(f"Wyczyszczono {n} pól `death_date` przy sprzeczności z datą urodzenia (wg lat w tekście).")

    if options.remove_self_parent and "id" in df.columns:
        n_f = n_m = 0
        for i in df.index:
            cid = id_cell_string(df.at[i, "id"])
            if not cid:
                continue
            if "father_id" in df.columns:
                fa = df.at[i, "father_id"]
                if fa is not None and fa == fa and id_cell_string(fa) == cid:
                    df.at[i, "father_id"] = None
                    n_f += 1
            if "mother_id" in df.columns:
                mo = df.at[i, "mother_id"]
                if mo is not None and mo == mo and id_cell_string(mo) == cid:
                    df.at[i, "mother_id"] = None
                    n_m += 1
        if n_f or n_m:
            log.append(f"Usunięto powiązanie self-parent: ojciec={n_f}, matka={n_m}.")

    if "father_id" in df.columns and "mother_id" in df.columns:
        n = 0
        for i in df.index:
            fa = df.at[i, "father_id"]
            mo = df.at[i, "mother_id"]
            if fa is None or (isinstance(fa, float) and fa != fa):
                continue
            if mo is None or (isinstance(mo, float) and mo != mo):
                continue
            if id_cell_string(fa) == id_cell_string(mo) and id_cell_string(fa):
                df.at[i, "mother_id"] = None
                n += 1
        if n:
            log.append(f"W {n} wierszach wyczyszczono `mother_id` (ten sam ID co `father_id`).")

    if options.cut_missing_parent_record:
        n_f = n_m = 0
        for i in df.index:
            if "father_id" in df.columns:
                fa = df.at[i, "father_id"]
                if fa is not None and fa == fa:
                    fs = id_cell_string(fa)
                    if fs and fs not in ids:
                        df.at[i, "father_id"] = None
                        n_f += 1
            if "mother_id" in df.columns:
                mo = df.at[i, "mother_id"]
                if mo is not None and mo == mo:
                    ms = id_cell_string(mo)
                    if ms and ms not in ids:
                        df.at[i, "mother_id"] = None
                        n_m += 1
        if n_f or n_m:
            log.append(f"Odetkano brakujące rekordy rodziców: ojciec={n_f}, matka={n_m}.")

    sex_by_id: dict[str, str] = {}
    if "id" in df.columns and "sex" in df.columns:
        for i in df.index:
            pid = id_cell_string(df.at[i, "id"])
            sx = _norm_sex(df.at[i, "sex"])
            if pid and sx:
                sex_by_id[pid] = sx

    if options.cut_parent_sex_collision and "id" in df.columns:
        n_f = n_m = 0
        for i in df.index:
            if "father_id" in df.columns:
                fa = df.at[i, "father_id"]
                if fa is not None and fa == fa:
                    fs = id_cell_string(fa)
                    if fs and sex_by_id.get(fs) == "F":
                        df.at[i, "father_id"] = None
                        n_f += 1
            if "mother_id" in df.columns:
                mo = df.at[i, "mother_id"]
                if mo is not None and mo == mo:
                    ms = id_cell_string(mo)
                    if ms and sex_by_id.get(ms) == "M":
                        df.at[i, "mother_id"] = None
                        n_m += 1
        if n_f or n_m:
            log.append(f"Odetkano rodzica przy kolizji płci (ojciec≠M / matka≠F): ojciec={n_f}, matka={n_m}.")

    year_by_id: dict[str, Optional[int]] = {}
    if "id" in df.columns and "birth_year" in df.columns:
        for i in df.index:
            pid = id_cell_string(df.at[i, "id"])
            if pid:
                year_by_id[pid] = parse_year_field(df.at[i, "birth_year"])

    if (options.cut_parent_too_young or options.cut_parent_too_old) and "birth_year" in df.columns:
        n_y_f = n_y_m = n_o_f = n_o_m = 0
        for i in df.index:
            cy = parse_year_field(df.at[i, "birth_year"])
            if cy is None:
                continue
            if "father_id" in df.columns and options.cut_parent_too_young:
                fa = df.at[i, "father_id"]
                if fa is not None and fa == fa:
                    fs = id_cell_string(fa)
                    fy = year_by_id.get(fs) if fs else None
                    if fy is not None:
                        age = cy - fy
                        if age < parent_min_age_at_birth:
                            df.at[i, "father_id"] = None
                            n_y_f += 1
            if "mother_id" in df.columns and options.cut_parent_too_young:
                mo = df.at[i, "mother_id"]
                if mo is not None and mo == mo:
                    ms = id_cell_string(mo)
                    my = year_by_id.get(ms) if ms else None
                    if my is not None:
                        age = cy - my
                        if age < parent_min_age_at_birth:
                            df.at[i, "mother_id"] = None
                            n_y_m += 1
            if "father_id" in df.columns and options.cut_parent_too_old:
                fa = df.at[i, "father_id"]
                if fa is not None and fa == fa:
                    fs = id_cell_string(fa)
                    fy = year_by_id.get(fs) if fs else None
                    if fy is not None:
                        age = cy - fy
                        if age > parent_max_age_at_birth:
                            df.at[i, "father_id"] = None
                            n_o_f += 1
            if "mother_id" in df.columns and options.cut_parent_too_old:
                mo = df.at[i, "mother_id"]
                if mo is not None and mo == mo:
                    ms = id_cell_string(mo)
                    my = year_by_id.get(ms) if ms else None
                    if my is not None:
                        age = cy - my
                        if age > parent_max_age_at_birth:
                            df.at[i, "mother_id"] = None
                            n_o_m += 1
        if n_y_f or n_y_m:
            log.append(
                f"Odetkano „zbyt młodego” rodzica (różnica lat < {parent_min_age_at_birth}): "
                f"ojciec={n_y_f}, matka={n_y_m}."
            )
        if n_o_f or n_o_m:
            log.append(
                f"Odetkano „zbyt starego” rodzica (różnica lat > {parent_max_age_at_birth}): "
                f"ojciec={n_o_f}, matka={n_o_m}."
            )

    if not log:
        log.append("Brak zmian — wybrane reguły nie znalazły problemów do poprawy (lub były już spełnione).")
    return df, log


def default_year_max(cfg: Any) -> int:
    """Górny rok urodzenia jak w walidacji: bieżący rok + bufor z konfiguracji (`validation_max_year_buffer`)."""
    y = int(datetime.now().year)
    try:
        buf = int(getattr(cfg, "validation_max_year_buffer", 2))
    except Exception:
        buf = 2
    return y + buf
