# -*- coding: utf-8 -*-
"""
Krótki „Przewodnik metod” w PDF — treść spójna z help_content (skrót metod + literatura).
Używa matplotlib.backends.backend_pdf (bez dodatkowych pakietów).
"""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, Union

from app.ui.text_pdf import write_plain_text_pdf

PdfTarget = Union[str, Path, BinaryIO]


def _flatten_references_markdown(section: str) -> str:
    """Markdown z sekcji „Literatura” — zwykły tekst do PDF (bez pogrubień)."""
    lines_out: list[str] = []
    for line in section.splitlines():
        ln = line.strip()
        if not ln:
            lines_out.append("")
            continue
        if ln.startswith("## "):
            lines_out.append("")
            lines_out.append(ln[3:].upper())
            lines_out.append("")
            continue
        ln = re.sub(r"\*\*(.+?)\*\*", r"\1", ln)
        if ln.startswith("*") and ln.endswith("*") and len(ln) > 2:
            ln = ln[1:-1]
        lines_out.append(ln)
    return "\n".join(lines_out).strip()


def build_methods_guide_plain_text() -> str:
    """Pełny tekst przewodnika: wstęp + literatura z help_content."""
    from app.ui import help_content as hc

    refs = _flatten_references_markdown(hc.SECTION_REFERENCES)
    sep = "=" * 72
    return f"{hc.METHODS_GUIDE_PDF_INTRO}\n\n{sep}\n\n{refs}"


def write_methods_guide_pdf(target: PdfTarget) -> None:
    """Zapis przewodnika do PDF (A4, DejaVu Sans); cel — ścieżka lub bufor (np. BytesIO)."""
    write_plain_text_pdf(
        build_methods_guide_plain_text(),
        target,
        wrap_width=96,
        fontsize=8.8,
    )


def methods_guide_pdf_bytes() -> bytes:
    """Cały PDF w pamięci (bytes) — eksport programowy / zapis pliku."""
    buf = io.BytesIO()
    write_methods_guide_pdf(buf)
    return buf.getvalue()
