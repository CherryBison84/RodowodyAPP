# -*- coding: utf-8 -*-
"""
Teksty pomocy po polsku: prosty język, skróty (F, GI, RIA…), wykresy, walidacja.
Wspólne dla okna na pulpicie (Tk) i wersji w przeglądarce (Streamlit).
Przy metodach statystycznych — skrótowa literatura naukowa.
"""

from __future__ import annotations

# --- Główny słownik (markdown dla Streamlit, zwykły tekst dla Tk) ---

GLOSSARY = """
## Słownik — najczęściej używane pojęcia

### Inbred i współczynnik F (Wright)
- **F** — liczba od 0 w górę, która mówi, **jak bardzo w rodowodzie powtarzają się ci sami przodkowie**. Im wyższe F, tym większe ryzyko, że u potomka spotykają się kopie genów od tych samych osób (to właśnie nazywa się inbredem). W aplikacji F jest liczone z zapisu rodziców w bazie, z możliwym limitem „ile pokoleń wstecz brać pod uwagę”.
- **Związek rodziców (Φ)** — klasycznie F potomka zależy od tego, jak bardzo **ojciec i matka są ze sobą spokrewnieni**. Tu Φ jest liczone z drzewa rodowego; jeśli w bazie brakuje ojca lub matki, obliczenia zatrzymują się na tym miejscu (**„founder-stop”** — tak traktujemy koniec znanej gałęzi).
- **Mean kinship (średni kinship)** — **średnia z Φ(i,j)** po parach różnych osobników (i≠j); opisuje, jak **średnio** spokrewniona jest populacja. **Średnie R = 2Φ̄** to średni współczynnik relacji Wrighta (autosomy). Przy bardzo dużym **n** program liczy średnią po parach **w losowej próbie** osobników (szybciej); przy mniejszym n — po wszystkich parach. **Ten sam limit pokoleń** co przy F / Φ dla pojedynczej pary.
- **Limit pokoleń** — możesz ograniczyć, jak głęboko program schodzi wstecz przy liczeniu F. **Bez limitu** schodzi tak daleko, jak pozwalają dane, aż do osób bez dalszych rodziców w bazie.
- **Wykres F a maksymalna głębokość** — pokazuje, czy wynik F „ustabilizował się”, gdy zwiększasz liczbę pokoleń. Jeśli od pewnego poziomu krzywa się już prawie nie zmienia, dalsze pokolenia niewiele dodają — to częsty znak, że w tym fragmencie rodowodu dane są w miarę pełne.

*(Te pojęcia wywodzą się z prac Sewalla Wrighta z lat 20. XX w.; pełne cytowania: **Pomoc → pełny dokument** albo sekcja **Literatura — źródła metod** w panelu Streamlit.)*

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
- **p_i** i wykres **Top 20** — kto z przodków (w rozumieniu founder-stop) ma **największy udział** w puli genów w populacji; wysoki słupek = duży wpływ jednej linii lub osoby.
- **Linie LB / LC** — etykiety z kolumny linii w danych; reszta trafia do **NA**.

### Odstępy międzypokoleniowe i rodziny
- **GI (Generation Interval)** — tu: **różnica lat urodzenia** potomka i rodzica (osobno dla ścieżek ojciec–syn, ojciec–córka itd.), gdy znamy oba lata. Średnie GI mówi, **po ilu latach** typowo pojawia się następne pokolenie.
- **Rodzina pełnego rodzeństwa** — dzieci z **tej samej pary** ojciec+matka; histogram pokazuje, ile takich rodzin ma 1, 2, 3… potomków w bazie.

### Trendy w czasie (Inbred TP)
- **TP** — podział według **roku urodzenia** osobnika.
- **Średnie F w roku** — średnia F wśród osób urodzonych w danym roku.
- **RIA (%)** — **jaki procent** osobników w roku ma F większe od zera (w sensie obliczeń numerycznych w programie).

### N_e (szacunek orientacyjny)
- Program podaje **przybliżoną efektywną wielkość populacji** na podstawie trendu średniego F w czasie i średniego odstępu międzypokoleniowego (GI). To **uproszczenie**: wynik mocno zależy od kompletności rodowodów i wybranego okresu — używaj jak wskazówki, nie jak precyzyjnej stałej biologicznej.

*(Związek tempa narastania inbredu z N_e ma korzenie u Wrighta; szczegóły w podręcznikach z listy na końcu.)*

### Walidacja bazy
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

**Kolejny krok:** w wersji przeglądarkowej i na pulpicie po imporcie przejdź do **Walidacja bazy** — tam jest **krótki wynik** (np. liczba błędów), **wypunktowanie** problemów, **CSV** z listą (id, typ, szczegóły) do poprawy w Excelu oraz pełny raport tekstowy.
"""


