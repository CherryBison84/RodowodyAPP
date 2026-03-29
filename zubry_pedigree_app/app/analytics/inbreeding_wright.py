"""
Liczenie współczynnika pokrewieństwa F (Wright) dla pojedynczych osobników
na podstawie drzewa rodowego.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional

from app.pedigree.ancestor_pedigree import Person


@dataclass(frozen=True)
class InbreedingResult:
    person_id: str
    F: float
    used_generations: int
    father_id: Optional[str]
    mother_id: Optional[str]
    father_name: Optional[str]
    mother_name: Optional[str]


def _get_parents(people: Dict[str, Person], person_id: str) -> tuple[Optional[str], Optional[str]]:
    p = people.get(person_id)
    if p is None:
        return None, None
    return p.father_id, p.mother_id


def _sanitize_depth(max_generations_back: int | None) -> int | None:
    if max_generations_back is None:
        return None
    depth = int(max_generations_back)
    return max(0, depth)


def _resolve_person_depth(*, person_id: str, people: Dict[str, Person], max_generations_back: int | None) -> int:
    depth_or_none = _sanitize_depth(max_generations_back)
    if depth_or_none is not None:
        return depth_or_none
    base_depth = _max_generations_to_founders(person_id=person_id, people=people)
    # Skala "remaining" odwzorowuje łączną długość ścieżek do wspólnych przodków.
    return int(2 * base_depth + 2)


def _resolve_offspring_depth(
    *,
    father_id: str,
    mother_id: str,
    people: Dict[str, Person],
    max_generations_back: int | None,
) -> int:
    depth_or_none = _sanitize_depth(max_generations_back)
    if depth_or_none is not None:
        return depth_or_none
    base_depth_f = _max_generations_to_founders(person_id=father_id, people=people)
    base_depth_m = _max_generations_to_founders(person_id=mother_id, people=people)
    return int(2 * max(int(base_depth_f), int(base_depth_m)) + 2)


def _resolve_batch_offspring_depth(
    *,
    parent_pairs: list[tuple[str, str]],
    people: Dict[str, Person],
    max_generations_back: int | None,
) -> int:
    depth_or_none = _sanitize_depth(max_generations_back)
    if depth_or_none is not None:
        return depth_or_none

    unique_ids: set[str] = set()
    for sire, dam in parent_pairs:
        unique_ids.add(sire)
        unique_ids.add(dam)

    base_depth = 0
    for pid in unique_ids:
        base_depth = max(base_depth, _max_generations_to_founders(person_id=pid, people=people))
    # Potomek dokłada jedno przejście od "proband" do rodziców.
    return int(2 * (base_depth + 1) + 2)


def _build_phi_f(people: Dict[str, Person]):
    @lru_cache(maxsize=None)
    def phi(a: str, b: str, remaining: int) -> float:
        if remaining < 0:
            return 0.0

        if a == b:
            return (1.0 + F(a, remaining)) / 2.0

        if remaining == 0:
            return 0.0

        sire_a, dam_a = _get_parents(people, a)
        if sire_a is None and dam_a is None:
            sire_b, dam_b = _get_parents(people, b)
            t1 = phi(a, sire_b, remaining - 1) if sire_b is not None else 0.0
            t2 = phi(a, dam_b, remaining - 1) if dam_b is not None else 0.0
            return 0.5 * (t1 + t2)

        t1 = phi(sire_a, b, remaining - 1) if sire_a is not None else 0.0
        t2 = phi(dam_a, b, remaining - 1) if dam_a is not None else 0.0
        return 0.5 * (t1 + t2)

    @lru_cache(maxsize=None)
    def F(x: str, remaining: int) -> float:
        if remaining < 1:
            return 0.0
        sire_x, dam_x = _get_parents(people, x)
        if sire_x is None or dam_x is None:
            return 0.0
        return phi(sire_x, dam_x, remaining - 1)

    return phi, F


def wright_inbreeding_F(
    person_id: str,
    people: Dict[str, Person],
    *,
    max_generations_back: int | None,
) -> InbreedingResult:
    """
    Współczynnik inbredu Wrighta:
    F(i) = Phi(sire(i), dam(i))

    Phi(a,b) (coancestry) liczony rekurencyjnie:
    - jeśli a == b: Phi(a,a) = (1 + F(a)) / 2
    - jeśli a != b:
      Phi(a,b) = 0, gdy brak rodziców u b
      w przeciwnym razie: Phi(a,b) = 0.5 * (Phi(a, sire(b)) + Phi(a, dam(b)))

    Traktowanie brakujących rodziców:
    - brak ojca/matki = osobnik jak founder => wkład IBD do Phi z innymi wynosi 0
    """
    depth = _resolve_person_depth(
        person_id=person_id,
        people=people,
        max_generations_back=max_generations_back,
    )
    _phi, F = _build_phi_f(people)

    father_id, mother_id = _get_parents(people, person_id)
    father_name: Optional[str] = None
    mother_name: Optional[str] = None
    if father_id is not None and father_id in people:
        father_name = people[father_id].name
    if mother_id is not None and mother_id in people:
        mother_name = people[mother_id].name

    F_val = F(person_id, depth)
    # Stabilizacja numeryczna (rekurencje z 0.5)
    if abs(F_val) < 1e-15:
        F_val = 0.0
    return InbreedingResult(
        person_id=person_id,
        F=float(F_val),
        used_generations=int(depth),
        father_id=father_id,
        mother_id=mother_id,
        father_name=father_name,
        mother_name=mother_name,
    )


def wright_offspring_inbreeding_F_from_parents(
    father_id: str,
    mother_id: str,
    people: Dict[str, Person],
    *,
    max_generations_back: int | None,
) -> float:
    """
    Liczy inbred potomka o rodzicach (father_id, mother_id) jako:
        F_offspring = Phi(father_id, mother_id)

    Implementacja jest spójna z wewnętrzną logiką rekurencji używaną w `wright_inbreeding_F`.
    """
    if not father_id or not mother_id:
        return 0.0
    if father_id == mother_id:
        # W przypadku self-cross: F_off = Phi(x, x) = (1 + F(x)) / 2.
        # Obliczamy F(x) jak w standardowej procedurze (w zależności od limitu).
        return (1.0 + wright_inbreeding_F(person_id=father_id, people=people, max_generations_back=max_generations_back).F) / 2.0

    depth = _resolve_offspring_depth(
        father_id=father_id,
        mother_id=mother_id,
        people=people,
        max_generations_back=max_generations_back,
    )
    phi, _F = _build_phi_f(people)
    F_off = phi(father_id, mother_id, depth)
    if abs(F_off) < 1e-15:
        return 0.0
    return float(F_off)


def wright_kinship_phi_and_relationship_R(
    individual_a_id: str,
    individual_b_id: str,
    people: Dict[str, Person],
    *,
    max_generations_back: int | None,
) -> tuple[float, float]:
    """
    Współczynnik współzgodności Φ (coancestry, Malecot/Wright) i współczynnik relacji R = 2Φ
    między dwoma osobnikami — ta sama rekurencja i głębokość co przy F hipotetycznego potomka
    z ojcem `individual_a_id` i matką `individual_b_id`.

    Dla kojarzenia: **F potomka = Φ(ojciec, matka)** przy tej samej głębokości liczenia.
    **R** to klasyczny współczynnik pokrewieństwa Wrighta (autosomy), np. R=0,5 dla rodzic–dziecko
    przy braku dodatkowego pokrewieństwa.
    """
    phi = wright_offspring_inbreeding_F_from_parents(
        individual_a_id,
        individual_b_id,
        people,
        max_generations_back=max_generations_back,
    )
    return float(phi), float(2.0 * phi)


def _max_generations_to_founders(*, person_id: str, people: Dict[str, Person], max_visits: int = 500_000) -> int:
    """
    Zwraca maksymalną liczbę pokoleń wstecz, potrzebną do zejścia aż do osobników,
    dla których brak jest przynajmniej jednego z rodziców (traktujemy je jak founderów/nieznanych rodziców).
    """
    from collections import deque

    if person_id not in people:
        return 0

    q = deque([(person_id, 0)])
    visited: set[str] = set()
    max_depth = 0
    visits = 0

    while q:
        nid, d = q.popleft()
        if nid in visited:
            continue
        visited.add(nid)
        visits += 1
        if visits > max_visits:
            # Ochrona przed błędnymi cyklami w rodowodzie.
            break

        p = people.get(nid)
        if p is None:
            continue

        sire, dam = p.father_id, p.mother_id

        # Founder (w sensie metodyki): osobnik, którego rodzice są nieznani (co najmniej jeden rodzic).
        if sire is None or dam is None:
            max_depth = max(max_depth, d)
            continue

        # Schodzimy do znanych rodziców.
        if sire is not None:
            q.append((sire, d + 1))
        if dam is not None:
            q.append((dam, d + 1))

    return int(max_depth)


def batch_offspring_inbreeding_F_from_parent_pairs(
    parent_pairs: list[tuple[str, str]],
    people: Dict[str, Person],
    *,
    max_generations_back: int | None,
) -> list[float]:
    """
    Liczy `F_offspring = Phi(sire, dam)` dla wielu par rodziców (sire, dam).

    Funkcja buduje wspólny cache dla rekurencji `phi()`/`F()` w obrębie jednego wywołania,
    dzięki czemu ranking wielu par jest dużo szybszy niż wielokrotne wołanie
    `wright_inbreeding_F()` w osobnych wywołaniach.
    """
    if not parent_pairs:
        return []

    depth = _resolve_batch_offspring_depth(
        parent_pairs=parent_pairs,
        people=people,
        max_generations_back=max_generations_back,
    )

    # W `wright_inbreeding_F` finalnie jest `F(person_id, depth)`,
    # a w `F()` jest wywołanie `phi(..., remaining - 1)`.
    # Dla potomka będącego "rodzicem-sztucznym" oznacza to, że phi ma remaining = depth - 1.
    remaining_for_phi = int(depth - 1)

    phi, _F = _build_phi_f(people)

    out: list[float] = []
    for sire, dam in parent_pairs:
        if not sire or not dam:
            out.append(0.0)
            continue
        out.append(float(phi(sire, dam, remaining_for_phi)))

    return out

