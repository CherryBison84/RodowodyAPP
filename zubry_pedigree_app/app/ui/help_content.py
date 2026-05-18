# -*- coding: utf-8 -*-
"""Teksty pomocy (markdown) — wersja przeglądarkowa (Streamlit)."""

from __future__ import annotations

from app.ui.metric_copy import F_PLAIN, RIA_HELP_TOOLTIP, RIA_PLAIN, RIA_PLAIN_SHORT

# --- Główny słownik (markdown) ---

GLOSSARY = f"""
## Słownik — najczęściej używane pojęcia

### Inbred i współczynnik F (Wright)
- {F_PLAIN}
- **Związek rodziców (Φ)** — klasycznie F potomka zależy od tego, jak bardzo **ojciec i matka są ze sobą spokrewnieni**. Tu Φ jest liczone z drzewa rodowego; jeśli w bazie brakuje ojca lub matki, obliczenia zatrzymują się na tym miejscu (**„founder-stop”** — tak traktujemy koniec znanej gałęzi).
- **Mean kinship (średni kinship)** — **średnia z Φ(i,j)** po parach różnych osobników (i≠j); opisuje, jak **średnio** spokrewniona jest populacja. **Średnie R = 2Φ̄** to średni współczynnik relacji Wrighta (autosomy). Przy bardzo dużym **n** program liczy średnią po parach **w losowej próbie** osobników (szybciej); przy mniejszym n — po wszystkich parach. **Ten sam limit pokoleń** co przy F / Φ dla pojedynczej pary.
- **Limit pokoleń** — możesz ograniczyć, jak głęboko program schodzi wstecz przy liczeniu F. **Bez limitu** schodzi tak daleko, jak pozwalają dane, aż do osób bez dalszych rodziców w bazie.
- **Wykres F a maksymalna głębokość** — pokazuje, czy wynik F „ustabilizował się”, gdy zwiększasz liczbę pokoleń. Jeśli od pewnego poziomu krzywa się już prawie nie zmienia, dalsze pokolenia niewiele dodają — to częsty znak, że w tym fragmencie rodowodu dane są w miarę pełne.

*(Te pojęcia wywodzą się z prac Sewalla Wrighta z lat 20. XX w.; pełne cytowania: sekcja **Literatura — źródła metod** na dole strony, w bloku pomocy.)*

### Jak „pełny” jest rodowód u jednego osobnika
- **MG** — do jakiego **najdalszego poziomu przodków** (pokolenia wstecz) w ogóle coś wiemy w zapisanym drzewie.
- **CG** — ile poziomów uznajemy za **wypełnione w sensie formalnym** (wg reguły z programu: poziom jest „kompletny”, gdy znana jest pełna liczba miejsc na tym poziomie drzewa).
- **EG (równoważne pełne pokolenia)** — jedna liczba, która **podsumowuje głębokość i kompletność** drzewa: znani przodkowie na kolejnych poziomach są ważeni tak, jak w typowych miarach rodowodowych stosowanych w hodowli zwierząt.
- **PCI** — średnia „pełności” poziomów od 1 do MG; **0–1** oznacza „im bliżej 1, tym więcej znanych przodków w stosunku do tego, ile teoretycznie mogłoby być”.

*(Takie miary są powszechne przy ocenie jakości baz rodowodowych; szczegóły metod — w sekcji **Literatura** w pomocy.)*

### Populacja — założyciele i linie
- **f_e** — **efektywna liczba założycieli**: z udziałów genów *p_i* liczymy `1 / suma(p_i²)`. Duże f_e ≈ wiele przodków realnie „wnosi” geny; małe ≈ niewielu dominuje. (Powiązane z klasycznymi miarami różnorodności genów pochodzących od fundatorów — zob. Boichard i wsp. 1997 oraz Lacy 1989 w literaturze poniżej.)
- **f_a** — druga miara z tej samej rodziny, liczona **w tej samej logice co reszta programu** (z founder-stop); pomaga porównać „ile linii” z „ile efektywnie widać w genach”.
- **Stosunek f_e / f_a** — jeśli jest wyraźnie mniejszy niż 1, bywa interpretowany jako sygnał, że **niewielu przodków dominuje** w stosunku do liczby linii — tylko jako podpowiedź, nie jako twarde rozstrzygnięcie.
- **p_i** i wykres **Top 20** — kto z przodków (w rozumieniu founder-stop) ma **największy udział** w puli genów w populacji; wysoki słupek = duży wpływ jednej linii lub osobnika.
- **Linie LB / LC** — etykiety z kolumny linii w danych; reszta trafia do **NA**.

### Odstępy międzypokoleniowe i rodziny
- **GI (Generation Interval)** — tu: **różnica lat urodzenia** potomka i rodzica (osobno dla ścieżek ojciec–syn, ojciec–córka itd.), gdy znamy oba lata. Średnie GI mówi, **po ilu latach** typowo pojawia się następne pokolenie.
- **Rodzina pełnego rodzeństwa** — dzieci z **tej samej pary** ojciec+matka; histogram pokazuje, ile takich rodzin ma 1, 2, 3… potomków w bazie.

### Trendy w czasie (Inbred TP)
- **TP** — podział według **roku urodzenia** osobnika.
- **Średnie F w roku** — średnia F wśród osób urodzonych w danym roku.
- {RIA_PLAIN}

### N_e (szacunek orientacyjny)
- Program podaje **przybliżoną efektywną wielkość populacji** na podstawie trendu średniego F w czasie i średniego odstępu międzypokoleniowego (GI). To **uproszczenie**: wynik mocno zależy od kompletności rodowodów i wybranego okresu — używaj jak wskazówki, nie jak precyzyjnej stałej biologicznej.

*(Związek tempa narastania inbredu z N_e ma korzenie u Wrighta; szczegóły w podręcznikach z listy na końcu.)*

### Walidacja spójności zbioru
- Program sprawdza m.in. **powtarzające się ID**, czy podani **rodzice istnieją w bazie**, rozsądność **płci, linii i lat**, oraz oczywiste **błędy w relacjach**. Ostrzeżenie nie zawsze znaczy błąd krytyczny — czasem wynika z historii stadka albo literówki w numerze; warto zajrzeć w szczegóły komunikatu.

### Mapowanie kolumn
- Do pełnej analizy najlepiej mieć sensownie zmapowane pola **id, sex, line, birth_year, father_id, mother_id**. Bez części z nich niektóre wykresy lub podziały (np. na płeć) nie będą działać.
- Pole **birth_location** (miejsce urodzenia) jest opcjonalne, ale warto je mapować: po imporcie można po nim filtrować rejestr osobników oraz pulę kandydatów do rankingu kojarzeń.
"""


