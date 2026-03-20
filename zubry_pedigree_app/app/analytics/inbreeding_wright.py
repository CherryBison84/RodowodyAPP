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
    if max_generations_back is None:
        # Wright F(i)=Phi(sire(i), dam(i)).
        # W naszym rekurencyjnym liczeniu parametry "remaining" odpowiadają łącznej
        # głębokości ścieżek prowadzących do wspólnych przodków (n1+n2),
        # więc do wartości "pokoleń do founderów" dodajemy skalowanie.
        base_depth = _max_generations_to_founders(person_id=person_id, people=people)
        depth = int(2 * base_depth + 2)
    else:
        depth = int(max_generations_back)
        if depth < 0:
            depth = 0

    @lru_cache(maxsize=None)
    def phi(a: str, b: str, remaining: int) -> float:
        """
        Coancestry (Phi) z ograniczeniem liczby pokoleń wstecz.

        Kluczowa poprawka względem wersji początkowej:
        - nie rekurujemy zawsze tylko po rodzicach jednego argumentu,
          bo to zaniża wynik, gdy drugi osobnik jest "founderem",
          ale pierwszy jest jego potomkiem.
        """
        if remaining < 0:
            return 0.0

        if a == b:
            # Phi(a,a) = (1 + F(a)) / 2
            return (1.0 + F(a, remaining)) / 2.0

        if remaining == 0:
            # Różne osoby bez możliwości zejścia w rodowodzie.
            return 0.0

        sire_a, dam_a = _get_parents(people, a)

        # Jeśli `a` nie ma zarejestrowanych rodziców (oba None), rekurujemy po `b`,
        # żeby złapać przypadki, gdy `a` jest descendantem `b` przy founderowym `b`.
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
            # Brak możliwości zejścia do rodziców.
            return 0.0

        sire_x, dam_x = _get_parents(people, x)
        if sire_x is None or dam_x is None:
            return 0.0

        return phi(sire_x, dam_x, remaining - 1)

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

    # Wyznaczamy głębokość rekurencji analogicznie do `wright_inbreeding_F`.
    if max_generations_back is None:
        # base_depth: maks. głębokość do founderów w liniach rodziców.
        unique_ids: set[str] = set()
        for sire, dam in parent_pairs:
            unique_ids.add(sire)
            unique_ids.add(dam)

        base_depth = 0
        for pid in unique_ids:
            base_depth = max(base_depth, _max_generations_to_founders(person_id=pid, people=people))
        # Dla potomka istnieje dodatkowe "pokolenie" (od potomka do wskazanych rodziców),
        # więc korygujemy base_depth o +1, analogicznie do scenariusza "offspring placeholder".
        depth = int(2 * (base_depth + 1) + 2)
    else:
        depth = int(max_generations_back)
        if depth < 0:
            depth = 0

    # W `wright_inbreeding_F` finalnie jest `F(person_id, depth)`,
    # a w `F()` jest wywołanie `phi(..., remaining - 1)`.
    # Dla potomka będącego "rodzicem-sztucznym" oznacza to, że phi ma remaining = depth - 1.
    remaining_for_phi = int(depth - 1)

    @lru_cache(maxsize=None)
    def phi(a: str, b: str, remaining: int) -> float:
        if remaining < 0:
            return 0.0

        if a == b:
            # Phi(a,a) = (1 + F(a)) / 2
            return (1.0 + F(a, remaining)) / 2.0

        if remaining == 0:
            return 0.0

        sire_a, dam_a = _get_parents(people, a)

        if sire_a is None and dam_a is None:
            # founder-stop dla `a`: "zejdź" po `b`, żeby znaleźć wspólnego przodka.
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

    out: list[float] = []
    for sire, dam in parent_pairs:
        if not sire or not dam:
            out.append(0.0)
            continue
        out.append(float(phi(sire, dam, remaining_for_phi)))

    return out

