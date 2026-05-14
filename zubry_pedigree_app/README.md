# Zubry Pedigree App — folder aplikacji

**Wersja (pyproject): 0.4.0** — pełny opis, nawigacja i instalacja: **[README.md w katalogu nadrzędnym](../README.md)**.

W tym katalogu są skrypty startowe, pakiet **`app/`**, `requirements.txt`, **`metrics_definition.md`** oraz (opcjonalnie lokalnie) plik **`EBPB_bison_report.xlsx`** używany jako domyślna baza w imporcie.

## Szybki start (stąd)

```bash
pip install -r requirements.txt
python run_web.py
```

Alternatywa: `python run_streamlit.py` albo `python run_app.py` (patrz nagłówki plików).

## Rozwój projektu: etapy, warianty, batch

Dodany został lekki pipeline, który porządkuje pracę nad projektem:

1. **Struktura**: `load -> analyze -> report` (`app/pipeline/stages.py`)
2. **Konfiguracja**: pliki JSON:
   - `config/gui.json` (parametry GUI),
   - `config/project_batch_example.json` (projekt batch + warianty).
3. **Warianty**: sekcja `variants` pozwala porównywać ustawienia (np. głębokość obliczeń).
4. **Batch**: sekcja `datasets` pozwala uruchomić te same etapy na wielu źródłach.
5. **Wyniki**: dla każdej pary `dataset x variant` zapisywane są pliki w `outputs/...`,
   a globalne porównanie trafia do `comparison.csv`.

### Uruchomienie pipeline

```bash
python app/main.py --project-config config/project_batch_example.json
```

Wynik: katalog z podfolderami per wariant oraz plik porównawczy `comparison.csv`.
