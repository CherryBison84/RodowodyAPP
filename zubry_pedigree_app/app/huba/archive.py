"""Pakowanie katalogu wyników do pobrania."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path


def zip_directory(root: Path) -> bytes:
    """Zwraca bajty archiwum ZIP z zawartością ``root`` (ścieżki względne do ``root``)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(root).as_posix())
    return buf.getvalue()
