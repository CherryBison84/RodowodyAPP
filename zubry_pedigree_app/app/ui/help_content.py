# -*- coding: utf-8 -*-
"""
Teksty pomocy po polsku: co oznaczają skróty (F, GI, RIA…), jak czytać wykresy
i jak rozumieć komunikaty — wspólne dla okna na pulpicie i wersji w przeglądarce.
"""

from __future__ import annotations

# --- Główny słownik (markdown dla Streamlit, zwykły tekst dla Tk) ---

GLOSSARY = """
## Słownik parametrów (najczęściej używanych)

### Inbred / Wright F
- **F (współczynnik inbredu Wrighta)** — prawdopodobieństwo, że dwa allele w danym locus u osobnika są identyczne przez pochodzenie (IBD). Wartość od 0 (brak inbredu w sensie zdefiniowanym w algorytmie) w górę.
- **F rodziców Φ(ojciec, matka)** — w klasycznej formule F potomka zależy od współczynnika pokrewieństwa między rodzicami. W aplikacji Φ jest liczone rekurencyjnie w rodowodzie (z zatrzymaniem na „founder-stop”, gdy brakuje ojca lub matki).
- **Limit pokoleń** — ogranicza głębokość wstecz przy liczeniu F; **bez limitu** schodzi do „founderów” (osób bez dalszych rodziców w bazie lub z brakiem rodzica).
- **Wykres diagnostyczny F vs max pokoleń** — pokazuje, jak stabilizuje się F, gdy zwiększasz limit głębokości. Jeśli krzywa się nie zmienia od pewnego poziomu, dalsze pokolenia nie wnoszą informacji.

### Kompletność rodowodu (osobnica)
- **MG (Maximum Generation)** — najwyższe pokolenie wstecz (g>0), w którym występuje przynajmniej jeden znany przodek w analizowanym drzewie.
- **CG (Complete Generations)** — liczba pokoleń g, dla których uznajemy poziom za „kompletny”: przyjmujemy regułę jak w kodzie — gdy dla pokolenia g wartość PCL_g = a_g / 2^g ≥ 1 (w praktyce pełna liczba slotów przodków na tym poziomie).
- **EG (Equivalent Complete Generations)** — suma a_g / 2^g po pokoleniach; miara „głębokości” i kompletności drzewa (im wyższe, tym więcej znanych przodków w wagach Malecot).
- **PCI (Pedigree Completeness Index)** — w module populacji: średnia z PCL_g po pokoleniach (1..G), gdzie PCL_g = a_g / 2^g; wartość od 0 do ok. 1+ w zależności od struktury.

### Populacja — założyciele i linie
- **f_e (efektywna liczba założycieli)** — 1 / Σ p_i², gdzie p_i to uśredniony wkład genów i-tego założyciela (founder-like, zgodnie z founder-stop). Im wyższe f_e, tym bardziej „rozproszony” jest wkład przodków.
- **f_a** — w tej implementacji liczone spójnie z logiką founder-stop; interpretacja zbliżona do efektywnej liczby przodków w analizowanym schemacie.
- **Bottleneck f_e / f_a** — stosunek < 1 może sugerować zawężenie materiału genetycznego względem liczby linii przodków (interpretacja jakościowa).
- **p_i** — udział (znormalizowany) wkładu i-tego założyciela w populacji; wykres pokazuje **Top 20** dominujących przodków (wg p_i).
- **Linie LB / LC** — etykiety hodowlane z kolumny `line`; pozostałe trafiaą do **NA**.

### GI i rodziny
- **GI (Generation Interval)** — tu: różnica lat urodzenia potomka i rodzica na danej ścieżce (O→Syn, O→Córka, M→Syn, M→Córka), przy znanych datach. Uśrednienie pokazuje typowy odstęp międzypokoleniowy.
- **Rodzina pełnego rodzeństwa** — osobnicy z tym samym znanym ojcem i matką; histogram pokazuje, ile takich rodzin ma daną liczbę potomków.

### Trendy w czasie (Inbred TP)
- **TP (time period)** — podział wg **roku urodzenia** osobnika w populacji.
- **Średnie F w roku** — średnia F wśród osób urodzonych w danym roku (po wyliczeniu F per osobnik).
- **RIA (Rate of Inbred Animals, %)** — odsetek osobników z F > 0 (w sensie numerycznym) w danym roku / grupie.

### N_e (przybliżenie)
- **N_e z trendu F × GI** — ze wzoru opartego na regresji średniego F w czasie: przybliżenie efektywnej wielkości populacji przy założeniu relacji ΔF na pokolenie ≈ (nachylenie F/rok) × średni GI. To **orientacyjna** miara — wrażliwa na kompletność bazy i okno czasowe.

### Walidacja bazy
- Sprawdza m.in. **unikalność ID**, spójność **sex / line / lata**, istnienie **ojca/matki** w bazie, podstawowe **konflikty płci** w relacjach rodzic–dziecko. Ostrzeżenia nie zawsze oznaczają błąd — mogą wynikać z historii hodowli lub literówek — warto je przejrzeć przed wnioskami.

### Mapowanie kolumn
- Pola **id, sex, line, birth_year, father_id, mother_id** są wymagane do pełnej analizy; brak mapowania ogranicza funkcje (np. bez płci nie zadziałają podziały M/F).
"""


