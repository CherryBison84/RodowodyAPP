"""Testy mapowania eksportów EBPB (raport i rejestr)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.data.dataset_loader import (  # noqa: E402
    detect_ebpb_input_kind,
    load_dataset_from_path,
    standardize_bison_report_dataframe,
)
from app.runtime_path import data_dir


@pytest.fixture(scope="module")
def report_path() -> Path:
    p = data_dir() / "EBPB_bison_report.xlsx"
    if not p.is_file():
        pytest.skip(f"Brak pliku testowego: {p}")
    return p


@pytest.fixture(scope="module")
def register_path() -> Path:
    p = data_dir() / "EBPB_register.xlsx"
    if not p.is_file():
        pytest.skip(f"Brak pliku testowego: {p}")
    return p


def test_detect_report_kind(report_path: Path) -> None:
    import pandas as pd

    df = pd.read_excel(report_path, sheet_name="Data set", nrows=5)
    assert detect_ebpb_input_kind(df) == "ebpb_report"


def test_detect_register_kind(register_path: Path) -> None:
    import pandas as pd

    df = pd.read_excel(register_path, sheet_name="Data set", nrows=5)
    assert detect_ebpb_input_kind(df) == "ebpb_register"


def test_load_report_maps_to_app_schema(report_path: Path) -> None:
    df, info = load_dataset_from_path(report_path)
    assert info.ebpb_format == "ebpb_report"
    assert info.rows > 1000
    assert "id" in df.columns
    assert df["id"].iloc[0] == "1"


def test_load_register_maps_to_app_schema(register_path: Path) -> None:
    df, info = load_dataset_from_path(register_path)
    assert info.ebpb_format == "ebpb_register"
    assert info.rows > 1000
    assert list(df.columns) == [
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
    ]
    assert df["id"].iloc[0] == "1"
    assert df["birth_date"].iloc[2] == "12.5.1891"
    assert "Berlin" in str(df["birth_location"].iloc[1])


def test_register_birth_location_merge() -> None:
    import pandas as pd

    raw = pd.DataFrame(
        {
            "Number": [1],
            "Name": ["X"],
            "Sex": ["M"],
            "father_number": [None],
            "mother_number": [None],
            "Birth year": [2000],
            "Birth location": ["Pless"],
            "Birth country": ["DE"],
            "Birth display": ["2000"],
            "Death display": [None],
            "ebpb_id": [10],
            "Subline": [None],
        }
    )
    out = standardize_bison_report_dataframe(raw)
    assert out["birth_location"].iloc[0] == "Pless, DE"