SECTION_VALIDATION = """
## Walidacja — co jest sprawdzane

- **Unikalność ID** — jeśli ten sam numer pojawia się dwa razy, program nie wie, który wiersz jest „prawdziwy” dla osobnika.
- **Rodzice w bazie** — jeśli wpiszesz `father_id` / `mother_id`, powinny wskazywać na **istniejący** rekord (inaczej gałąź kończy się „w powietrzu”).
- **Płeć, linia, rok urodzenia** — czy wartości mają sens (np. rok w rozsądnym zakresie).
- **Relacje rodzic–dziecko** — m.in. oczywiste sprzeczności z płcią roli rodzica.

Status **OK** znaczy: **nie znaleziono błędów krytycznych**. **Ostrzeżenia** warto przejrzeć przed wnioskami hodowlanymi — często da się je zrozumieć po historii danych lub po poprawce pojedynczych pól.

**Mapa braków (walidacja):** poziomy pas pól obok siebie — w każdym **nazwa kolumny** i **% wierszy z luką** (NaN, puste, „nan”), w **kolejności jak w rejestrze**; kolory **leśne** (jasna mgła = mało braków, ciemniejszy mech/kora = więcej).

**Eksport CSV:** możesz pobrać listę problemów (**id**, **waga** ERROR/WARN, **typ_problemu**, **szczegoly**) — do filtrowania i poprawy w Excelu. Dla problemów dotyczących całej bazy (np. cykl w rodowodzie) w kolumnie id jest `_GLOBAL_`.
"""


SECTION_PERSONS = """
## Osobniki (tabela)

Widzisz listę rekordów z możliwością sortowania. **Szukaj po ID** (pełne lub fragment) szybko zawęża listę; w wersji na pulpicie jest też przycisk **Znajdź**, który zaznacza pierwszy pasujący wiersz w tabeli.

Nowy filtr **Miejsce ur. (birth_location)** zawęża tabelę do wybranej lokalizacji (lub do **NA**, gdy pole jest puste/brak danych).

Kolumna z **linią (ojciec/matka)** to skrót: **skąd pochodzi linia** po stronie ojca i matki w drzewie — bez otwierania wykresu rodowodu możesz szybko zobaczyć strukturę kojarzeń w stadzie.

**Udział założycieli** w szczegółach osobnika to rozkład genów w modelu **founder-stop** (jak przy F): brak ojca lub matki kończy gałąź; wartości procentowe sumują się do 100 % przy pełnym opisie przodków w bazie.
"""


SECTION_PEDIGREE = """
## Rodowód (graf)

- **Limit pokoleń** — ile poziomów w górę (wstecz) od wybranej osoby. Przy bardzo dużym drzewie program może **ograniczyć rysunek**, żeby nadal dało się go czytać.
- **Tryb czytelny** — mniej napisów na węzłach, lepszy widok przy gęstym grafie.
- **Linie (sireline / damline)** — pokazują **odległość do „bazy” linii** po stronie ojca i matki.

**Jak czytać graf:** każdy węzeł to osobnik, strzałki to relacje **rodzic → dziecko**. Brak rodzica w bazie = **koniec gałęzi** (w danych traktujemy to jak punkt startowy rodowodu).
"""