SECTION_LOADING = """
## Wczytywanie bazy

1. **Plik CSV/XLSX** — aplikacja próbuje dopasować nazwy kolumn; jeśli się nie uda, wybierz kolumny ręcznie.
2. **URL** — pobranie pliku i takie samo mapowanie jak dla pliku lokalnego.
3. **ID testowe** — rekord `99999` jest traktowany jako techniczny i pomijany w statystykach populacji.

**Po wczytaniu** zobaczysz skrót walidacji. Pełny raport opisuje konkretne problemy (duplikaty, brakujące linki rodziców itd.).
"""


SECTION_VALIDATION = """
## Walidacja bazy (co jest sprawdzane)

- **Unikalność ID** — duplikaty uniemożliwiają jednoznaczne powiązanie osobnika z rodowodem.
- **Istnienie rodziców** — jeśli podano `father_id` / `mother_id`, powinny wskazywać na rekordy w bazie.
- **Płeć, linia, rok urodzenia** — podstawowa spójność typów i rozsądny zakres lat.
- **Relacje rodzic–dziecko** — m.in. zgodność płci rodzica z rolą (ostrzeżenia przy typowych konfliktach).

Status „OK” oznacza brak **błędów krytycznych**; **ostrzeżenia** warto przeanalizować przed wnioskami hodowlanymi — często wynikają z historii danych albo literówek w ID.
"""


SECTION_PERSONS = """
## Osobniki

Tabela pokazuje rekordy z bazy z możliwością sortowania. Kolumna **linia (sire/dam)** to uproszczone podsumowanie przynależności do linii ojca i matki (founder ID po stronie ojca i matki), liczone z drzewa rodowego — pomaga szybko zorientować się w strukturze bez otwierania wykresu.
"""


SECTION_PEDIGREE = """
## Rodowód (graf przodków)

- **Limit pokoleń** — ile poziomów w głąb od wybranego osobnika; przy bardzo gęstym drzewie aplikacja może zawęzić wizualizację, żeby zachować czytelność.
- **Tryb czytelny** — mniej etykiet na węzłach, lepszy podgląd dużych drzew.
- **Linie (sireline / damline)** — founder po stronie ojca i matki oraz liczba kroków — pomaga ocenić odległość od linii bazowych.

**Interpretacja:** węzeł to osobnik, krawędzie to relacje rodzic–dziecko. Brak rodzica w bazie = koniec gałęzi (founder w rozumieniu danych).
"""


SECTION_INBRED = """
## Inbred (Wright F) — osobnik

- Wynik **F** dotyczy wybranego ID przy aktualnym limicie pokoleń (lub bez limitu).
- **Wykres F vs max pokoleń** — jeśli F rośnie tylko do pewnej głębokości i potem się stabilizuje, dalsze pokolenia nie zmieniają oszacowania — to normalne przy kompletnych danych w tym fragmencie drzewa.
- Wykres **kompletności (PCL)** pokazuje, jak wypełnione są kolejne poziomy przodków względem maksymalnej liczby miejsc (2^g).
"""


SECTION_MATING = """
## Mating (ranking par)

- Dla par **samiec × samica** z populacji (po filtrze wieku) liczone jest **F hipotetycznego potomka** przy tych samych zasadach co F w rodowodzie.
- **Do 36 par** — wszystkie pary są sortowane po **najmniejszym** F, a następnie wybierane **zachłannie** kolejne najlepsze pary z ograniczeniem: **ten sam osobnik** (jako ojciec lub matka) może pojawić się w liście wynikowej **co najwyżej 3 razy**. Dzięki temu ranking nie składa się z wielokrotnych powtórzeń tych samych reproduktorów.
- Limity liczby samców/samic i limit pokoleń wpływają na czas obliczeń i zakres przeszukania — to nie jest pełna enumeracja całej populacji, jeśli limity są niskie.
"""


