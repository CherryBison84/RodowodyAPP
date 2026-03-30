# WisentPedigree Pro+ (RodowodyAPP)

Aplikacja **webowa (Streamlit)** do wczytywania baz rodowodowych, walidacji, analizy **inbredu (F Wright)**, **kompletności rodowodu**, **pokrewieństwa par**, **parametrów populacyjnych** i prostego **planu hodowlanego**. Interfejs oraz raporty są w języku polskim; motyw wizualny jest dopasowany do czytelnej pracy z dużymi zbiorami.

Kod źródłowy znajduje się w katalogu **`zubry_pedigree_app/`**.

## Wymagania

- Python **3.10+** (zalecany aktualny 3.11–3.14)
- System operacyjny: Windows, macOS lub Linux

## Instalacja

```bash
cd zubry_pedigree_app
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Uruchomienie

**Zalecane** — Streamlit z wyborem portu i próbą otwarcia przeglądarki:

```bash
cd zubry_pedigree_app
python run_web.py
```

Tylko serwer Streamlit (jak `streamlit run`):

```bash
cd zubry_pedigree_app
python run_streamlit.py
```

Z **katalogu głównego repozytorium** (bez `cd` do podfolderu):

```bash
python run_streamlit.py
```

Bezpośrednio (musisz być w katalogu, gdzie moduł `app` jest na `PYTHONPATH`, zwykle `zubry_pedigree_app/`):

```bash
cd zubry_pedigree_app
python -m streamlit run app/ui/streamlit/streamlit_app.py
```

Nie uruchamiaj `streamlit_app.py` poleceniem `python streamlit_app.py` — wymagane jest `streamlit run`.

## Nawigacja w aplikacji

Typowy przepływ:

1. **Import danych** — CSV / XLSX / URL, mapowanie kolumn, opcjonalnie baza domyślna.
2. **Walidacja** — spójność zbioru, mapa braków w kolumnach.
3. **Rejestr** — lista osobników.
4. **Analiza osobnicza** — graf przodków, F (Wright), kompletność (EG, PCL, PCI), linie.
5. **Populacja** — dashboard (metryki tematyczne), wykresy (m.in. trendy F, GI, założyciele).
6. **Pary i kojarzenia** — Φ, R dla par, ranking kojarzeń.
7. **Plan hodowlany** — scenariusze i podpowiedzi par.
8. **Raporty** — podgląd i eksport (TXT / DOCX).

Na dole strony: zwinięta pomoc (**Słownik parametrów**, **Literatura**).

## Dane i dokumentacja metodyczna

- Domyślna przykładowa baza: **`zubry_pedigree_app/EBPB_bison_report.xlsx`** (wczytywana z poziomu Import jako „domyślna baza”, jeśli plik istnieje).
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

**Magdalena Perlińska-Teresiak** — 2026
