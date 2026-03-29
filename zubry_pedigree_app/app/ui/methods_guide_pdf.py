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

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

PdfTarget = Union[str, Path, BinaryIO]


def _flatten_references_markdown(section: str) -> str:
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


def _wrap_words(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return [] if not text.strip() else [text.strip()]
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur and cur_len + add > width:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur_len = cur_len + add if cur else len(w)
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def build_methods_guide_plain_text() -> str:
    from app.ui import help_content as hc

    refs = _flatten_references_markdown(hc.SECTION_REFERENCES)
    sep = "=" * 72
    return f"{hc.METHODS_GUIDE_PDF_INTRO}\n\n{sep}\n\n{refs}"


def _lines_for_pdf() -> list[str]:
    full = build_methods_guide_plain_text()
    out: list[str] = []
    for para in full.split("\n\n"):
        for raw_line in para.split("\n"):
            raw_line = raw_line.rstrip()
            if not raw_line:
                out.append("")
                continue
            if set(raw_line) <= {"="} and len(raw_line) > 20:
                out.append(raw_line)
                continue
            out.extend(_wrap_words(raw_line, 96))
        out.append("")
    while out and out[-1] == "":
        out.pop()
    return out


def write_methods_guide_pdf(target: PdfTarget) -> None:
    """
    Zapisuje wielostronicowy PDF (A4, DejaVu Sans, UTF-8).
    `target` — ścieżka lub bufor binarny (np. BytesIO).
    """
    lines = _lines_for_pdf()
    fig_w, fig_h = 8.27, 11.69
    margin_x = 0.07
    margin_top = 0.96
    margin_bottom = 0.07
    line_step = 0.0215
    max_lines = max(10, int((margin_top - margin_bottom) / line_step))
    fontsize = 8.8

    with PdfPages(target) as pdf:
        idx = 0
        n = len(lines)
        while idx < n:
            chunk = lines[idx : idx + max_lines]
            idx += max_lines
            fig = Figure(figsize=(fig_w, fig_h))
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis("off")
            y = margin_top
            for line in chunk:
                ax.text(
                    margin_x,
                    y,
                    line,
                    fontsize=fontsize,
                    fontfamily="DejaVu Sans",
                    transform=ax.transAxes,
                    va="top",
                )
                y -= line_step
            pdf.savefig(fig)
            plt.close(fig)


def methods_guide_pdf_bytes() -> bytes:
    buf = io.BytesIO()
    write_methods_guide_pdf(buf)
    return buf.getvalue()
