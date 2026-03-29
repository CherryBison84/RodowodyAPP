"""Spójność Φ / R z F potomka z tej samej implementacji Wrighta."""

from __future__ import annotations

from app.analytics.inbreeding_wright import (
    wright_kinship_phi_and_relationship_R,
    wright_offspring_inbreeding_F_from_parents,
)
from app.pedigree.ancestor_pedigree import Person


def _tiny_people() -> dict[str, Person]:
    # Proste drzewo: dziadkowie -> rodzice -> dziecko; brak inbredu w rodzicach.
    return {
        "GF": Person(id="GF", name="GF", father_id=None, mother_id=None, sex="M", line="LB", birth_year=2000),
        "GM": Person(id="GM", name="GM", father_id=None, mother_id=None, sex="F", line="LC", birth_year=2000),
        "S": Person(id="S", name="S", father_id="GF", mother_id="GM", sex="M", line="LB", birth_year=2010),
        "D": Person(id="D", name="D", father_id="GF", mother_id="GM", sex="F", line="LC", birth_year=2012),
    }


def test_phi_matches_offspring_f_and_r_is_twice_phi() -> None:
    people = _tiny_people()
    max_back = 8
    f_off = wright_offspring_inbreeding_F_from_parents("S", "D", people, max_generations_back=max_back)
    phi, r = wright_kinship_phi_and_relationship_R("S", "D", people, max_generations_back=max_back)
    assert abs(phi - f_off) < 1e-9
    assert abs(r - 2.0 * phi) < 1e-9
    # Rodzeństwo pełne: F potomka rodziców-rodzeństwa = 0.25
    assert abs(phi - 0.25) < 1e-6
