# Zubry Pedigree App

Aplikacja do analizy rodowodowej żubrów (Tkinter + Streamlit).

W tym katalogu znajdują się m.in. skrypty startowe, domyślna baza `EBPB_bison_report.xlsx` oraz `metrics_definition.md`.

**Streamlit** (`app/ui/streamlit/`) odwzorowuje główne moduły wersji Tk: wczytywanie, osobniki (z liniami), rodowód, analizy (F + mating), populacja (wykresy), raport tekstowy. Pełny eksport DOC/PDF i część wykresów zaawansowanych (GI, trendy czasowe) są nadal w Tk.

## Uruchomienie (po instalacji)

### Tkinter
```bash
cd zubry_pedigree_app
python run_tk.py
```

Alternatywnie:
```bash
python -m app.ui.tk.main
```

### Streamlit

Zalecane (uruchamia właściwy kontekst Streamlit — bez ostrzeżeń „ScriptRunContext”):

```bash
cd zubry_pedigree_app
python run_streamlit.py
```

Alternatywnie bezpośrednio:

```bash
streamlit run app/ui/streamlit/streamlit_app.py
```

**Nie** uruchamiaj `streamlit_app.py` przez zwykłe `python streamlit_app.py` — Streamlit wymaga `streamlit run`.

