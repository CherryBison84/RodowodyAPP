"""Mapa osobników (`Person`) oraz BFS po drzewie potomków (krawędzie rodzic → dziecko)."""

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
        pid = str(row["id"])
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


def build_parent_to_children_map(people: Dict[str, Person]) -> Dict[str, List[str]]:
    """Dla każdego ID rodzica — lista dzieci wskazujących go jako ojca lub matkę (kolejność po ID)."""
    ch: Dict[str, List[str]] = {}
    for pid, p in people.items():
        sid = str(pid)
        for par in (p.father_id, p.mother_id):
            if not par:
                continue
            ch.setdefault(str(par), []).append(sid)
    for par_id in ch:
        ch[par_id] = sorted(set(ch[par_id]), key=str)
    return ch


def get_descendant_levels_and_edges(
    person_id: str,
    depth: int,
    people: Dict[str, Person],
) -> tuple[Dict[str, int], List[Tuple[str, str]]]:
    """
    BFS w dół (rodzic → dziecko): odległość pokoleń od osoby startowej (start = 0).

    ``edges`` to krawędzie **parent → child** (rodzic po lewej).
    """
    if depth < 0:
        return {}, []

    from collections import deque

    pid0 = str(person_id)
    levels: Dict[str, int] = {pid0: 0}
    edges: List[Tuple[str, str]] = []
    child_map = build_parent_to_children_map(people)

    q = deque([pid0])
    while q:
        current = q.popleft()
        cur_level = levels[current]
        if cur_level >= depth:
            continue
        for child_id in child_map.get(current, []):
            edges.append((current, child_id))
            next_level = cur_level + 1
            prev = levels.get(child_id)
            if prev is None or next_level < prev:
                levels[child_id] = next_level
                q.append(child_id)

    level_nodes: Set[str] = set(levels.keys())
    deduped: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()
    for a, b in edges:
        if a in level_nodes and b in level_nodes:
            if (a, b) not in seen:
                seen.add((a, b))
                deduped.append((a, b))
    return levels, deduped


def get_descendant_levels_unbounded(person_id: str, people: Dict[str, Person]) -> Dict[str, int]:
    """Wszyscy potomkowie w dół, bez limitu pokoleń (BFS po mapie rodzic → dzieci)."""
    from collections import deque

    pid0 = str(person_id)
    levels: Dict[str, int] = {pid0: 0}
    q = deque([pid0])
    child_map = build_parent_to_children_map(people)

    while q:
        current = q.popleft()
        cur_level = levels[current]
        for child_id in child_map.get(current, []):
            next_level = cur_level + 1
            prev = levels.get(child_id)
            if prev is None or next_level < prev:
                levels[child_id] = next_level
                q.append(child_id)

    return levels