SECTION_LOADING = """
## Wczytywanie bazy

1. **Plik CSV lub XLSX** — program próbuje sam rozpoznać kolumny. Jeśli się nie uda, wybierasz odpowiedniki ręcznie.
2. **Adres URL** — pobranie pliku z sieci i takie samo mapowanie jak z dysku.
3. **Rekord testowy** — ID **99999** jest traktowane technicznie i **nie wchodzi** do statystyk populacji.

**Kolejny krok:** po imporcie przejdź do **Walidacja spójności zbioru** — tam jest **krótki wynik** (np. liczba błędów), **wypunktowanie** problemów, **CSV** z listą (id, typ, szczegóły) do poprawy w Excelu oraz pełny raport tekstowy.
"""


SECTION_VALIDATION = """
## Walidacja — co jest sprawdzane

Program traktuje bazę jak **drzewo rodowe** i szuka niespójności typowych dla plików hodowlanych.

- **Unikalność ID** — powtórzone numery osobników; puste lub nieczytelne `id` w wierszu.
- **Rodzice w bazie** — `father_id` / `mother_id` powinny (jeśli wypełnione) wskazywać na **istniejący** rekord; inaczej gałąź kończy się w powietrzu (ostrzeżenie przy analizach „founder-stop”).
- **Cykle w grafie rodzic–dziecko** — z kolumn `father_id` / `mother_id` budowany jest graf skierowany (**dziecko → rodzic**, gdy wskazany ID istnieje w bazie). **Cykl** (pętla) oznacza, że można „zejść” łańcuchem rodziców i wrócić do punktu wyjścia — w rzeczywistości to **niemożliwe**, a w programie psuje strukturę pokoleń i obliczenia. Zwykle winne są **pomyłki w numerach**, **duplikaty ID**, **zamiana kolumn** lub zły merge arkuszy. Komunikat walidacji: ERROR **„Cykl w rodowodzie”**; w CSV eksportu: `id` = **`_GLOBAL_`** oraz przykładowe węzły na cyklu.
- **Self-parent** — ten sam osobnik wskazany jako **własny ojciec lub matka** (osobna reguła w zakładce Rodzice).
- **Ta sama osoba jako ojciec i matka** — błąd krytyczny (np. zamiana kolumn lub literówka).
- **Płeć vs rola rodzica** — w drzewie ojciec powinien być **M**, matka **F** (gdy płeć jest w bazie); wykrywa zamianę ojca z matką lub błędny zapis płci.
- **Płeć, linia, rok urodzenia** — wartości poza sensownym zakresem lat; braki `birth_year`; wiek rodzica przy urodzeniu potomka (heurystyka 0–80 lat).
- **Spójność linii** — `father_line` / `mother_line` vs linia zapisanego rodzica.
- **Kompletność rodziców w rekordach** — statystyka: ile rekordów ma pełną parę, ile brakuje ojca, matki lub obojga (jakość danych o przodkach bezpośrednich).
- **Daty tekstowe** — heurystyka na polach `birth_date` / `death_date`: czy wyciągnięte lata nie sugerują zgonu przed urodzeniem.

**Relacje rodzic–dziecko** — łącznie z powyższym: program szuka błędów w pliku, powtórzeń lub luk w numerach, pomyłek przy rodzicach, nielogicznych dat i błędnych powiązań.

Status **OK** znaczy: **nie znaleziono błędów krytycznych**. **Ostrzeżenia** warto przejrzeć przed wnioskami hodowlanymi — często da się je zrozumieć po historii danych lub po poprawce pojedynczych pól.

**Mapa braków (walidacja):** poziomy pas pól wyłącznie dla **kolumn schematu importu** (model aplikacji / raport), nie dla dodatkowych kolumn z arkusza. W pasie tylko **% wierszy z luką** (NaN, puste, „nan”); **nazwy kolumn** ukośnie pod pasem. Kolory **leśne** (jasna mgła = mało braków, ciemniejszy mech/kora = więcej), bez osobnego paska legendy — dokładne % w każdej komórce mapy.

**Eksport CSV:** możesz pobrać listę problemów (**id**, **waga** ERROR/WARN, **typ_problemu**, **szczegoly**) — do filtrowania i poprawy w Excelu. Dla problemów dotyczących całej bazy (np. cykl w rodowodzie) w kolumnie id jest `_GLOBAL_`.

**Wykres podsumowania:** słupki z liczbą wpisów błędów i ostrzeżeń (zgodnie z eksportem) oraz najczęstsze typy problemów — ułatwia szybki przegląd jakości bazy przed pracą z tabelą i CSV.

**Podmenu Walidacja:** **dziewięć** podsekcji w **dwóch rzędach** przycisków (szerokość dopasowana do krótkiej nazwy) — m.in. arkusz/braki pól, ID i płeć, rodzice, lata i daty, graf, linie Z/M, przodkowie, raport z wykresem i pełnym CSV oraz **Auto-poprawki**. W każdej (oprócz auto-poprawek) widać odpowiedni wycinek problemów; częściowy CSV jest przy tabeli, pełny eksport — w podsekcji **Raport + CSV**.

**Automatyczne poprawki:** osobna podsekcja **Auto-poprawki** — reguły (duplikaty, brak ID, lata, daty tekstowe, self-parent, brakujący rodzic w bazie, kolizja płci, wiek rodzica wg progów z `config/gui.json`), podgląd logu bez zapisu, zastosowanie z przeliczeniem walidacji lub przywrócenie ostatniego stanu z importu.
"""


