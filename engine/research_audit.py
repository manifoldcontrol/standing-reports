"""AI research-claim audit: typed multi-verifier evidence + independence profiling.

For a fully AI-generated research artifact, agreement among artifacts can be
*correlated* verification -- many seals tracing to one authoring cognition --
rather than independent confirmation. This module records that and derives
standing from the claim graph, not from ad-hoc booleans:

  * VerifierSeal        -- one verification act, content-addressed over its FULL
                           immutable payload (checker, lineages, context, result,
                           snapshot), with optional artifact/event provenance.
  * IndependenceProfile -- execution / encoding / cognitive / expert paths, plus
                           correlated and unknown-lineage AI groups. A Lean kernel
                           and Macaulay2 are two EXECUTION paths that may still
                           consume one AI ENCODING; the profile keeps them apart.
  * ClaimAssessment     -- per claim: required vs closed vs missing obligations,
                           evidence classes, replay + adequacy status, the
                           independence profile, and flags.
  * assess_research_standing -- assess claims from the graph, seals, snapshot,
                           and an optional policy.

The retention gate remains the sole standing authority; this only records and composes evidence.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from .models import content_id

RESEARCH_EVIDENCE_CLASSES = (
    "lean_kernel", "computer_algebra", "symbolic_script", "semantic_adequacy",
    "literature_review", "independent_expert_review", "release_replay",
)
CHECKER_CLASSES = (
    "formal_kernel", "computer_algebra", "symbolic_script",
    "ai_reviewer", "human_expert", "literature",
)
_DETERMINISTIC = frozenset({"formal_kernel", "computer_algebra"})

# the four claims are separate nodes (novelty and external validation are
# independent axes over the affine-group-scheme claim, not a single ladder)
RESEARCH_CLAIM_LEVELS = (
    "formal_counterexample_in_hopf_encoding",
    "formal_counterexample_as_affine_group_scheme",
    "historically_novel_counterexample",
    "externally_validated_mathematical_counterexample",
)


@dataclass
class VerifierSeal:
    seal_id: str
    obligation_id: str
    evidence_class: str
    checker: str
    checker_class: str
    subject_lineage: tuple = ()
    checker_lineage: tuple = ()
    shared_context: tuple = ()
    result: str = "accept"
    snapshot_id: str | None = None
    independent_reconstruction: bool = False
    source_artifact_hash: str | None = None
    output_artifact_hash: str | None = None
    verification_event_id: str | None = None
    evidence_origin: str = "modelled"
    schema: str = "verifier-seal-v0"

    @classmethod
    def new(cls, obligation_id, evidence_class, checker, checker_class, *,
            subject_lineage=(), checker_lineage=(), shared_context=(),
            result="accept", snapshot_id=None, independent_reconstruction=False,
            source_artifact_hash=None, output_artifact_hash=None,
            verification_event_id=None, evidence_origin="modelled"):
        # The address must bind the EVIDENCE, not just the assertion: without the artifact
        # hashes and origin, a modelled seal and an extracted one collide on seal_id.
        sid = content_id("seal", {
            "obligation_id": obligation_id, "evidence_class": evidence_class,
            "checker": checker, "checker_class": checker_class,
            "subject_lineage": sorted(subject_lineage),
            "checker_lineage": sorted(checker_lineage),
            "shared_context": sorted(shared_context),
            "result": result, "snapshot_id": snapshot_id,
            "source_artifact_hash": source_artifact_hash,
            "output_artifact_hash": output_artifact_hash,
            "verification_event_id": verification_event_id,
            "evidence_origin": evidence_origin,
            "independent_reconstruction": independent_reconstruction,
        })
        return cls(seal_id=sid, obligation_id=obligation_id, evidence_class=evidence_class,
                   checker=checker, checker_class=checker_class,
                   subject_lineage=tuple(subject_lineage),
                   checker_lineage=tuple(checker_lineage),
                   shared_context=tuple(shared_context), result=result,
                   snapshot_id=snapshot_id,
                   independent_reconstruction=independent_reconstruction,
                   source_artifact_hash=source_artifact_hash,
                   output_artifact_hash=output_artifact_hash,
                   verification_event_id=verification_event_id,
                   evidence_origin=evidence_origin)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "VerifierSeal":
        d = dict(d)
        for k in ("subject_lineage", "checker_lineage", "shared_context"):
            if isinstance(d.get(k), list):
                d[k] = tuple(d[k])
        return VerifierSeal(**d)


@dataclass(frozen=True)
class IndependenceProfile:
    execution_paths: int
    encoding_paths: int
    cognitive_paths: int
    external_expert_paths: int
    correlated_ai_groups: int
    unknown_lineage_groups: int


def _components(units, keyed):
    """Union-find components over `units`, linked when they share any key."""
    n = len(units)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first: dict = {}
    for i, u in enumerate(units):
        for k in keyed(u):
            if k in first:
                a, b = find(i), find(first[k])
                parent[a] = b
            else:
                first[k] = i
    comps: dict = {}
    for i in range(n):
        comps.setdefault(find(i), []).append(units[i])
    return list(comps.values())


class IndependenceLedger:
    def __init__(self, seals=()):
        self.seals = list(seals)

    def add(self, seal: VerifierSeal) -> VerifierSeal:
        self.seals.append(seal)
        return seal

    def restricted(self, obligation_ids) -> "IndependenceLedger":
        keep = set(obligation_ids)
        return IndependenceLedger([s for s in self.seals if s.obligation_id in keep])

    # --- primitives ---
    def _accepting(self):
        return [s for s in self.seals if s.result == "accept"]

    def _subjects(self) -> set:
        out: set = set()
        for s in self._accepting():
            out |= set(s.subject_lineage)
        return out

    def _authored_context(self) -> set:
        """Contexts tied to the authoring ecosystem (deterministic checks + self-review)."""
        subj = self._subjects()
        out: set = set()
        for s in self._accepting():
            inside = (s.checker_class in _DETERMINISTIC
                      or (s.checker_class == "ai_reviewer"
                          and set(s.checker_lineage) and set(s.checker_lineage) <= subj))
            if inside:
                out |= set(s.shared_context)
        return out

    def _ai_groups(self):
        ai = [s for s in self._accepting() if s.checker_class == "ai_reviewer"]
        return _components(ai, lambda s: {("lin", l) for l in s.checker_lineage}
                           | {("ctx", c) for c in s.shared_context}
                           | ({("seal", s.seal_id)} if not s.checker_lineage and not s.shared_context else set()))

    # --- counts ---
    def execution_paths(self) -> set:
        return {s.checker for s in self._accepting() if s.checker_class in _DETERMINISTIC}

    def human_reviews(self) -> set:
        return {s.checker for s in self._accepting() if s.checker_class == "human_expert"}

    def encoding_paths(self) -> int:
        hashes = {s.source_artifact_hash for s in self._accepting() if s.source_artifact_hash}
        if hashes:
            return len(hashes)
        sigs = {frozenset(s.subject_lineage) for s in self._accepting() if s.subject_lineage}
        return len(sigs)

    def cognitive_paths(self) -> int:
        authored = [s for s in self._accepting() if s.subject_lineage]
        base = len(_components(authored, lambda s: {("m", l) for l in s.subject_lineage}
                              | {("ctx", c) for c in s.shared_context})) if authored else 0
        # a human expert and an independent AI reconstruction are extra cognitive paths
        return base + len(self.human_reviews()) + self.independent_ai_paths()

    def independent_ai_paths(self) -> int:
        subj, authored_ctx = self._subjects(), self._authored_context()
        count = 0
        for g in self._ai_groups():
            lineage: set = set()
            ctx: set = set()
            recon = False
            for s in g:
                lineage |= set(s.checker_lineage)
                ctx |= set(s.shared_context)
                recon = recon or s.independent_reconstruction
            if lineage and not lineage <= subj and not (ctx & authored_ctx) and recon:
                count += 1
        return count

    def correlated_ai_groups(self) -> int:
        subj = self._subjects()
        return sum(1 for g in self._ai_groups()
                   if (lin := set().union(*[set(s.checker_lineage) for s in g])) and lin <= subj)

    def unknown_lineage_groups(self) -> int:
        return sum(1 for g in self._ai_groups() if all(not s.checker_lineage for s in g))

    def independence_profile(self) -> IndependenceProfile:
        return IndependenceProfile(
            execution_paths=len(self.execution_paths()),
            encoding_paths=self.encoding_paths(),
            cognitive_paths=self.cognitive_paths(),
            external_expert_paths=len(self.human_reviews()),
            correlated_ai_groups=self.correlated_ai_groups(),
            unknown_lineage_groups=self.unknown_lineage_groups())

    def effective_independent_reviews(self) -> int:
        return (len(self.execution_paths()) + len(self.human_reviews())
                + self.independent_ai_paths())

    def flags(self) -> list:
        out = []
        subj, authored_ctx = self._subjects(), self._authored_context()
        for s in self._accepting():
            if s.checker_class == "ai_reviewer" and not s.checker_lineage:
                out.append({"kind": "unknown_ai_checker_lineage", "seal_id": s.seal_id})
        for g in self._ai_groups():
            lineage: set = set()
            ctx: set = set()
            recon = False
            for s in g:
                lineage |= set(s.checker_lineage)
                ctx |= set(s.shared_context)
                recon = recon or s.independent_reconstruction
            if lineage and lineage <= subj:
                out.append({"kind": "correlated_ai_review", "lineage": sorted(lineage),
                            "seals": [s.seal_id for s in g]})
            elif lineage and not lineage <= subj and ((ctx & authored_ctx) or not recon):
                out.append({"kind": "partial_independence", "lineage": sorted(lineage),
                            "reason": "shared_context" if (ctx & authored_ctx)
                                      else "no_independent_reconstruction"})
        if not self.human_reviews():
            out.append({"kind": "no_human_expert_review",
                        "detail": "external validation boundary open"})
        return out


@dataclass(frozen=True)
class ResearchStandingPolicy:
    """The authority model: which requirements each claim must meet for standing.

    The independence thresholds gate only the externally-validated claim, so a
    Lean kernel plus Macaulay2 (two execution paths over one AI encoding) cannot
    by themselves satisfy semantic independence -- that needs an external expert.
    The retention gate applies this policy; the policy does not confer standing itself.
    """
    require_release_replay: bool = True
    require_semantic_adequacy: bool = True
    min_execution_paths: int = 2
    min_encoding_paths: int = 2
    min_cognitive_paths: int = 2
    min_external_expert_paths: int = 1
    require_human_expert: bool = True
    require_exact_commit: bool = True
    allow_modelled_release_standing: bool = False
    independence_gated: tuple = ("externally_validated_mathematical_counterexample", "external_validation_claim")

    @property
    def policy_id(self) -> str:
        return content_id("policy", asdict(self))

    def _predicates(self, standing_label, *, replay, adequacy, profile, snapshot_id):
        p = []
        if self.require_exact_commit:
            p.append(("exact_commit_identity", bool(snapshot_id), "exact commit identity absent"))
        if self.require_release_replay:
            p.append(("release_replay_closed", bool(replay), "release replay not closed"))
        if self.require_semantic_adequacy:
            p.append(("semantic_adequacy_closed", bool(adequacy), "semantic adequacy not closed"))
        if standing_label in self.independence_gated:
            ep, en = profile["execution_paths"], profile["encoding_paths"]
            cg, ex = profile["cognitive_paths"], profile["external_expert_paths"]
            p.append((f"execution_paths>={self.min_execution_paths}", ep >= self.min_execution_paths,
                      f"execution_paths: {ep} < {self.min_execution_paths}"))
            p.append((f"encoding_paths>={self.min_encoding_paths}", en >= self.min_encoding_paths,
                      f"encoding_paths: {en} < {self.min_encoding_paths}"))
            p.append((f"cognitive_paths>={self.min_cognitive_paths}", cg >= self.min_cognitive_paths,
                      f"cognitive_paths: {cg} < {self.min_cognitive_paths}"))
            p.append((f"external_expert_paths>={self.min_external_expert_paths}",
                      ex >= self.min_external_expert_paths,
                      f"external_expert_paths: {ex} < {self.min_external_expert_paths}"))
            if self.require_human_expert:
                p.append(("human_expert_present", ex >= 1, "no human expert review"))
        return p

    def evaluate(self, *, claim_id, standing_label, closure_complete, replay_verified,
                 semantic_adequacy_verified, independence_profile, snapshot_id):
        preds = self._predicates(standing_label, replay=replay_verified,
                                 adequacy=semantic_adequacy_verified,
                                 profile=independence_profile, snapshot_id=snapshot_id)
        satisfied = [name for name, ok, _ in preds if ok]
        unmet = [reason for _, ok, reason in preds if not ok]
        if not closure_complete:
            unmet = ["closure incomplete"] + unmet
        ok = closure_complete and all(o for _, o, _ in preds)
        return PolicyEvaluation(policy_id=self.policy_id, claim_id=claim_id,
                                closure_complete=closure_complete, policy_satisfied=ok,
                                satisfied_requirements=satisfied, unmet_requirements=unmet,
                                resulting_standing=(standing_label if ok else None))


@dataclass
class PolicyEvaluation:
    policy_id: str
    claim_id: str
    closure_complete: bool
    policy_satisfied: bool
    satisfied_requirements: list = field(default_factory=list)
    unmet_requirements: list = field(default_factory=list)
    resulting_standing: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClaimAssessment:
    claim_id: str
    standing: str | None
    complete: bool
    required_obligations: list = field(default_factory=list)
    closed_obligations: list = field(default_factory=list)
    missing_obligations: list = field(default_factory=list)
    evidence_classes: list = field(default_factory=list)
    replay_verified: bool = False
    semantic_adequacy_verified: bool = False
    independence_profile: dict = field(default_factory=dict)
    flags: list = field(default_factory=list)
    policy_id: str | None = None
    policy_evaluation: dict = field(default_factory=dict)
    evidence_origin: str = "modelled"   # untrusted until seals prove otherwise 

    def to_dict(self) -> dict:
        return asdict(self)

_MATH_ORDER = (
    "hopf_counterexample_claim",
    "group_scheme_counterexample_claim",
    "external_validation_claim",
)


def assess_research_standing(*, graph, claim_ids, ledger, snapshot_id=None, policy=None):
    """Assess each claim from graph closure + seals under a standing policy.

    Returns {claim_id: ClaimAssessment}. `complete` is closure (obligations
    satisfied); `standing` is granted only when the policy is also satisfied.
    """
    policy = policy or ResearchStandingPolicy()
    accepting = {s.obligation_id for s in ledger.seals if s.result == "accept"}

    def satisfied(oid):
        return oid in accepting or graph.get(oid).is_success_terminal

    out = {}
    for cid in claim_ids:
        closure = graph.dependency_closure(cid)
        required, closed, missing, ev = [], [], [], set()
        replay = adequacy = False
        for oid in closure:
            o = graph.get(oid)
            if o.evidence_class == "claim":
                continue
            if satisfied(oid):
                ev.add(o.evidence_class)
                if o.evidence_class == "release_replay":
                    replay = True
                if o.evidence_class == "semantic_adequacy":
                    adequacy = True
            if o.evidence_role != "required":
                continue
            required.append(oid)
            (closed if satisfied(oid) else missing).append(oid)
        closure_complete = not missing
        sub = ledger.restricted(closure)
        profile = asdict(sub.independence_profile())
        closure_seals = [s for s in sub.seals if s.result == "accept"]
        # Fail CLOSED: absence of evidence is not extraction. An empty closure has no
        # modelled seal, so an `any(... == "modelled")` test would call it extracted.
        origin = ("extracted" if closure_seals and all(
            getattr(s, "evidence_origin", "modelled") == "extracted" for s in closure_seals)
            else "modelled")
        pe = policy.evaluate(
            claim_id=cid, standing_label=graph.get(cid).formal_target,
            closure_complete=closure_complete, replay_verified=replay,
            semantic_adequacy_verified=adequacy, independence_profile=profile,
            snapshot_id=snapshot_id)
        out[cid] = ClaimAssessment(
            claim_id=cid, standing=pe.resulting_standing, complete=closure_complete,
            required_obligations=sorted(required), closed_obligations=sorted(closed),
            missing_obligations=sorted(missing), evidence_classes=sorted(ev),
            replay_verified=replay, semantic_adequacy_verified=adequacy,
            independence_profile=profile, flags=sub.flags(),
            policy_id=policy.policy_id, policy_evaluation=pe.to_dict(),
            evidence_origin=origin)
    return out


def standing_summary(assessments, graph, id_to_name=None):
    """Machine-readable summary: granted mathematical standing + blocked-claim reasons."""
    names = id_to_name or {}
    by_label = {graph.get(cid).formal_target: a for cid, a in assessments.items()}
    granted = None
    for label in _MATH_ORDER:
        if label in by_label and by_label[label].standing:
            granted = label
    blocked = {}
    for label, a in by_label.items():
        if a.standing:
            continue
        reasons = [f"{names.get(m, m)} obligation open" for m in a.missing_obligations]
        reasons += [r for r in a.policy_evaluation.get("unmet_requirements", [])
                    if r != "closure incomplete"]
        blocked[label] = reasons
    return {"standing": granted, "blocked_claims": blocked}
