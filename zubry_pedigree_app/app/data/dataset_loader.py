"""Wczytywanie CSV/XLSX, standaryzacja kolumn do schematu aplikacji i ścieżka bazy domyślnej."""

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


# Kolumny schematu aplikacji po imporcie (raport EBPB / mapowanie) — bez dodatkowych pól z arkusza.
STANDARD_BISON_REPORT_COLUMNS: tuple[str, ...] = (
    "id",
    "name",
    "alt_name",
    "sex",
    "line",
    "birth_year",
    "status",
    "father_id",
    "father_name",
    "father_line",
    "mother_id",
    "mother_name",
    "mother_line",
    "birth_date",
    "death_date",
    "birth_location",
)


_ID_REGEX = re.compile(r"^\d+[A-Za-z]*$")


def dataframe_app_schema_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Tylko kolumny importowane do modelu (stała kolejność). Pomija dodatkowe kolumny z pliku.
    Gdy zbiór nie zawiera żadnej ze standardowych nazw, zwraca kopię bez zmian.
    """
    present = [c for c in STANDARD_BISON_REPORT_COLUMNS if c in df.columns]
    if not present:
        return df.copy()
    return df.loc[:, present].copy()


def _clean_column_name(col: object) -> object:
    if not isinstance(col, str):
        return col
    return col.replace("\n", " ").strip()


def _optional_str(v: object) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    return s if s else None


def _norm_sex(v: object) -> Optional[str]:
    s = _optional_str(v)
    if s is None:
        return None
    s_up = s.upper()
    return s_up if s_up in {"M", "F"} else None


def _norm_line(v: object) -> Optional[str]:
    s = _optional_str(v)
    if s is None:
        return None
    s_up = s.upper()
    return s_up if s_up in {"LB", "LC"} else None


def _drop_test_id_rows(df: pd.DataFrame, *, id_col: str, test_id: str) -> pd.DataFrame:
    try:
        return df[df[id_col].astype(str) != str(test_id)].reset_index(drop=True)
    except Exception:
        return df[df[id_col] != test_id].reset_index(drop=True)


def _detect_csv_sep(text: str) -> str:
    """Wybiera separator po pierwszym wierszu (Excel PL często używa „;”)."""
    first = text.split("\n", 1)[0]
    if not first.strip():
        return ","
    n_semi = first.count(";")
    n_comma = first.count(",")
    return ";" if n_semi > n_comma else ","


def _read_csv(source: Path | BinaryIO) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        return pd.read_csv(source, sep=None, engine="python")
    raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace")
    return pd.read_csv(BytesIO(raw), sep=_detect_csv_sep(text))


def _read_dataframe_from_ext(source: Path | BinaryIO, *, ext: str) -> pd.DataFrame:
    ext = ext.lower()
    if ext == ".csv":
        return _read_csv(source)
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(source, sheet_name=0)
    raise ValueError(f"Nieobsługiwany typ pliku: {ext}")


def _columns_lower_map(df: pd.DataFrame) -> dict[str, str]:
    """Pierwsza kolumna o danej nazwie (bez rozróżniania wielkości liter) → oryginalna nazwa."""
    out: dict[str, str] = {}
    for c in df.columns:
        key = str(c).strip().lower()
        if key and key not in out:
            out[key] = c
    return out


def _pick_source_column(df: pd.DataFrame, logical: str, candidates: tuple[str, ...]) -> str:
    lower_map = _columns_lower_map(df)
    for c in candidates:
        if c in df.columns:
            return c
        key = str(c).strip().lower()
        if key in lower_map:
            return lower_map[key]
    logical_key = logical.strip().lower()
    if logical_key in lower_map:
        return lower_map[logical_key]
    raise ValueError(
        f"Brak wymaganej kolumny „{logical}” w pliku "
        f"(szukano jednej z nazw: {list(candidates)}). "
        f"Kolumny w pliku: {list(df.columns)}"
    )


def _has_app_schema_headers(df: pd.DataFrame) -> bool:
    return "id" in _columns_lower_map(df)


def _rename_columns_to_app_schema(df: pd.DataFrame) -> pd.DataFrame:
    lower_map = _columns_lower_map(df)
    rename = {
        lower_map[key]: key
        for key in STANDARD_BISON_REPORT_COLUMNS
        if key in lower_map and lower_map[key] != key
    }
    return df.rename(columns=rename)


def _finalize_bison_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("id", "father_id", "mother_id"):
        if col in df.columns:
            df[col] = df[col].apply(_parse_id)
    if "sex" in df.columns:
        sex = df["sex"].astype(str).str.strip().str.upper()
        df["sex"] = sex.where(sex.isin(["M", "F"]), other=None)
    for col in [
        "name",
        "alt_name",
        "father_name",
        "mother_name",
        "birth_date",
        "death_date",
        "birth_location",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).where(df[col].notna(), other=None)
            df[col] = df[col].str.strip().replace({"": None})
    if "id" in df.columns:
        df = df[df["id"].notna()].reset_index(drop=True)
        df = _drop_test_id_rows(df, id_col="id", test_id="99999")
    schema = [c for c in STANDARD_BISON_REPORT_COLUMNS if c in df.columns]
    return df.loc[:, schema].reset_index(drop=True)


def _birth_location_series(df: pd.DataFrame) -> pd.Series:
    """
    Stary raport: jedna kolumna „Birth location”.
    Nowy raport EBPB: „birth_loc_name” + „birth_country” (łączone do jednego pola w modelu).
    """
    lower_map = _columns_lower_map(df)
    if "birth location" in lower_map:
        return df[lower_map["birth location"]]
    if "birth_location" in lower_map:
        return df[lower_map["birth_location"]]

    loc_c = lower_map.get("birth_loc_name")
    cc_c = lower_map.get("birth_country")
    if not loc_c and not cc_c:
        return pd.Series([None] * len(df), index=df.index, dtype=object)

    n = len(df)
    loc_vals = df[loc_c].tolist() if loc_c else [None] * n
    cc_vals = df[cc_c].tolist() if cc_c else [None] * n
    merged: list[Optional[str]] = []
    for lv, cv in zip(loc_vals, cc_vals):
        loc = _optional_str(lv)
        cc = _optional_str(cv)
        if loc and cc:
            merged.append(f"{loc}, {cc}")
        else:
            merged.append(loc or cc)
    return pd.Series(merged, index=df.index, dtype=object)


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

    Obsługiwane są:
    - starszy eksport z nagłówkami scalonymi (pandas: „Father”, „Unnamed: 8”…),
    - aktualny raport EBPB (m.in. „father_number”, „mother_number”, „birth_loc_name”),
    - plik już w schemacie aplikacji (np. cleaned.xlsx z kolumnami id, sex, …).
    """
    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]

    if _has_app_schema_headers(df):
        df = _rename_columns_to_app_schema(df)
        if "birth_location" not in df.columns:
            loc = _birth_location_series(df)
            if loc.notna().any():
                df["birth_location"] = loc
        return _finalize_bison_dataframe(df)

    col_sex = _pick_source_column(df, "Sex", ("Sex", "sex"))
    col_id = _pick_source_column(df, "Number", ("Number", "number", "id"))
    col_name = _pick_source_column(df, "Name", ("Name", "name"))
    col_alt = _pick_source_column(df, "Alt name", ("Alt name", "alt_name"))
    col_line = _pick_source_column(df, "Line", ("Line", "line"))
    col_by = _pick_source_column(df, "Birth year", ("Birth year", "birth_year"))
    col_status = _pick_source_column(df, "Status", ("Status", "status"))
    col_fid = _pick_source_column(
        df, "Father / father_number", ("Father", "father_number", "father_id")
    )
    col_fname = _pick_source_column(df, "Father name", ("Unnamed: 8", "father_name"))
    col_fline = _pick_source_column(df, "Father line", ("Unnamed: 9", "father_line"))
    col_mid = _pick_source_column(
        df, "Mother / mother_number", ("Mother", "mother_number", "mother_id")
    )
    col_mname = _pick_source_column(df, "Mother name", ("Unnamed: 11", "mother_name"))
    col_mline = _pick_source_column(df, "Mother line", ("Unnamed: 12", "mother_line"))
    col_bdate = _pick_source_column(df, "Birth date", ("Birth date", "birth_date"))
    col_ddate = _pick_source_column(df, "Death date", ("Death date", "death_date"))

    out = pd.DataFrame(
        {
            "sex": df[col_sex],
            "id": df[col_id],
            "name": df[col_name],
            "alt_name": df[col_alt],
            "line": df[col_line],
            "birth_year": df[col_by],
            "status": df[col_status],
            "father_id": df[col_fid],
            "father_name": df[col_fname],
            "father_line": df[col_fline],
            "mother_id": df[col_mid],
            "mother_name": df[col_mname],
            "mother_line": df[col_mline],
            "birth_date": df[col_bdate],
            "death_date": df[col_ddate],
            "birth_location": _birth_location_series(df),
        },
        index=df.index,
    )

    return _finalize_bison_dataframe(out)


