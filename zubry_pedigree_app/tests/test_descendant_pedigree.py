"""Testy BFS potomków i mapy rodzic → dzieci."""

from __future__ import annotations

import unittest

from app.pedigree.ancestor_pedigree import (
    Person,
    build_parent_to_children_map,
    get_descendant_levels_and_edges,
    get_descendant_levels_unbounded,
)


def _tiny_population() -> dict[str, Person]:
    return {
        "1": Person("1", "A", "F", None, None, None, 2000),
        "2": Person("2", "B", "M", None, None, None, 1998),
        "3": Person("3", "C", "M", None, "1", "2", 2020),
        "4": Person("4", "D", "F", None, "2", "1", 2022),
    }


class DescendantPedigreeTests(unittest.TestCase):
    def test_parent_to_children_map(self) -> None:
        ppl = _tiny_population()
        m = build_parent_to_children_map(ppl)
        self.assertEqual(set(m.get("1", [])), {"3", "4"})
        self.assertEqual(set(m.get("2", [])), {"3", "4"})

    def test_descendant_levels_depth(self) -> None:
        ppl = _tiny_population()
        lv, ed = get_descendant_levels_and_edges("2", depth=2, people=ppl)
        self.assertEqual(lv["2"], 0)
        self.assertEqual(lv["3"], 1)
        self.assertEqual(lv["4"], 1)
        self.assertEqual(set(ed), {("2", "3"), ("2", "4")})

    def test_descendant_unbounded(self) -> None:
        ppl = _tiny_population()
        lv = get_descendant_levels_unbounded("2", people=ppl)
        self.assertEqual(set(lv.keys()), {"2", "3", "4"})


if __name__ == "__main__":
    unittest.main()
