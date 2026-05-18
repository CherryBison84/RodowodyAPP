"""
Spójne, krótkie opisy metryk (F, RIA) — jeden plik źródłowy dla pomocy, UI i raportów tekstowych.
"""

# --- F (Wright) — prosty język, zgodny z docs/metrics_definition.md ---
F_PLAIN = (
    "**F** — współczynnik inbredu Wrighta (od 0 w górę): mówi, **jak bardzo w rodowodzie powtarzają się ci sami przodkowie** "
    "po stronie ojca i matki. Im wyższe F, tym większe ryzyko, że u osobnika spotykają się kopie genów od tych samych osób "
    "(to jest **zinbredowanie** w sensie hodowlanym). W programie F liczone jest z zapisu rodziców w bazie, z limitem pokoleń albo bez limitu."
)

# --- RIA — zawsze ten sam sens: udział zinbredowanych = F > 0 przy tym samym limicie F ---
RIA_PLAIN = (
    "**RIA (%)** — **udział zinbredowanych**: jaki **procent** osobników ma **F > 0** "
    "(przy **tym samym** limicie pokoleń przy liczeniu **F** co pozostałe wskaźniki w danej sekcji / na wykresie)."
)

RIA_PLAIN_SHORT = "udział zinbredowanych: % z F>0 (ten sam limit F co widok)"

# Krótsza podpowiedź pod „?” (bez markdown)
RIA_HELP_TOOLTIP = (
    "RIA: udział zinbredowanych w procentach — osobnicy z F>0; ten sam limit pokoleń przy liczeniu F co w tej sekcji."
)
