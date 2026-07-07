"""Etykiety nawigacji HUBA (wspólne dla UI, bez importów cyklicznych)."""

from __future__ import annotations

from typing import Final

NAV_STEP1: Final[str] = "Krok 1 — Wczytanie danych"
NAV_STEP2: Final[str] = "Krok 2 — Walidacja"
NAV_STEP3: Final[str] = "Krok 3 — Czyszczenie automatyczne"
NAV_STEP4: Final[str] = "Krok 4 — Czyszczenie ręczne"
NAV_STEP5: Final[str] = "Krok 5 — Wyniki"

# Ręczna korekta pojedynczych rekordów jest częścią głównego przepływu aplikacji.
MANUAL_CLEAN_ENABLED: Final[bool] = True

NAV_SECTIONS: Final[tuple[str, ...]] = (
    NAV_STEP1,
    NAV_STEP2,
    NAV_STEP3,
    NAV_STEP4,
    NAV_STEP5,
)

_NAV_LEGACY: Final[dict[str, str]] = {
    "Moduł 1 — Błędy w bazie": NAV_STEP2,
    "Krok 2 — Błędy w bazie": NAV_STEP2,
    "Poprawki ręczne": NAV_STEP4,
    "Edycja ręczna": NAV_STEP4,
    "Krok 3 — Czyszczenie ręczne": NAV_STEP4,
    "Konfiguracja": NAV_STEP3,
    "Przetwarzanie wsadowe": NAV_STEP3,
    "Krok 3 — Czyszczenie": NAV_STEP3,
    "Krok 3 — Czyszczenie wsadowe": NAV_STEP3,
    "Krok 4 — Czyszczenie automatyczne": NAV_STEP3,
    "Wyniki": NAV_STEP5,
    "Krok 4 — Wyniki": NAV_STEP5,
}
