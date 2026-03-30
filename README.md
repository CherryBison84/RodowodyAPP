# RodowodyAPP / WisentPedigree Pro+

Główny kod aplikacji znajduje się w katalogu **`zubry_pedigree_app/`** (uruchamianie, baza domyślna, dokumentacja metodyki).

## Szybki start

```bash
cd zubry_pedigree_app
source ../.venv/bin/activate   # lub .venv w tym katalogu
python run_web.py
```

Alternatywnie (tylko serwer Streamlit, bez automatycznego otwarcia przeglądarki):

```bash
cd zubry_pedigree_app
python run_streamlit.py
```

Z katalogu nadrzędnego (repo root): `python run_streamlit.py` — dodaje `zubry_pedigree_app` do `PYTHONPATH`.