SECTION_INBRED = """
## Inbred (F) — jeden osobnik

- Wynik **F** dotyczy **wybranego numeru ID** przy ustawionym limicie pokoleń (albo bez limitu).
- **Wykres F vs głębokość** — jeśli F przestaje rosnąć po kilku pokoleniach, to zwykle znaczy, że **dalej wstecz program już nic nowego nie „widzi”** albo dane się nie zmieniają; to normalne przy częściowo wypełnionych rodowodach.
- **Wykres kompletności (PCL)** — pokazuje, **jak bardzo wypełnione** są kolejne poziomy przodków w porównaniu z maksymalną liczbą miejsc na tym poziomie.
"""


SECTION_MATING = """
## Mating (propozycje par) i kinship

- Dla par **samiec × samica** (po filtrze wieku) liczone jest **F hipotetycznego potomka** — w tej metodyce jest ono równe **Φ** (współczynnik współzgodności, *kinship* / coancestry) między ojcem a matką. **R = 2Φ** to klasyczny **współczynnik relacji Wrighta** (autosomy). W rankingu i w panelu „Kinship” widać obie wartości.
- Lista pokazuje **do 36 par**, posortowanych od **najmniejszego Φ** (= F potomka). Ten sam osobnik może być w liście **co najwyżej 3 razy** (jako sire lub dam).
- **Macierz Φ**: po obliczeniu rankingu możesz zapisać tabelę **wszystkich par sire×dam** z aktualnego zestawu kandydatów (CSV) — wiersze = samce, kolumny = samice, komórka = Φ.
- **Kinship dowolnej pary**: dwa wybrane ID z bazy — **Φ** i **R**; **Φ(A,B) = Φ(B,A)** (symetria współzgodności Malecota). **F potomka** z hipotetycznego kojarzenia tych osobników jako rodziców jest równe **Φ**.
- **Dlaczego taki wynik?** (Streamlit / zakładka „Para” w Tk): rozkład na **wspólnych przodków**, **wkład do Φ** (w tym skalowanie do wartości z rekurencji, gdy suma surowych ścieżek przekracza Φ przez nakładanie się dróg genów) oraz **liczba par niezależnych ścieżek** w grafie rodowym.
- **Filtr miejsca urodzenia** (birth_location) może dodatkowo zawęzić kandydatów do par — przydatne, gdy chcesz porównywać kojarzenia tylko w wybranej grupie.
- **Limity** liczby samców, samic i pokoleń **skracają czas** i nie muszą obejmować całej populacji.
"""


SECTION_POPULATION = """
## Populacja — liczby u góry

- **n** — ile osobników jest w analizie (bez rekordu testowego).
- **Średnie F** — średnia F po osobnikach przy wybranym limicie dla populacji.
- **Mean kinship Φ̄** i **średnie R (2Φ̄)** — średnia współzgodności po parach i≠j (przy dużym stadzie: losowa próba; patrz słownik).
- **f_e, f_a** — miary związane z **założycielami** i różnorodnością genów (patrz słownik).
- **RIA % (globalna)** — odsetek osobników z F > 0 przy tym samym limicie pokoleń co reszta sekcji.
- **f_ge** — liczba odrębnych identyfikatorów założycielskich w modelu wkładów (founder-stop), tj. rozmiar listy średnich wkładów p_i.
- **% braków rodziców** — albo odsetek **rekordów** z brakiem ojca lub matki, albo odsetek **pustych slotów** (ojciec+matka) względem 2n.
- **Kohorta aktywna** — osobnicy urodzeni w ostatnich X latach (rok ur.); **reproduktorzy** — unikalne ID ojca/matki przy urodzeniach potomstwa w tym samym oknie; wersja „w koh.” ogranicza do płci zgodnej z kohortą.
- **Koncentracja ojców** — jaki udział potomstwa z **znanym ojcem** przypada na 5 lub 10 najczęściej używanych ojców.
- Zakładka **Okresy, ryzyko…** — porównanie urodzeń 1950–1980 / 1981–2000 / 2001–dziś, uproszczony ranking „ryzyka” dla linii LB i LC oraz wykresy trendu reproduktorów i udziału linii w czasie.
- **Założyciele (brak ojca lub matki)** — ile rekordów ma **dziurę** po jednej ze stron rodziców — ważne przy interpretacji F i metryk potomstwa.
- Ustawienia **F** (z limitem lub bez) wpływają też na histogram F i trendy **F / RIA**.

**N_e** w podpisie to tylko **szacunek z trendów** — nie traktuj go jak wyniku z programu hodowlanego klasy stricte eksperckiej.
"""


