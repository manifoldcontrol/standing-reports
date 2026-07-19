"""ObligationGraph: the project's dependency DAG over obligations.

Edges run prerequisite -> dependent (toward the root theorem). The graph
enforces its own consistency (unique ids, matched reverse edges, no dangling
references, acyclic), derives topological order and critical-path value,
reports readiness under terminal-failure semantics, propagates refutation, and
summarises progress. It is pure bookkeeping and confers no standing.
"""
from __future__ import annotations
import hashlib
import json
from .models import Obligation, ProgressSnapshot, SCHEMA_VERSION


class ObligationGraphError(ValueError):
    pass


class ObligationGraph:
    def __init__(self):
        self._obl: dict = {}

    # --- construction ---
    def add(self, obl: Obligation) -> Obligation:
        if obl.obligation_id in self._obl:
            raise ObligationGraphError(f"duplicate obligation id {obl.obligation_id!r}")
        self._obl[obl.obligation_id] = obl
        return obl

    def add_dependency(self, prereq_id: str, dependent_id: str) -> None:
        """Canonical edge API: wires BOTH directions. `prereq` before `dependent`."""
        for oid in (prereq_id, dependent_id):
            if oid not in self._obl:
                raise ObligationGraphError(f"unknown obligation {oid!r}")
        if prereq_id == dependent_id:
            raise ObligationGraphError("self-dependency")
        pre, dep = self._obl[prereq_id], self._obl[dependent_id]
        if dependent_id not in pre.downstream_dependents:
            pre.downstream_dependents.append(dependent_id)
        if prereq_id not in dep.prerequisites:
            dep.prerequisites.append(prereq_id)

    # --- access ---
    def get(self, oid: str) -> Obligation:
        return self._obl[oid]

    def __len__(self) -> int:
        return len(self._obl)

    def __contains__(self, oid: str) -> bool:
        return oid in self._obl

    def obligations(self) -> list:
        return list(self._obl.values())

    def ids(self) -> list:
        return list(self._obl.keys())

    # --- integrity ---
    def assert_consistent(self) -> None:
        """Full structural check: ids unique, refs exist, reverse edges matched,
        acyclic. The single guard deserialisation and mutation should call."""
        for oid, o in self._obl.items():
            if o.obligation_id != oid:
                raise ObligationGraphError(
                    f"id/key mismatch {oid!r} != {o.obligation_id!r}")
            for p in o.prerequisites:
                if p not in self._obl:
                    raise ObligationGraphError(
                        f"{oid} references unknown prerequisite {p!r}")
                if oid not in self._obl[p].downstream_dependents:
                    raise ObligationGraphError(
                        f"missing reverse edge: {p} -> {oid}")
            for d in o.downstream_dependents:
                if d not in self._obl:
                    raise ObligationGraphError(
                        f"{oid} references unknown dependent {d!r}")
                if oid not in self._obl[d].prerequisites:
                    raise ObligationGraphError(
                        f"missing prerequisite edge: {oid} in {d}")
        self.assert_acyclic()

    def detect_cycle(self):
        WHITE, GREY, BLACK = 0, 1, 2
        color = {oid: WHITE for oid in self._obl}
        path: list = []

        def visit(u):
            color[u] = GREY
            path.append(u)
            for v in self._obl[u].downstream_dependents:
                if v not in self._obl:
                    raise ObligationGraphError(f"edge to unknown obligation {v!r}")
                if color[v] == GREY:
                    return path[path.index(v):] + [v]   # complete cycle, closed
                if color[v] == WHITE:
                    c = visit(v)
                    if c:
                        return c
            color[u] = BLACK
            path.pop()
            return None

        for oid in self._obl:
            if color[oid] == WHITE:
                c = visit(oid)
                if c:
                    return c
        return None

    def assert_acyclic(self) -> None:
        c = self.detect_cycle()
        if c:
            raise ObligationGraphError("cycle: " + " -> ".join(c))

    def graph_hash(self) -> str:
        payload = [o.to_dict() for o in
                   sorted(self._obl.values(), key=lambda o: o.obligation_id)]
        return "sha256:" + hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()[:32]

    def to_dict(self) -> dict:
        return {"schema": SCHEMA_VERSION,
                "obligations": [o.to_dict() for o in self._obl.values()]}

    @staticmethod
    def from_dict(d: dict) -> "ObligationGraph":
        g = ObligationGraph()
        for od in d.get("obligations", []):
            g.add(Obligation.from_dict(od))
        g.assert_consistent()
        return g

    # --- ordering ---
    def topological_order(self) -> list:
        self.assert_acyclic()
        indeg = {oid: 0 for oid in self._obl}
        for o in self._obl.values():
            for dd in o.downstream_dependents:
                indeg[dd] += 1
        ready = sorted(oid for oid, k in indeg.items() if k == 0)
        order: list = []
        while ready:
            u = ready.pop(0)
            order.append(u)
            newly = []
            for v in self._obl[u].downstream_dependents:
                indeg[v] -= 1
                if indeg[v] == 0:
                    newly.append(v)
            ready = sorted(ready + newly)
        if len(order) != len(self._obl):
            raise ObligationGraphError("cycle detected during toposort")
        return order

    # --- roots / critical path ---
    def terminals(self) -> list:
        return [o for o in self._obl.values() if not o.downstream_dependents]

    def _values(self, residual: bool = False) -> dict:
        self.assert_acyclic()
        memo: dict = {}

        def val(u):
            if u in memo:
                return memo[u]
            best = 0.0
            for d in self._obl[u].downstream_dependents:
                best = max(best, val(d))
            node = self._obl[u]
            own = node.critical_path_weight
            if residual and node.is_terminal:
                own = 0.0     # closed / refuted work is no longer outstanding
            memo[u] = own + best
            return memo[u]

        for oid in self._obl:
            val(oid)
        return memo

    def critical_value(self, oid: str) -> float:
        """Total longest weighted path from `oid` to any terminal."""
        return self._values()[oid]

    def residual_critical_value(self, oid: str) -> float:
        """Longest weighted path counting only *outstanding* (non-terminal) work."""
        return self._values(residual=True)[oid]

    def critical_path(self) -> list:
        if not self._obl:
            return []
        val = self._values()
        sources = [oid for oid, o in self._obl.items() if not o.prerequisites]
        sources = sources or list(self._obl)
        start = max(sources, key=lambda x: (val[x], x))
        path = [start]
        u = start
        while self._obl[u].downstream_dependents:
            u = max(self._obl[u].downstream_dependents, key=lambda x: (val[x], x))
            path.append(u)
        return path

    # --- readiness (terminal-failure aware) ---
    def _prereq_satisfied(self, pid: str) -> bool:
        o = self._obl[pid]
        if o.status == "discharged":
            return True
        if o.status == "superseded":                 # replacement edge resolution
            rep = o.superseded_by
            return bool(rep) and rep in self._obl and self._obl[rep].status == "discharged"
        return False

    def is_ready(self, oid: str) -> bool:
        o = self._obl[oid]
        for p in o.prerequisites:
            if p not in self._obl:
                raise ObligationGraphError(
                    f"dangling prerequisite {p!r} for {oid!r}")
        if o.status != "open":
            return False
        return all(self._prereq_satisfied(p) for p in o.prerequisites)

    def ready_obligations(self) -> list:
        return [self._obl[oid] for oid in self._obl if self.is_ready(oid)]

    # --- failure propagation ---
    def propagate(self) -> "ObligationGraph":
        """Block active obligations whose prerequisites failed or are unresolved.

        refuted / blocked prerequisite -> dependent blocked (typed cause);
        superseded-without-discharged-replacement -> dependent blocked. Runs to
        a fixpoint so blocking is transitive.
        """
        changed = True
        while changed:
            changed = False
            for o in self._obl.values():
                if o.status not in ("open", "assigned", "in_progress"):
                    continue
                for p in o.prerequisites:
                    if p not in self._obl:
                        continue
                    pre = self._obl[p]
                    cause = None
                    if pre.status == "refuted":
                        cause = "refuted_prerequisite"
                    elif pre.status == "blocked":
                        cause = "blocked_prerequisite"
                    elif pre.status == "superseded" and not self._prereq_satisfied(p):
                        cause = "unresolved_supersession"
                    if cause:
                        o.status = "blocked"
                        o.blocking_cause = {"reason": cause, "prerequisite_id": p}
                        changed = True
                        break
        return self

    def project_outcome(self) -> str:
        terms = self.terminals()
        if any(t.status == "refuted" for t in terms):
            return "refuted"
        if terms and all(t.status == "discharged" for t in terms):
            return "proved"
        return "in_progress"

    # --- progress ---
    def selected_critical_path_distance(self) -> int:
        """Non-closed obligations remaining on the selected critical path."""
        return sum(1 for oid in self.critical_path()
                   if not self._obl[oid].is_closed)

    def all_terminal_remaining_work(self) -> int:
        """Outstanding (non-terminal) obligations across the whole graph."""
        return sum(1 for o in self._obl.values() if not o.is_terminal)

    def root_distance(self) -> int:
        return self.selected_critical_path_distance()

    def obligations_by_class(self, evidence_class) -> list:
        return [o for o in self._obl.values() if o.evidence_class == evidence_class]

    def dependency_closure(self, obligation_id, *, exclude_classes=()) -> set:
        """Transitive prerequisites of `obligation_id` (inclusive), skipping
        excluded classes. Excluded nodes (e.g. `simulation`) are neither included
        nor traversed, so such a branch stays out of a claim's closure."""
        self.assert_consistent()
        exclude = set(exclude_classes)
        closure: set = set()

        def visit(cur):
            if cur in closure or cur not in self._obl:
                return
            if self._obl[cur].evidence_class in exclude:
                return
            closure.add(cur)
            for p in self._obl[cur].prerequisites:
                visit(p)

        visit(obligation_id)
        return closure

    def progress(self, verifier_spend=0.0, semantic_redundancy=0.0,
                 template_reuse_count=0) -> ProgressSnapshot:
        closed = [o for o in self._obl.values() if o.is_closed]
        crit = set(self.critical_path())
        crit_closed = [o for o in closed if o.obligation_id in crit]
        blocked = [o for o in self._obl.values() if o.status == "blocked"]
        return ProgressSnapshot(
            obligations_closed=len(closed),
            critical_obligations_closed=len(crit_closed),
            root_distance=self.selected_critical_path_distance(),
            all_terminal_remaining_work=self.all_terminal_remaining_work(),
            blocked_count=len(blocked),
            verifier_spend=float(verifier_spend),
            semantic_redundancy=float(semantic_redundancy),
            template_reuse_count=int(template_reuse_count),
        )