SECTION_PERSONS = """
## Osobniki (tabela)

Widzisz listę rekordów z możliwością sortowania. **Szukaj po ID** (pełne lub fragment) szybko zawęża listę.

Nowy filtr **Miejsce ur. (birth_location)** zawęża tabelę do wybranej lokalizacji (lub do **NA**, gdy pole jest puste/brak danych).

Kolumna z **linią (ojciec/matka)** to skrót: **skąd pochodzi linia** po stronie ojca i matki w drzewie — bez otwierania wykresu rodowodu możesz szybko zobaczyć strukturę kojarzeń w stadzie.

**Udział założycieli** w szczegółach osobnika to rozkład genów w modelu **founder-stop** (jak przy F): brak ojca lub matki kończy gałąź; wartości procentowe sumują się do 100 % przy pełnym opisie przodków w bazie.
"""


SECTION_PEDIGREE = """
## Rodowód (graf)

- **Rodzaj grafu** — **przodkowie** (BFS w górę po `father_id` / `mother_id`), **potomkowie** (BFS w dół: wszyscy, którzy wskazują danego osobnika jako ojca lub matkę), albo **łączone drzewo**: ta sama osoba na środku (oś Y = 0), przodkowie na ujemnych poziomach, potomkowie na dodatnich — jeden duży rysunek (przy dużej liczbie węzłów program automatycznie **zmniejsza limit pokoleń** dla czytelności).
- **Limit pokoleń** — gdy nie zaznaczasz „bez limitu”, ogranicza głębokość w górę **albo** w dół (w zależności od rodzaju grafu). Przy bardzo dużym drzewie program może dodatkowo **uciąć** rysunek wg progu liczby węzłów.
- **Bez limitu** — pełne zejście do brakujących rodziców (przodkowie) albo do liści (potomkowie: osobnicy bez dzieci w bazie), o ile rozmiar grafu mieści się w progu; inaczej stosowany jest limit gęstości jak wcześniej.
- **Tryb czytelny** — mniej napisów na węzłach, lepszy widok przy gęstym grafie.
- **Linie (sireline / damline)** — pokazują **odległość do „bazy” linii** po stronie ojca i matki.

**Jak czytać graf:** każdy węzeł to osobnik, strzałki to relacje **rodzic → dziecko**. Brak rodzica w bazie = **koniec gałęzi** (w danych traktujemy to jak punkt startowy rodowodu). W widoku potomków „w dół” strzałki wychodzą od rodzica do dziecka w kolejnych pokoleniach.
"""


