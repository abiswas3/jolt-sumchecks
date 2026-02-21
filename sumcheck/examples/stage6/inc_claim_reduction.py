"""
Stage 6: Inc Claim Reduction

Batches the RamInc and RdInc increment polynomials at multiple
cycle points into a single fresh opening.

    Σ_{X_t} RamInc · (eq(r2, X_t) + γ·eq(r4, X_t))
           + γ² · RdInc · (eq(r4, X_t) + γ·eq(r5, X_t))
    = RamInc(r2) + γ·RamInc(r4) + γ²·RdInc(r4) + γ³·RdInc(r5)

Source: jolt-core/src/zkvm/inc/claim_reduction.rs
Spec:   references/stage6.md § IncClaimReduction
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Pow,
    cp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage6_inc_claim_reduction() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
    r4_cycle = Opening(4, DIM_CYCLE)
    r5_cycle = Opening(5, DIM_CYCLE)
    gamma = Const("γ")

    ram_inc = cp("RamInc", X_t)
    rd_inc  = cp("RdInc", X_t)

    # RamInc · (eq(r2, X_t) + γ·eq(r4, X_t))
    # + γ² · RdInc · (eq(r4, X_t) + γ·eq(r5, X_t))
    integrand = add(
        Mul(ram_inc, add(verifier.eq(r2_cycle, X_t), Mul(gamma, verifier.eq(r4_cycle, X_t)))),
        Mul(Pow(gamma, 2), Mul(rd_inc, add(verifier.eq(r4_cycle, X_t), Mul(gamma, verifier.eq(r5_cycle, X_t))))),
    )

    rhs = add(
        cp("RamInc", r2_cycle),
        Mul(gamma, cp("RamInc", r4_cycle)),
        Mul(Pow(gamma, 2), cp("RdInc", r4_cycle)),
        Mul(Pow(gamma, 3), cp("RdInc", r5_cycle)),
    )

    return SumcheckSpec(
        name="IncClaimReduction",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(6, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("RamInc", [Opening(6, DIM_CYCLE)]),
            ("RdInc",  [Opening(6, DIM_CYCLE)]),
        ],
    )