SECTION_REPORTS = """
## Raporty

- W wersji **na pulpicie (Tk)** raport może zbierać walidację, skrót populacji i dane osobnika oraz eksport do **DOCX/PDF** z wykresami.
- Raport populacji obejmuje teraz także: **mean kinship (Φ̄, R)**, skrót **GI (4 ścieżki)**, podsumowanie **rodzin pełnego rodzeństwa** oraz **top miejsc urodzenia**.
- W **Streamlit** masz podgląd tekstowy i zapis **.txt**; zakres metryk został ujednolicony i obejmuje m.in. mean kinship, GI oraz podsumowanie miejsc urodzenia.
"""


SECTION_BREEDING = """
## Plan hodowlany (tylko Tk)

Ścieżka w menu: **Analityka hodowlana → Plan hodowli** (obok innych narzędzi hodowlanych).

Moduł **proponuje pary** przy ograniczeniach: wiek, linia, ile razy można użyć tego samego reproduktora, cele dotyczące średniego lub maksymalnego F. Wynik **zależy od tego, jak dobre są rodowody w bazie** i jak ustawisz liczenie ryzyka inbredu.

Po **kliknięciu wiersza** w tabeli widać **statystyki** (F potomka i rodziców, MG/EG/PCI rodziców). **Duży graf rodowodu** potomka otwiera się przyciskiem **„Pokaż rodowód potomka w nowym oknie”**; stamtąd można zapisać obraz jako **JPEG**.

W Streamlit odpowiednik modułu jest **w budowie**.
"""


SECTION_SETTINGS = """
## Ustawienia

- **Tk:** część ustawień (np. domyślna głębokość F, eksport) jest zapamiętywana **w sesji** i używana przy kolejnych krokach.
- Po zapisie pliku z aplikacji (JPEG, CSV, DOCX, PDF itd.) system próbuje **automatycznie otworzyć** go w domyślnej aplikacji (macOS: `open`, Windows: skojarzony program, Linux: `xdg-open`).
- **Streamlit:** ustawienia dotyczą **tej samej sesji w przeglądarce** i znikają po zamknięciu karty (nie są zapisywane na dysku jak osobny plik konfiguracyjny). Pobrania plików obsługuje przeglądarka — otwarcie zależy od jej ustawień.
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
    "Wysoki słupek przy **0** = dużo osobników, u których w tym modelu **nie widać inbredu**; "
    "„Ogon” w prawo = część osobników ma **wyższe F**."
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
    "Dolny: **RIA (%)** — jaki procent osobników urodzonych w danym roku ma **F > 0**. "
    "Pozwala zobaczyć, czy inbred „w czasie” rośnie czy maleje; różnice M/F mogą wynikać z kojarzeń albo z **różnej kompletności danych**."
)

CHART_INBRED_TP_LINE = (
    "Jak wykres trendu F i RIA wg płci, ale **osobno dla linii LB, LC i NA** — porównanie trendów między liniami hodowlanymi."
)

CHART_F_RIA_SMOOTH = (
    "Dwa panele (A/B): u góry **średnie F po roku urodzenia**, na dole **RIA (%)**. "
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
— Φ (coancestry) i R = 2Φ: dla kojarzenia F hipotetycznego potomka = Φ między ojcem a matką;
  R — współczynnik relacji Wrighta (autosomy), zgodnie z implementacją w programie.
— MG, CG, EG, PCI: miary kompletności / głębokości rodowodu u osobnika lub w populacji.
— p_i, f_e, f_a: wkłady genów „założycieli” w rozumieniu founder-stop; wykres Top 20 p_i.
— GI: odstępy międzypokoleniowe z różnic lat urodzenia (ścieżki ojciec/matka → potomek).
— N_e: przybliżenie z trendu średniego F i średniego GI — wyłącznie orientacyjnie.
— Walidacja: kontrola ID, referencji rodziców, cykli, self-parent, płci, lat, spójności linii.

Pełniejsze objaśnienia: menu Pomoc w aplikacji (wersja na pulpit) lub panel boczny Streamlit.
Wersja oprogramowania i parametry obliczeń (limity pokoleń, filtry) należy podać przy cytowaniu
wyników z konkretnej sesji.
""".strip()


