# -*- coding: utf-8 -*-
"""Pomoc dla aktualnego zakresu WisentPedigree DataCleaner."""

from __future__ import annotations

GLOSSARY = """
## Słownik DataCleaner

- **Schemat aplikacji** — wspólny zestaw kolumn, do którego mapowane są raport i rejestr EBPB.
- **Walidacja** — kontrola jakości danych bez modyfikowania rekordów.
- **ERROR** — problem krytyczny, który wymaga sprawdzenia przed analizą rodowodową.
- **WARN** — ostrzeżenie jakościowe; może być uzasadnione historycznie, ale powinno zostać ocenione.
- **Auto-poprawka** — jawna, wybrana przez użytkownika reguła zmiany danych.
- **Manifest** — techniczny zapis konfiguracji, źródeł, sum kontrolnych i wyniku przebiegu.
"""

SECTION_LOADING = """
## Wczytywanie danych

Program przyjmuje lokalne pliki CSV, XLS lub XLSX. Automatycznie rozpoznaje raport i rejestr EBPB
oraz mapuje je do wspólnego schematu. Niestandardowy plik musi już zawierać kolumny schematu
aplikacji — interfejs nie pobiera danych z URL i nie oferuje ręcznego mapowania kolumn.

Rekord techniczny `99999` pozostaje widoczny podczas walidacji. Użytkownik decyduje w Kroku 4,
czy ma zostać pominięty w pliku wynikowym.
"""

SECTION_VALIDATION = """
## Walidacja — co jest sprawdzane

Program kontroluje między innymi:

- puste i powtarzające się ID;
- nieznane kody płci;
- odwołania do nieistniejących rodziców;
- self-parent i tę samą osobę wskazaną jako oboje rodziców;
- cykle w grafie rodowodu;
- zgodność płci z rolą ojca lub matki;
- zakres roku urodzenia i wiek rodzica przy narodzinach potomka;
- zgodność linii rodziców;
- kompletność danych o rodzicach;
- podejrzenie śmierci przed urodzeniem.

Walidacja nie zmienia danych. Problemy można pobrać jako CSV, poprawić ręcznie w Kroku 3 albo
obsłużyć wybranymi regułami automatycznymi w Kroku 4. Po każdej transformacji walidacja jest
wykonywana ponownie, a wynik pokazuje stan przed i po czyszczeniu.
"""

SECTION_REFERENCES = """
## Literatura i odpowiedzialność

Struktura rodowodu jest reprezentowana jako graf skierowany. Kontrole jakości wykorzystują jawne,
deterministyczne reguły zapisane w Pythonie. Wynik czyszczenia powinien zostać oceniony przez osobę
z wiedzą domenową; aplikacja nie odtwarza brakujących informacji biologicznych i nie podejmuje
decyzji hodowlanych.
"""

FULL_HELP_DOCUMENT = "\n\n---\n\n".join(
    (GLOSSARY, SECTION_LOADING, SECTION_VALIDATION, SECTION_REFERENCES)
)