SECTION_INBRED = """
## Inbred (F) — jeden osobnik

- **F** (Wright) — definicja jak w **Słowniku** u góry pomocy; tutaj liczysz **F** dla jednego numeru ID przy ustawionym limicie pokoleń (albo bez limitu).
- **Wykres F vs głębokość** — jeśli F przestaje rosnąć po kilku pokoleniach, to zwykle znaczy, że **dalej wstecz program już nic nowego nie „widzi”** albo dane się nie zmieniają; to normalne przy częściowo wypełnionych rodowodach.
- **Wykres kompletności (PCL)** — pokazuje, **jak bardzo wypełnione** są kolejne poziomy przodków w porównaniu z maksymalną liczbą miejsc na tym poziomie.
"""


SECTION_MATING = """
## Mating (propozycje par) i kinship

- Dla par **samiec × samica** (po filtrze wieku) liczone jest **F hipotetycznego potomka** — w tej metodyce jest ono równe **Φ** (współczynnik współzgodności, *kinship* / coancestry) między ojcem a matką. **R = 2Φ** to klasyczny **współczynnik relacji Wrighta** (autosomy). W rankingu i w panelu „Kinship” widać obie wartości.
- Lista pokazuje **do 36 par**, posortowanych od **najmniejszego Φ** (= F potomka). Ten sam osobnik może być w liście **co najwyżej 3 razy** (jako sire lub dam).
- **Macierz Φ**: po obliczeniu rankingu możesz zapisać tabelę **wszystkich par sire×dam** z aktualnego zestawu kandydatów (CSV) — wiersze = samce, kolumny = samice, komórka = Φ.
- **Kinship dowolnej pary**: dwa wybrane ID z bazy — **Φ** i **R**; **Φ(A,B) = Φ(B,A)** (symetria współzgodności Malecota). **F potomka** z hipotetycznego kojarzenia tych osobników jako rodziców jest równe **Φ**.
- **Dlaczego taki wynik?** (sekcja analizy par): rozkład na **wspólnych przodków**, **wkład do Φ** (w tym skalowanie do wartości z rekurencji, gdy suma surowych ścieżek przekracza Φ przez nakładanie się dróg genów) oraz **liczba par niezależnych ścieżek** w grafie rodowym.
- **Filtr miejsca urodzenia** (birth_location) może dodatkowo zawęzić kandydatów do par — przydatne, gdy chcesz porównywać kojarzenia tylko w wybranej grupie.
- **Limity** liczby samców, samic i pokoleń **skracają czas** i nie muszą obejmować całej populacji.
"""


