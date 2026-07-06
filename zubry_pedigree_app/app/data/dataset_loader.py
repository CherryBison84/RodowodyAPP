"""Wczytywanie CSV/XLSX, standaryzacja kolumn do schematu aplikacji i ścieżka bazy domyślnej."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

import numpy as np
import pandas as pd

from app.data.ebpb_formats import EBPB_FORMAT_LABELS, EbpbInputKind, ebpb_format_label

# Zgodność wsteczna (starsze importy UI / testów).
ebpb_format_source_suffix = ebpb_format_label

EBPB_SAMPLE_FILENAMES: tuple[str, ...] = (
    "EBPB_bison_report.xlsx",
    "EBPB_register.xlsx",
)

__all__ = [
    "DatasetInfo",
    "EBPB_FORMAT_LABELS",
    "EBPB_SAMPLE_FILENAMES",
    "EbpbInputKind",
    "STANDARD_BISON_REPORT_COLUMNS",
    "dataframe_app_schema_columns",
    "detect_ebpb_input_kind",
    "ebpb_format_label",
    "get_default_bison_report_path",
    "load_dataset_from_bytes",
    "load_dataset_from_path",
    "load_default_bison_report",
    "standardize_bison_report_dataframe",
]


@dataclass(frozen=True)
class DatasetInfo:
    """Metadane wczytanego zbioru po standaryzacji do schematu aplikacji."""

    rows: int
    columns: int
    ebpb_format: EbpbInputKind = "ebpb_report"


# Kolumny schematu aplikacji po imporcie (raport lub rejestr EBPB) — bez dodatkowych pól z arkusza.
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
    """Usuwa znaki nowej linii i skrajne spacje z tekstowej nazwy kolumny."""
    if not isinstance(col, str):
        return col
    return col.replace("\n", " ").strip()


def _optional_str(v: object) -> Optional[str]:
    """Konwertuje wartość arkusza na niepusty tekst albo ``None``."""
    if v is None:
        return None
    if isinstance(v, float) and np.isnan(v):
        return None
    s = str(v).strip()
    return s if s else None


def _norm_sex(v: object) -> Optional[str]:
    """Normalizuje płeć do ``M``/``F`` albo wartości pustej."""
    s = _optional_str(v)
    if s is None:
        return None
    s_up = s.upper()
    return s_up if s_up in {"M", "F"} else None


def _norm_line(v: object) -> Optional[str]:
    """Normalizuje linię rodowodową do ``LB``/``LC`` albo wartości pustej."""
    s = _optional_str(v)
    if s is None:
        return None
    s_up = s.upper()
    return s_up if s_up in {"LB", "LC"} else None


def _detect_csv_sep(text: str) -> str:
    """Wybiera separator po pierwszym wierszu (Excel PL często używa „;”)."""
    first = text.split("\n", 1)[0]
    if not first.strip():
        return ","
    n_semi = first.count(";")
    n_comma = first.count(",")
    return ";" if n_semi > n_comma else ","


def _read_csv(source: Path | BinaryIO) -> pd.DataFrame:
    """Wczytuje CSV, wykrywając separator dla źródeł binarnych z uploadu."""
    if isinstance(source, (str, Path)):
        return pd.read_csv(source, sep=None, engine="python")
    raw = source.read()
    text = raw.decode("utf-8-sig", errors="replace")
    return pd.read_csv(BytesIO(raw), sep=_detect_csv_sep(text))


def _read_dataframe_from_ext(source: Path | BinaryIO, *, ext: str) -> pd.DataFrame:
    """Wczytuje ramkę pandas według rozszerzenia pliku wejściowego."""
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
    """Wybiera wymaganą kolumnę źródłową lub zgłasza czytelny błąd importu."""
    col = _pick_optional_source_column(df, logical, candidates)
    if col is None:
        raise ValueError(
            f"Brak wymaganej kolumny „{logical}” w pliku "
            f"(szukano jednej z nazw: {list(candidates)}). "
            f"Kolumny w pliku: {list(df.columns)}"
        )
    return col


def _pick_optional_source_column(
    df: pd.DataFrame, logical: str, candidates: tuple[str, ...]
) -> str | None:
    """Wybiera opcjonalną kolumnę źródłową po nazwach kandydujących."""
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
    return None


def _series_from_optional_column(df: pd.DataFrame, col: str | None) -> pd.Series:
    """Zwraca serię kolumny lub pustą serię obiektową dla brakującego pola."""
    if col is None:
        return pd.Series([None] * len(df), index=df.index, dtype=object)
    return df[col]


def _has_app_schema_headers(df: pd.DataFrame) -> bool:
    """Sprawdza, czy arkusz wygląda na już zapisany w schemacie aplikacji."""
    return "id" in _columns_lower_map(df)


def _rename_columns_to_app_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Zmienia wielkość liter nazw kolumn na kanoniczne nazwy schematu aplikacji."""
    lower_map = _columns_lower_map(df)
    rename = {
        lower_map[key]: key
        for key in STANDARD_BISON_REPORT_COLUMNS
        if key in lower_map and lower_map[key] != key
    }
    return df.rename(columns=rename)


