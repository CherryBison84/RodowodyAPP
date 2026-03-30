# Zubry Pedigree App

Aplikacja do analizy rodowodowej żubrów — **interfejs webowy (Streamlit)**.

W tym katalogu znajdują się m.in. skrypty startowe, domyślna baza `EBPB_bison_report.xlsx` oraz `metrics_definition.md`.

## Uruchomienie (po instalacji)

Zalecane — Streamlit i otwarcie przeglądarki:

```bash
cd zubry_pedigree_app
python run_web.py
```

Tylko Streamlit (jak `streamlit run`):

```bash
cd zubry_pedigree_app
python run_streamlit.py
```

Bezpośrednio:

```bash
streamlit run app/ui/streamlit/streamlit_app.py
```

**Nie** uruchamiaj `streamlit_app.py` przez zwykłe `python streamlit_app.py` — Streamlit wymaga `streamlit run`.

## Zależności

```bash
pip install -r requirements.txt
```
