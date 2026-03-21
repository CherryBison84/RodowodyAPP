# RodowodyAPP / WisentPedigree Pro+

Główny kod aplikacji znajduje się w katalogu **`zubry_pedigree_app/`** (uruchamianie, baza domyślna, dokumentacja metodyki).

## Szybki start

```bash
cd zubry_pedigree_app
source ../.venv/bin/activate   # lub .venv w tym katalogu
python run_tk.py
```

Streamlit:

```bash
cd zubry_pedigree_app
python run_streamlit.py
```

Z katalogu nadrzędnego (repo root) możesz też użyć skryptów w rootcie: `run_tk.py`, `run_streamlit.py` — dodają one `zubry_pedigree_app` do `PYTHONPATH`.
