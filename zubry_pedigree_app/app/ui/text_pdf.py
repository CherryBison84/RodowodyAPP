"""PDF z wieloliniowego tekstu (A4, matplotlib PdfPages) — bez dodatkowych pakietów."""

from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO, Iterable, Union

from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

PdfTarget = Union[str, Path, BinaryIO]


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


def plain_text_to_pdf_lines(text: str, *, wrap_width: int = 90) -> list[str]:
    """Spłaszcza tekst do listy linii gotowych do rysowania (łamanie długich wierszy)."""
    out: list[str] = []
    for raw_line in text.splitlines():
        raw_line = raw_line.rstrip()
        if not raw_line:
            out.append("")
            continue
        if set(raw_line) <= {"="} and len(raw_line) > 20:
            out.append(raw_line)
            continue
        out.extend(_wrap_words(raw_line, wrap_width))
    while out and out[-1] == "":
        out.pop()
    return out


def iter_pdf_line_chunks(lines: Iterable[str], *, max_lines_per_page: int) -> Iterable[list[str]]:
    buf: list[str] = []
    n = int(max_lines_per_page)
    for line in lines:
        buf.append(line)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


def write_plain_text_pdf(
    text: str,
    target: PdfTarget,
    *,
    wrap_width: int = 90,
    fig_w: float = 8.27,
    fig_h: float = 11.69,
    margin_x: float = 0.07,
    margin_top: float = 0.96,
    margin_bottom: float = 0.07,
    line_step: float = 0.0215,
    fontsize: float = 8.5,
    fontfamily: str = "DejaVu Sans",
) -> None:
    """Zapis wielostronicowy PDF (tekst verbatim z zawijaniem długich linii)."""
    lines = plain_text_to_pdf_lines(text, wrap_width=wrap_width)
    max_lines = max(10, int((margin_top - margin_bottom) / line_step))

    with PdfPages(target) as pdf:
        for chunk in iter_pdf_line_chunks(lines, max_lines_per_page=max_lines):
            fig = Figure(figsize=(fig_w, fig_h))
            fig.patch.set_facecolor("white")
            ax = fig.add_axes([0, 0, 1, 1])
            ax.axis("off")
            y = margin_top
            for line in chunk:
                ax.text(
                    margin_x,
                    y,
                    line,
                    fontsize=fontsize,
                    fontfamily=fontfamily,
                    transform=ax.transAxes,
                    va="top",
                )
                y -= line_step
            pdf.savefig(fig)
            plt.close(fig)


def plain_text_pdf_bytes(text: str, *, wrap_width: int = 90, fontsize: float = 8.5) -> bytes:
    buf = io.BytesIO()
    write_plain_text_pdf(text, buf, wrap_width=wrap_width, fontsize=fontsize)
    return buf.getvalue()


# Usuwamy potencjalne znaki problematyczne dla niektórych fontów PDF (np. zamienne myślniki).
_RE_SOFT_HYPHEN = re.compile("\u00ad")


def sanitize_text_for_pdf(text: str) -> str:
    return _RE_SOFT_HYPHEN.sub("", text)
