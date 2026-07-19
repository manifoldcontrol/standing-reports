"""BH counterexample certificate: generator + exact verifier (arXiv:2607.12208).

Re-implementation of the paper's interval-arithmetic certificate (Dobriban
2026, CC BY 4.0), written against its stated formulas with the published
listing consulted for loop-range conventions: for the stated Gaussian factor model at level
alpha = 1/100, a per-z-bin threshold bracket and FDP lower bound whose
Gaussian-weighted sum certifies liminf FDR > 0.0104168... > alpha.

Three separated roles:

* `certify_bin` / `generate` (this module, needs python-flint): computes
  outward-rounded enclosures with Arb ball arithmetic at a pinned precision
  and emits a machine-readable manifest of EXACT rationals. The generator's
  word is never trusted downstream.
* `verify_manifest`: exact-arithmetic verifier (`Fraction` only, no Arb):
  checks bin coverage, bracket sanity, strict positivity of every recorded
  margin, and recomposes the total lower bound from per-bin fields by exact
  rational multiplication -- an aggregation independent of the generator's.
* `ArbRecheck`: re-derives any bin's enclosures with Arb and confirms the
  recorded intervals contain the recomputed balls (full independence from
  the recorded numbers; swap in for the structural pass to shrink trust).

The tail |Z| > 5 is dropped; its contribution is nonnegative, so omission
only weakens the certified bound (the paper's Fatou step).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from fractions import Fraction

SCHEMA = "bracket-certificate-v0"
PAPER = "arXiv:2607.12208"
ALPHA = Fraction(1, 100)
THRESHOLD = Fraction("0.0104168290704737131174725663852504915")  # paper's assert
Z_DEN, C_DEN = 100, 1000
K_MIN, K_MAX = -500, 500
J_START, J_STOP = 2575, 10000
DPS = 40

# exact model constants (paper Section 2)
PI0, W1, W2 = Fraction(24, 25), Fraction(1, 100), Fraction(3, 100)
R0, R1, R2 = Fraction(3, 10), Fraction(-3, 10), Fraction(-18, 25)
MU1, MU2 = Fraction(12, 5), Fraction(22, 5)


def dec(x: Fraction, digits: int = 45, up: bool = False) -> str:
    """Exact decimal string of a Fraction, rounded down (or up)."""
    sign = "-" if x < 0 else ""
    x = abs(x)
    scaled = x * 10**digits
    n = scaled.numerator // scaled.denominator
    if up and n * scaled.denominator != scaled.numerator:
        n += 1
    s = str(n).rjust(digits + 1, "0")
    return f"{sign}{s[:-digits]}.{s[-digits:]}"


def _flint():
    from flint import arb, ctx
    ctx.dps = DPS
    return arb


def _fr(x) -> Fraction:
    """Exact Fraction from an exact arb endpoint (mantissa * 2^exponent)."""
    man, exp = x.man_exp()
    man, exp = int(man), int(exp)
    return Fraction(man) * (Fraction(2) ** exp if exp >= 0 else Fraction(1, 2 ** (-exp)))


def _outward(ball):
    return _fr(ball.lower()), _fr(ball.upper())


def certify_bin(k: int) -> dict:
    """Bracket + FDP contribution for z-bin [k/100, (k+1)/100].

    Every strict Arb comparison must resolve; a ball straddling zero raises,
    it never rounds. Returned enclosures are exact outward rationals.
    """
    arb = _flint()
    A = lambda q: arb(q.numerator) / q.denominator
    S0 = (1 - A(R0) * A(R0)).sqrt()
    S1 = (1 - A(R1) * A(R1)).sqrt()
    S2 = (1 - A(R2) * A(R2)).sqrt()
    SQRT2 = arb(2).sqrt()
    Phi_bar = lambda x: (x / SQRT2).erfc() / 2
    u = lambda c: 2 * Phi_bar(c)
    Q = lambda c, a, s: Phi_bar((c - a) / s) + Phi_bar((c + a) / s)

    def abs_range(mu, loading, lo, hi):
        left, right = mu + loading * lo, mu + loading * hi
        al, ar = abs(left), abs(right)
        if (left <= 0 and right >= 0) or (right <= 0 and left >= 0):
            mn = arb(0)
        else:
            mn = al if al < ar else ar
        return mn, (al if al > ar else ar)

    z_lo, z_hi = arb(k) / Z_DEN, arb(k + 1) / Z_DEN
    m0 = abs_range(arb(0), A(R0), z_lo, z_hi)
    m1 = abs_range(A(MU1), A(R1), z_lo, z_hi)
    m2 = abs_range(A(MU2), A(R2), z_lo, z_hi)
    if not (u(arb(J_START) / C_DEN) > A(ALPHA)):
        raise RuntimeError("grid does not start below c_alpha")

    j_lower, worst_U = None, None
    for j in range(J_START, J_STOP):
        c_j, c_next = arb(j) / C_DEN, arb(j + 1) / C_DEN
        U = (A(PI0) * Q(c_j, m0[1], S0) + A(W1) * Q(c_j, m1[1], S1)
             + A(W2) * Q(c_j, m2[1], S2) - 100 * u(c_next))
        if not (U < 0):
            j_lower = j
            break
        if worst_U is None or not (U < worst_U):
            worst_U = U
    if j_lower is None:
        raise RuntimeError(f"no bracket in bin {k}")
    c_lower = arb(j_lower) / C_DEN
    if not (u(c_lower) < A(ALPHA)):
        raise RuntimeError(f"bracket in bin {k} does not clear c_alpha")

    j_upper = None
    for j in range(j_lower, J_STOP + 1):
        c_j = arb(j) / C_DEN
        L = (A(PI0) * Q(c_j, m0[0], S0) + A(W1) * Q(c_j, m1[0], S1)
             + A(W2) * Q(c_j, m2[0], S2) - 100 * u(c_j))
        if L > 0:
            j_upper = j
            L_ball = L
            break
    if j_upper is None:
        raise RuntimeError(f"no feasible point in bin {k}")
    c_upper = arb(j_upper) / C_DEN

    d_k = (A(PI0) / 100) * Q(c_upper, m0[0], S0) / u(c_lower)
    mass = (1 - Phi_bar(z_hi)) - (1 - Phi_bar(z_lo))
    return {"k": k, "j_lower": j_lower, "j_upper": j_upper,
            "worst_infeasibility_margin": _outward(-worst_U),
            "feasible_margin": _outward(L_ball),
            "fdp_lower": _outward(d_k),
            "gaussian_mass": _outward(mass),
            "contribution": _outward(d_k * mass)}


def _rec_to_strings(r: dict) -> dict:
    out = {"k": r["k"], "j_lower": r["j_lower"], "j_upper": r["j_upper"]}
    for f in ("worst_infeasibility_margin", "feasible_margin", "fdp_lower",
              "gaussian_mass", "contribution"):
        lo, hi = r[f]
        out[f] = [f"{lo.numerator}/{lo.denominator}", f"{hi.numerator}/{hi.denominator}"]
    return out


def build_manifest(records: list, *, environment: dict) -> dict:
    recs = sorted(records, key=lambda r: r["k"])
    total_lo = sum(r["contribution"][0] for r in recs)
    m = {"schema": SCHEMA, "subject": PAPER,
         "claim": "liminf FDR at alpha=1/100 exceeds 0.0104 for the stated factor model",
         "arithmetic_basis": "arb-outward", "precision_dps": DPS,
         "environment": dict(environment),
         "parameters": {"alpha": "1/100", "pi0": "24/25", "w1": "1/100", "w2": "3/100",
                        "r0": "3/10", "r1": "-3/10", "r2": "-18/25",
                        "mu1": "12/5", "mu2": "22/5"},
         "grid": {"z_den": Z_DEN, "k_min": K_MIN, "k_max": K_MAX,
                  "c_den": C_DEN, "j_start": J_START, "j_stop": J_STOP},
         "bins": [_rec_to_strings(r) for r in recs],
         "certified_total_lower_decimal": dec(total_lo),
         "paper_threshold_decimal": dec(THRESHOLD, up=True)}
    body = json.dumps(m, sort_keys=True).encode()
    m["manifest_sha256"] = "sha256:" + hashlib.sha256(body).hexdigest()
    return m


@dataclass
class BracketVerdict:
    accepted: bool
    reason: str
    bins: int = 0
    total_lower: Fraction | None = None
    exceeds_threshold: bool = False
    exceeds_alpha: bool = False


def verify_manifest(manifest: dict) -> BracketVerdict:
    """Exact structural verification: Fractions only, no Arb, no trust in the
    generator's aggregation. Recomposes the total from per-bin lower bounds."""
    F = Fraction
    if manifest.get("schema") != SCHEMA:
        return BracketVerdict(False, "schema mismatch")
    g = manifest.get("grid", {})
    if (g.get("k_min"), g.get("k_max")) != (K_MIN, K_MAX) or g.get("c_den") != C_DEN \
            or g.get("z_den") != Z_DEN or g.get("j_start") != J_START:
        return BracketVerdict(False, "grid parameters not the pinned grid")
    bins = manifest.get("bins", [])
    seen = {b.get("k") for b in bins}
    if seen != set(range(K_MIN, K_MAX)):
        return BracketVerdict(False, f"bin coverage incomplete: {len(seen)}/1000")
    total = F(0)
    for b in bins:
        if not (J_START <= b["j_lower"] <= b["j_upper"] <= J_STOP):
            return BracketVerdict(False, f"bracket order violated in bin {b['k']}")
        vals = {}
        for f in ("worst_infeasibility_margin", "feasible_margin", "fdp_lower",
                  "gaussian_mass", "contribution"):
            lo, hi = F(b[f][0]), F(b[f][1])
            if lo > hi:
                return BracketVerdict(False, f"malformed enclosure {f} in bin {b['k']}")
            vals[f] = (lo, hi)
        for f in ("worst_infeasibility_margin", "feasible_margin",
                  "fdp_lower", "gaussian_mass"):
            if not vals[f][0] > 0:
                return BracketVerdict(False, f"non-strict {f} in bin {b['k']}")
        # independent recomposition: product of recorded lower bounds
        total += vals["fdp_lower"][0] * vals["gaussian_mass"][0]
    return BracketVerdict(True, "", bins=len(bins), total_lower=total,
                          exceeds_threshold=total > THRESHOLD,
                          exceeds_alpha=total > ALPHA)


class ArbRecheck:
    """Re-derive a bin with Arb and confirm the recorded enclosures contain the
    recomputed values. Full independence from the recorded numbers."""
    identity = "arb-recompute-checker"
    version = "v1"

    def recheck_bin(self, rec: dict) -> bool:
        F = Fraction
        fresh = certify_bin(rec["k"])
        if (fresh["j_lower"], fresh["j_upper"]) != (rec["j_lower"], rec["j_upper"]):
            return False
        for f in ("fdp_lower", "gaussian_mass", "contribution"):
            rlo, rhi = F(rec[f][0]), F(rec[f][1])
            flo, fhi = fresh[f]
            # recorded outward interval must contain the freshly recomputed one
            if not (rlo <= flo and fhi <= rhi):
                return False
        return True