SECTION_POPULATION = """
## Parametry populacyjne

Metryki **na dashboardzie** są pogrupowane tematycznie (nagłówki z kolorową krawędzią); **liczby** w danej grupie są w tym samym kolorze akcentu co sekcja. **Wykresy** wybiera się z pięciu zakładek (również w tych kolorach), a w każdej zakładce — konkretny podwykres. Objaśnienia: **?** przy etykiecie. Pełniejsze definicje: **Słownik parametrów** na dole strony.

**N_e** (pod metrykami) to uproszczony Szacunek z trendów **F** i **GI** — wyłącznie orientacyjnie.

Pod dashboardem: **dwa rzędy przycisków** (menu wykresów) — urodzenia, kompletność, **F**, założyciele **p_i**, **GI**, rodziny, trendy **F/RIA**, PCL itd. Tekst **Interpretacja** zależy od opcji „rozwinięte podpowiedzi” nad dashboardem.
"""

# Podpowiedzi pod ikoną ? (st.metric / kontrolki) — sekcja Populacja
POPULATION_METRIC_HELP = {
    "n": "Liczba osobników w tej analizie (pomijany jest rekord testowy).",
    "mean_f": "Średnia **F** (Wright) po osobnikach — jak w słowniku; przy tym samym limicie pokoleń co ustawienia powyżej (lub bez limitu).",
    "fe": "**f_e** — efektywna liczba założycieli: 1/Σp_i² z rozkładu średnich wkładów genów **p_i** (founder-stop).",
    "fa": "**f_a** — druga miara różnorodności założycieli (founder-stop); definicja jak w słowniku parametrów.",
    "ria": RIA_HELP_TOOLTIP,
    "fge": "**f_ge** — liczba odrębnych identyfikatorów „założycielskich” w modelu wkładów (rozmiar listy średnich **p_i**).",
    "eg": "**EG** — średnia z miary równoważnych pełnych pokoleń rodowodu (głębokość i kompletność); szczegóły w słowniku.",
    "gi": "**GI** — średni odstęp międzypokoleniowy w latach (łączy ścieżki ojciec→dziecko i matka→dziecko).",
    "ne": "**N_e** — uproszczony szacunek efektywnej wielkości populacji z trendów średniego F i GI; wyłącznie orientacyjnie.",
    "pct_par": "Odsetek **rekordów**, w których brakuje ojca lub matki w polu.",
    "pct_slot": "Odsetek **pustych slotów** rodziców względem 2n (dwa sloty na osobnika).",
    "founders_n": "Liczba rekordów traktowanych jak **założyciele** (brak co najmniej jednego rodzica w danych).",
    "conc": "Koncentracja kojarzeń: jaki % potomstwa z **znanym ojcem** przypada na 5 i 10 najczęściej występujących ojców.",
    "coh_n": "Liczba osobników urodzonych w ostatnich X latach (rok ur.); X ustawiasz polem „Kohorta aktywna” powyżej.",
    "coh_mf": "W tym samym oknie lat: liczba samców i samic.",
    "repr_all": "**Reproduktorzy** w całej bazie: ile różnych ojców i matek wystąpiło jako rodzic przy znanych urodzeniach potomstwa.",
    "repr_coh": "Reproduktorzy w odniesieniu do potomstwa z tej samej kohorty aktywnej co metryki obok.",
}

POPULATION_CONTROL_HELP = {
    "verbose": "Gdy włączone, bloki „Interpretacja” pod wykresami w zakładkach otwierają się domyślnie rozwinięte.",
    "f_ub": "Bez limitu: **F** liczone wstecz aż do founderów (wolniejsze na dużych bazach).",
    "f_dep": "Przy włączonym limicie: maksymalna głębokość pokoleń wstecz przy liczeniu **F** dla populacji i trendów.",
    "act_y": "Szerokość okna w latach (od bieżącego roku wstecz) dla **koherty aktywnej** — rok urodzenia.",
    "vuln_r": "Dla tabeli ryzyka linii: ile ostatnich lat urodzeń wziąć pod uwagę.",
    "vuln_a": "Szerokość okna „aktywnych” lat dla drugiej części heurystyki ryzyka linii (LB/LC).",
}