def load_dataset_from_path(path: str | Path) -> tuple[pd.DataFrame, DatasetInfo]:
    path = Path(path)
    df = _read_dataframe_from_ext(path, ext=path.suffix)

    df_std = standardize_bison_report_dataframe(df)
    return df_std, DatasetInfo(rows=len(df_std), columns=len(df_std.columns))


def load_dataset_from_bytes(data: bytes, filename: str) -> tuple[pd.DataFrame, DatasetInfo]:
    bio: BinaryIO = BytesIO(data)
    df = _read_dataframe_from_ext(bio, ext=Path(filename).suffix)

    df_std = standardize_bison_report_dataframe(df)
    return df_std, DatasetInfo(rows=len(df_std), columns=len(df_std.columns))


def get_default_bison_report_path() -> Path:
    """
    Domyślny plik bazy, dostarczony w paczce aplikacji.
    """
    from app.runtime_path import data_dir

    return data_dir() / "EBPB_bison_report.xlsx"


def load_default_bison_report() -> tuple[pd.DataFrame, DatasetInfo]:
    """Wczytuje przykładową bazę z ``data/EBPB_bison_report.xlsx``."""
    path = get_default_bison_report_path()
    if not path.exists():
        raise FileNotFoundError(f"Nie znaleziono domyślnej bazy: {path}")
    return load_dataset_from_path(path)

