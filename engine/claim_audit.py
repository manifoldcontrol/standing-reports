"""Generic research-claim audit harness.

Everything project-specific -- which claims exist, which obligations support
them, which kernel declarations close which obligation, who authored the
subject -- lives in a `ClaimMap`: DATA, content-addressed, supplied per
project. The harness owns only the invariants:

* the manifest carries OBSERVATIONS (commit, pins, hashes, the raw axiom
  report); a manifest stating its own closure is refused ;
* the verifier parses the report and DERIVES kernel closure under the map;
* classes a kernel cannot decide close only from attributed attestations,
  and attesting a kernel-decidable obligation is refused;
* snapshots use the manifest's real pins -- missing pins raise ;
* evidence origin is structural and fails closed .

The Grothendieck pilot is instance #1 (`grothendieck_intake` builds its map
from the existing demo constants); slackMCA_v4 is instance #2
(`claim_maps/slackmca_v4.py`). Auditing a new project means writing a map,
not code.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .models import Obligation, WorkspaceSnapshot, content_id, EVIDENCE_CLASSES
from .obligation_graph import ObligationGraph
from .research_audit import (
    VerifierSeal, IndependenceLedger, assess_research_standing, ResearchStandingPolicy,
)


class ClaimAuditError(ValueError):
    pass


CLEAN_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
ATTESTED_CLASSES = frozenset({"semantic_adequacy", "literature_review",
                              "independent_expert_review"})

_AXIOM_LINE = re.compile(r"'([\w.]+)'\s+depends on axioms\s*:\s*\[([^\]]*)\]")


def validate_commit_hash(value):
    if not re.fullmatch(r"[0-9a-f]{40}", value or ""):
        raise ClaimAuditError("release surfaces require an exact 40-character commit hash")


def parse_axiom_report(text):
    """Raw `#print axioms` output -> {short_decl: frozenset(axioms)}.

    Whitespace is normalised first: the kernel wraps long axiom lists across
    lines. Keyed by the final name component, so namespace layout differences
    between commits do not break matching.
    """
    flat = re.sub(r"\s+", " ", text or "")
    return {name.split(".")[-1]: frozenset(a.strip() for a in axioms.split(",") if a.strip())
            for name, axioms in _AXIOM_LINE.findall(flat)}


@dataclass
class ClaimMap:
    """Per-project audit interpretation. Content-addressed: `map_id` changes
    whenever the interpretation does, so a verdict always names the map that
    produced it."""
    project: str
    authors: tuple                 # subject lineage of the formalisation
    obligations: dict              # name -> (evidence_class, evidence_role)
    claims: dict                   # claim name -> [dependency names]
    claim_order: tuple             # scan order for the granted standing (last wins)
    claim_standing: dict           # claim name -> lifecycle label when complete
    decl_obligations: dict         # kernel obligation -> (declaration, ...)
    kernel_source_suffix: str      # manifest source_hashes key suffix for the subject
    clean_axioms: frozenset = field(default_factory=lambda: CLEAN_AXIOMS)

    def __post_init__(self):
        names = set(self.obligations) | set(self.claims)
        for cls, _ in self.obligations.values():
            if cls not in EVIDENCE_CLASSES:
                raise ClaimAuditError(f"unknown evidence class {cls!r}")
        for c, deps in self.claims.items():
            for d in deps:
                if d not in names:
                    raise ClaimAuditError(f"claim {c!r} depends on unknown {d!r}")
        for name in self.decl_obligations:
            if name not in self.obligations:
                raise ClaimAuditError(f"decl_obligations names unknown obligation {name!r}")
            if self.obligations[name][0] != "lean_kernel":
                raise ClaimAuditError(
                    f"{name!r} is not lean_kernel: only kernel obligations derive from the report")
        for c in self.claim_order:
            if c not in self.claims:
                raise ClaimAuditError(f"claim_order names unknown claim {c!r}")

    @property
    def map_id(self) -> str:
        return content_id("claimmap", {
            "project": self.project, "authors": sorted(self.authors),
            "obligations": {k: list(v) for k, v in sorted(self.obligations.items())},
            "claims": {k: sorted(v) for k, v in sorted(self.claims.items())},
            "claim_order": list(self.claim_order),
            "claim_standing": dict(sorted(self.claim_standing.items())),
            "decl_obligations": {k: sorted(v) for k, v in sorted(self.decl_obligations.items())},
            "clean_axioms": sorted(self.clean_axioms)})


def build_claim_graph(cmap: ClaimMap):
    g = ObligationGraph()
    obl = {name: g.add(Obligation.new(name, evidence_class=cls, evidence_role=role))
           for name, (cls, role) in cmap.obligations.items()}
    for name in cmap.claims:
        obl[name] = g.add(Obligation.new(name, evidence_class="claim"))
    for claim, deps in cmap.claims.items():
        for d in deps:
            g.add_dependency(obl[d].obligation_id, obl[claim].obligation_id)
    return g, obl


def derive_kernel_closure(observations, decl_obligations, clean_axioms=CLEAN_AXIOMS):
    """Closure from what the kernel reported; nothing is asserted. An
    obligation closes iff every declaration it names was observed AND each
    axiom set is within the clean basis."""
    closed, detail = [], {}
    for obligation, decls in sorted(decl_obligations.items()):
        seen = {d: observations.get(d) for d in decls}
        missing = sorted(d for d, ax in seen.items() if ax is None)
        unclean = sorted(d for d, ax in seen.items()
                         if ax is not None and not ax <= clean_axioms)
        ok = not missing and not unclean
        detail[obligation] = {"closed": ok, "missing_declarations": missing,
                              "unclean_declarations": unclean}
        if ok:
            closed.append(obligation)
    return closed, detail


def extracted_snapshot(manifest):
    for f in ("toolchain_id", "mathlib_revision", "lake_manifest_hash"):
        if not manifest.get(f):
            raise ClaimAuditError(f"extracted manifest must record a real {f}")
    src = dict(manifest.get("source_hashes") or {})
    if not src:
        raise ClaimAuditError("extracted manifest must record source_hashes")
    return WorkspaceSnapshot.new(
        source_hashes={"commit": manifest["commit"], **src},
        lake_manifest_hash=manifest["lake_manifest_hash"],
        toolchain_id=manifest["toolchain_id"],
        mathlib_revision=manifest["mathlib_revision"],
        verification_state="release_verified")


def _extracted_seals(cmap, obl, manifest, closed_kernel, snapshot_id, report_hash):
    S = []
    commit = manifest["commit"]
    src = manifest.get("source_hashes") or {}
    subject = next((v for k, v in sorted(src.items())
                    if k.endswith(cmap.kernel_source_suffix)), None)
    if not subject:
        raise ClaimAuditError(
            f"manifest records no hash for a source matching {cmap.kernel_source_suffix!r}")
    common = dict(subject_lineage=cmap.authors, snapshot_id=snapshot_id,
                  evidence_origin="extracted")
    for name in closed_kernel:
        S.append(VerifierSeal.new(
            obl[name].obligation_id, "lean_kernel", "lean-kernel", "formal_kernel",
            source_artifact_hash=subject, output_artifact_hash=report_hash,
            verification_event_id=f"lake-env-lean:{commit}", **common))
    if "release_replay" in obl and (manifest.get("lean") or {}).get("built"):
        S.append(VerifierSeal.new(
            obl["release_replay"].obligation_id, "release_replay", "lake-build",
            "symbolic_script", source_artifact_hash=manifest["lake_manifest_hash"],
            output_artifact_hash=report_hash,
            verification_event_id=f"lake-build:{commit}", **common))
    m2 = manifest.get("macaulay2") or {}
    if "macaulay2_identities" in obl and m2.get("ok"):
        if not m2.get("source_hash") or not m2.get("output_hash"):
            raise ClaimAuditError("macaulay2 block claims ok but records no hashes")
        S.append(VerifierSeal.new(
            obl["macaulay2_identities"].obligation_id, "computer_algebra", "macaulay2",
            "computer_algebra", source_artifact_hash=m2["source_hash"],
            output_artifact_hash=m2["output_hash"],
            verification_event_id=f"m2:{commit}", **common))
    for att in manifest.get("attestations") or []:
        name = att.get("obligation")
        if name not in cmap.obligations:
            raise ClaimAuditError(f"attestation names an unknown obligation: {name!r}")
        cls = cmap.obligations[name][0]
        if cls not in ATTESTED_CLASSES:
            raise ClaimAuditError(
                f"{name!r} is class {cls!r}: only {sorted(ATTESTED_CLASSES)} may be attested")
        if not att.get("checker") or not att.get("checker_class") or not att.get("statement"):
            raise ClaimAuditError(f"attestation for {name!r} must name checker, checker_class, statement")
        S.append(VerifierSeal.new(
            obl[name].obligation_id, cls, att["checker"], att["checker_class"],
            checker_lineage=tuple(att.get("checker_lineage") or ()),
            shared_context=tuple(att.get("shared_context") or ()),
            verification_event_id="sha256:" + hashlib.sha256(
                att["statement"].encode("utf-8")).hexdigest(), **common))
    return S


def summarise(cmap, commit, snap, origin, policy, assessments, graph, id_to_name,
              ledger, extra=None):
    claims = {}
    for cid, a in assessments.items():
        name = graph.get(cid).formal_target
        entry = {"complete": a.complete,
                 "missing_obligations": sorted(id_to_name.get(m, m) for m in a.missing_obligations),
                 "evidence_classes": a.evidence_classes}
        if a.standing:
            if a.evidence_origin == "modelled" and not policy.allow_modelled_release_standing:
                entry["standing"] = "modelled_claim_assessment"
            else:
                entry["standing"] = cmap.claim_standing.get(name, "granted")
        claims[name] = entry
    granted = None
    for name in cmap.claim_order:
        if claims.get(name, {}).get("standing"):
            granted = claims[name]["standing"]
    prof = ledger.independence_profile()
    fk = {f["kind"] for f in ledger.flags()}
    flags = [x for c, x in (("correlated_ai_review", "correlated_ai_review"),
                            ("no_human_expert_review", "external_validation_boundary_open"),
                            ("unknown_ai_checker_lineage", "unknown_ai_checker_lineage"))
             if c in fk]
    out = {"project": cmap.project, "claim_map_id": cmap.map_id, "commit": commit,
           "snapshot_id": snap.snapshot_id, "evidence_origin": origin,
           "policy_id": policy.policy_id, "standing": granted, "claims": claims,
           "independence": {"execution_paths": prof.execution_paths,
                            "external_expert_paths": prof.external_expert_paths,
                            "correlated_ai_groups": prof.correlated_ai_groups},
           "flags": flags}
    out.update(extra or {})
    return out


def audit_manifest(manifest, cmap: ClaimMap, policy=None, *, report_text=None):
    """The generic extracted-evidence audit: observations in, standing out."""
    validate_commit_hash(manifest.get("commit"))
    if "closed_obligations" in manifest:
        raise ClaimAuditError(
            "manifest must not carry closed_obligations: the subject supplies "
            "observations, the verifier derives closure")
    if report_text is None:
        raise ClaimAuditError("extracted audit requires the raw #print axioms report")
    policy = policy or ResearchStandingPolicy()
    observations = parse_axiom_report(report_text)
    if not observations:
        raise ClaimAuditError("axiom report parsed to zero declarations")
    closed_kernel, detail = derive_kernel_closure(
        observations, cmap.decl_obligations, cmap.clean_axioms)
    report_hash = "sha256:" + hashlib.sha256(report_text.encode("utf-8")).hexdigest()

    graph, obl = build_claim_graph(cmap)
    snap = extracted_snapshot(manifest)
    ledger = IndependenceLedger(
        _extracted_seals(cmap, obl, manifest, closed_kernel, snap.snapshot_id, report_hash))
    claim_ids = [obl[k].obligation_id for k in cmap.claims]
    a = assess_research_standing(graph=graph, claim_ids=claim_ids, ledger=ledger,
                                 snapshot_id=snap.snapshot_id, policy=policy)
    id_to_name = {o.obligation_id: n for n, o in obl.items()}
    extra = {"declarations_observed": sorted(observations),
             "kernel_closure": detail, "axioms_report_hash": report_hash}
    return graph, obl, a, summarise(cmap, manifest["commit"], snap, "extracted",
                                    policy, a, graph, id_to_name, ledger, extra=extra)


def read_report(path):
    """Raw report bytes -> text (+bytes). PowerShell `*>` writes UTF-16."""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16"), raw
    return raw.decode("utf-8-sig", errors="replace"), raw
