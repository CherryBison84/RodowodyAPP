# Oddanie projektu przez MS Teams

## Plik do przesłania

Do zadania w MS Teams należy przesłać archiwum:

`RodowodyAPP_v1.1_MS_Teams.zip`

Archiwum zawiera kod aplikacji, dane przykładowe, konfigurację, testy oraz dokumentację. Nie zawiera środowisk wirtualnych, katalogu `.git`, cache ani lokalnych wyników roboczych.

## Co znajduje się w projekcie

- `README.md` — główna instrukcja uruchomienia i opis architektury.
- `CHANGELOG.md` — krótka historia zmian wersji projektu.
- `PRZEWODNIK_EGZAMINACYJNY.md` — materiał do prezentacji projektu.
- `zubry_pedigree_app/` — właściwa aplikacja DataCleaner.
- `zubry_pedigree_app/data/` — przykładowe pliki EBPB.
- `zubry_pedigree_app/tests/` — testy automatyczne.

## Szybkie uruchomienie po rozpakowaniu

```bash
cd zubry_pedigree_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 run_web.py
```

W systemie Windows aktywacja środowiska wygląda tak:

```bash
.venv\Scripts\activate
```

## Testy

```bash
cd zubry_pedigree_app
pip install -r requirements-dev.txt
python -m pytest -q
```

Ostatnia lokalna weryfikacja projektu: `21 passed`.

## Repozytorium

Repozytorium GitHub:

https://github.com/CherryBison84/RodowodyAPP

Wersja oddawana: `1.1.0`.

Krótki opis zmian w wersji 1.1: zmieniono kolejność kroków czyszczenia, dopracowano sidebar aplikacji oraz ujednolicono dokumentację.

## Finalna checklista

- Aplikacja pokazuje wersję `1.1.0` w panelu bocznym.
- Dokumentacja i UI mają tę samą kolejność kroków.
- Paczka ZIP nie zawiera `.git`, `.venv`, cache ani lokalnych wyników.
- Testy automatyczne przechodzą: `21 passed`.
