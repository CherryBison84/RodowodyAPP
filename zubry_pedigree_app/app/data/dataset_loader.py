from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DatasetInfo:
    rows: int
    columns: int


_ID_REGEX = re.compile(r"^\d+[A-Za-z]*$")


def _clean_column_name(col: object) -> object:
    if not isinstance(col, str):
        return col
    return col.replace("\n", " ").strip()


def _parse_id(value: object) -> Optional[str]:
    """
    Excel często zapisuje ID jako float (np. 123.0) albo jako string (np. 693a).
    Dla grafu rodowodu potrzebujemy spójnego formatu klucza.
    """
    if value is None:
        return None
    if isinstance(value, float) and np.isnan(value):
        return None

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return None

    # Excel bywa zapisany jako np. "123.0" - zamieniamy na "123".
    if re.fullmatch(r"\d+\.0+", s):
        s = str(int(float(s)))

    # Uporządkuj whitespace.
    s = s.replace(" ", "")
    if _ID_REGEX.fullmatch(s):
        return s
    return None


def standardize_bison_report_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Konwertuje surowy arkusz do wspólnego schematu potrzebnego do rodowodu.
    """
    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]

    rename_map = {
        "Sex": "sex",
        "Number": "id",
        "Name": "name",
        "Alt name": "alt_name",
        "Line": "line",
        "Birth year": "birth_year",
        "Status": "status",
        "Father": "father_id",
        "Unnamed: 8": "father_name",
        "Unnamed: 9": "father_line",
        "Mother": "mother_id",
        "Unnamed: 11": "mother_name",
        "Unnamed: 12": "mother_line",
        "Birth date": "birth_date",
        "Death date": "death_date",
        "Birth location": "birth_location",
    }

    missing = [c for c in rename_map.keys() if c not in df.columns]
    if missing:
        raise ValueError(f"Brak wymaganych kolumn w pliku: {missing}")

    df = df.rename(columns=rename_map)

    df["id"] = df["id"].apply(_parse_id)
    df["father_id"] = df.get("father_id", pd.Series(index=df.index)).apply(_parse_id)
    df["mother_id"] = df.get("mother_id", pd.Series(index=df.index)).apply(_parse_id)

    # Ujednolicamy płeć do M/F (reszta -> None).
    sex = df["sex"].astype(str).str.strip().str.upper()
    df["sex"] = sex.where(sex.isin(["M", "F"]), other=None)

    # Daty/lokalizacje zostawiamy jako stringi, ale czyścimy whitespace.
    for col in ["name", "alt_name", "father_name", "mother_name", "birth_date", "death_date", "birth_location"]:
        if col in df.columns:
            df[col] = df[col].astype(str).where(df[col].notna(), other=None)
            df[col] = df[col].str.strip().replace({"": None})

    df = df[df["id"].notna()].reset_index(drop=True)
    return df


def load_dataset_from_path(path: str | Path) -> tuple[pd.DataFrame, DatasetInfo]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(path)
    elif ext in {".xlsx", ".xls"}:
        df = pd.read_excel(path, sheet_name=0)
    else:
        raise ValueError(f"Nieobsługiwany typ pliku: {ext}")

    df_std = standardize_bison_report_dataframe(df)
    return df_std, DatasetInfo(rows=len(df_std), columns=len(df_std.columns))


def load_dataset_from_bytes(data: bytes, filename: str) -> tuple[pd.DataFrame, DatasetInfo]:
    bio: BinaryIO = BytesIO(data)
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        df = pd.read_csv(bio)
    elif ext in {".xlsx", ".xls"}:
        df = pd.read_excel(bio, sheet_name=0)
    else:
        raise ValueError(f"Nieobsługiwany typ pliku: {ext}")

    df_std = standardize_bison_report_dataframe(df)
    return df_std, DatasetInfo(rows=len(df_std), columns=len(df_std.columns))


def get_default_bison_report_path() -> Path:
    """
    Domyślny plik bazy, dostarczony w paczce aplikacji.
    """
    # dataset_loader.py -> data -> app -> zubry_pedigree_app
    # -> repo root
    base_dir = Path(__file__).resolve().parents[2]
    return base_dir / "EBPB_bison_report.xlsx"


def load_default_bison_report() -> tuple[pd.DataFrame, DatasetInfo]:
    path = get_default_bison_report_path()
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono domyślnej bazy: {path}")
    return load_dataset_from_path(path)

