"""Project-layer data model (v3 dev note, section 3).

Additive to the theorem-layer runtime: these records describe a *governed Lean
project* -- its snapshots, obligations, patches, strategy changes, and progress
-- one level above the per-theorem CanonicalProofState. They confer no standing
(the retention gate does) and no identity (the registry does); they organise project-scale
search so the existing verifier/gate boundary can be driven across a real
dependency graph (e.g. the KTV formalisation, github.com/guanyangwang/ktv-swap-lean).

Schema note: this is the project layer's own record schema (`project-v0`),
additive to and independent of `verification-event-v0`.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Literal

SCHEMA_VERSION = "project-v0"

ObligationStatus = Literal[
    "open", "assigned", "in_progress", "discharged",
    "refuted", "blocked", "superseded",
]
OBLIGATION_STATUSES = frozenset({
    "open", "assigned", "in_progress", "discharged",
    "refuted", "blocked", "superseded",
})
ACTIVE_STATUSES = frozenset({"open", "assigned", "in_progress"})
# "closed" = successfully done or replaced; "terminal" also includes failure.
CLOSED_STATUSES = frozenset({"discharged", "superseded"})
TERMINAL_STATUSES = frozenset({"discharged", "superseded", "refuted"})
EVIDENCE_CLASSES = frozenset({
    "claim", "analytic", "rigorous_numerical", "simulation", "release_replay",
    "lean_kernel", "computer_algebra", "symbolic_script",
    "semantic_adequacy", "literature_review", "independent_expert_review",
})
EVIDENCE_ROLES = frozenset({"required", "corroborating", "diagnostic"})
ResearchEvidenceClass = Literal[
    "claim", "lean_kernel", "computer_algebra", "symbolic_script",
    "semantic_adequacy", "literature_review", "independent_expert_review",
    "release_replay",
]
EvidenceRole = Literal["required", "corroborating", "diagnostic"]

PatchStanding = Literal[
    "sandboxed", "locally_verified", "module_verified",
    "project_verified", "release_verified",
]
PATCH_STANDING_ORDER = (
    "sandboxed", "locally_verified", "module_verified",
    "project_verified", "release_verified",
)
SnapshotVerificationState = Literal[
    "unverified", "interactive_verified", "release_verified",
]
SNAPSHOT_STATES = frozenset({"unverified", "interactive_verified", "release_verified"})


def _sha(body: dict) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def content_id(prefix: str, body: dict) -> str:
    """Deterministic content-addressed id (mirrors events.event.make)."""
    return f"{prefix}_{_sha(body)[:12]}"


@dataclass
class WorkspaceSnapshot:
    """The exact source tree + toolchain a verification act ran against."""
    snapshot_id: str
    parent_snapshot_id: str | None = None
    source_hashes: dict = field(default_factory=dict)
    lake_manifest_hash: str | None = None
    mathlib_revision: str | None = None
    toolchain_id: str | None = None
    build_cache_key: str | None = None
    created_by_event_id: str | None = None
    verification_state: SnapshotVerificationState = "unverified"
    schema: str = SCHEMA_VERSION

    @classmethod
    def new(cls, source_hashes, parent_snapshot_id=None, lake_manifest_hash=None,
            mathlib_revision=None, toolchain_id=None, created_by_event_id=None,
            verification_state="unverified"):
        # toolchain identity is part of the snapshot AND the cache key: the same
        # sources under a bumped Lean toolchain are a different verification act.
        ident = {"source_hashes": source_hashes, "parent": parent_snapshot_id,
                 "lake": lake_manifest_hash, "mathlib": mathlib_revision,
                 "toolchain": toolchain_id}
        sid = content_id("snap", ident)
        return cls(
            snapshot_id=sid, parent_snapshot_id=parent_snapshot_id,
            source_hashes=dict(source_hashes),
            lake_manifest_hash=lake_manifest_hash, mathlib_revision=mathlib_revision,
            toolchain_id=toolchain_id,
            build_cache_key="bc_" + _sha({"src": source_hashes,
                                          "mathlib": mathlib_revision,
                                          "toolchain": toolchain_id})[:16],
            created_by_event_id=created_by_event_id,
            verification_state=verification_state,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "WorkspaceSnapshot":
        return WorkspaceSnapshot(**d)


@dataclass
class Obligation:
    """A formal target plus its role in the project dependency graph."""
    obligation_id: str
    formal_target: str
    informal_claim_ref: str | None = None
    module: str | None = None
    prerequisites: list = field(default_factory=list)
    downstream_dependents: list = field(default_factory=list)
    critical_path_weight: float = 1.0   # this node's own weight
    status: ObligationStatus = "open"
    assigned_proposer: str | None = None
    verification_history: list = field(default_factory=list)
    adequacy_state: str = "unknown"
    completion_contract: str | None = None
    evidence_class: ResearchEvidenceClass = "claim"
    evidence_role: EvidenceRole = "required"
    superseded_by: str | None = None
    blocking_cause: dict = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    schema: str = SCHEMA_VERSION

    @classmethod
    def new(cls, formal_target, module=None, prerequisites=None,
            informal_claim_ref=None, critical_path_weight=1.0,
            completion_contract=None, evidence_class="claim", evidence_role="required"):
        oid = content_id("obl", {"target": formal_target, "module": module,
                                 "evidence_class": evidence_class})
        return cls(
            obligation_id=oid, formal_target=formal_target, module=module,
            informal_claim_ref=informal_claim_ref,
            prerequisites=list(prerequisites or []),
            critical_path_weight=float(critical_path_weight),
            completion_contract=completion_contract, evidence_class=evidence_class,
            evidence_role=evidence_role,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Obligation":
        return Obligation(**d)

    # --- status predicates (terminal semantics) ---
    @property
    def is_success_terminal(self) -> bool:
        return self.status == "discharged"

    @property
    def is_failure_terminal(self) -> bool:
        return self.status == "refuted"

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def is_closed(self) -> bool:
        return self.status in CLOSED_STATUSES

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES


@dataclass
class WorkspacePatch:
    """A transactional source patch: the project-scale unit of a candidate."""
    patch_id: str
    base_snapshot_id: str
    files_changed: list = field(default_factory=list)
    declarations_added: list = field(default_factory=list)
    declarations_modified: list = field(default_factory=list)
    declarations_removed: list = field(default_factory=list)
    expected_obligations_closed: list = field(default_factory=list)
    affected_modules: list = field(default_factory=list)
    proposer_id: str | None = None
    strategy_event_id: str | None = None
    patch_hash: str = ""
    standing: PatchStanding = "sandboxed"
    schema: str = SCHEMA_VERSION

    @classmethod
    def new(cls, base_snapshot_id, files_changed, declarations_added=None,
            declarations_modified=None, declarations_removed=None,
            expected_obligations_closed=None, affected_modules=None,
            proposer_id=None, strategy_event_id=None):
        h = _sha({"base": base_snapshot_id, "files": files_changed,
                  "add": declarations_added or [], "mod": declarations_modified or [],
                  "rm": declarations_removed or []})
        return cls(
            patch_id="patch_" + h[:12], base_snapshot_id=base_snapshot_id,
            files_changed=list(files_changed),
            declarations_added=list(declarations_added or []),
            declarations_modified=list(declarations_modified or []),
            declarations_removed=list(declarations_removed or []),
            expected_obligations_closed=list(expected_obligations_closed or []),
            affected_modules=list(affected_modules or []),
            proposer_id=proposer_id, strategy_event_id=strategy_event_id,
            patch_hash="sha256:" + h[:32], standing="sandboxed",
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "WorkspacePatch":
        return WorkspacePatch(**d)

    def promoted(self, standing: str) -> "WorkspacePatch":
        """Copy advanced to `standing`. Monotonic: never demotes."""
        if standing not in PATCH_STANDING_ORDER:
            raise ValueError(f"unknown standing {standing!r}")
        if PATCH_STANDING_ORDER.index(standing) < PATCH_STANDING_ORDER.index(self.standing):
            raise ValueError(f"cannot demote patch {self.standing} -> {standing}")
        d = self.to_dict()
        d["standing"] = standing
        return WorkspacePatch.from_dict(d)


@dataclass
class StrategyEvent:
    """A typed, parent-linked change of the project's approach."""
    event_id: str
    actor: str
    scope: str
    previous_strategy: str
    new_strategy: str
    evidence: list = field(default_factory=list)
    parent_event_id: str | None = None
    resulting_plan_hash: str | None = None
    schema: str = SCHEMA_VERSION

    @classmethod
    def new(cls, actor, scope, previous_strategy, new_strategy, evidence=None,
            parent_event_id=None, resulting_plan_hash=None):
        # id covers the COMPLETE immutable content: two events that differ in
        # actor / evidence / resulting plan must not collide.
        eid = content_id("se", {
            "actor": actor, "scope": scope,
            "previous_strategy": previous_strategy, "new_strategy": new_strategy,
            "evidence": list(evidence or []), "parent_event_id": parent_event_id,
            "resulting_plan_hash": resulting_plan_hash,
        })
        return cls(
            event_id=eid, actor=actor, scope=scope,
            previous_strategy=previous_strategy, new_strategy=new_strategy,
            evidence=list(evidence or []), parent_event_id=parent_event_id,
            resulting_plan_hash=resulting_plan_hash,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "StrategyEvent":
        return StrategyEvent(**d)


@dataclass
class ProgressSnapshot:
    """Activity vs movement on the critical path."""
    obligations_closed: int = 0
    critical_obligations_closed: int = 0
    root_distance: int = 0                     # selected critical path distance
    all_terminal_remaining_work: int = 0       # outstanding across every path
    blocked_count: int = 0
    verifier_spend: float = 0.0
    semantic_redundancy: float = 0.0
    template_reuse_count: int = 0
    schema: str = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ProgressSnapshot":
        return ProgressSnapshot(**d)


@dataclass
class ProjectState:
    """The durable root object for a Lean formalisation campaign.

    Carries the identity of its obligation graph (id + content hash). The graph
    itself lives in an `ObligationGraph`; `open_obligations` is a *derived*
    cache of that graph's active nodes, refreshed by `attach_graph`.
    """
    project_id: str
    manifest_hash: str
    upstream_commit: str | None = None
    toolchain_id: str | None = None
    module_graph: dict = field(default_factory=dict)
    declaration_index: dict = field(default_factory=dict)
    obligation_graph_id: str | None = None
    obligation_graph_hash: str | None = None
    open_obligations: list = field(default_factory=list)
    retained_templates: list = field(default_factory=list)
    claim_graph_id: str | None = None
    active_snapshot_id: str | None = None
    stable_snapshot_id: str | None = None
    provenance: dict = field(default_factory=dict)
    schema: str = SCHEMA_VERSION

    @classmethod
    def new(cls, manifest_hash, upstream_commit=None, toolchain_id=None,
            active_snapshot_id=None):
        pid = content_id("proj", {"manifest": manifest_hash, "commit": upstream_commit})
        return cls(
            project_id=pid, manifest_hash=manifest_hash,
            upstream_commit=upstream_commit, toolchain_id=toolchain_id,
            active_snapshot_id=active_snapshot_id, stable_snapshot_id=active_snapshot_id,
        )

    def attach_graph(self, graph) -> "ProjectState":
        """Bind the obligation graph's identity and refresh the derived cache.

        Duck-typed on `graph.graph_hash()` / `graph.obligations()` to avoid a
        models<->graph import cycle.
        """
        gh = graph.graph_hash()
        self.obligation_graph_hash = gh
        self.obligation_graph_id = "og_" + gh.split(":")[-1][:12]
        self.open_obligations = [o.obligation_id for o in graph.obligations()
                                 if o.is_active]
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ProjectState":
        return ProjectState(**d)


JSON_SCHEMA = {
    "schema_version": SCHEMA_VERSION,
    "ProjectState": ["project_id", "manifest_hash"],
    "WorkspaceSnapshot": ["snapshot_id"],
    "Obligation": ["obligation_id", "formal_target"],
    "WorkspacePatch": ["patch_id", "base_snapshot_id"],
    "StrategyEvent": ["event_id", "actor", "previous_strategy", "new_strategy"],
    "ProgressSnapshot": [],
}


def validate(record_type: str, d: dict) -> None:
    """Structural + semantic validation (not merely required-field presence).

    Checks required fields, schema version, enum membership, primitive types,
    and non-negative weights. Raises ValueError on the first violation.
    """
    req = JSON_SCHEMA.get(record_type)
    if req is None:
        raise ValueError(f"unknown record type {record_type!r}")
    missing = [k for k in req if d.get(k) in (None, "")]
    if missing:
        raise ValueError(f"{record_type} missing required fields: {missing}")
    if d.get("schema") not in (None, SCHEMA_VERSION):
        raise ValueError(f"{record_type} wrong schema {d.get('schema')!r}")

    if record_type == "Obligation":
        if d.get("status", "open") not in OBLIGATION_STATUSES:
            raise ValueError(f"bad obligation status {d.get('status')!r}")
        ec = d.get("evidence_class")
        if ec is not None and ec not in EVIDENCE_CLASSES:
            raise ValueError(f"bad evidence_class {ec!r}")
        er = d.get("evidence_role")
        if er is not None and er not in EVIDENCE_ROLES:
            raise ValueError(f"bad evidence_role {er!r}")
        w = d.get("critical_path_weight", 1.0)
        if not isinstance(w, (int, float)) or isinstance(w, bool) or w < 0:
            raise ValueError(f"critical_path_weight must be a non-negative number, got {w!r}")
        for lst in ("prerequisites", "downstream_dependents", "verification_history"):
            if not isinstance(d.get(lst, []), list):
                raise ValueError(f"{lst} must be a list")
    elif record_type == "WorkspacePatch":
        if d.get("standing", "sandboxed") not in PATCH_STANDING_ORDER:
            raise ValueError(f"bad patch standing {d.get('standing')!r}")
    elif record_type == "WorkspaceSnapshot":
        if d.get("verification_state", "unverified") not in SNAPSHOT_STATES:
            raise ValueError(f"bad snapshot state {d.get('verification_state')!r}")
