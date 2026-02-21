"""
Stage 5: Registers Val Evaluation

Proves that RegistersVal is consistent with the register
increments via a less-than ordering check.

    Σ_{X_t} RdInc(X_t) · RdWa(r4_K, X_t) · LT(X_t, r4_cycle)
    = RegistersVal(r4_K, r4_cycle)

Source: jolt-core/src/zkvm/registers/val_evaluation.rs
Spec:   references/stage5.md § RegistersValEvaluation
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_REG
from ...ast import (
    Mul, VerifierPoly,
    vp, cp,
)
from ...spec import SumcheckSpec


def stage5_registers_val_evaluation() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r4_cycle = Opening(4, DIM_CYCLE)
    r4_k_reg = Opening(4, DIM_K_REG)

    rd_inc = cp("RdInc", X_t)
    rd_wa  = vp("RdWa", r4_k_reg, X_t)
    lt     = VerifierPoly("LT_tilde", [X_t, r4_cycle])

    # RdInc(X_t) · RdWa(r4_K, X_t) · LT(X_t, r4_cycle)
    integrand = Mul(Mul(rd_inc, rd_wa), lt)

    rhs = vp("RegistersVal", r4_k_reg, r4_cycle)

    return SumcheckSpec(
        name="RegistersValEvaluation",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(5, DIM_CYCLE)],
        rounds="log2(T)",
        degree=3,
        openings=[
            ("RdInc", [Opening(5, DIM_CYCLE)]),
            ("RdWa",  [r4_k_reg, Opening(5, DIM_CYCLE)]),
        ],
    )
