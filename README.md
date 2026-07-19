# standing-reports

Audits of machine-generated mathematics, published with the evidence that
produced them. Each report states what a body of formal work supports, under
a fixed policy, from committed evidence -- and replays with one command:

```bash
python3 verify.py reports/<report-dir>
```

`verify.py` re-checks the evidence hashes, re-runs the frozen evaluation
engine in `engine/`, and compares the recomputed verdict to the committed
one field by field. A report you cannot replay is a claim, not a report.

## what a standing report is

A subject (a Lean formalization at an exact commit) is extracted on its own
toolchain: the kernel is asked for the axioms of each principal declaration,
and the raw output is committed together with source hashes and toolchain
pins. The manifest carries observations only -- a manifest that states its
own conclusions is refused. A claim map, committed beside the evidence,
fixes the interpretation: which declarations close which obligation, and
which obligations each claim requires. The engine derives closure from the
raw kernel output under that map and evaluates each claim under a fixed
policy. What a kernel cannot decide -- whether a formal statement expresses
the informal claim, whether a result is new, whether an outside expert has
reviewed it -- never closes from the kernel side; it closes only from an
attributed attestation whose full text is hashed into the record, or it
stays open and the verdict says so.

## glossary

- **claim** -- a named assertion under audit (for example: this repository
  formalizes a counterexample of rank four).
- **obligation** -- one requirement in a claim's support: a theorem to be
  present and axiom-clean, a replayed build, a recorded review.
- **extraction** -- running the subject's own build and asking the kernel
  for the axioms of each declaration; the raw output is the evidence.
- **claim map** -- the committed interpretation: declaration-to-obligation
  and obligation-to-claim tables, content-addressed as `claimmap_...`.
- **attestation** -- a recorded, attributed review closing an obligation
  the kernel cannot decide; its statement text is hashed into the record.
- **policy** -- the fixed requirements for standing, content-addressed as
  `policy_...`; a verdict always names the policy it was computed under.
- **standing** -- the level a claim's evidence supports under the policy;
  `null` means the policy's requirements are not met, and the verdict
  lists what is missing.
- **independence** -- a count of distinct paths in the evidence: execution
  paths (different checkers), reviewer lineages (a reviewer sharing the
  subject's authors is counted as correlated, and flagged), and outside
  expert reviews.
- **verdict** -- the engine's output: per-claim standing, kernel closure,
  independence counts, flags, and the identifiers of everything above.

## reports

| subject | commit | standing | note |
|---|---|---|---|
| [grothendieck-rank-four](reports/grothendieck-rank-four-2efab4e3/REPORT.md) | `2efab4e3` | null | two required theorems absent from the source; no attestation can override a missing theorem |
| [grothendieck-rank-four](reports/grothendieck-rank-four-94d662fe/REPORT.md) | `94d662fe` | release_verified | 14/14 declarations axiom-clean; reviewer shares the subject's lineage, flagged as correlated |
| [rs-mca slackMCA_v4](reports/rs-mca-slackmca-v4-3404d21b/REPORT.md) | `3404d21b` | release_verified | 14/14 declarations axiom-clean; reviewer lineage distinct from the subject's, no correlation flag |

No report here carries `externally_validated`: no human expert review is on
record for any of these subjects, and the policy does not let machine
evidence substitute for one. That line moves when a person signs a review,
not before.

## related

[verification-events](https://github.com/manifoldcontrol/verification-events)
defines the event grammar this provenance follows;
[lean-introspect](https://github.com/manifoldcontrol/lean-introspect)
extracts proof-term structure and kernel-transitive axioms;
[csr-seed](https://github.com/manifoldcontrol/csr-seed) pins document and
symbol identity; [fold-registry](https://github.com/manifoldcontrol/fold-registry)
applies the same discipline to one paper's claim table. This repository is
what those pieces are for.
