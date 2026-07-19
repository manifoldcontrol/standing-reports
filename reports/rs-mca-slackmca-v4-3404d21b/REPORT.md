# rs-mca slackMCA_v4 @ 3404d21b

Subject: the Lean 4 package `experimental/lean/slackMCA_v4` in
`przchojecki/rs-mca` at commit `3404d21b64c876c6d9b995ad3e29d7120ab27a54`
-- a formalization of the finitary core of a paper on list decoding of
Reed-Solomon codes on smooth multiplicative domains. Authors of the
formalization, per the repository's log: drafted by one AI system
(Aristotle/Harmonic), reviewed and packaged by another (Codex).

## verdict

The evidence supports both mathematical claims. Standing:
**release_verified** for the Part I entropy claim (locator fibers,
coefficient pigeonhole, quotient cores, inverse quotient, fiber and
entropy bounds) and the Part II rigidity claim (cyclotomic and
Fermat-field rigidity, one bad parameter per support), under policy
`policy_08a0946eaffe` and claim map `claimmap_d58819dd2f37`.

All 14 declarations are axiom-clean (each depending only on `propext`,
`Classical.choice`, `Quot.sound`), extracted on the repository's own
toolchain (Lean 4.28.0, its pinned mathlib). Kernel closure: 11 of 11.
This independently reproduces, from the kernel, the repository's own
statement that its main theorems depend only on the standard axioms.

The semantic-adequacy obligation is closed by a recorded attestation: a
statement-level comparison of the paper's labeled theorems against the
Lean source, definitional roots first, verifying among other things that
the formalized decoding list, monomial-prefix words, and bad-parameter
predicate are the paper's objects, and that every divergence found is a
generalization rather than a weakening. Five residuals are named in the
attestation; none is required by the two claims.

## flags and boundary

- No correlation flag: the adequacy reviewer's lineage (Claude) is
  distinct from the subject's authors (Aristotle, Codex). The verdict
  counts this review as an independent path.
- `external_validation_boundary_open`: no human expert review of this
  package is on record anywhere, and the corresponding claim's standing
  is null.
- Independence: one execution path (the Lean kernel).

## reproduce

```bash
python3 ../../verify.py .
```

Evidence: `manifest.json`, `slackmca_report.txt` (raw kernel output,
hash-pinned), `claim_map.json`, `verdict.json`.
