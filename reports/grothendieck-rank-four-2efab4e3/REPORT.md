# grothendieck-rank-four @ 2efab4e3

Subject: `j2d9w5xtjn-png/GrothendieckRankP2` at commit
`2efab4e3f877851594da5d2af08534182ca33979`, a Lean 4 formalization of a
rank-four finite locally free group scheme that is not killed by four,
addressing Grothendieck's question whether every finite locally free
group scheme of order n is annihilated by n. The repository states that
its contents were produced by AI systems (Codex, Claude).

## verdict

Standing: **null** under policy `policy_08a0946eaffe` and claim map
`claimmap_246c7652800c`. The evidence does not support the counterexample
claims at this commit.

Every declaration the kernel was asked about is axiom-clean: 10 of 10,
each depending only on `propext`, `Classical.choice`, `Quot.sound`.
Standing is withheld because two required obligations cannot close. The
declarations that would close them, a noncocommutativity theorem and a
categorical power-map theorem, are absent from the source at this commit.
Kernel closure: 6 of 8.

Obligations of this kind close only from kernel evidence; the engine
refuses attestations that name them.

## boundary

- The verdict concerns this commit's source. A later commit of the same
  repository adds both missing results; see the companion report at
  `94d662fe`.
- Independence: one execution path (the Lean kernel), no outside expert
  review on record.

## reproduce

```bash
python3 ../../verify.py .
```

Evidence: `manifest.json` (observations: commit, toolchain, source
hashes), `pinned_report.txt` (raw kernel output, hash-pinned by the
manifest), `claim_map.json` (the interpretation, content-addressed),
`verdict.json` (the engine's output, replayed by the command above).
