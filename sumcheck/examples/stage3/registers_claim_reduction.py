"""
Stage 3: Registers Claim Reduction

Batches the three register-value claims (RdWriteValue, Rs1Value,
Rs2Value) into a single opening point using γ-batching.

Source: jolt-core/src/zkvm/registers/claim_reduction.rs
Spec:   references/stage3.md § RegistersClaimReduction
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Pow,
    vp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage3_registers_claim_reduction() -> SumcheckSpec:
    X_j = Var("X_j", DIM_CYCLE)
    r1_cycle = Opening(1, DIM_CYCLE)
    gamma = Const("γ")

    batch = add(
        vp("RdWriteValue", X_j),
        Mul(gamma, vp("Rs1Value", X_j)),
        Mul(Pow(gamma, 2), vp("Rs2Value", X_j)),
    )

    integrand = Mul(verifier.eq(r1_cycle, X_j), batch)

    rhs = add(
        vp("RdWriteValue", r1_cycle),
        Mul(gamma, vp("Rs1Value", r1_cycle)),
        Mul(Pow(gamma, 2), vp("Rs2Value", r1_cycle)),
    )

    return SumcheckSpec(
        name="RegistersClaimReduction",
        sum_vars=[X_j],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(3, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("RdWriteValue", [Opening(3, DIM_CYCLE)]),
            ("Rs1Value",     [Opening(3, DIM_CYCLE)]),
            ("Rs2Value",     [Opening(3, DIM_CYCLE)]),
        ],
    )
