# grothendieck-rank-four @ 94d662fe

Subject: `j2d9w5xtjn-png/GrothendieckRankP2` at commit
`94d662fee6ddf6806d425c93c2ed8239e3f90463` -- the same repository as the
companion report at `2efab4e3`, at a later commit that adds the two
previously missing results. Authors of the formalization: AI systems
(Codex, Claude), per the repository's own statement.

## verdict

The evidence supports the two mathematical claims at this commit.
Standing: **release_verified** for the Hopf-algebra counterexample claim
and the group-scheme counterexample claim, under policy
`policy_08a0946eaffe` and claim map `claimmap_246c7652800c`.

All 14 declarations are axiom-clean (each depending only on `propext`,
`Classical.choice`, `Quot.sound`), including the noncocommutativity
theorem and the categorical power-map theorem absent at the earlier
commit. Kernel closure: 8 of 8. The semantic-adequacy obligation --
whether the formal statements express the manuscript's claim -- is closed
by a recorded attestation: a statement-level review of the manuscript
theorem against the Lean source, definitional roots first, with its full
text hashed into the record.

## flags and boundary

- `correlated_ai_review`: the adequacy reviewer's lineage (Claude)
  overlaps the subject's authors (Codex, Claude). The review is recorded
  and its content stands, and the verdict counts it as a correlated path,
  not an independent one.
- `external_validation_boundary_open`: no human expert review is on
  record. The claim "externally validated" is a separate claim here, and
  its standing is null.
- Independence: one execution path; a second checker (computer algebra)
  has not been run against this evidence.

## reproduce

```bash
python3 ../../verify.py .
```

Evidence: `manifest.json`, `later_report.txt` (raw kernel output,
hash-pinned), `claim_map.json`, `verdict.json`.