def _finalize_bison_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Czyści techniczny zapis pól i układa kolumny w standardowej kolejności.

    Nie usuwa rekordów ani nie zamienia nieznanych kodów domenowych na braki. Dzięki
    temu walidator widzi rzeczywisty stan wejścia, a decyzje o usunięciu rekordów są
    wykonywane dopiero w jawnym etapie transformacji.
    """
    df = df.copy()
    for col in ("id", "father_id", "mother_id"):
        if col in df.columns:
            df[col] = df[col].apply(_parse_id)
    if "sex" in df.columns:
        # Zachowaj np. kod `U`, aby walidator mógł go wykazać. Normalizacja do
        # M/F/None w tym miejscu ukrywałaby błąd danych źródłowych.
        sex = df["sex"].astype(str).str.strip().str.upper()
        df["sex"] = sex.where(df["sex"].notna() & sex.ne(""), other=None)
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
    schema = [c for c in STANDARD_BISON_REPORT_COLUMNS if c in df.columns]
    return df.loc[:, schema].reset_index(drop=True)


def _birth_location_series(df: pd.DataFrame) -> pd.Series:
    """
    Łączy miejsce i kraj urodzenia w jedno pole (raport: birth_loc_name + birth_country;
    rejestr: Birth location + Birth country; stary eksport: jedna kolumna „Birth location”).
    """
    lower_map = _columns_lower_map(df)
    loc_c = (
        lower_map.get("birth_loc_name")
        or lower_map.get("birth location")
        or lower_map.get("birth_location")
    )
    cc_c = lower_map.get("birth_country") or lower_map.get("birth country")
    if not loc_c and not cc_c:
        return pd.Series([None] * len(df), index=df.index, dtype=object)
    if loc_c and not cc_c:
        return df[loc_c]
    if cc_c and not loc_c:
        return df[cc_c]

    n = len(df)
    loc_vals = df[loc_c].tolist()
    cc_vals = df[cc_c].tolist()
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


def detect_ebpb_input_kind(df: pd.DataFrame) -> EbpbInputKind:
    """Rozpoznaje typ eksportu EBPB po nagłówkach (przed standaryzacją)."""
    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]
    if _has_app_schema_headers(df):
        return "app_schema"
    if _is_ebpb_register_format(df):
        return "ebpb_register"
    return "ebpb_report"


def _is_ebpb_register_format(df: pd.DataFrame) -> bool:
    """Rejestr EBPB — rozpoznanie po charakterystycznych nagłówkach arkusza."""
    lower_map = _columns_lower_map(df)
    register_markers = (
        "ebpb_id",
        "birth display",
        "death display",
        "birth day",
        "subline",
        "father_pedigree_line",
        "mother_pedigree_line",
    )
    return any(marker in lower_map for marker in register_markers)


def _standardize_ebpb_register_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Mapuje eksport rejestru EBPB (``EBPB_register.xlsx``) do schematu aplikacji."""
    col_sex = _pick_source_column(df, "Sex", ("Sex", "sex"))
    col_id = _pick_source_column(df, "Number", ("Number", "number", "id"))
    col_name = _pick_source_column(df, "Name", ("Name", "name"))
    col_alt = _pick_optional_source_column(df, "Alt name", ("Alt name", "alt_name"))
    col_line = _pick_optional_source_column(df, "Line", ("Line", "line"))
    col_by = _pick_optional_source_column(df, "Birth year", ("Birth year", "birth_year"))
    col_status = _pick_optional_source_column(df, "Status", ("Status", "status"))
    col_fid = _pick_source_column(
        df, "father_number", ("father_number", "Father", "father_id")
    )
    col_fname = _pick_optional_source_column(df, "father_name", ("father_name", "Father name"))
    col_fline = _pick_optional_source_column(df, "father_line", ("father_line", "Father line"))
    col_mid = _pick_source_column(
        df, "mother_number", ("mother_number", "Mother", "mother_id")
    )
    col_mname = _pick_optional_source_column(df, "mother_name", ("mother_name", "Mother name"))
    col_mline = _pick_optional_source_column(df, "mother_line", ("mother_line", "Mother line"))
    col_bdate = _pick_optional_source_column(
        df, "Birth display", ("Birth display", "Birth date", "birth_date")
    )
    col_ddate = _pick_optional_source_column(
        df, "Death display", ("Death display", "Death date", "death_date")
    )

    out = pd.DataFrame(
        {
            "sex": df[col_sex],
            "id": df[col_id],
            "name": df[col_name],
            "alt_name": _series_from_optional_column(df, col_alt),
            "line": _series_from_optional_column(df, col_line),
            "birth_year": _series_from_optional_column(df, col_by),
            "status": _series_from_optional_column(df, col_status),
            "father_id": df[col_fid],
            "father_name": _series_from_optional_column(df, col_fname),
            "father_line": _series_from_optional_column(df, col_fline),
            "mother_id": df[col_mid],
            "mother_name": _series_from_optional_column(df, col_mname),
            "mother_line": _series_from_optional_column(df, col_mline),
            "birth_date": _series_from_optional_column(df, col_bdate),
            "death_date": _series_from_optional_column(df, col_ddate),
            "birth_location": _birth_location_series(df),
        },
        index=df.index,
    )
    return _finalize_bison_dataframe(out)


