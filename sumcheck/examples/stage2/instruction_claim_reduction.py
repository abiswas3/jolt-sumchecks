"""
Stage 2: Instruction Claim Reduction

Aggregates 3 instruction lookup claims into a single opening
point using γ-batching.

    Σ_{X_j} eq(r_cycle^(1), X_j)
      · (LookupOutput + γ · LeftLookupOp + γ² · RightLookupOp)
    = LookupOutput(r^(1)) + γ · LeftLookupOp(r^(1))
      + γ² · RightLookupOp(r^(1))

Source: jolt-core/src/zkvm/instruction_lookups/claim_reduction.rs
Spec:   references/stage2.md § Instruction Claim Reduction
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Pow,
    vp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage2_instruction_claim_reduction() -> SumcheckSpec:
    X_j = Var("X_j", DIM_CYCLE)
    r_cycle = Opening(1, DIM_CYCLE)
    gamma = Const("γ")

    lookup   = vp("LookupOutput", X_j)
    left_op  = vp("LeftLookupOperand", X_j)
    right_op = vp("RightLookupOperand", X_j)

    # LookupOutput + γ · LeftLookupOp + γ² · RightLookupOp
    batch = add(
        lookup,
        Mul(gamma, left_op),
        Mul(Pow(gamma, 2), right_op),
    )

    integrand = Mul(verifier.eq(r_cycle, X_j), batch)

    rhs = add(
        vp("LookupOutput", r_cycle),
        Mul(gamma, vp("LeftLookupOperand", r_cycle)),
        Mul(Pow(gamma, 2), vp("RightLookupOperand", r_cycle)),
    )

    return SumcheckSpec(
        name="InstructionClaimReduction",
        sum_vars=[X_j],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(2, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("LookupOutput",       [Opening(2, DIM_CYCLE)]),
            ("LeftLookupOperand",   [Opening(2, DIM_CYCLE)]),
            ("RightLookupOperand",  [Opening(2, DIM_CYCLE)]),
            ("LeftInstructionInput", [Opening(2, DIM_CYCLE)]),
            ("RightInstructionInput",[Opening(2, DIM_CYCLE)]),
        ],
    )
