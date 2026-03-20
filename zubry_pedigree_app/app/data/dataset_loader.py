from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional
from urllib.parse import urlparse
from urllib.request import urlopen

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
    # Pomijamy rekord testowy, jeśli występuje w pliku.
    try:
        df = df[df["id"].astype(str) != "99999"].reset_index(drop=True)
    except Exception:
        df = df[df["id"] != "99999"].reset_index(drop=True)
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


def load_raw_dataframe_from_bytes(data: bytes, filename: str) -> pd.DataFrame:
    """
    Wczytuje surową tabelę (bez standardyzacji mapowania kolumn).
    Użyteczne, gdy pobrano plik z internetu, ale jego schemat nie pasuje
    do domyślnych nazw kolumn w aplikacji.
    """
    bio: BinaryIO = BytesIO(data)
    ext = Path(filename).suffix.lower()
    if ext == ".csv":
        return pd.read_csv(bio)
    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(bio, sheet_name=0)
    raise ValueError(f"Nieobsługiwany typ pliku: {ext}")


def download_bytes_from_url(url: str, *, timeout_s: float = 120.0) -> bytes:
    """
    Pobiera plik binarny z podanego URL.
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Niepoprawny URL.")

    with urlopen(url, timeout=timeout_s) as resp:  # nosec B310
        return resp.read()


def _guess_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name
    return name if name else "downloaded_dataset.xlsx"


def load_dataset_from_url(
    url: str,
    *,
    filename_hint: str | None = None,
) -> tuple[pd.DataFrame, DatasetInfo]:
    """
    Pobiera plik z internetu (URL) i próbuje wczytać go jako bazę
    zgodną z domyślnym schematem aplikacji.
    """
    filename = filename_hint or _guess_filename_from_url(url)
    data = download_bytes_from_url(url)
    return load_dataset_from_bytes(data=data, filename=filename)


def load_raw_dataframe_from_url(
    url: str,
    *,
    filename_hint: str | None = None,
) -> pd.DataFrame:
    filename = filename_hint or _guess_filename_from_url(url)
    data = download_bytes_from_url(url)
    return load_raw_dataframe_from_bytes(data=data, filename=filename)


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


def standardize_bison_report_dataframe_with_column_mapping(
    df: pd.DataFrame,
    column_mapping: dict[str, Optional[str]],
    *,
    test_id: str = "99999",
) -> pd.DataFrame:
    """
    Standardizuje dowolnie sformatowaną bazę do wspólnego schematu aplikacji,
    na podstawie mapowania kolumn dostarczonego przez użytkownika.

    Oczekiwane klucze w `column_mapping` (wewnętrzne nazwy pól aplikacji):
      - id (ID/Number)
      - sex (M/F)
      - line (LB/LC)
      - birth_year (rok urodzenia)
      - father_id (ID ojca)
      - mother_id (ID matki)
      - name (opcjonalnie; imię/etykieta)
      - father_line (opcjonalnie)
      - mother_line (opcjonalnie)

    Funkcja zawsze tworzy pełny zestaw kolumn: patrz schema w `Person`.
    """

    df = df.copy()
    df.columns = [_clean_column_name(c) for c in df.columns]

    def _clean_mapping_val(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # czasem mapping może zawierać "nan" jako string
        s = str(v).strip()
        if not s or s.lower() == "nan" or s.lower() in {"none", "null"}:
            return None
        return _clean_column_name(s)

    mapping_clean: dict[str, Optional[str]] = {k: _clean_mapping_val(v) for k, v in column_mapping.items()}

    def _optional_str(v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        s = str(v).strip()
        return s if s else None

    def _norm_sex(v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        s = str(v).strip().upper()
        if s in {"M", "F"}:
            return s
        return None

    def _norm_line(v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, float) and np.isnan(v):
            return None
        s = str(v).strip().upper()
        if s in {"LB", "LC"}:
            return s
        return None

    def _get_series(expected_key: str, *, required: bool) -> pd.Series:
        raw_col = mapping_clean.get(expected_key)
        if not raw_col:
            if required:
                raise ValueError(f"Brak mapowania kolumny: {expected_key}")
            return pd.Series([None] * len(df), index=df.index)
        if raw_col not in df.columns:
            raise ValueError(f"Nie ma kolumny `{raw_col}` w pliku (wymagane: {expected_key}).")
        return df[raw_col]

    # Wymagane minimum dla całej logiki rodowodowej/rodowej
    s_id = _get_series("id", required=True)
    s_sex = _get_series("sex", required=True)
    s_line = _get_series("line", required=True)
    s_birth_year = _get_series("birth_year", required=True)
    s_father_id = _get_series("father_id", required=True)
    s_mother_id = _get_series("mother_id", required=True)

    # Opisowe/pomocnicze (opcjonalnie)
    s_name = _get_series("name", required=False)
    s_alt_name = _get_series("alt_name", required=False)
    s_father_name = _get_series("father_name", required=False)
    s_mother_name = _get_series("mother_name", required=False)
    s_father_line = _get_series("father_line", required=False)
    s_mother_line = _get_series("mother_line", required=False)
    s_status = _get_series("status", required=False)
    s_birth_date = _get_series("birth_date", required=False)
    s_death_date = _get_series("death_date", required=False)
    s_birth_location = _get_series("birth_location", required=False)

    out = pd.DataFrame(
        {
            "id": s_id.apply(_parse_id),
            "name": s_name.map(_optional_str),
            "alt_name": s_alt_name.map(_optional_str),
            "sex": s_sex.map(_norm_sex),
            "line": s_line.map(_norm_line),
            "birth_year": s_birth_year.where(s_birth_year.notna(), None),
            "status": s_status.map(_optional_str),
            "father_id": s_father_id.apply(_parse_id),
            "father_name": s_father_name.map(_optional_str),
            "father_line": s_father_line.map(_norm_line),
            "mother_id": s_mother_id.apply(_parse_id),
            "mother_name": s_mother_name.map(_optional_str),
            "mother_line": s_mother_line.map(_norm_line),
            "birth_date": s_birth_date.map(_optional_str),
            "death_date": s_death_date.map(_optional_str),
            "birth_location": s_birth_location.map(_optional_str),
        }
    )

    # Odfiltruj rekordy bez ID oraz rekord testowy.
    out = out[out["id"].notna()].reset_index(drop=True)
    try:
        out = out[out["id"].astype(str) != str(test_id)].reset_index(drop=True)
    except Exception:
        # fallback - jeśli coś pójdzie nie tak w typach
        out = out[out["id"] != test_id].reset_index(drop=True)

    return out

