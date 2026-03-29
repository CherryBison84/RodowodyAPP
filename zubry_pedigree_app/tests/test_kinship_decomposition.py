"""Dekompozycja Φ: zgodność skalowania z rekurencją; pełne rodzeństwo."""

from __future__ import annotations

from app.analytics.kinship_decomposition import explain_pair_kinship
from app.analytics.inbreeding_wright import wright_kinship_phi_and_relationship_R
from app.pedigree.ancestor_pedigree import Person
from tests.test_kinship_phi import _tiny_people


def test_explain_full_sibs_scaled_matches_phi() -> None:
    people = _tiny_people()
    ex = explain_pair_kinship("S", "D", people, max_generations_back=8)
    phi_r, _ = wright_kinship_phi_and_relationship_R("S", "D", people, max_generations_back=8)
    assert abs(ex.phi_recursive - phi_r) < 1e-9
    s_phi = sum(d.contribution_to_phi for d in ex.path_pairs)
    assert abs(s_phi - ex.phi_recursive) < 1e-6


def test_parent_child_symmetry_phi() -> None:
    p = dict(_tiny_people())
    p["GM2"] = Person(id="GM2", name="GM2", father_id=None, mother_id=None, sex="F", line="LC", birth_year=2000)
    p["C"] = Person(id="C", name="C", father_id="S", mother_id="GM2", sex="M", line="LB", birth_year=2020)
    a, _ = wright_kinship_phi_and_relationship_R("S", "C", p, max_generations_back=12)
    b, _ = wright_kinship_phi_and_relationship_R("C", "S", p, max_generations_back=12)
    assert abs(a - b) < 1e-9
    assert abs(a - 0.25) < 1e-6
