"""
Stage 1: SpartanOuter

This is the FIRST and most complex sumcheck in Jolt.  It proves
that the entire execution trace satisfies all 19 R1CS constraints
(plus 1 zero-padded) in a single batched sumcheck.

The integrand has a fixed structure:

    eq((τ_t, τ_b), (X_t, X_b)) · L_{τ_c}(X_c) · Az(X_t,X_b,X_c) · Bz(X_t,X_b,X_c)

Three summation axes:
  X_t ∈ {0,1}^{log₂ T}  — cycle (which timestep)
  X_b ∈ {0,1}           — group selector (two constraint groups)
  X_c ∈ {-5, ..., 4}    — constraint index within group

eq is the standard multilinear Lagrange basis over (X_t, X_b).
L_{τ_c} is a UNIVARIATE Lagrange interpolant over the 10-element
domain {-5,...,4} — this is the "univariate skip" optimisation.

Az and Bz are tables of linear combinations of virtual polynomials.
For each constraint (b, c):
  Az[b,c] is the "guard" — typically boolean, selects when active
  Bz[b,c] is the "value" — the equality to enforce when guard is on
  Az · Bz = 0 means: "if guard is on, then value = 0"

The constraints are split into two groups for prover efficiency:
  Group 0 (X_b = 0): Bz values fit in ~64 bits  → faster arithmetic
  Group 1 (X_b = 1): Bz values need ~128 bits   → wider but fewer

After the sumcheck, the prover opens all 37 R1CS input virtual
polynomials at r_cycle^(1), from which the verifier reconstructs
Az and Bz at the random point.

Source: jolt-core/src/zkvm/spartan/outer.rs
        jolt-core/src/zkvm/r1cs/evaluation.rs (Az/Bz definitions)
        jolt-core/src/zkvm/r1cs/constraints.rs (group assignments)
Spec:   references/stage1.md
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_GROUP
from ...ast import (
    Const, Neg, VirtualPoly,
    vp, add, sub, scale,
)
from ...spec import SpartanSpec, Constraint


def stage1_spartan_outer() -> SpartanSpec:
    # ── Variables ──
    X_t = Var("X_t", DIM_CYCLE)    # cycle / timestep
    X_b = Var("X_b", DIM_GROUP)    # constraint group selector

    # All constraint polynomials are virtual, evaluated at the cycle var.
    def v(name: str) -> VirtualPoly:
        return vp(name, X_t)

    # ── First group (X_b = 0): boolean guards, ~64-bit values ──
    #
    # These 10 constraints have small Bz values (fit in 64 bits),
    # which allows the prover to use fast machine-word arithmetic.
    #
    # Source: AzFirstGroup / BzFirstGroup in evaluation.rs

    group0 = [
        # c = -5:  If NOT a load/store, then RamAddress must be zero.
        Constraint(
            "RamAddrZeroIfNotLoadStore",
            az=sub(Const(1), v("OpFlags(Load)"), v("OpFlags(Store)")),
            bz=v("RamAddress"),
        ),
        # c = -4:  If load, then RamRead == RamWrite (memory unchanged).
        Constraint(
            "RamReadEqRamWriteIfLoad",
            az=v("OpFlags(Load)"),
            bz=sub(v("RamReadValue"), v("RamWriteValue")),
        ),
        # c = -3:  If load, then RamRead == RdWrite (loaded value goes to register).
        Constraint(
            "RamReadEqRdWriteIfLoad",
            az=v("OpFlags(Load)"),
            bz=sub(v("RamReadValue"), v("RdWriteValue")),
        ),
        # c = -2:  If store, then Rs2 == RamWrite (register value goes to memory).
        Constraint(
            "Rs2EqRamWriteIfStore",
            az=v("OpFlags(Store)"),
            bz=sub(v("Rs2Value"), v("RamWriteValue")),
        ),
        # c = -1:  If ADD/SUB/MUL, then LeftLookupOperand must be zero
        #          (arithmetic ops use a single-value range check, not interleaved).
        Constraint(
            "LeftLookupZeroUnlessAddSubMul",
            az=add(v("OpFlags(Add)"), v("OpFlags(Sub)"), v("OpFlags(Mul)")),
            bz=v("LeftLookupOperand"),
        ),
        # c = 0:   If NOT ADD/SUB/MUL, then LeftLookupOp == LeftInstructionInput
        #          (interleaved operand bits pass through directly).
        Constraint(
            "LeftLookupEqLeftInputOtherwise",
            az=sub(Const(1), v("OpFlags(Add)"), v("OpFlags(Sub)"), v("OpFlags(Mul)")),
            bz=sub(v("LeftLookupOperand"), v("LeftInstructionInput")),
        ),
        # c = 1:   If ASSERT instruction, then LookupOutput must be 1.
        Constraint(
            "AssertLookupOne",
            az=v("OpFlags(Assert)"),
            bz=sub(v("LookupOutput"), Const(1)),
        ),
        # c = 2:   If JUMP, then NextUnexpandedPC == LookupOutput.
        Constraint(
            "NextUnexpPCEqLookupIfJump",
            az=v("ShouldJump"),
            bz=sub(v("NextUnexpandedPC"), v("LookupOutput")),
        ),
        # c = 3:   If VirtualInstruction (but not last in sequence),
        #          then NextPC == PC + 1 (advance through virtual sequence).
        Constraint(
            "NextPCEqPCPlusOneIfInline",
            az=sub(v("OpFlags(VirtualInstruction)"), v("OpFlags(LastInSeq)")),
            bz=sub(v("NextPC"), v("PC"), Const(1)),
        ),
        # c = 4:   If next instruction is virtual but not the first in sequence,
        #          then the current instruction must not update the unexpanded PC.
        Constraint(
            "MustStartSequenceFromBeginning",
            az=sub(v("NextIsVirtual"), v("NextIsFirstInSequence")),
            bz=sub(Const(1), v("OpFlags(DoNotUpdateUnexpandedPC)")),
        ),
    ]

    # ── Second group (X_b = 1): boolean guards, ~128-bit values ──
    #
    # These 9 constraints have wider Bz values (up to ~160 bits for
    # arithmetic results), requiring big-integer arithmetic on the
    # prover side.  There is also 1 zero-padded dummy constraint to
    # make both groups the same size (10 each).
    #
    # Source: AzSecondGroup / BzSecondGroup in evaluation.rs

    group1 = [
        # c = -5:  If load/store, then RamAddress == Rs1 + Imm.
        Constraint(
            "RamAddrEqRs1PlusImmIfLoadStore",
            az=add(v("OpFlags(Load)"), v("OpFlags(Store)")),
            bz=sub(v("RamAddress"), v("Rs1Value"), v("Imm")),
        ),
        # c = -4:  If ADD, then RightLookupOp == Left + Right.
        Constraint(
            "RightLookupAdd",
            az=v("OpFlags(Add)"),
            bz=sub(v("RightLookupOperand"), v("LeftInstructionInput"), v("RightInstructionInput")),
        ),
        # c = -3:  If SUB, then RightLookupOp == Left - Right + 2^64.
        #          (the +2^64 is a bias to keep the value unsigned)
        Constraint(
            "RightLookupSub",
            az=v("OpFlags(Sub)"),
            bz=add(
                sub(v("RightLookupOperand"), v("LeftInstructionInput")),
                v("RightInstructionInput"),
                Neg(Const("2^64")),
            ),
        ),
        # c = -2:  If MUL, then RightLookupOp == Product.
        Constraint(
            "RightLookupEqProductIfMul",
            az=v("OpFlags(Mul)"),
            bz=sub(v("RightLookupOperand"), v("Product")),
        ),
        # c = -1:  Otherwise (not ADD/SUB/MUL/ADVICE),
        #          RightLookupOp == RightInstructionInput.
        Constraint(
            "RightLookupEqRightInputOtherwise",
            az=sub(
                Const(1),
                v("OpFlags(Add)"), v("OpFlags(Sub)"),
                v("OpFlags(Mul)"), v("OpFlags(Advice)"),
            ),
            bz=sub(v("RightLookupOperand"), v("RightInstructionInput")),
        ),
        # c = 0:   If WriteLookupOutputToRD flag, then RdWrite == LookupOutput.
        Constraint(
            "RdWriteEqLookupIfWriteLookupToRd",
            az=v("WriteLookupOutputToRD"),
            bz=sub(v("RdWriteValue"), v("LookupOutput")),
        ),
        # c = 1:   If WritePCtoRD flag, then RdWrite == UnexpandedPC + 4
        #          (minus 2 if compressed instruction).
        Constraint(
            "RdWriteEqPCPlusConstIfWritePCtoRD",
            az=v("WritePCtoRD"),
            bz=add(
                sub(v("RdWriteValue"), v("UnexpandedPC"), Const(4)),
                scale(2, v("OpFlags(IsCompressed)")),
            ),
        ),
        # c = 2:   If BRANCH taken, then NextUnexpandedPC == PC + Imm.
        Constraint(
            "NextUnexpPCEqPCPlusImmIfBranch",
            az=v("ShouldBranch"),
            bz=sub(v("NextUnexpandedPC"), v("UnexpandedPC"), v("Imm")),
        ),
        # c = 3:   Otherwise (not branch, not jump), NextUnexpandedPC == PC + 4
        #          (or +2 if compressed, or unchanged if DoNotUpdate).
        Constraint(
            "NextUnexpPCUpdateOtherwise",
            az=sub(Const(1), v("ShouldBranch"), v("OpFlags(Jump)")),
            bz=add(
                sub(v("NextUnexpandedPC"), v("UnexpandedPC"), Const(4)),
                scale(4, v("OpFlags(DoNotUpdateUnexpandedPC)")),
                scale(2, v("OpFlags(IsCompressed)")),
            ),
        ),
        # c = 4:   Zero-padded dummy to make both groups size 10.
        Constraint(
            "(zero-padded)",
            az=Const(0),
            bz=Const(0),
        ),
    ]

    # ── All 37 R1CS input virtual polynomials ──
    #
    # After the sumcheck, the prover opens EVERY R1CS input at
    # r_cycle^(1).  The verifier uses these 37 openings to
    # reconstruct Az and Bz at the random point and check the
    # final sumcheck message.
    #
    # Source: ALL_R1CS_INPUTS in jolt-core/src/zkvm/r1cs/inputs.rs

    r1cs_inputs = [
        "LeftInstructionInput", "RightInstructionInput", "Product",
        "WriteLookupOutputToRD", "WritePCtoRD", "ShouldBranch",
        "PC", "UnexpandedPC", "Imm",
        "RamAddress", "Rs1Value", "Rs2Value", "RdWriteValue",
        "RamReadValue", "RamWriteValue",
        "LeftLookupOperand", "RightLookupOperand",
        "NextUnexpandedPC", "NextPC", "NextIsVirtual", "NextIsFirstInSequence",
        "LookupOutput", "ShouldJump",
        "OpFlags(AddOperands)", "OpFlags(SubtractOperands)", "OpFlags(MultiplyOperands)",
        "OpFlags(Load)", "OpFlags(Store)", "OpFlags(Jump)",
        "OpFlags(WriteLookupOutputToRD)", "OpFlags(VirtualInstruction)",
        "OpFlags(Assert)", "OpFlags(DoNotUpdateUnexpandedPC)",
        "OpFlags(Advice)", "OpFlags(IsCompressed)",
        "OpFlags(IsFirstInSequence)", "OpFlags(IsLastInSequence)",
    ]

    return SpartanSpec(
        name="SpartanOuter (Stage 1)",
        cycle_var=X_t,
        group_var=X_b,
        constraint_domain=list(range(-5, 5)),  # [-5, -4, ..., 4]
        groups=[group0, group1],
        input_claim=Const(0),                  # R1CS satisfaction: Az · Bz sums to 0
        openings=[(name, [Opening(1, DIM_CYCLE)]) for name in r1cs_inputs],
    )
