"""Start terminalowej wersji WisentPedigree DataCleaner."""

from __future__ import annotations

from app.runtime_path import ensure_package_root_on_path

ensure_package_root_on_path()

from app.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
