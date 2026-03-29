"""Średni kinship po parach — spójność z Φ z inbreeding_wright."""

from __future__ import annotations

from app.analytics.mean_kinship import mean_kinship_pairwise

from tests.test_kinship_phi import _tiny_people


def test_mean_kinship_tiny_pedigree_exact() -> None:
    people = _tiny_people()
    ids = ["S", "D", "GF", "GM"]
    m_phi, m_r, note = mean_kinship_pairwise(
        people,
        ids,
        max_generations_back=8,
        exhaustive_max_n=99,
    )
    # Pary: SD=0.25; S/GF, S/GM, D/GF, D/GM = 0.25 (rodzic–dziecko); GF–GM = 0 (founderzy).
    expect = (5 * 0.25) / 6.0
    assert m_phi is not None and abs(m_phi - expect) < 1e-5
    assert m_r is not None and abs(m_r - 2.0 * expect) < 1e-5
    assert "parach" in note
