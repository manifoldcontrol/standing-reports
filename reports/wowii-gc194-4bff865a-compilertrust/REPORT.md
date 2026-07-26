# wowii-gc194 @ 4bff865a — companion verdict, enumerated compiler-trust basis

This directory commits the companion verdict for the subject of
`../wowii-gc194-4bff865a/` (read that report first; the subject, evidence
bytes, manifest, and adequacy attestation are identical). One declared
difference: the claim map's clean basis is the classical trio PLUS the two
axioms the extraction observed on every theorem —

    Lean.ofReduceBool, Lean.trustCompiler

— the compiler-trust axioms minted by the subject's five `native_decide`
steps. Under this named wider basis the four kernel obligations close and
both mathematical claims reach `release_verified_compiler_trust`.

The label carries the basis on purpose. What this verdict says: at the
pin, the counterexample and the `answer(False)` refutation are
kernel-accepted, statement-adequate (recorded attestation, reviewer
lineage disjoint from the subject's), and release-replayed, with a
trusted base of the Lean kernel PLUS Lean's compiled native evaluator.
What it does not say: `release_verified` under the classical trio — that
is exactly what the primary report withholds, with the six theorems
named. No human expert review is on record; the external-validation
boundary is open under both bases.

## reproduce

```bash
python3 ../../verify.py .
```

Same evidence bytes as the primary directory; `claim_map.json` here is
the companion map (`claimmap_13a4cffb22fc`) whose `clean_axioms` field is
the only interpretive change, and `verdict.json` is recomputed field by
field by the command above.