SECTION_REPORTS = """
## Raporty

- **Podgląd tekstowy** oraz zapis **.pdf** (A4, tekst z zawijaniem wierszy), **.docx** i **.txt**.
- Raport zbiorczy zawiera m.in.: **datę generacji**, **źródło danych**, **parametry liczenia** (np. głębokość F/EG/PCI), **opis zbioru** (kolumny modelu, płeć, lata urodzenia, braki slotów rodzicielskich), **skrót walidacji** (status i liczby — bez listy problemów; szczegóły i CSV w module walidacji), dalej **metryki populacji** (F z min/med/maks, **RIA** — udział zinbredowanych, EG/PCI, f_e/f_a, linie, top założyciele wg p_i), **mean kinship (Φ̄, R)**, **GI** i **rodziny pełnego rodzeństwa**, **miejsca urodzenia** (top N wg konfiguracji).
- **Wykresy** z modułu Populacja i **PNG rodowodów** dołączasz osobno (pobrania w aplikacji).
"""


SECTION_BREEDING = """
## Scenariusze planu hodowlanego

W **nawigacji bocznej** wybierz **Scenariusze planu hodowlanego**.

Moduł **proponuje pary** przy ograniczeniach: wiek, linia, miejsce urodzenia, limit kandydatów, ile razy można użyć tej samej samicy / samca, opcjonalny **górny próg F potomka** (oraz informacja, gdy **średnie F** zestawu przekracza wybrany próg — bez dodatkowego filtrowania). Wynik **zależy od kompletności rodowodów** i od ustawień liczenia F (limit pokoleń lub do founderów).

Po wyborze pozycji na liście widać **statystyki** (F potomka i rodziców, MG/EG/PCI rodziców). **Graf rodowodu hipotetycznego potomka** jest pod szczegółami pary, z możliwością **pobrania PNG**.
"""


# --- Wykresy populacji (interpretacja) ---

CHART_BIRTH_SEX = (
    "Słupki pokazują, **ile osobników urodziło się w każdej dekadzie** (np. lata 90.), osobno **samce (M)** i **samice (F)**. "
    "Dzięki temu widać skalę przyrostu i to, czy w którymś okresie nie dominuje jedna płeć. "
    "Pusta dekada = brak danych albo rok poza wybranym zakresem."
)

CHART_BIRTH_LINE = (
    "Jak wykres płci, ale podział według **linii** w danych (najczęściej **LB** i **LC**). "
    "Widać, która linia była liczniejsza w kolejnych dekadach. Zwierzęta bez LB/LC często nie trafiają na ten wykres."
)

CHART_FM_RATIO = (
    "**Stosunek F/M** = liczba samic podzielona przez liczbę samców urodzonych w dekadzie. "
    "Linia pozioma przy **1** oznacza równy udział; wartość **powyżej 1** — więcej samic. "
    "Gdy w dekadzie nie ma wcale samców, punkt może zniknąć (nie da się dzielić przez zero)."
)

CHART_COMP_SEX = (
    "Dla **M** i **F** osobno: średnie **MG, CG, EG** (patrz słownik). "
    "Porównujesz, czy jedna płeć ma w bazie **średnio głębszy lub bardziej kompletny** rodowód — często to efekt historii rejestracji, a nie „naturalnej” różnicy biologicznej."
)

CHART_COMP_LINE = (
    "To samo co wykres kompletności wg płci, ale **osobno dla LB, LC** i pozostałych (**NA**). "
    "Ułatwia zobaczyć, czy jedna linia hodowlana ma lepsze dokumentowanie rodowodów."
)

CHART_HIST_F = (
    "**Rozkład F** w całej populacji (przy wybranym limicie pokoleń dla F). "
    "Wysoki słupek przy **0** = dużo osobników z **F = 0** (w tym modelu brak sygnału zinbredowania); "
    "„Ogon” w prawo = część osobników ma **wyższe F**."
)

CHART_F_SCATTER_BIRTH = (
    "Wykres punktowy: każda kropka to jeden osobnik (oś X = rok urodzenia, oś Y = F). "
    "Przy dużej liczbie punktów ważniejszy od pojedynczej kropki jest **trend** i zagęszczenie obszarów; "
    "nakładanie punktów jest normalne przy powtarzalnych wartościach F."
)