SECTION_POPULATION = """
## Populacja — metryki u góry

- **n** — liczba osobników po odfiltrowaniu ID testowego.
- **Średnie F** — średnia z F (Wright) po osobnikach przy wybranym limicie pokoleń dla F populacji.
- **f_e, f_a** — efektywne liczby (założyciele / przodkowie) — patrz słownik.
- **Założyciele (brak ojca lub matki)** — liczba rekordów z brakiem któregoś z rodziców (informacja o dziurach w rodowodzie).
- **Parametry F** (bez limitu / max pokoleń) — tak samo liczone są histogram F i trendy **F/RIA** oraz (w Tk) spójne metryki.

**N_e** w podpisie — szacunek z trendu średniego F w czasie i średniego GI; traktuj jako wskaźnik orientacyjny.
"""


SECTION_REPORTS = """
## Raporty

- Zbiera **walidację**, skrót **statystyk populacji** i ewentualnie dane osobnika (wersja Tk: eksport DOCX/PDF z wykresami).
- W Streamlit dostępny jest podgląd tekstowy i eksport **.txt** — pełny układ dokumentu jak w Tk wymaga środowiska z modułami raportowymi.
"""


SECTION_BREEDING = """
## Plan hodowlany (Tk)

W głównym oknie: **Analityka hodowlana → Plan hodowli** (podzakładka obok Inbredu i optymalizacji kojarzeń).

Moduł wspiera **dobór par** z ograniczeniami (wiek, linia, limity użyć reproduktorów, cele F średniej/maks.). Wyniki zależą od kompletności rodowodów i parametrów ryzyka inbredu (głębokość liczenia F dla hipotetycznego potomka).

Po **zaznaczeniu wiersza** w tabeli propozycji par pokazują się **statystyki** (F potomka i rodziców, MG/EG/PCI dla obojga rodziców). **Graf rodowodu** hipotetycznego potomka (głębokość zależy od ustawień ryzyka inbredu w planie) otwiera się przyciskiem **„Pokaż rodowód potomka w nowym oknie”**; w tym oknie można zapisać podgląd jako **JPEG**.

W Streamlit sekcja jest **w rozwoju** — pełna logika jak w Tk będzie dodawana etapami.
"""


SECTION_SETTINGS = """
## Ustawienia

- W **Tk** ustawienia domyślne (głębokość F, rodowód, eksport) są zapisywane w sesji i używane przy kolejnych akcjach.
- W **Streamlit** ustawienia dotyczą **bieżącej sesji przeglądarki** (nie są trwałe na dysku).
"""


# --- Wykresy populacji (interpretacja) ---

CHART_BIRTH_SEX = (
    "Słupki pokazują liczbę urodzonych osobników w każdej dekadzie (np. 1990–1999), "
    "osobno dla samców (M) i samic (F). Pozwala ocenić skalę przyrostu i ewentualne "
    "przesunięcia struktury płciowej w czasie. Puste dekady = brak danych lub rok poza zakresem filtra."
)

CHART_BIRTH_LINE = (
    "Podobnie jak wykres płci, ale podział wg kolumny `line` (typowo LB vs LC). "
    "Pokazuje, która linia dominuje demograficznie w kolejnych dekadach. Osobniki spoza LB/LC zwykle nie wchodzą do tych słupków."
)

CHART_FM_RATIO = (
    "Stosunek **F/M** = liczba samic / liczba samców urodzonych w dekadzie (od 1900). "
    "Linia pozioma przy 1.0 to równy udział; wartości >1 oznaczają przewagę samic. "
    "Jeśli w dekadzie nie ma samców, punkt może być pominięty (dzielenie przez zero)."
)

CHART_COMP_SEX = (
    "Dla każdej płci (M/F) pokazane są średnie **MG, CG, EG** (patrz słownik). "
    "Porównujesz, czy jedna płeć ma średnio głębszy / bardziej kompletny rodowód w bazie — "
    "często wynika to z historii rejestracji (np. więcej danych po jednej linii)."
)

CHART_COMP_LINE = (
    "Jak wyżej, ale średnie MG/CG/EG są liczone osobno dla **LB**, **LC** i pozostałych (**NA**). "
    "Ułatwia zobaczyć różnice kompletności między liniami hodowlanymi."
)

