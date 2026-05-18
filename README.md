# WisentPedigree Pro+ (RodowodyAPP)

**Wersja aplikacji (pakiet): 0.6.0**

**HUBA-WPB Cleaner** — aplikacja **webowa (Streamlit)** do wczytywania baz rodowodowych żubrów, **walidacji** (wykresy podsumowań, eksport CSV), **automatycznych poprawek** i eksportu oczyszczonych plików. Interfejs i treści pomocy są po polsku.

Kod źródłowy: katalog **`zubry_pedigree_app/`**.

## Wymagania

- Python **3.10+** (zalecany 3.11–3.14)
- Windows, macOS lub Linux

## Instalacja

```bash
cd zubry_pedigree_app
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uruchomienie

**Zalecane** — Streamlit z wyborem portu i otwarciem przeglądarki:

```bash
cd zubry_pedigree_app
python3 run_web.py
```

Tylko serwer Streamlit:

```bash
python3 run_streamlit.py
```

Z katalogu głównego repozytorium:

```bash
python3 run_streamlit.py
```

Tryb wsadowy (bez UI):

```bash
cd zubry_pedigree_app
python3 app/main.py --project-config config/huba_project.example.json
```

Na macOS, przy problemach z obserwatorem plików: `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`.

## Nawigacja w aplikacji (HUBA)

1. **Krok 1 — Wczytanie danych** — upload CSV/XLSX, katalog plików, łączenie zbiorów.
2. **Krok 2 — Walidacja** — kategorie kontroli, wykresy, eksport CSV z problemami.
3. **Krok 3 — Czyszczenie ręczne** — edycja rekordów (gdy włączone w konfiguracji nawigacji).
4. **Krok 4 — Czyszczenie automatyczne** — reguły auto-poprawek i uruchomienie projektu wsadowego.
5. **Krok 5 — Wyniki** — pobranie oczyszczonych plików i archiwum ZIP.

Na dole strony: zwinięta pomoc (**Słownik parametrów**, **Literatura**).

## Dane i dokumentacja

- Przykładowa baza: **`zubry_pedigree_app/data/EBPB_bison_report.xlsx`**
- Metryki (F, RIA, GI…): **`zubry_pedigree_app/docs/metrics_definition.md`**

## Zależności

Zobacz **`zubry_pedigree_app/requirements.txt`**: Streamlit, pandas, numpy, matplotlib, networkx, openpyxl, Pillow.

## Struktura repozytorium

| Element | Opis |
|--------|------|
| `zubry_pedigree_app/app/huba/` | Silnik wsadowy i etapy przetwarzania |
| `zubry_pedigree_app/app/ui/streamlit/` | Interfejs HUBA |
| `zubry_pedigree_app/run_web.py` | Start z przeglądarką |
| `run_streamlit.py` (root) | Start z katalogu głównego repo |

## Autorka

**[Magdalena Perlińska-Teresiak](https://github.com/CherryBison84)** — [repozytorium na GitHubie](https://github.com/CherryBison84/RodowodyAPP) · 2026
