"""
Tworzenie opisu osobników (kto z kim spokrewniony, po ilu pokoleniach wstecz)
z wczytanej tabeli identyfikatorów, płci i rodziców.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

import pandas as pd


@dataclass(frozen=True)
class Person:
    id: str
    name: Optional[str]
    sex: Optional[str]
    # Przynależność do linii (np. LB/LC/C) z pliku wejściowego.
    line: Optional[str]
    father_id: Optional[str]
    mother_id: Optional[str]
    birth_year: Optional[object]


def build_people_map(df_std: pd.DataFrame) -> Dict[str, Person]:
    people: Dict[str, Person] = {}
    for _, row in df_std.iterrows():
        pid = row["id"]
        people[pid] = Person(
            id=pid,
            name=row.get("name"),
            sex=row.get("sex"),
            line=row.get("line"),
            father_id=row.get("father_id"),
            mother_id=row.get("mother_id"),
            birth_year=row.get("birth_year"),
        )
    return people


def _placeholder_person(person_id: str) -> Person:
    return Person(
        id=person_id,
        name=None,
        sex=None,
        line=None,
        father_id=None,
        mother_id=None,
        birth_year=None,
    )


def get_ancestor_levels_and_edges(
    person_id: str,
    depth: int,
    people: Dict[str, Person],
) -> tuple[Dict[str, int], List[Tuple[str, str]]]:
    """
    Zwraca:
    - `levels`: odległość (ile pokoleń) od osoby startowej do przodków (start = 0)
    - `edges`: krawędzie parent -> child dla wylosowanych przodków (tylko do węzłów w `levels`)
    """
    if depth < 0:
        return {}, []

    # BFS w górę: child -> parents.
    from collections import deque

    levels: Dict[str, int] = {person_id: 0}
    edges: List[Tuple[str, str]] = []

    q = deque([person_id])
    while q:
        current = q.popleft()
        cur_level = levels[current]
        if cur_level >= depth:
            continue

        person = people.get(current) or _placeholder_person(current)

        parents = []
        if person.father_id:
            parents.append(person.father_id)
        if person.mother_id:
            parents.append(person.mother_id)

        for parent_id in parents:
            if not parent_id:
                continue
            edges.append((parent_id, current))
            next_level = cur_level + 1

            prev = levels.get(parent_id)
            if prev is None or next_level < prev:
                levels[parent_id] = next_level
                q.append(parent_id)

    # Dedup krawędzi (mogą pojawić się przy tym samym ojcu/matce w różnych ścieżkach).
    level_nodes: Set[str] = set(levels.keys())
    deduped = []
    seen = set()
    for a, b in edges:
        if a in level_nodes and b in level_nodes:
            if (a, b) not in seen:
                seen.add((a, b))
                deduped.append((a, b))
    return levels, deduped


def get_ancestor_levels_unbounded(
    person_id: str,
    people: Dict[str, Person],
) -> Dict[str, int]:
    """
    Zwraca wszystkie poziomy przodków bez zadanego limitu pokoleń.

    BFS w górę kończy się naturalnie, gdy:
    - nie ma więcej znanych rodziców dla węzłów,
    - albo trafiamy na rodzica będącego referencją bez rekordu w `people`
      (liczymy go jako przodka na danym poziomie, ale nie schodzimy dalej).
    """
    from collections import deque

    levels: Dict[str, int] = {person_id: 0}
    q = deque([person_id])

    while q:
        current = q.popleft()
        cur_level = levels[current]

        p = people.get(current)
        if p is None:
            # referencja bez rekordu -> nie mamy rodziców do dalszego zejścia
            continue

        parents: list[str] = []
        if p.father_id:
            parents.append(p.father_id)
        if p.mother_id:
            parents.append(p.mother_id)

        for parent_id in parents:
            next_level = cur_level + 1
            prev = levels.get(parent_id)
            if prev is None or next_level < prev:
                levels[parent_id] = next_level
                # Jeśli parent nie istnieje jako rekord, to dodaliśmy go do levels,
                # ale i tak nie będzie miał dalszych rodziców (p = None).
                q.append(parent_id)

    return levels


def ensure_people_for_nodes(levels: Dict[str, int], people: Dict[str, Person]) -> Dict[str, Person]:
    """
    Dołączamy placeholdery dla rodziców, którzy są referencjami, ale nie istnieją jako rekordy.
    """
    out = dict(people)
    for pid in levels.keys():
        if pid not in out:
            out[pid] = _placeholder_person(pid)
    return out

