# wowii-gc194 @ 4bff865a

Subject: the disproof of Written on the Wall II Graph Conjecture 194
(E. DeLaVina's Graffiti.pc catalogue) proposed to
google-deepmind/formal-conjectures in PR #4542. The kernel proofs live in
the author's fork (`anagnorisis2peripeteia/formal-conjectures`) at commit
`4bff865a14c2cd61fefbffbe9c49cbfc5a89ac45`; the upstream PR flips the
conjecture to `answer(False)` and links that pin as its `formal_proof`.
The PR discloses that the work was produced with two AI systems (GPT-5.6
Thinking and Codex). The counterexample is an 18-vertex graph: an
11-clique, four vertices adjacent to every clique vertex, and three
leaves; it satisfies the conjecture's hypothesis with equality and has no
Hamiltonian path because its three leaves would all need to be endpoints
of one.

## verdict

Standing is withheld under this report's policy, and the reason is the
finding: every theorem in the subject rests on Lean's compiler-trust
axioms. The kernel reports, for all six theorems (connectivity,
independence number 4, neighborhood-independence sum 54, average 3, no
Hamiltonian path, and the assembled `answer(False)` equivalence):

    [propext, Classical.choice, Lean.ofReduceBool, Lean.trustCompiler, Quot.sound]

`Lean.ofReduceBool` and `Lean.trustCompiler` enter through the five
`native_decide` calls in the file: those steps are checked by Lean's
compiled native evaluator, not by kernel reduction, so the trusted base of
this disproof includes the Lean compiler. The graph definition itself
(`counterexample`) depends on no axioms. This report's clean basis is the
classical trio (`propext`, `Classical.choice`, `Quot.sound`), the same
basis this project's own retention gate enforces, so all four kernel
obligations refuse with the theorems named; the committed verdict is that
refusal. Nothing here asserts an error in the mathematics: a recorded
semantic-adequacy review (reviewer lineage disjoint from the subject's)
verified the construction against its stated properties, re-derived the
docstring arithmetic (independence number 4; neighborhood sum
54 = 44 + 7 + 3; average 3; hypothesis with equality), and confirmed the
`answer(False)` statement internalizes the upstream open-form conjecture,
with one refutation-safe narrowing noted (`Type` for upstream's `Type*`).

A companion verdict under the enumerated wider basis — the trio plus the
two observed compiler-trust axioms — is committed beside this one
(`../wowii-gc194-4bff865a-compilertrust/`). Under that named basis the
kernel legs close and both mathematical claims reach
`release_verified_compiler_trust`. The label carries the basis on
purpose: a verdict under a wider trust base does not wear the narrower
label.

## independence

The subject's disclosed lineage is GPT-5.6 Thinking + Codex. The
semantic-adequacy reviewer's lineage (claude) is disjoint from it, so the
review counts as an uncorrelated AI cognitive path and no correlation
flag is raised. One deterministic execution path (the Lean kernel plus,
for the flagged steps, its compiled evaluator) produced the formal
evidence. No human expert review of the subject or of this audit is on
record; the external-validation boundary is open, and machine evidence
does not substitute for it under this policy.

## scope and boundary

- Audited: the seven public declarations of the pinned file, their
  kernel-transitive axiom sets from the raw `#print axioms` report
  committed here, and the semantic adequacy of the statements against
  the repository's own conjecture rendering and docstring.
- The refutation logic outside `native_decide` is small and was reviewed:
  the leaf-endpoint lemma is decision-procedure-free walk combinatorics;
  the final assembly instantiates the counterexample and discharges the
  hypothesis numerically.
- Out of scope: whether the repository's formalization faithfully renders
  DeLaVina's original catalogue entry (the subject under audit is the PR
  against the repository's formalization; the catalogue URL did not
  resolve at review time), and the PR body's stronger two-parameter
  family, which is not among the pinned file's public declarations.
- The upstream PR-head commit and statement-file hash are recorded in
  `manifest.json` under `upstream`, so a later force-push of the PR is
  visible as a hash change.

## reproduce

```bash
python3 ../../verify.py .
```

`manifest.json` carries observations only (pins, source hashes, the raw
report's hash, the upstream statement anchor) plus the recorded adequacy
attestation; `wowii_report.txt` is the raw kernel output; `claim_map.json`
is the committed interpretation; `verdict.json` is recomputed field by
field by the command above.