CHART_HIST_F = (
    "Histogram wartości **F** dla wszystkich osobników w populacji (przy wybranym limicie pokoleń dla F). "
    "Pik przy 0 oznacza dużą liczbę osobników bez wykrytego inbredu w modelu; rozciągnięty „ogon” w prawo — obecność wyższych F."
)

CHART_FOUNDERS_PI = (
    "**Top 20** założycieli wg **p_i** (udział w puli genów). Wysoki słupek = duży wkład danego przodka w populację — "
    "może wskazywać na silny bottleneck lub dominację kilku linii. Oś Y: wartość p_i po normalizacji."
)

CHART_GI_BAR = (
    "**GI** = różnica lat urodzenia potomka i rodzica. Wykres pokazuje średnie GI dla czterech ścieżek: "
    "ojciec→syn, ojciec→córka, matka→syn, matka→córka (tylko gdy znane są obie daty). "
    "Różnice między słupkami odpowiadają typowym opóźnieniom reprodukcji między płciami/rolami rodziców."
)

CHART_GI_TREND = (
    "Dla każdej dekady **urodzenia potomka** liczone jest średnie GI osobno dla 4 ścieżek. "
    "Trendy pokazują, czy odstępy międzypokoleniowe się wydłużają lub skracają w czasie (zmiany zarządzania stadkiem, selekcji)."
)

CHART_FAMILY = (
    "Każda **rodzina pełnego rodzeństwa** = ta sama para rodziców (ojciec i matka znani). "
    "Słupek przy rozmiarze k oznacza liczbę takich rodzin, które mają dokładnie k potomków w bazie; "
    "kategoria „10+” grupuje większe rodziny."
)

CHART_INBRED_TP_SEX = (
    "Górny panel: **średnie F** w roku urodzenia, osobno M i F. Dolny: **RIA (%)** — jaki odsetek osobników "
    "urodzonych w danym roku ma F>0. Pozwala ocenić, czy średni poziom inbredu i udział „zinbredowanych” rośnie lub maleje w czasie; "
    "różnice M/F mogą wynikać z różnej struktury kojarzeń lub kompletności danych."
)

CHART_INBRED_TP_LINE = (
    "Analogicznie do wykresu wg płci, ale linie **LB**, **LC** i pozostałe (**NA**). "
    "Umożliwia porównanie trendów F i RIA między liniami hodowlanymi w kolejnych rocznikach."
)


def all_charts_text() -> str:
    """Jedna strona ze wszystkimi opisami wykresów (menu Pomoc w Tk)."""
    parts = [
        "## Interpretacja wykresów populacji\n",
        "### Urodzenia: płeć\n",
        CHART_BIRTH_SEX,
        "\n\n### Urodzenia: LB/LC\n",
        CHART_BIRTH_LINE,
        "\n\n### Female/Male ratio\n",
        CHART_FM_RATIO,
        "\n\n### Kompletność: płeć\n",
        CHART_COMP_SEX,
        "\n\n### Kompletność: linie\n",
        CHART_COMP_LINE,
        "\n\n### Rozkład F\n",
        CHART_HIST_F,
        "\n\n### Założyciele p_i\n",
        CHART_FOUNDERS_PI,
        "\n\n### GI (średni)\n",
        CHART_GI_BAR,
        "\n\n### GI trend\n",
        CHART_GI_TREND,
        "\n\n### Rodziny pełne\n",
        CHART_FAMILY,
        "\n\n### Inbred TP: płeć\n",
        CHART_INBRED_TP_SEX,
        "\n\n### Inbred TP: linie\n",
        CHART_INBRED_TP_LINE,
        "\n",
    ]
    return "".join(parts)


FULL_HELP_DOCUMENT = (
    GLOSSARY
    + "\n\n---\n\n"
    + SECTION_LOADING
    + "\n\n"
    + SECTION_VALIDATION
    + "\n\n"
    + SECTION_PERSONS
    + "\n\n"
    + SECTION_PEDIGREE
    + "\n\n"
    + SECTION_INBRED
    + "\n\n"
    + SECTION_MATING
    + "\n\n"
    + SECTION_POPULATION
    + "\n\n"
    + SECTION_REPORTS
    + "\n\n"
    + SECTION_BREEDING
    + "\n\n"
    + SECTION_SETTINGS
    + "\n\n---\n\n"
    + all_charts_text()
)