def standardize_bison_report_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Konwertuje surowy arkusz do wspólnego schematu potrzebnego do rodowodu.

    Obsługiwane są:
    - starszy eksport z nagłówkami scalonymi (pandas: „Father”, „Unnamed: 8”…),
    - aktualny raport EBPB (m.in. „father_number”, „mother_number”, „birth_loc_name”),
    - rejestr EBPB (``EBPB_register.xlsx``: Birth/Death display, Birth location + country),
    - plik już w schemacie aplikacji (np. cleaned.xlsx z kolumnami id, sex, …).
    """
    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]

    # Rejestr przed schematem aplikacji (unika mylenia z oczyszczonym eksportem).
    if _is_ebpb_register_format(df):
        return _standardize_ebpb_register_dataframe(df)

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
    col_bdate = _pick_optional_source_column(
        df,
        "Birth date",
        ("Birth date", "birth_date", "Birth display"),
    )
    col_ddate = _pick_optional_source_column(
        df,
        "Death date",
        ("Death date", "death_date", "Death display"),
    )

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
            "birth_date": _series_from_optional_column(df, col_bdate),
            "death_date": _series_from_optional_column(df, col_ddate),
            "birth_location": _birth_location_series(df),
        },
        index=df.index,
    )

    return _finalize_bison_dataframe(out)


def _load_raw_dataframe(source: Path | BinaryIO, *, ext: str) -> pd.DataFrame:
    """Wczytuje surowy arkusz, preferując zakładkę ``Data set`` w plikach Excela."""
    ext = ext.lower()
    if ext in {".xlsx", ".xls"}:
        try:
            xl = pd.ExcelFile(source)
            sheet: str | int = "Data set" if "Data set" in xl.sheet_names else 0
            return pd.read_excel(source, sheet_name=sheet)
        except Exception:
            if isinstance(source, BytesIO):
                source.seek(0)
    return _read_dataframe_from_ext(source, ext=ext)


def _finalize_load(
    df_raw: pd.DataFrame,
    *,
    source_name: str = "",
) -> tuple[pd.DataFrame, DatasetInfo]:
    """Standaryzuje surową ramkę i buduje metadane rozpoznanego formatu EBPB."""
    kind = detect_ebpb_input_kind(df_raw)
    if kind == "ebpb_report" and source_name and "register" in source_name.lower():
        df_probe = df_raw.copy()
        df_probe.columns = [_clean_column_name(c) for c in df_probe.columns]
        if _is_ebpb_register_format(df_probe):
            kind = "ebpb_register"
    df_std = standardize_bison_report_dataframe(df_raw)
    return df_std, DatasetInfo(rows=len(df_std), columns=len(df_std.columns), ebpb_format=kind)


def load_dataset_from_path(path: str | Path) -> tuple[pd.DataFrame, DatasetInfo]:
    """Wczytuje CSV/XLS/XLSX z dysku i zwraca ramkę w schemacie aplikacji."""
    path = Path(path)
    df = _load_raw_dataframe(path, ext=path.suffix)
    return _finalize_load(df, source_name=path.name)


def load_dataset_from_bytes(data: bytes, filename: str) -> tuple[pd.DataFrame, DatasetInfo]:
    """Wczytuje plik uploadowany z UI na podstawie bajtów i nazwy pliku."""
    bio: BinaryIO = BytesIO(data)
    df = _load_raw_dataframe(bio, ext=Path(filename).suffix)
    return _finalize_load(df, source_name=filename)


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
