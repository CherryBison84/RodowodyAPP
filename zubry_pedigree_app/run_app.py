"""
Start z IDE: Run → ten plik. Domyślnie Streamlit w przeglądarce (`--ui web`).

Katalog roboczy: folder `zubry_pedigree_app/` (tam, gdzie leży ten plik).
"""

from __future__ import annotations

from app.runtime_path import ensure_package_root_on_path

ensure_package_root_on_path()

from app.main import main

if __name__ == "__main__":
    main()