CHART_FOUNDERS_PI = (
    "**Dwadzieścia największych** udziałów **p_i** — kto z przodków (w rozumieniu obliczeń programu) **najbardziej zdominował** pulę genów. "
    "Wysoki słupek może oznaczać silny wpływ kilku linii albo wąskie „gardło” w pochodzeniu materiału genetycznego. "
    "Metodyka oparta jest na prawdopodobieństwach pochodzenia genów — zob. Boichard i wsp. (1997) w sekcji literatury."
)

CHART_GI_BAR = (
    "**GI** to tu różnica **rok urodzenia potomka minus rok urodzenia rodzica** (tylko gdy oba lata są znane). "
    "Wykres pokazuje średnie dla czterech ścieżek: ojciec→syn, ojciec→córka, matka→syn, matka→córka. "
    "Różnice między słupkami odpowiadają temu, **kto i po ilu latach** typowo rodzi potomstwo w stadzie."
)

CHART_GI_TREND = (
    "Dla każdej dekady **urodzenia potomka** liczone jest średnie GI osobno dla czterech ścieżek. "
    "Widać, czy **odstępy międzypokoleniowe** z czasem się wydłużają czy skracają — może to wiązać się ze zmianą zarządzania hodowlą."
)

CHART_GI_4PATHS_SMOOTH = (
    "Cztery osobne panele (ojciec→syn, ojciec→córka, matka→syn, matka→córka): "
    "**jasna linia = wartości surowe**, **ciemna linia = wygładzenie**. "
    "To ułatwia porównanie kierunku trendu GI między ścieżkami bez utraty surowej zmienności."
)

CHART_FAMILY = (
    "**Rodzina pełnego rodzeństwa** = te same znane **ojciec i matka**. "
    "Słupek przy liczbie **k** oznacza: tyle rodzin ma dokładnie **k** potomków w bazie; "
    "grupa **10+** zbiera większe rodziny razem."
)

CHART_INBRED_TP_SEX = (
    "Górny panel: **średnie F** według roku urodzenia, osobno **M** i **F**. "
    "Dolny panel: **RIA (%)** — " + RIA_PLAIN_SHORT + ". "
    "Pozwala zobaczyć, czy udział zinbredowanych „w czasie” rośnie czy maleje; różnice M/F mogą wynikać z kojarzeń albo z **różnej kompletności danych**."
)

CHART_INBRED_TP_LINE = (
    "Jak wykres trendu F i RIA wg płci, ale **osobno dla linii LB, LC i NA** — porównanie trendów między liniami hodowlanymi. "
    "Dolny panel: **RIA (%)** — " + RIA_PLAIN_SHORT + "."
)

CHART_F_RIA_SMOOTH = (
    "Dwa panele (A/B): u góry **średnie F po roku urodzenia**, na dole **RIA (%)** — "
    + RIA_PLAIN_SHORT + ". "
    "Czarna seria pokazuje przebieg surowy, czerwona — wygładzony trend, dzięki czemu łatwiej ocenić długofalowe zmiany."
)


# Skrót metod + cytowanie (PDF „Przewodnik metod”) — tekst płaski, bez markdown.
METHODS_GUIDE_PDF_INTRO = """
WISENTPEDIGREE PRO+ — KRÓTKI PRZEWODNIK METOD

Dokument pomocniczy do cytowania w publikacjach i raportach hodowlanych.
Program analizuje strukturę rodowodów wyłącznie na podstawie zapisanych relacji
rodzic–dziecko oraz dostępnych dat; wnioski biologiczne zależą od kompletności bazy.

Zakres obliczeń (skrót)
— F (Wright): współczynnik inbredu z rekurencji rodowodowej; opcjonalny limit pokoleń
  lub liczenie bez limitu (founder-stop przy braku rodzica w danych).
— RIA: udział zinbredowanych — procent osobników z F>0 przy tym samym limicie F co metryki populacji / wykres.
— Φ (coancestry) i R = 2Φ: dla kojarzenia F hipotetycznego potomka = Φ między ojcem a matką;
  R — współczynnik relacji Wrighta (autosomy), zgodnie z implementacją w programie.
— MG, CG, EG, PCI: miary kompletności / głębokości rodowodu u osobnika lub w populacji.
— p_i, f_e, f_a: wkłady genów „założycieli” w rozumieniu founder-stop; wykres Top 20 p_i.
— GI: odstępy międzypokoleniowe z różnic lat urodzenia (ścieżki ojciec/matka → potomek).
— N_e: przybliżenie z trendu średniego F i średniego GI — wyłącznie orientacyjnie.
— Walidacja: kontrola ID, referencji rodziców, cykli, self-parent, płci, lat, spójności linii.
""".strip()


