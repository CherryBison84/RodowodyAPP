from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import networkx as nx


def _normalize_sex(x: object) -> Optional[str]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    s = str(x).strip().lower()
    if s in {"m", "male", "samiec", "samiec.", "s", "1", "true"}:
        return "M"
    if s in {"f", "female", "samica", "samica.", "k", "0", "false"}:
        return "F"
    # Accept Polish full words / common variants
    if "sam" in s:
        if "samiec" in s:
            return "M"
        if "samica" in s:
            return "F"
    return None


def _to_datetime_or_nat(series: pd.Series) -> pd.Series:
    # Coerce invalid values to NaT (unknown birth dates).
    return pd.to_datetime(series, errors="coerce", utc=False)


@dataclass(frozen=True)
class PopulationGroups:
    tp: Set[str]
    rp: Set[str]
    anc: Set[str]


class BisonPedigree:
    """
    Pedigree engine for bison lineage analysis.

    - Builds a directed acyclic graph (DAG) using a parent -> child orientation.
    - Supports filtering populations: TP, RP, ANC.
    - Provides common demographic/genetic metrics.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        id_col: str = "ID",
        father_col: str = "Ojciec",
        mother_col: str = "Matka",
        sex_col: str = "Plec",
        birthdate_col: str = "Data_urodzenia",
    ) -> None:
        self.id_col = id_col
        self.father_col = father_col
        self.mother_col = mother_col
        self.sex_col = sex_col
        self.birthdate_col = birthdate_col

        self.data_ids: Set[str] = set()
        self.external_ids: Set[str] = set()

        self.father_of: Dict[str, Optional[str]] = {}
        self.mother_of: Dict[str, Optional[str]] = {}
        self.sex_of: Dict[str, Optional[str]] = {}
        self.birth_of: Dict[str, pd.Timestamp] = {}

        self.G: nx.DiGraph = nx.DiGraph()
        self.founders: Set[str] = set()

        self._topo_order: Optional[List[str]] = None
        self._reverse_topo_order: Optional[List[str]] = None

        self._ancestor_dist_cache: Dict[str, Dict[str, int]] = {}

        self._build(df)

    def _build(self, df: pd.DataFrame) -> None:
        # Polish column names sometimes contain diacritics.
        # We keep defaults ASCII, but accept common Polish variants.
        sex_col_polish = "P\u0142e\u0107"  # Polish column name with diacritics: Plec

        required = {self.id_col, self.father_col, self.mother_col, self.sex_col, self.birthdate_col}
        missing = required - set(df.columns)
        if missing:
            # If only sex column is missing, try Polish diacritic variant.
            if missing == {self.sex_col} and self.sex_col in {"Plec"} and sex_col_polish in df.columns:
                self.sex_col = sex_col_polish
            else:
                raise ValueError(f"Missing required columns: {sorted(missing)}")

        # Normalize core columns.
        dfn = df.copy()
        dfn[self.id_col] = dfn[self.id_col].astype(str).str.strip()
        dfn[self.father_col] = dfn[self.father_col].astype("object")
        dfn[self.mother_col] = dfn[self.mother_col].astype("object")

        # Use NA-like handling for empty strings.
        def _clean_parent_col(s: pd.Series) -> pd.Series:
            out = s.copy()
            out = out.where(~out.isna(), other=np.nan)
            out = out.astype("object")
            # Turn empty strings into NaN.
            out = out.apply(lambda v: np.nan if v is None else (str(v).strip() if str(v).strip() else np.nan))
            # Ensure "nan" string does not leak.
            out = out.apply(lambda v: np.nan if isinstance(v, str) and v.lower() == "nan" else v)
            return out

        dfn[self.father_col] = _clean_parent_col(dfn[self.father_col])
        dfn[self.mother_col] = _clean_parent_col(dfn[self.mother_col])
        dfn[self.sex_col] = dfn[self.sex_col].apply(_normalize_sex)
        dfn[self.birthdate_col] = _to_datetime_or_nat(dfn[self.birthdate_col])

        self.data_ids = set(dfn[self.id_col].tolist())
        # Map parents (may reference IDs not present in df).
        fathers = dfn.set_index(self.id_col)[self.father_col].to_dict()
        mothers = dfn.set_index(self.id_col)[self.mother_col].to_dict()
        sex = dfn.set_index(self.id_col)[self.sex_col].to_dict()
        birth = dfn.set_index(self.id_col)[self.birthdate_col].to_dict()

        # Add external nodes for parent IDs that appear in the pedigree columns but are not in the table.
        external: Set[str] = set()
        for child_id in self.data_ids:
            f = fathers.get(child_id)
            m = mothers.get(child_id)
            if isinstance(f, str) and f.strip() and f not in self.data_ids:
                external.add(f)
            if isinstance(m, str) and m.strip() and m not in self.data_ids:
                external.add(m)

        self.external_ids = external

        # Build parent pointers for all nodes.
        all_ids = self.data_ids | self.external_ids
        for nid in all_ids:
            self.father_of[nid] = None
            self.mother_of[nid] = None
            self.sex_of[nid] = None
            self.birth_of[nid] = pd.NaT

        for nid in self.data_ids:
            f = fathers.get(nid)
            m = mothers.get(nid)
            self.father_of[nid] = None if (isinstance(f, float) and np.isnan(f)) else (str(f).strip() if f is not None else None)
            self.mother_of[nid] = None if (isinstance(m, float) and np.isnan(m)) else (str(m).strip() if m is not None else None)
            self.sex_of[nid] = sex.get(nid)
            self.birth_of[nid] = birth.get(nid, pd.NaT)

        # External nodes have no recorded parents (treated as founders if no other links exist).
        # If external IDs still appear as parents, their own parents are not known unless present as rows.

        # Create graph: parent -> child.
        G = nx.DiGraph()
        G.add_nodes_from(all_ids)
        for child_id in self.data_ids:
            for parent_role, parent_id in [("father", self.father_of[child_id]), ("mother", self.mother_of[child_id])]:
                if parent_id is None:
                    continue
                if parent_id not in all_ids:
                    continue
                # Edge parent -> child.
                G.add_edge(parent_id, child_id)
        self.G = G

        if not nx.is_directed_acyclic_graph(self.G):
            # We still build the object; validations can report cycles.
            self.founders = set()
        else:
            self.founders = {n for n in self.G.nodes if self._is_founder(n)}

        self._topo_order = None
        self._reverse_topo_order = None
        self._ancestor_dist_cache.clear()

    def _is_founder(self, node_id: str) -> bool:
        # Founder is an individual with no parents present in the table.
        # In our graph, that means indegree == 0 (no incoming edges).
        return self.G.in_degree(node_id) == 0

    @property
    def topo_order(self) -> List[str]:
        if self._topo_order is None:
            self._topo_order = list(nx.topological_sort(self.G))
        return self._topo_order

    @property
    def reverse_topo_order(self) -> List[str]:
        if self._reverse_topo_order is None:
            self._reverse_topo_order = list(reversed(self.topo_order))
        return self._reverse_topo_order

    def validate(self) -> Dict[str, object]:
        """
        Returns structured validation output.
        """
        out: Dict[str, object] = {}
        out["is_dag"] = nx.is_directed_acyclic_graph(self.G)

        cycles_sample: List[List[str]] = []
        if not out["is_dag"]:
            try:
                cyc = nx.find_cycle(self.G, orientation="original")
                cycles_sample = [[e[0] for e in cyc[:5]]]
            except Exception:
                cycles_sample = []
        out["cycles_sample"] = cycles_sample

        # Parent birth date must be <= child birth date (if both are known).
        issues: List[Tuple[str, str, str]] = []
        tol = pd.Timedelta(days=1)
        for child_id in self.data_ids:
            cb = self.birth_of.get(child_id, pd.NaT)
            if cb is pd.NaT or pd.isna(cb):
                continue
            father_id = self.father_of.get(child_id)
            mother_id = self.mother_of.get(child_id)
            for parent_id in [father_id, mother_id]:
                if parent_id is None:
                    continue
                pb = self.birth_of.get(parent_id, pd.NaT)
                if pb is pd.NaT or pd.isna(pb):
                    continue
                if pb > cb + tol:
                    issues.append((child_id, parent_id, "parent_younger_expected"))

        out["parent_age_violations_count"] = len(issues)
        out["parent_age_violations_sample"] = issues[:20]

        # References to parent IDs not present in the table.
        out["external_parent_references_count"] = len(self.external_ids)

        return out

    def filter_populations(
        self,
        rp_birth_year_start: Optional[int] = None,
        rp_birth_year_end: Optional[int] = None,
    ) -> PopulationGroups:
        """
        Partition:
        - TP: all input individuals.
        - RP: active individuals based on birth year interval.
        - ANC: all ancestors of RP individuals (intersected with dataset IDs).
        """
        tp = set(self.data_ids)
        if rp_birth_year_start is None and rp_birth_year_end is None:
            rp = set(tp)
        else:
            years = {}
            for nid in tp:
                b = self.birth_of.get(nid, pd.NaT)
                if b is pd.NaT or pd.isna(b):
                    years[nid] = None
                else:
                    years[nid] = int(b.year)

            rp = set()
            for nid in tp:
                y = years.get(nid)
                if y is None:
                    continue
                if rp_birth_year_start is not None and y < rp_birth_year_start:
                    continue
                if rp_birth_year_end is not None and y > rp_birth_year_end:
                    continue
                rp.add(nid)

        anc = set()
        if rp:
            anc = nx.ancestors(self.G, rp) & self.data_ids
        return PopulationGroups(tp=tp, rp=rp, anc=anc)

    def _get_ancestor_distances(
        self,
        node_id: str,
        max_depth: Optional[int] = None,
        allowed_nodes: Optional[Set[str]] = None,
        include_self: bool = False,
    ) -> Dict[str, int]:
        """
        Compute shortest generational distances from `node_id` to its ancestors
        using reverse edges (child -> parent).
        """
        if allowed_nodes is None:
            allowed_nodes = set(self.G.nodes)

        # Cache only for full-graph allowed set (common case).
        if allowed_nodes == set(self.G.nodes) and max_depth is None and not include_self:
            cached = self._ancestor_dist_cache.get(node_id)
            if cached is not None:
                return cached

        rev = self.G.reverse(copy=False)
        dist: Dict[str, int] = {}
        from collections import deque

        if include_self:
            dist[node_id] = 0

        q = deque([(node_id, 0)])
        seen = {node_id}
        while q:
            cur, d = q.popleft()
            # Ancestors exclude the node itself (d>0).
            if d > 0 and cur in allowed_nodes:
                dist[cur] = d
            if max_depth is not None and d >= max_depth:
                continue
            for parent in rev.successors(cur):
                if parent in seen:
                    continue
                if parent not in allowed_nodes:
                    continue
                seen.add(parent)
                q.append((parent, d + 1))

        if allowed_nodes == set(self.G.nodes) and max_depth is None and not include_self:
            self._ancestor_dist_cache[node_id] = dist
        return dist

    def tracked_generations(self, pop_ids: Set[str], max_depth: Optional[int] = None) -> pd.Series:
        """
        For each individual in `pop_ids`, compute max number of generations traced back to founders.
        """
        if not self.founders:
            # In cycle-containing graphs founders are not well-defined in DAG sense.
            return pd.Series({nid: np.nan for nid in pop_ids}, name="tracked_generations")

        vals = {}
        founders = self.founders
        for nid in pop_ids:
            dists = self._get_ancestor_distances(nid, max_depth=max_depth)
            founder_depths = [d for anc, d in dists.items() if anc in founders]
            vals[nid] = max(founder_depths) if founder_depths else 0
        return pd.Series(vals, name="tracked_generations")

    def _closure_ancestors(self, nodes: Set[str]) -> Set[str]:
        if not nodes:
            return set()
        return nx.ancestors(self.G, nodes) | set(nodes)

    def compute_inbreeding_wright(
        self,
        pop_ids: Set[str],
        max_depth: Optional[int] = 20,
    ) -> pd.Series:
        """
        Compute Wright's inbreeding coefficient F for individuals in `pop_ids`.

        Uses the common-ancestor summation:
            F_i = sum_a (1/2)^(m(a)+n(a)+1) * (1 + F_a)
        where m/n are generational distances from sire/dam to ancestor a.
        """
        if not pop_ids:
            return pd.Series(dtype=float, name="F")
        if not nx.is_directed_acyclic_graph(self.G):
            raise ValueError("Inbreeding requires a directed acyclic pedigree graph (DAG).")

        # Limit the considered pedigree depth for performance:
        # closure contains all nodes reachable backwards from RP individuals
        # within `max_depth` generations (using reverse edges: child -> parent).
        if max_depth is None:
            closure = self._closure_ancestors(pop_ids)
        else:
            from collections import deque

            rev = self.G.reverse(copy=False)
            seen: Set[str] = set(pop_ids)
            q = deque([(nid, 0) for nid in pop_ids])
            while q:
                cur, d = q.popleft()
                if d >= max_depth:
                    continue
                for parent in rev.successors(cur):
                    if parent in seen:
                        continue
                    seen.add(parent)
                    q.append((parent, d + 1))
            closure = seen

        subG = self.G.subgraph(closure)
        topo = list(nx.topological_sort(subG))
        F: Dict[str, float] = {n: 0.0 for n in topo}

        # Gene-dropping / path-sum weights:
        # For a given start node u (one of the parents), compute:
        #   w_u[a] = sum_{paths u <- ... <- a} (1/2)^{dist(a,u)}
        # where dist is the number of generations between a and u along a path.
        # These weights aggregate contributions over all paths (not just shortest).
        visit_cache: Dict[str, Dict[str, float]] = {}

        def _visit_weights(start: str) -> Dict[str, float]:
            cached = visit_cache.get(start)
            if cached is not None:
                return cached

            # Reachable ancestors of `start` inside `closure`, including `start` itself.
            # _get_ancestor_distances uses BFS on reverse edges and only needs reachability,
            # not path enumeration; reachability is enough to define the induced subgraph.
            dist_map = self._get_ancestor_distances(
                start,
                max_depth=None,
                allowed_nodes=closure,
                include_self=True,
            )
            nodes = set(dist_map.keys())
            if not nodes:
                visit_cache[start] = {}
                return visit_cache[start]

            H = self.G.subgraph(nodes)
            topo_H = list(nx.topological_sort(H))
            rev_topo_H = list(reversed(topo_H))

            w: Dict[str, float] = {n: 0.0 for n in nodes}
            w[start] = 1.0

            # Propagate weights backwards along parent links.
            # Since we process in reverse topological order, w[v] already includes
            # contributions from all descendants within H when we propagate.
            for v in rev_topo_H:
                mass = w.get(v, 0.0)
                if mass == 0.0:
                    continue
                for parent in H.predecessors(v):
                    w[parent] = w.get(parent, 0.0) + 0.5 * mass

            visit_cache[start] = w
            return w

        for node in topo:
            sire = self.father_of.get(node)
            dam = self.mother_of.get(node)
            if sire is None or dam is None:
                continue
            if sire not in closure or dam not in closure:
                continue

            w_s = _visit_weights(sire)
            w_d = _visit_weights(dam)

            if not w_s or not w_d:
                continue

            # Sum only over common ancestors inside closure.
            if len(w_s) <= len(w_d):
                small, large = w_s, w_d
            else:
                small, large = w_d, w_s

            total = 0.0
            for a, ws_a in small.items():
                wd_a = large.get(a)
                if wd_a is None or wd_a == 0.0:
                    continue
                total += (1.0 + F.get(a, 0.0)) * ws_a * wd_a

            # Inbreeding is the coancestry between the parents.
            F[node] = 0.5 * total

        return pd.Series({nid: F.get(nid, 0.0) for nid in pop_ids}, name="F")

    def traced_generations_stats(self, pop_ids: Set[str], max_depth: Optional[int] = None) -> Dict[str, float]:
        """
        Traced generations:
        - Gmax: maximum traced generations back to founders among `pop_ids`.
        - Ge: equivalent number of generations derived from effective number of founders:
               Ge = log2(fe)
        """
        tg = self.tracked_generations(pop_ids, max_depth=max_depth)
        gmax = float(np.nanmax(tg.to_numpy(dtype=float))) if len(tg) else float("nan")
        fe = self.effective_number_of_founders(pop_ids)
        ge = float(np.log2(fe)) if np.isfinite(fe) and fe > 0 else float("nan")
        return {"Gmax": gmax, "Ge_equivalent": ge, "fe": fe}

    def line_length_distribution(
        self,
        pop_ids: Set[str],
        parent_role: str,
        max_steps: int = 50,
    ) -> pd.Series:
        """
        Length (in generations) of a single genealogical line back to a founder:
        - parent_role: 'father' or 'mother'
        - length counts edges traversed (founder has length 0).
        """
        if parent_role not in {"father", "mother"}:
            raise ValueError("parent_role must be 'father' or 'mother'")

        if not self.founders:
            # For cycle graphs founders are not reliably defined.
            return pd.Series({nid: np.nan for nid in pop_ids}, name=f"{parent_role}_line_length")

        get_parent = self.father_of.get if parent_role == "father" else self.mother_of.get
        founders = self.founders
        vals: Dict[str, int] = {}

        for nid in pop_ids:
            cur = nid
            steps = 0
            visited = {cur}
            for _ in range(max_steps):
                if cur in founders:
                    break
                p = get_parent(cur)
                if p is None or p not in self.G:
                    # Unknown chain ends: treat as length so far.
                    break
                if p in visited:
                    # Should not happen for DAG; break defensively.
                    break
                visited.add(p)
                cur = p
                steps += 1
            vals[nid] = steps

        return pd.Series(vals, name=f"{parent_role}_line_length")

    def _compute_marginal_founder_weights(self, pop_ids: Set[str]) -> Dict[str, float]:
        """
        Move genetic mass backward from RP to founders.

        Mass is conserved during propagation by "moving" it from descendants to parents.
        The accumulated mass at founders yields founder contributions up to normalization.
        """
        closure = self._closure_ancestors(pop_ids)
        if not closure:
            return {}
        subG = self.G.subgraph(closure)
        topo = list(nx.topological_sort(subG))
        rev_topo = list(reversed(topo))

        # Identify founders inside closure (indegree==0 within the closure subgraph).
        founders = {n for n in closure if subG.in_degree(n) == 0}

        m: Dict[str, float] = {n: 0.0 for n in closure}
        for nid in pop_ids:
            if nid in closure:
                m[nid] += 1.0

        founder_weight: Dict[str, float] = {f: 0.0 for f in founders}
        for v in rev_topo:
            mass = m[v]
            if mass <= 0:
                continue
            if v in founders:
                founder_weight[v] += mass
                m[v] = 0.0
                continue

            sire = self.father_of.get(v)
            dam = self.mother_of.get(v)
            if sire is not None and sire in closure:
                m[sire] += 0.5 * mass
            if dam is not None and dam in closure:
                m[dam] += 0.5 * mass
            m[v] = 0.0

        return founder_weight

    def effective_number_of_founders(self, pop_ids: Set[str]) -> float:
        weights = self._compute_marginal_founder_weights(pop_ids)
        total = float(sum(weights.values()))
        if total <= 0:
            return float("nan")
        probs = [w / total for w in weights.values() if w > 0]
        if not probs:
            return float("nan")
        return 1.0 / float(sum(p * p for p in probs))

    def effective_number_of_ancestors(self, pop_ids: Set[str]) -> float:
        """
        Effective number of ancestors (fa) computed from marginal contributions
        of all ancestors excluding the reference population nodes.

        Implementation:
        - Start with mass=1 at each reference individual.
        - Move mass backward from each node to its parents (mass is moved, not duplicated).
        - Accumulate mass at every ancestor node except nodes in pop_ids.
        - Normalize accumulated ancestor masses to probabilities and compute 1/sum(p^2).
        """
        if not pop_ids:
            return float("nan")

        closure = self._closure_ancestors(pop_ids)
        if not closure:
            return float("nan")
        subG = self.G.subgraph(closure)
        topo = list(nx.topological_sort(subG))
        rev_topo = list(reversed(topo))

        m: Dict[str, float] = {n: 0.0 for n in closure}
        for nid in pop_ids:
            if nid in closure:
                m[nid] += 1.0

        anc_weight: Dict[str, float] = {n: 0.0 for n in closure if n not in pop_ids}
        for v in rev_topo:
            mass = m[v]
            if mass <= 0:
                continue
            if v not in pop_ids and v in anc_weight:
                anc_weight[v] += mass

            sire = self.father_of.get(v)
            dam = self.mother_of.get(v)
            if sire is not None and sire in closure:
                m[sire] += 0.5 * mass
            if dam is not None and dam in closure:
                m[dam] += 0.5 * mass
            m[v] = 0.0

        total = float(sum(anc_weight.values()))
        if total <= 0:
            return float("nan")
        probs = [w / total for w in anc_weight.values() if w > 0]
        if not probs:
            return float("nan")
        return 1.0 / float(sum(p * p for p in probs))

    def intergenerational_interval(
        self,
        pop_ids: Set[str],
        min_valid_dt_days: int = 0,
    ) -> Dict[str, float]:
        """
        Mean parent age at birth of offspring, in years, split by:
        - Ojciec-Syn
        - Ojciec-Corka
        - Matka-Syn
        - Matka-Corka
        """
        pathways = {"father_son": [], "father_daughter": [], "mother_son": [], "mother_daughter": []}

        min_td = pd.Timedelta(days=min_valid_dt_days)
        for child_id in pop_ids:
            cb = self.birth_of.get(child_id, pd.NaT)
            if cb is pd.NaT or pd.isna(cb):
                continue
            csex = self.sex_of.get(child_id)
            if csex is None:
                continue

            father_id = self.father_of.get(child_id)
            mother_id = self.mother_of.get(child_id)

            def _handle_parent(pid: Optional[str], kind: str) -> None:
                if pid is None:
                    return
                pb = self.birth_of.get(pid, pd.NaT)
                if pb is pd.NaT or pd.isna(pb):
                    return
                dt = cb - pb
                if dt < min_td:
                    return
                years = float(dt / np.timedelta64(1, "D")) / 365.25
                if kind == "father":
                    if csex == "M":
                        pathways["father_son"].append(years)
                    elif csex == "F":
                        pathways["father_daughter"].append(years)
                elif kind == "mother":
                    if csex == "M":
                        pathways["mother_son"].append(years)
                    elif csex == "F":
                        pathways["mother_daughter"].append(years)

            _handle_parent(father_id, "father")
            _handle_parent(mother_id, "mother")

        def _mean_or_nan(xs: List[float]) -> float:
            return float(np.mean(xs)) if xs else float("nan")

        return {
            "Ojciec-Syn": _mean_or_nan(pathways["father_son"]),
            "Ojciec-Corka": _mean_or_nan(pathways["father_daughter"]),
            "Matka-Syn": _mean_or_nan(pathways["mother_son"]),
            "Matka-Corka": _mean_or_nan(pathways["mother_daughter"]),
        }

    def Ne_from_inbreeding_trend(
        self,
        pop_ids: Set[str],
        F: pd.Series,
        min_years: int = 3,
    ) -> float:
        """
        Estimate effective population size (Ne) from inbreeding trend:
            Ne ~= 1 / (2 * DeltaF_per_generation)

        We:
        - compute mean F by birth year for individuals in pop_ids
        - fit a slope dF/dyear by least squares
        - estimate generation interval g from intergenerational interval (mean across 4 pathways)
        - convert to DeltaF per generation: DeltaF = slope * g
        """
        if not pop_ids:
            return float("nan")
        if F.empty:
            return float("nan")

        # Birth year groups.
        tmp = []
        for nid in pop_ids:
            b = self.birth_of.get(nid, pd.NaT)
            if b is pd.NaT or pd.isna(b):
                continue
            y = int(b.year)
            f = F.get(nid, np.nan)
            if pd.isna(f):
                continue
            tmp.append((y, float(f)))
        if len(tmp) < min_years:
            return float("nan")
        dfy = pd.DataFrame(tmp, columns=["year", "F"])
        mean_by_year = dfy.groupby("year", as_index=False)["F"].mean().sort_values("year")
        if mean_by_year.shape[0] < min_years:
            return float("nan")

        years = mean_by_year["year"].to_numpy(dtype=float)
        fvals = mean_by_year["F"].to_numpy(dtype=float)
        slope = float(np.polyfit(years, fvals, 1)[0])  # dF/dyear

        gi = self.intergenerational_interval(pop_ids)
        vals = [gi[k] for k in ["Ojciec-Syn", "Ojciec-Corka", "Matka-Syn", "Matka-Corka"]]
        vals = [v for v in vals if not pd.isna(v)]
        if not vals:
            return float("nan")
        g = float(np.mean(vals))
        deltaF = slope * g
        if deltaF <= 0:
            return float("inf")
        return float(1.0 / (2.0 * deltaF))

    def pedigree_subgraph(self, individual_id: str, generations: int = 4) -> nx.DiGraph:
        """
        Induced pedigree subgraph for UI: node + ancestors up to `generations` generations.
        """
        if individual_id not in self.G:
            raise KeyError(f"Unknown individual id: {individual_id}")
        if generations < 0:
            raise ValueError("generations must be >= 0")

        # Gather ancestors within depth.
        dist_map = self._get_ancestor_distances(individual_id, max_depth=generations)
        nodes = {individual_id} | set(dist_map.keys())
        return self.G.subgraph(nodes).copy()

    def pci(
        self,
        pop_ids: Set[str],
        max_generations: int = 4,
    ) -> Dict[str, float]:
        """
        Pedigree completeness index (PCI) for each generation depth.

        PCI(g) is averaged over individuals in pop_ids:
            r_i(g) = (# distinct known ancestors at distance g) / (2^g)
            PCI(g) = mean_i r_i(g) * 100
        Returns both per-generation PCI and overall average across g=1..max_generations.
        """
        if not pop_ids or max_generations <= 0:
            return {"PCI_overall": float("nan")}
        if not nx.is_directed_acyclic_graph(self.G):
            # Still compute with distances, but results may be meaningless.
            pass

        pci_by_g: Dict[int, float] = {}
        for g in range(1, max_generations + 1):
            ratios = []
            for nid in pop_ids:
                dists = self._get_ancestor_distances(nid, max_depth=g)
                anc_at_g = [anc for anc, d in dists.items() if d == g]
                known_count = len(set(anc_at_g))
                ratios.append(known_count / (2**g))
            pci_by_g[g] = float(np.mean(ratios)) * 100.0 if ratios else float("nan")

        pci_overall = float(np.nanmean([pci_by_g[g] for g in pci_by_g])) if pci_by_g else float("nan")
        out = {"PCI_overall": pci_overall}
        out.update({f"PCI_{g}": pci_by_g[g] for g in pci_by_g})
        return out

