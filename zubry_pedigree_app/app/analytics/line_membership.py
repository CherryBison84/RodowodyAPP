"""Śledzenie „linii sire/dam”: założyciel gałęzi i liczba kroków w górę rodowodu."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set, Tuple

from app.pedigree.ancestor_pedigree import Person


@dataclass(frozen=True)
class LineMembership:
    person_id: str
    person_name: Optional[str]

    sire_founder_id: Optional[str]
    sire_founder_name: Optional[str]
    sire_steps: int

    dam_founder_id: Optional[str]
    dam_founder_name: Optional[str]
    dam_steps: int


@dataclass(frozen=True)
class LineMembershipLite:
    """Uproszczony wynik linii do tabel w GUI (bez zbędnych pól)."""

    person_id: str
    person_name: Optional[str]

    sire_founder_id: Optional[str]
    sire_founder_name: Optional[str]
    sire_steps: int

    dam_founder_id: Optional[str]
    dam_founder_name: Optional[str]
    dam_steps: int


def compute_all_line_memberships(
    people: Dict[str, Person],
    *,
    person_ids: Optional[Iterable[str]] = None,
) -> Dict[str, LineMembershipLite]:
    """Liczy przynależność do linii ojca i matki dla wielu ID (memoizacja, szybkie dla rejestru)."""

    targets = list(person_ids) if person_ids is not None else list(people.keys())

    memo_sire: Dict[str, Tuple[Optional[str], Optional[str], int]] = {}
    memo_dam: Dict[str, Tuple[Optional[str], Optional[str], int]] = {}

    visiting: Set[str] = set()

    def trace_rec(current: str, *, parent_field: str) -> Tuple[Optional[str], Optional[str], int]:
        memo = memo_sire if parent_field == "father_id" else memo_dam
        if current in memo:
            return memo[current]

        if current not in people:
            # Spójnie z get_line_membership(): start spoza people => brak linii.
            memo[current] = (None, None, 0)
            return memo[current]

        if current in visiting:
            # cykl - bezpieczne zakończenie.
            p = people.get(current)
            memo[current] = (current, p.name if p else None, 0)
            return memo[current]

        visiting.add(current)
        p = people.get(current)
        parent_id = getattr(p, parent_field) if p else None

        if parent_id is None:
            res = (current, p.name if p else None, 0)
            memo[current] = res
            visiting.remove(current)
            return res

        if parent_id not in people:
            # parent_id to founder, ale brak rekordu.
            res = (parent_id, None, 1)
            memo[current] = res
            visiting.remove(current)
            return res

        founder_id, founder_name, steps_parent = trace_rec(parent_id, parent_field=parent_field)
        res = (founder_id, founder_name, steps_parent + 1)
        memo[current] = res
        visiting.remove(current)
        return res

    out: Dict[str, LineMembershipLite] = {}
    for pid in targets:
        p = people.get(pid)
        person_name = p.name if p else None
        sire_founder_id, sire_founder_name, sire_steps = trace_rec(pid, parent_field="father_id")
        dam_founder_id, dam_founder_name, dam_steps = trace_rec(pid, parent_field="mother_id")
        out[pid] = LineMembershipLite(
            person_id=pid,
            person_name=person_name,
            sire_founder_id=sire_founder_id,
            sire_founder_name=sire_founder_name,
            sire_steps=sire_steps,
            dam_founder_id=dam_founder_id,
            dam_founder_name=dam_founder_name,
            dam_steps=dam_steps,
        )

    return out


def _trace_line(
    start_id: str,
    people: Dict[str, Person],
    *,
    parent_field: str,
) -> tuple[Optional[str], Optional[str], int]:
    """Idzie w górę po `father_id` lub `mother_id` do brakującego rodzica = „założyciel” tej linii."""
    if start_id not in people:
        return None, None, 0

    current = start_id
    visited: Set[str] = set()
    steps = 0

    while True:
        if current in visited:
            # Ochrona przed cyklami w danych.
            return current, people.get(current).name if current in people else None, steps
        visited.add(current)

        p = people.get(current)
        if p is None:
            return current, None, steps

        parent_id = getattr(p, parent_field)
        if parent_id is None:
            # founder stop: brak rodzica po tej linii
            return current, p.name, steps

        steps += 1
        if parent_id not in people:
            # Nie mamy rekordu rodzica, ale to on jest "założycielem" dla tej linii.
            return parent_id, None, steps

        current = parent_id


def get_line_membership(person_id: str, people: Dict[str, Person]) -> LineMembership:
    p = people.get(person_id)
    person_name = p.name if p else None

    sire_founder_id, sire_founder_name, sire_steps = _trace_line(
        person_id, people, parent_field="father_id"
    )
    dam_founder_id, dam_founder_name, dam_steps = _trace_line(
        person_id, people, parent_field="mother_id"
    )

    return LineMembership(
        person_id=person_id,
        person_name=person_name,
        sire_founder_id=sire_founder_id,
        sire_founder_name=sire_founder_name,
        sire_steps=sire_steps,
        dam_founder_id=dam_founder_id,
        dam_founder_name=dam_founder_name,
        dam_steps=dam_steps,
    )