SECTION_REFERENCES = """
## Literatura — skąd biorą się metody

Poniżej **klasyczne i często cytowane** pozycje, do których nawiązują pojęcia używane w rodowodowej genetyce. **Wynik w aplikacji** zależy zawsze od **jakości i głębokości Twojej bazy** — program liczy z tego, co jest zapisane jako rodzice i daty.

1. **Współczynnik inbredu i pokrewieństwa (F, Φ)** — Wright, S. (1922). *Coefficients of inbreeding and relationship.* The American Naturalist **56**, 330–338. DOI: 10.1086/279872.  
   Wprowadzenie podręcznikowe: Falconer, D. S., & Mackay, T. F. C. (1996). *Introduction to Quantitative Genetics* (4th ed.). Longman — rozdziały o pokrewieństwie i inbredzie.

2. **Teoria pokrewieństwa (w tle wag Malecot dla ścieżek genealogicznych)** — Malécot, G. (1948). *Les mathématiques de l'hérédité*. Masson et Cie, Paris.  
   Nowsze ujęcie całościowe: Lynch, M., & Walsh, B. (1998). *Genetics and Analysis of Quantitative Traits.* Sinauer.

3. **Prawdopodobieństwa pochodzenia genów, p_i, różnorodność z rodowodu** — Boichard, D., Maignel, L., & Verrier, É. (1997). *The value of using probabilities of gene origin to measure genetic variability in a population.* Genetics Selection Evolution **29**(1), 5–23.  
   (Bardzo bliskie temu, co hodowcy nazywają analizą wkładu założycieli / „gene origin”.)

4. **Reprezentacja fundatorów w rodowodzie (founder equivalents / genome equivalents)** — Lacy, R. C. (1989). *Analysis of founder representation in pedigrees: founder equivalents and founder genome equivalents.* Zoo Biology **8**, 111–123.

5. **Przykład pracy z dużą bazą rodowodową i inbredem** — MacCluer, J. W., Boyce, A. J., Dyke, B., Weitkamp, L. R., Pfenning, D. W., & Parsons, C. J. (1983). *Inbreeding and pedigree structure in Standardbred horses.* Journal of Heredity **74**, 27–33.  
   (Ilustruje, jak jakość rodowodu wpływa na sens metryk populacyjnych.)

6. **Długość pokolenia (Generation Interval)** — definicje i zastosowania w hodowli: Falconer & Mackay (1996); u zwierząt gospodarskich także prace przeglądowe w czasopismach typu *Journal of Animal Science* / *Journal of Animal Breeding and Genetics*.

7. **Efektywna wielkość populacji N_e a tempo inbredu** — klasyczny związek w idealizowanych modelach: Wright, S. (1931). *Evolution in Mendelian populations.* Genetics **16**, 97–159; omówienia w Falconer & Mackay oraz Lynch & Walsh. **Szacunek N_e w tej aplikacji** jest uproszczony i oparty na trendach z Twoich danych — traktuj go orientacyjnie.

*Jeśli cytujesz wyniki z programu w pracy naukowej lub raporcie hodowlanym, opisz proszę wersję oprogramowania, parametry (limity pokoleń, filtry) oraz źródło danych.*

**PDF do cytowań:** w menu **Pomoc** (Tk) lub przycisk pobierania w panelu Streamlit dostępny jest skrócony **Przewodnik metod** w formacie PDF (ten skrót + bibliografia poniżej).
"""


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
    + "\n\n"
    + SECTION_SETTINGS
    + "\n\n---\n\n"
    + SECTION_REFERENCES
    + "\n\n---\n\n"
    + all_charts_text()
)
