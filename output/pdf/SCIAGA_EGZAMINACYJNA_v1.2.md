# Ściąga egzaminacyjna - WisentPedigree DataCleaner v1.2.0

## 1. Projekt w jednym zdaniu

WisentPedigree DataCleaner przygotowuje bazy rodowodowe żubrów EBPB do dalszej analizy: wczytuje różne formaty plików, standaryzuje dane, waliduje relacje rodowodowe, wykonuje wybrane poprawki i eksportuje oczyszczony zbiór z raportem.

## 2. Konkretny problem

- Dane EBPB mogą pochodzić z różnych eksportów: raportu i rejestru.
- Pliki mają różne kolumny, nazwy pól i poziom kompletności.
- Typowe problemy: puste lub powtarzające się ID, błędni rodzice, self-parent, cykle, niezgodna płeć rodzica, błędne lata i daty.
- Ręczna kontrola dużych arkuszy jest trudna, czasochłonna i mało powtarzalna.

## 3. Cel projektu

- Ujednolicić dane wejściowe do jednego schematu.
- Wykryć problemy jakościowe w rodowodzie.
- Dać użytkownikowi kontrolę nad czyszczeniem automatycznym i ręcznym.
- Wygenerować raporty, manifest i oczyszczone pliki wynikowe.

## 4. Dwie części wymagane w projekcie

### Część integracyjna

- Import CSV/XLS/XLSX.
- Rozpoznanie formatu EBPB: raport lub rejestr.
- Mapowanie do wspólnego schematu aplikacji.
- Opcjonalne łączenie kilku baz.
- Walidacja przed zmianami.
- Transformacje i eksport wyników.

### Część główna

- Aplikacja webowa Streamlit.
- Pięć kroków pracy użytkownika.
- Ten sam silnik dostępny również przez CLI.
- Interfejs po polsku, z raportami i pobieraniem wyników.

## 5. Kolejność pracy w aplikacji

1. Krok 1 - Wczytanie danych.
2. Krok 2 - Walidacja.
3. Krok 3 - Czyszczenie automatyczne.
4. Krok 4 - Czyszczenie ręczne.
5. Krok 5 - Wyniki.

## 6. Architektura - najważniejsze komponenty

```text
Użytkownik
  |-> Streamlit UI
  |-> CLI / JSON
        |
        v
Loader danych -> wspólny schemat pandas
        |
        v
Katalog baz / łączenie plików
        |
        v
Walidacja wejściowa
        |
        |-> Auto-fix
        |-> Edycja ręczna
        v
Ponowna walidacja
        |
        v
Eksport: XLSX/CSV + HTML + JSON + ZIP
```

## 7. Flowchart struktury aplikacji

```text
zubry_pedigree_app
  app/data      -> import, schemat, walidacja, auto-fix
  app/huba      -> silnik procesu: load -> validate -> transform -> export
  app/ui        -> Streamlit, sidebar, kroki aplikacji
  app/pedigree  -> osoby i relacje rodzic-potomstwo
  app/analytics -> metryki pokrewieństwa i inbredu
  config        -> przykładowe JSON
  data          -> przykładowe pliki EBPB
  tests         -> testy jakości
```

## 8. Struktura repozytorium

```text
README.md                         - opis projektu, uruchomienie, architektura
CHANGELOG.md                      - krótka historia wersji
ODDANIE_MS_TEAMS.md               - instrukcja dla prowadzącego
PRZEWODNIK_EGZAMINACYJNY.md       - materiał do prezentacji
zubry_pedigree_app/
  app/data/                       - import, mapowanie, walidacja, auto-fix
  app/huba/                       - silnik procesu i eksport
  app/ui/streamlit/               - interfejs aplikacji
  app/pedigree/                   - model osób i relacji rodowodu
  app/analytics/                  - metryki pokrewieństwa i inbredu
  config/                         - przykładowe konfiguracje JSON
  data/                           - przykładowe dane EBPB
  tests/                          - testy automatyczne
```

## 9. Najważniejsze pliki do pokazania

- `README.md` - wymagania, instalacja, diagram, AI.
- `PRZEWODNIK_EGZAMINACYJNY.md` - gotowy opis prezentacji.
- `app/data/dataset_loader.py` - import i standaryzacja.
- `app/data/validator.py` - reguły walidacji.
- `app/data/auto_fix.py` - automatyczne poprawki.
- `app/huba/engine.py` - przebieg procesu.
- `app/ui/streamlit/streamlit_app.py` - główny UI.
- `tests/` - potwierdzenie jakości.

## 10. Walidacja - co sprawdza program

- Brak ID i duplikaty ID.
- Nieznane kody płci.
- Brakujące rekordy rodziców.
- Osobnik jako własny rodzic.
- Ojciec i matka jako ta sama osoba.
- Cykle w grafie rodowodu.
- Niezgodność płci z rolą ojca lub matki.
- Zakres roku urodzenia i sprzeczne daty.
- Zbyt młody lub zbyt stary rodzic.
- Niezgodności linii rodowodowych.

## 11. Wyniki generowane przez projekt

- Oczyszczone pliki CSV/XLSX.
- `comparison.csv` - porównanie przed i po czyszczeniu.
- `final_report.html` - raport końcowy.
- `manifest.json` - konfiguracja, wersja, źródła, suma kontrolna.
- ZIP z katalogiem wyników.

## 12. Uruchomienie aplikacji webowej

```bash
cd zubry_pedigree_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run_web.py
```

Windows:

```bash
.venv\Scripts\activate
```

## 13. Wersja terminalowa bez UI

```bash
cd zubry_pedigree_app
python run_cli.py run --input data/EBPB_bison_report.xlsx --project-name terminal_demo
```

## 14. Testy

```bash
cd zubry_pedigree_app
pip install -r requirements-dev.txt
python -m pytest -q
```

Ostatnia weryfikacja: `21 passed`.

## 15. AI w projekcie - gotowa odpowiedź

Narzędzia generatywnej AI, w tym Codex, były używane jako wsparcie programistyczne: do porządkowania kodu, dokumentacji, testów i przeglądu spójności projektu. AI nie działa w aplikacji produkcyjnej, nie przetwarza danych użytkownika i nie podejmuje decyzji hodowlanych. Walidacja i czyszczenie są deterministycznymi regułami zapisanymi w Pythonie.

## 16. Co powiedzieć o ograniczeniach

- Aplikacja wspiera kontrolę jakości, ale nie zastępuje eksperta.
- Auto-fix może usunąć podejrzane powiązanie, ale nie odtwarza prawdziwej informacji biologicznej.
- Wynik powinien być oceniony przez osobę z wiedzą domenową.

## 17. Najważniejsze zdanie na koniec

Projekt jest ukierunkowany na jeden konkretny problem: powtarzalne i udokumentowane przygotowanie danych rodowodowych żubrów do dalszej analizy, z zachowaniem kontroli użytkownika nad czyszczeniem.
