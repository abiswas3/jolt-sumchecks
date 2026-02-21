"""
Stage 3: Instruction Input

Proves that LeftInstructionInput and RightInstructionInput are
derived from the correct operand sources (Rs1, Rs2, Imm, PC)
based on the instruction flags.

Source: jolt-core/src/zkvm/instruction_input/mod.rs
Spec:   references/stage3.md § InstructionInput
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, Mul, Pow,
    vp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage3_instruction_input() -> SumcheckSpec:
    X_j = Var("X_j", DIM_CYCLE)
    r1_cycle = Opening(1, DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
    gamma = Const("γ")

    # eq(r1, X_j) · (IsRs2·Rs2 + IsImm·Imm + γ·(IsRs1·Rs1 + IsPC·UnexpPC))
    # + γ² · eq(r2, X_j) · same_thing
    right_operand = add(
        Mul(vp("InstructionFlags(RightOperandIsRs2Value)", X_j), vp("Rs2Value", X_j)),
        Mul(vp("InstructionFlags(RightOperandIsImm)", X_j), vp("Imm", X_j)),
    )
    left_operand = add(
        Mul(vp("InstructionFlags(LeftOperandIsRs1Value)", X_j), vp("Rs1Value", X_j)),
        Mul(vp("InstructionFlags(LeftOperandIsPC)", X_j), vp("UnexpandedPC", X_j)),
    )
    poly_block = add(right_operand, Mul(gamma, left_operand))

    integrand = Mul(
        add(verifier.eq(r1_cycle, X_j), Mul(Pow(gamma, 2), verifier.eq(r2_cycle, X_j))),
        poly_block,
    )

    rhs = add(
        vp("RightInstructionInput", r1_cycle),
        Mul(gamma, vp("LeftInstructionInput", r1_cycle)),
        Mul(Pow(gamma, 2), vp("RightInstructionInput", r2_cycle)),
        Mul(Pow(gamma, 3), vp("LeftInstructionInput", r2_cycle)),
    )

    return SumcheckSpec(
        name="InstructionInput",
        sum_vars=[X_j],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(3, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("InstructionFlags(LeftOperandIsRs1Value)",   [Opening(3, DIM_CYCLE)]),
            ("Rs1Value",                                  [Opening(3, DIM_CYCLE)]),
            ("InstructionFlags(LeftOperandIsPC)",          [Opening(3, DIM_CYCLE)]),
            ("UnexpandedPC",                              [Opening(3, DIM_CYCLE)]),
            ("InstructionFlags(RightOperandIsRs2Value)",   [Opening(3, DIM_CYCLE)]),
            ("Rs2Value",                                  [Opening(3, DIM_CYCLE)]),
            ("InstructionFlags(RightOperandIsImm)",        [Opening(3, DIM_CYCLE)]),
            ("Imm",                                       [Opening(3, DIM_CYCLE)]),
        ],
    )
