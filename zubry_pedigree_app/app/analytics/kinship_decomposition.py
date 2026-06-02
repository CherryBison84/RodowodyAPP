"""
Rozkład Φ na ścieżki do wspólnych przodków (wzór ścieżkowy); suma = Φ z rekurencji przy tym samym limicie.
Przy silnym inbredzie liczba ścieżek jest ograniczana tak jak przy liczeniu F dla pary.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple

from app.analytics.inbreeding_wright import (
    _resolve_offspring_depth,
    wright_inbreeding_F,
    wright_offspring_inbreeding_F_from_parents,
)
from app.pedigree.ancestor_pedigree import Person


@dataclass(frozen=True)
class PathPairDetail:
    """
    Pojedyncza para ścieżek do wspólnego przodka użyta w rozkładzie Φ.

    ``contribution_raw`` przechowuje surowy wyraz ścieżkowy
    ``(1/2)^(na+nb+1)(1+F_C)``, a ``contribution_to_phi`` jego proporcjonalny
    udział po skalowaniu do wyniku rekurencji Wrighta.
    """

    ancestor_id: str
    n_edges_a: int
    n_edges_b: int
    path_a: Tuple[str, ...]
    path_b: Tuple[str, ...]
    f_ancestor: float
    contribution_raw: float
    contribution_to_phi: float


@dataclass(frozen=True)
class PairKinshipExplanation:
    """
    Pełny opis rozkładu pokrewieństwa pary osobników.

    ``path_scale`` jest ilorazem ``phi_recursive / phi_path_sum_raw`` gdy suma
    surowa jest dodatnia; ``by_ancestor`` zawiera krotki
    ``(ancestor_id, wkład_do_Φ, suma_surowa, liczba_par_ścieżek)`` posortowane
    malejąco po wkładzie do Φ.
    """

    individual_a: str
    individual_b: str
    max_edges: int
    phi_recursive: float
    phi_path_sum_raw: float
    path_scale: float
    n_path_pairs: int
    n_distinct_common_ancestors: int
    path_pairs: Tuple[PathPairDetail, ...]
    by_ancestor: Tuple[Tuple[str, float, float, int], ...]

    @property
    def path_discrepancy(self) -> float:
        """Bezwzględna różnica między rekurencyjną Φ a surową sumą ścieżek."""
        return abs(self.phi_recursive - self.phi_path_sum_raw)


def _enumerate_paths_from(
    start_id: str,
    people: Mapping[str, Person],
    max_edges: int,
    *,
    max_paths: int = 250_000,
) -> List[Tuple[str, int, Tuple[str, ...]]]:
    """
    Wszystkie ścieżki w górę (ojciec/matka) od `start_id` do przodka końcowego węzła ścieżki.
    Zwraca listę (ancestor_id, n_edges, path_tuple) — path_tuple to łańcuch od pierwszego
    rodzica do przodka włącznie.
    """
    out: List[Tuple[str, int, Tuple[str, ...]]] = []

    def walk(pid: str, dist: int, chain: Tuple[str, ...]) -> None:
        if len(out) >= max_paths:
            return
        if dist > max_edges:
            return
        p = people.get(pid)
        if p is None:
            return
        for par in (p.father_id, p.mother_id):
            if par is None:
                continue
            nd = dist + 1
            if nd > max_edges:
                continue
            nchain = chain + (par,)
            out.append((par, nd, nchain))
            if len(out) >= max_paths:
                return
            walk(par, nd, nchain)

    walk(start_id, 0, ())
    return out


def explain_pair_kinship(
    individual_a_id: str,
    individual_b_id: str,
    people: Dict[str, Person],
    *,
    max_generations_back: Optional[int],
    max_paths_per_side: int = 250_000,
) -> PairKinshipExplanation:
    """
    Rozkłada Φ(A,B) na pary ścieżek do wspólnych przodków + sumuje wkład per przodek.
    """
    a = str(individual_a_id).strip()
    b = str(individual_b_id).strip()
    if not a or not b or a not in people or b not in people:
        return PairKinshipExplanation(
            individual_a=a,
            individual_b=b,
            max_edges=0,
            phi_recursive=0.0,
            phi_path_sum_raw=0.0,
            path_scale=1.0,
            n_path_pairs=0,
            n_distinct_common_ancestors=0,
            path_pairs=(),
            by_ancestor=(),
        )

    phi_recursive = float(
        wright_offspring_inbreeding_F_from_parents(
            a, b, people, max_generations_back=max_generations_back
        )
    )

    if a == b:
        # Φ(a,a) = (1+F(a))/2 — nie rozbijamy na pary ścieżek do wspólnych przodków zewnętrznych.
        fa = float(wright_inbreeding_F(person_id=a, people=people, max_generations_back=max_generations_back).F)
        return PairKinshipExplanation(
            individual_a=a,
            individual_b=b,
            max_edges=0,
            phi_recursive=phi_recursive,
            phi_path_sum_raw=phi_recursive,
            path_scale=1.0,
            n_path_pairs=0,
            n_distinct_common_ancestors=0,
            path_pairs=(),
            by_ancestor=((a, phi_recursive, phi_recursive, 0),),
        )

    max_edges = int(
        _resolve_offspring_depth(
            father_id=a,
            mother_id=b,
            people=people,
            max_generations_back=max_generations_back,
        )
    )
    max_edges = max(0, min(max_edges, 80))

    paths_a = _enumerate_paths_from(a, people, max_edges, max_paths=max_paths_per_side)
    paths_b = _enumerate_paths_from(b, people, max_edges, max_paths=max_paths_per_side)
    ga: Dict[str, List[Tuple[int, Tuple[str, ...]]]] = defaultdict(list)
    gb: Dict[str, List[Tuple[int, Tuple[str, ...]]]] = defaultdict(list)
    # Ścieżka „zerowa” do samego siebie — potrzebna m.in. dla relacji rodzic–dziecko (wspólny przodek = rodzic).
    ga[a].append((0, ()))
    gb[b].append((0, ()))
    for end_id, n_e, chain in paths_a:
        ga[end_id].append((n_e, chain))
    for end_id, n_e, chain in paths_b:
        gb[end_id].append((n_e, chain))

    common = set(ga.keys()) & set(gb.keys())
    details: List[PathPairDetail] = []
    agg: Dict[str, float] = {}
    n_pairs_per_ancestor: Dict[str, int] = {}

    for c in common:
        f_c = float(
            wright_inbreeding_F(person_id=c, people=people, max_generations_back=max_generations_back).F
        )
        mult = 1.0 + f_c
        for na, pa in ga[c]:
            for nb, pb in gb[c]:
                pow_v = 0.5 ** (na + nb + 1)
                contrib_raw = float(pow_v * mult)
                details.append(
                    PathPairDetail(
                        ancestor_id=c,
                        n_edges_a=na,
                        n_edges_b=nb,
                        path_a=pa,
                        path_b=pb,
                        f_ancestor=f_c,
                        contribution_raw=contrib_raw,
                        contribution_to_phi=0.0,  # uzupełnione po skalowaniu
                    )
                )
                agg[c] = agg.get(c, 0.0) + contrib_raw
                n_pairs_per_ancestor[c] = n_pairs_per_ancestor.get(c, 0) + 1

    phi_path_sum_raw = float(sum(d.contribution_raw for d in details))
    if phi_path_sum_raw > 1e-18 and abs(phi_recursive) > 1e-18:
        path_scale = float(phi_recursive) / phi_path_sum_raw
    elif phi_path_sum_raw <= 1e-18 and abs(phi_recursive) <= 1e-18:
        path_scale = 1.0
    elif abs(phi_recursive) <= 1e-18:
        path_scale = 0.0
    else:
        path_scale = 1.0

    scaled_details: List[PathPairDetail] = []
    for d in details:
        scaled_details.append(
            PathPairDetail(
                ancestor_id=d.ancestor_id,
                n_edges_a=d.n_edges_a,
                n_edges_b=d.n_edges_b,
                path_a=d.path_a,
                path_b=d.path_b,
                f_ancestor=d.f_ancestor,
                contribution_raw=d.contribution_raw,
                contribution_to_phi=float(d.contribution_raw * path_scale),
            )
        )
    scaled_details.sort(key=lambda x: x.contribution_to_phi, reverse=True)

    agg_phi: Dict[str, float] = {}
    for d in scaled_details:
        agg_phi[d.ancestor_id] = agg_phi.get(d.ancestor_id, 0.0) + d.contribution_to_phi

    by_sorted = sorted(
        ((cid, agg_phi.get(cid, 0.0), agg.get(cid, 0.0), n_pairs_per_ancestor.get(cid, 0)) for cid in agg),
        key=lambda t: t[1],
        reverse=True,
    )
    by_tuples = tuple(by_sorted)

    return PairKinshipExplanation(
        individual_a=a,
        individual_b=b,
        max_edges=max_edges,
        phi_recursive=phi_recursive,
        phi_path_sum_raw=phi_path_sum_raw,
        path_scale=path_scale,
        n_path_pairs=len(scaled_details),
        n_distinct_common_ancestors=len(agg),
        path_pairs=tuple(scaled_details),
        by_ancestor=by_tuples,
    )


def close_kinship_note(phi: float) -> Optional[str]:
    """Krótka interpretacja dla hodowcy na podstawie Φ (coancestry)."""
    if phi is None or phi < 1e-12:
        return None
    if phi >= 0.375 - 1e-6:
        return "Bardzo bliskie pokrewieństwo (Φ ≥ ok. 3/8): typowe dla bliskiego rodzeństwa lub potomstwa po silnym inbredzie — wysokie ryzyko homozygotyczności."
    if phi >= 0.25 - 1e-6:
        return "Bliskie pokrewieństwo (Φ ≥ 1/4): jak pełne rodzeństwo lub rodzic–dziecko w prostym modelu — kojarzenia wymagają szczególnej ostrożności."
    if phi >= 0.125 - 1e-6:
        return "Umiarkowanie bliskie (Φ ≥ 1/8): okolica pierwszego kuzynostwa — warto porównać z polityką hodowlaną stadka."
    if phi >= 0.0625 - 1e-6:
        return "Łagodniejsze, ale widoczne (Φ ≥ 1/16): np. okolica półkuzynostwa — nadal ma znaczenie przy kumulacji w populacji."
    return None
