# bh-fdr-certificate @ arXiv:2607.12208

Subject: the interval-arithmetic certificate in E. Dobriban, "The
Benjamini-Hochberg Procedure Can Fail to Control the FDR for Correlated
Two-Sided Gaussian Tests" (arXiv:2607.12208, July 2026, CC BY 4.0). The
paper constructs a Gaussian factor model for which, at level 1/100, the
false discovery rate exceeds its nominal level in the limit. The final
strict inequality rests on a computational certificate over a rational
grid. The paper states that its proof was produced by one AI system
(GPT-5.6 Pro) and checked by the author.

## verdict

The certificate replicates. A re-implementation of the paper's per-bin
bracket construction, written against its stated formulas with the
published listing consulted for loop-range conventions, reproduces the
certified total exactly:

    0.010416829070473713117472566385250491510...

This matches every published digit and exceeds both the paper's stated
threshold and 1/100 in exact rational comparison.

The evidence in this directory is the replication's artifact: 1000 z-bin
records over [-5, 5], each carrying its threshold bracket and exact
outward rational enclosures for the infeasibility margin, the feasible
point, the FDP lower bound, and the Gaussian bin mass. The committed
verdict is recomputed from those records by exact fraction arithmetic,
with an aggregation independent of the generator's. A recomputation
checker that re-derives any bin with ball arithmetic and requires the
recorded intervals to contain the fresh values ships in
`engine/bh_certificate.py` (`ArbRecheck`); it needs python-flint and
`verify.py` does not run it.

## independence

Two implementation lineages agree digit-for-digit on the certified
value: the paper's certificate (GPT-5.6 Pro, python-flint 0.8.0) and
this one (Claude, python-flint 0.9.0). The algorithm is the same by
construction. Distinct: the authorship, the library version, the
exact-rational extraction of every enclosure, the machine-readable
manifest, and the fraction-only verifier.

## scope and boundary

- Replicated: the computational certificate, meaning the per-bin
  brackets, the strict sign conditions, and the certified sum (the
  paper's Section 6 and Appendix B).
- Reviewed without machine checking: the analytic reduction from the FDR
  to that sum (the paper's bracketing and lower-bound lemmas and the
  limit argument). The implemented formulas follow it; no proof
  assistant has checked it, here or in the paper.
- The contribution of the factor variable outside [-5, 5] is dropped by
  the paper and by this replication. It is nonnegative, so dropping it
  weakens the certified bound and nothing else.
- No human expert review of this replication is on record.

## reproduce

```bash
python3 ../../verify.py .
```

`manifest.json` is the full certificate artifact, exact rationals
throughout, self-hash verified. `verdict.json` is the recomputation
target the command above reproduces field by field.