SECTION_REFERENCES = """
## Literatura — skąd biorą się metody

Poniżej **podstawowe i w dalszym ciągu standardowo cytowane** pozycje w genetyce ilościowej i analizie rodowodów (z aktualnymi identyfikatorami DOI, gdzie są ustalone). **Wynik w aplikacji** zależy od **jakości i kompletności Twojej bazy** (zapis rodziców i dat).

1. **Inbred (F), pokrewieństwo (Φ), współczynnik relacji** — Wright, S. (1922). *Coefficients of inbreeding and relationship.* The American Naturalist **56**, 330–338. https://doi.org/10.1086/279872  
   Wprowadzenie podręcznikowe: Falconer, D. S., & Mackay, T. F. C. (1996). *Introduction to Quantitative Genetics* (4th ed.). Pearson / Longman.  
   Współczesne ujęcie (ścieżki genealogiczne, selekcja, demografia genetyczna): Walsh, B., & Lynch, M. (2018). *Evolution and Selection of Quantitative Traits*. Oxford University Press.

2. **Teoria pokrewieństwa (identity by descent, ścieżki w rodowodzie)** — Malécot, G. (1948). *Les mathématiques de l'hérédité*. Masson, Paris — klasyka modelu; formalizm i notacja w Walsh & Lynch (2018).

3. **Prawdopodobieństwa pochodzenia genów (p_i, „gene origin”)** — Boichard, D., Maignel, L., & Verrier, É. (1997). *The value of using probabilities of gene origin to measure genetic variability in a population.* Genetics Selection Evolution **29**, 5–23. https://doi.org/10.1186/1297-9686-29-1-5

4. **Fundatorzy w rodowodzie — founder equivalents / founder genome equivalents** — Lacy, R. C. (1989). *Analysis of founder representation in pedigrees: founder equivalents and founder genome equivalents.* Zoo Biology **8**, 111–123. https://doi.org/10.1002/zoo.1430080202

5. **Odstęp pokoleniowy (generation interval, GI)** — definicje i związek z pracą selekcji: rozdziały w Falconer & Mackay (1996) oraz w Walsh & Lynch (2018).

6. **Efektywna wielkość populacji (N_e) a tempo inbredu** — Wright, S. (1931). *Evolution in Mendelian populations.* Genetics **16**, 97–159. https://doi.org/10.1093/genetics/16.2.97  
   Omówienia: Falconer & Mackay (1996); Walsh & Lynch (2018). **W programie** szacunek N_e jest uproszczony (trendy z wczytanych danych) — **tylko orientacyjnie**.
"""


def all_charts_text() -> str:
    """Zbiór opisów wykresów populacji (pełna pomoc / Streamlit)."""
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
        "\n\n### F vs rok urodzenia\n",
        CHART_F_SCATTER_BIRTH,
        "\n\n### Założyciele p_i\n",
        CHART_FOUNDERS_PI,
        "\n\n### GI (średni)\n",
        CHART_GI_BAR,
        "\n\n### GI trend\n",
        CHART_GI_TREND,
        "\n\n### GI: 4 ścieżki (surowe + wygładzone)\n",
        CHART_GI_4PATHS_SMOOTH,
        "\n\n### Rodziny pełne\n",
        CHART_FAMILY,
        "\n\n### Inbred TP: płeć\n",
        CHART_INBRED_TP_SEX,
        "\n\n### Inbred TP: linie\n",
        CHART_INBRED_TP_LINE,
        "\n\n### F i RIA: surowe + wygładzone\n",
        CHART_F_RIA_SMOOTH,
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
    + "\n\n---\n\n"
    + SECTION_REFERENCES
    + "\n\n---\n\n"
    + all_charts_text()
)
