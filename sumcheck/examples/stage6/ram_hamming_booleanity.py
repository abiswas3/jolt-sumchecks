"""
Stage 6: RAM Hamming Booleanity

This is the simplest sumcheck in Jolt — it proves that the RAM
hamming-weight polynomial H is boolean-valued (H ∈ {0,1} at
every point on the hypercube).

The booleanity trick: p is boolean iff p^2 - p = 0.
So we prove:

    Σ_{X_t ∈ {0,1}^{log T}}  eq(r_cycle, X_t) · (H(X_t)^2 - H(X_t))  =  0

Degree: eq(1) × (H^2 - H)(2) = 3

Source: jolt-core/src/zkvm/ram/hamming_booleanity.rs
Spec:   references/stage6.md § RamHammingBooleanitySumcheck
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Add, Pow, Neg,
    vp,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage6_ram_hamming_booleanity() -> SumcheckSpec:
    # The single free variable: cycle/timestep
    X_t = Var("X_t", DIM_CYCLE)

    # The eq selector binds to the cycle point from Stage 1
    r_cycle = Opening(1, DIM_CYCLE)

    # The polynomial being checked for booleanity
    H = vp("RamHammingWeight", X_t)

    # Build the integrand:  eq(r, X_t) · (H^2 - H)
    integrand = Mul(verifier.eq(r_cycle, X_t), Add(Pow(H, 2), Neg(H)))

    return SumcheckSpec(
        name="RamHammingBooleanity",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=Const(0),           # RHS is zero (booleanity check)
        opening_point=[Opening(6, DIM_CYCLE)],
        rounds="log2(T)",
        degree=3,
        openings=[
            # After the sumcheck, H is opened at the fresh cycle point
            ("RamHammingWeight", [Opening(6, DIM_CYCLE)]),
        ],
    )
