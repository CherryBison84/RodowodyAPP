# WisentPedigree Pro+ (RodowodyAPP)

**Wersja aplikacji (pakiet): 0.5.0**

Aplikacja **webowa (Streamlit)** do wczytywania baz rodowodowych, **walidacji** (w tym eksport CSV, wykresy podsumowań i **automatyczne poprawki** w sesji), analizy **inbredu (F Wright)**, **kompletności rodowodu**, **parametrów populacyjnych** oraz raportów. Interfejs i treści pomocy są po polsku; motyw wizualny jest dopasowany do pracy z dużymi zbiorami.

Kod źródłowy znajduje się w katalogu **`zubry_pedigree_app/`**.

## Wymagania

- Python **3.10+** (zalecany aktualny 3.11–3.14)
- System operacyjny: Windows, macOS lub Linux

## Instalacja

```bash
cd zubry_pedigree_app
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uruchomienie

**Zalecane** — Streamlit z wyborem portu i próbą otwarcia przeglądarki:

```bash
cd zubry_pedigree_app
python3 run_web.py
```

Tylko serwer Streamlit:

```bash
cd zubry_pedigree_app
python3 run_streamlit.py
```

Z **katalogu głównego repozytorium**:

```bash
python3 run_streamlit.py
```

Bezpośrednio (katalog roboczy: `zubry_pedigree_app/`, żeby moduł `app` był na `PYTHONPATH`):

```bash
cd zubry_pedigree_app
python3 -m streamlit run app/ui/streamlit/streamlit_app.py
```

Na macOS, przy problemach z obserwatorem plików Streamlit, można ustawić np. `STREAMLIT_SERVER_FILE_WATCHER_TYPE=none`.

## Nawigacja w aplikacji

Typowy przepływ:

1. **Import danych** — CSV / XLSX / URL, mapowanie kolumn (w tym ręczne przy uploadzie), opcjonalnie baza domyślna (plik **`EBPB_bison_report.xlsx`** obok `run_web.py`, jeśli go dodasz lokalnie).
2. **Walidacja** — podmenu w dwóch rzędach (m.in. arkusz/ID/rodzice/chronologia/graf/linie/przodkowie/raport), **auto-poprawki** jako osobna podsekcja, eksporty CSV, czytelniejsze wykresy podsumowań.
3. **Rejestr** — lista osobników.
4. **Analiza osobnicza** — graf **przodków**, **potomków** lub **łączony** (przodkowie + potomkowie w jednym rysunku), F (Wright), kompletność (EG, PCL, PCI), linie, rozkład wspólnych przodków rodziców.
5. **Populacja** — dashboard i wykresy (m.in. trendy F, GI, założyciele).
6. **Pary** — sekcja może być tymczasowo ograniczona (zależnie od wersji kodu).
7. **Raporty** — podgląd i eksport (TXT / PDF / DOCX).

Na dole strony: zwinięta pomoc (**Słownik parametrów**, **Literatura**).

## Dane i dokumentacja metodyczna

- Opcjonalna lokalna baza przykładowa: **`zubry_pedigree_app/EBPB_bison_report.xlsx`** (ścieżka zgodna z loaderem domyślnej bazy).
- **`zubry_pedigree_app/metrics_definition.md`** — definicje metryk (F, GI, f_e, RIA itd.), spójne z widokami w aplikacji.

## Główne zależności (Python)

Zobacz **`zubry_pedigree_app/requirements.txt`**: m.in. Streamlit, pandas, numpy, matplotlib, networkx, openpyxl, python-docx, Pillow.

## Struktura repozytorium (skrót)

| Element | Opis |
|--------|------|
| `zubry_pedigree_app/app/` | Logika: dane, rodowód, analityka, UI Streamlit |
| `zubry_pedigree_app/app/ui/streamlit/` | Widoki, wykresy, styl |
| `zubry_pedigree_app/run_web.py` | Start z przeglądarką |
| `zubry_pedigree_app/run_streamlit.py` | Start minimalny (`streamlit run`) |
| `run_streamlit.py` (root) | Start z katalogu głównego repo |

## Autorka

**[Magdalena Perlińska-Teresiak](https://github.com/CherryBison84)** — [repozytorium na GitHubie](https://github.com/CherryBison84/RodowodyAPP) · 2026
