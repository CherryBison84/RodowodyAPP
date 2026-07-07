# Zubry Pedigree App — HUBA-WPB Cleaner

**Wersja (pyproject): 1.2.0** — pełny opis i instalacja: **[README.md w katalogu nadrzędnym](../README.md)**.

Aplikacja **Streamlit** do wczytywania baz rodowodowych żubrów, **walidacji**, **edycji ręcznej**, **automatycznych poprawek** i eksportu wyników (tryb wsadowy z JSON).

## Struktura katalogów

| Katalog | Zawartość |
|---------|-----------|
| `app/` | Logika: `data/`, `huba/`, `pedigree/`, `analytics/`, `ui/streamlit/` |
| `app/assets/` | Logo, ikona i zasoby graficzne UI |
| `config/` | Przykładowe konfiguracje JSON (`gui.json`, projekty HUBA) |
| `data/` | Przykładowe bazy: `EBPB_bison_report.xlsx` (raport), `EBPB_register.xlsx` (rejestr) |
| `docs/` | `metrics_definition.md` — definicje metryk |
| `outputs/` | Wyniki batch (generowany lokalnie, w `.gitignore`) |

## Szybki start

```bash
pip install -r requirements.txt
python run_web.py
```

Alternatywa: `python run_streamlit.py` (sam serwer) lub `python run_app.py` (CLI: UI albo `--project-config`).

## Wersja terminalowa bez GUI

```bash
python run_cli.py run --input data/EBPB_bison_report.xlsx --project-name test_terminal
```

Kilka plików w jednym uruchomieniu:

```bash
python run_cli.py run --input data/EBPB_bison_report.xlsx data/EBPB_register.xlsx --project-name pakiet_terminal
```

Konfiguracja JSON:

```bash
python run_cli.py init-config config/datacleaner_cli.example.json
python run_cli.py run --config config/datacleaner_cli.example.json
```

Wyniki: `outputs/<nazwa_projektu>/`, w tym `comparison.csv`, `final_report.html`, `manifest.json` i oczyszczone bazy.

## Tryb wsadowy (HUBA)

Etapy: `load` → `validate` → `transform` → `export` (`app/huba/stages.py`).

```bash
python app/main.py --project-config config/huba_project.example.json
```

Wyniki trafiają do `outputs/<nazwa_projektu>/` (manifest, pliki oczyszczone, raporty walidacji).

Architektura, przepływ danych, instrukcja testowania i opis wykorzystania AI znajdują się w
**[głównym README](../README.md)**.
