"""Etykiety formatów wejściowych EBPB (bez zależności od pandas)."""

from __future__ import annotations

from typing import Literal

EbpbInputKind = Literal["app_schema", "ebpb_report", "ebpb_register"]

EBPB_FORMAT_LABELS: dict[EbpbInputKind, str] = {
    "app_schema": "schemat aplikacji",
    "ebpb_report": "raport EBPB",
    "ebpb_register": "rejestr EBPB",
}


def ebpb_format_label(kind: str) -> str:
    """Krótka etykieta formatu do UI (np. przy nazwie pliku)."""
    return EBPB_FORMAT_LABELS.get(kind, kind)  # type: ignore[arg-type]
