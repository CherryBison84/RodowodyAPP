Metodyka Analizy Rodowodowej Żubrów (Bison bonasus)

Metodyka opiera się na podziale bazy danych na trzy grupy:
1. Populację Całkowitą (TP)
2. Populację Referencyjną (RP) (osobniki żyjące lub aktywne rozrodczo)
3. Przodków (ANC)

1. Analiza Indywidualna (dla wybranego osobnika)
Dla każdego osobnika identyfikowanego przez unikalny numer (kolumna `Number` w Twojej bazie) wylicza się następujące wskaźniki jakości rodowodu i genetyki:

1.1. Indywidualny współczynnik inbredu Wrighta (`F`)
Definicja: prawdopodobieństwo (P), że dwa allele w danym locus u danego osobnika są identyczne ze względu na wspólne pochodzenie od wspólnego przodka.
Metoda obliczeń: algorytm Wrighta analizuje ścieżki rodowodowe łączące rodziców osobnika przez ich wspólnych przodków. Przyjmuje się, że założyciele mają współczynnik inbredu równy `0`.

1.2. Głębokość rodowodu (Pedigree Depth)
MG (Maximum Generations Traced): maksymalna liczba prześledzonych pokoleń, tj. liczba pokoleń dzieląca osobnika od jego najdalszego znanego przodka.
EqG / EG (Equivalent Complete Generations): obliczana jako suma `(1/2)^n` dla każdego zidentyfikowanego przodka, gdzie `n` to liczba pokoleń do tego przodka. Wartość powyżej `5` sugeruje wysoką jakość danych.

1.3. Pochodzenie (Ancestry)
Linia męska (Sireline): śledzenie przodków wyłącznie w linii ojcowskiej aż do założyciela.
Linia żeńska (Damline): śledzenie przodków wyłącznie w linii matczynej aż do założycielki.

1.4. Indeks kompletności rodowodu (`PCI`)
Miara proporcji znanych przodków w każdym pokoleniu wstecz.

1.5. Definicja założyciela (Founder)
Założyciel: osobnik, którego oboje rodzice są nieznani albo został wprowadzony do bazy na bardzo wczesnym etapie historii populacji (np. żubry z początków restytucji).
Założyciel linii męskiej: samiec z nieznanym ojcem.
Założycielka linii żeńskiej: samica z nieznaną matką.

1.6. Traktowanie brakujących rodziców
Jeżeli w bazie brakuje informacji o rodzicach (np. brak numeru ojca lub matki), osobnik jest traktowany jako założyciel.
Założenie: tacy osobnicy nie są ze sobą spokrewnieni (standardowa procedura w analizach rodowodowych, mająca na celu uniknięcie niedoszacowania różnorodności genetycznej).

2. Analiza Populacyjna (dla całej grupy / RP)
Analiza pozwala ocenić stan genetyczny całej populacji żubrów, zależnie od tego, czy analizujemy TP czy RP.

2.1. Parametry pochodzenia genów
2.1.1. Efektywna liczba założycieli (`f_e`)
Hipotetyczna liczba założycieli o równym wkładzie genetycznym, która dałaby taką samą różnorodność, jak obserwujemy w populacji.

2.1.2. Efektywna liczba przodków (`f_a`)
Minimalna liczba przodków (niekoniecznie założycieli) wyjaśniająca całkowitą zmienność genetyczną, uwzględniająca straty wynikające z nierównomiernego rozrodu.

2.1.3. Ekwiwalent genomowy założycieli (`f_ge`)
Liczba założycieli przy założeniu braku utraty alleli (wskaźnik zależny od przyjętej definicji/modelu).

2.2. Wskaźniki strat genetycznych
2.2.1. Efekt wąskiego gardła (Bottleneck effect)
Stosunek `f_e / f_a`. Wartości znacznie odbiegające od `1.0` sugerują wystąpienie wąskiego gardła.

2.2.2. Wskaźnik dryfu genetycznego
Stosunek `f_e / f_ge`.

2.2.3. Efektywna wielkość populacji (`N_e`)
Wielkość populacji obliczana na podstawie tempa wzrostu inbredu na pokolenie. Zgodnie z wytycznymi FAO wartość `N_e` powinna być wyższa niż `50` (interpretacja zależna od założeń obliczeń).

2.3. Odstęp międzypokoleniowy (`GI`) i struktura rodzin
2.3.1. GI (Generation Interval)
Średni wiek rodziców w momencie narodzin potomstwa, które następnie bierze udział w dalszym rozrodzie.
Obliczany dla 4 ścieżek: Ojciec–Syn, Ojciec–Córka, Matka–Syn, Matka–Córka.

2.3.2. Struktura rodzin
Np. liczba i średnia wielkość rodzin pełnego rodzeństwa.

3. Proponowane wizualizacje
Aby wyniki były czytelne, aplikacja powinna generować:

3.1. Trendy czasowe (wykresy liniowe)
1. Zmiana średniego współczynnika inbredu (`F`) w populacji na przestrzeni lat.
2. Zmiana stosunku płci (Female-Male Ratio) urodzonych osobników w czasie.
3. Zmiany odstępów międzypokoleniowych (`GI`) dla poszczególnych ścieżek dziedziczenia.

3.2. Rozkłady (density plots / histogramy)
1. Rozkład liczby prześledzonych pokoleń (MG / CG / EG) w populacji referencyjnej z podziałem na płeć.
2. Histogram dat urodzenia (liczebność populacji w dekadach / latach).

3.3. Udziały genetyczne (wykresy słupkowe)
1. Wkład genetyczny poszczególnych założycieli lub linii (np. Twoja linia LB) do obecnej populacji.
2. Procentowy udział osobników zinbredowanych w populacji całkowitej.

3.4. Struktura rodowodowa (grafy NetworkX)
1. Drzewo rodowodowe osobnika: interaktywny graf pokazujący ścieżki do założycieli.
2. Grafy linii (Sirelines/Damlines): wizualizacja przepływu wartości genetycznej od założycieli linii do obecnych osobników.

Wskazówka implementacyjna:
Do obliczeń można użyć Pandas (GI oraz statystyki opisowe), NetworkX (struktura rodowodu i ścieżki do założycieli) oraz Matplotlib/Seaborn do odwzorowania estetyki wykresów.