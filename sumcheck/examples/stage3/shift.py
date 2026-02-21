"""
Stage 3: Shift

Proves that the "next-step" virtual polynomials (NextUnexpandedPC,
NextPC, NextIsVirtual, NextIsFirstInSequence, NextIsNoop) are
consistent with their non-shifted counterparts via the EqPlusOne
relation.

Source: jolt-core/src/zkvm/shift/mod.rs
Spec:   references/stage3.md § Shift
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Pow, VerifierPoly,
    vp, eq, add, sub,
)
from ...spec import SumcheckSpec


def stage3_shift() -> SumcheckSpec:
    X_j = Var("X_j", DIM_CYCLE)
    r1_cycle = Opening(1, DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
    gamma = Const("γ")

    eq_plus_one_1 = VerifierPoly("EqPlusOne_tilde", [r1_cycle, X_j])
    eq_plus_one_2 = VerifierPoly("EqPlusOne_tilde", [r2_cycle, X_j])

    # 5 polynomials batched with γ:
    # EqPlusOne(r1, X_j) · (UnexpPC + γ·PC + γ²·IsVirtual + γ³·IsFirstInSeq)
    # + γ⁴ · EqPlusOne(r2, X_j) · (1 - IsNoop)
    batch1 = add(
        vp("UnexpandedPC", X_j),
        Mul(gamma, vp("PC", X_j)),
        Mul(Pow(gamma, 2), vp("OpFlags(VirtualInstruction)", X_j)),
        Mul(Pow(gamma, 3), vp("OpFlags(IsFirstInSequence)", X_j)),
    )

    integrand = add(
        Mul(eq_plus_one_1, batch1),
        Mul(Pow(gamma, 4), Mul(eq_plus_one_2, sub(Const(1), vp("InstructionFlags(IsNoop)", X_j)))),
    )

    rhs = add(
        vp("NextUnexpandedPC", r1_cycle),
        Mul(gamma, vp("NextPC", r1_cycle)),
        Mul(Pow(gamma, 2), vp("NextIsVirtual", r1_cycle)),
        Mul(Pow(gamma, 3), vp("NextIsFirstInSequence", r1_cycle)),
        Mul(Pow(gamma, 4), sub(Const(1), vp("NextIsNoop", r2_cycle))),
    )

    return SumcheckSpec(
        name="Shift",
        sum_vars=[X_j],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(3, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("UnexpandedPC",                [Opening(3, DIM_CYCLE)]),
            ("PC",                          [Opening(3, DIM_CYCLE)]),
            ("OpFlags(VirtualInstruction)",  [Opening(3, DIM_CYCLE)]),
            ("OpFlags(IsFirstInSequence)",   [Opening(3, DIM_CYCLE)]),
            ("InstructionFlags(IsNoop)",     [Opening(3, DIM_CYCLE)]),
        ],
    )
