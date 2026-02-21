"""
Example sumcheck encodings from the Jolt specification.

Run directly:   python3 -m sumcheck
Or import:      from sumcheck.examples import stage1_spartan_outer

Each function returns a fully-constructed spec object that can be
pretty-printed, inspected, or walked programmatically.

Currently encoded:
  stage6_ram_hamming_booleanity()  — simplest sumcheck (degree 3, RHS=0)
  stage1_spartan_outer()           — Spartan R1CS constraint table (20 constraints)
"""

from .ast import (
    Var, Opening, Const, CommittedPoly, VirtualPoly, VerifierPoly,
    Add, Mul, Pow, Neg, FSum, Prod,
    vp, cp, eq, add, sub, mul, scale,
)
from .spec import (
    SumcheckSpec, SpartanSpec, Constraint,
    ProductConstraint, ProductVirtSpec,
)
from .printer import print_sumcheck, print_spartan


# ═══════════════════════════════════════════════════════════════════
# Stage 6: RamHammingBooleanity
# ═══════════════════════════════════════════════════════════════════
#
# This is the simplest sumcheck in Jolt — it proves that the RAM
# hamming-weight polynomial H is boolean-valued (H ∈ {0,1} at
# every point on the hypercube).
#
# The booleanity trick: p is boolean iff p^2 - p = 0.
# So we prove:
#
#     Σ_{X_t ∈ {0,1}^{log T}}  eq(r_cycle, X_t) · (H(X_t)^2 - H(X_t))  =  0
#
# The eq polynomial is a selector — it lets the sumcheck run over
# all T timesteps while binding to a specific random point r_cycle
# from a prior stage.
#
# Degree breakdown:
#   eq(r, X_t)  contributes degree 1 (multilinear)
#   H^2 - H    contributes degree 2
#   total = 3
#
# Source: jolt-core/src/zkvm/ram/hamming_booleanity.rs
# Spec:   references/stage6.md § RamHammingBooleanitySumcheck
# ═══════════════════════════════════════════════════════════════════

def stage6_ram_hamming_booleanity() -> SumcheckSpec:
    # The single free variable: cycle/timestep
    X_t = Var("X_t", "log2(T)")

    # The eq selector binds to the cycle point from Stage 1
    r_cycle = Opening(1, "cycle")

    # The polynomial being checked for booleanity
    H = vp("RamHammingWeight", X_t)

    # Build the integrand:  eq(r, X_t) · (H^2 - H)
    integrand = Mul(eq(r_cycle, X_t), Add(Pow(H, 2), Neg(H)))

    return SumcheckSpec(
        name="RamHammingBooleanity",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=Const(0),           # RHS is zero (booleanity check)
        rounds="log2(T)",               # one round per timestep bit
        # degree is auto-computed: eq(1) × (H^2 - H)(2) = 3
        openings=[
            # After the sumcheck, H is opened at the fresh cycle point
            ("RamHammingWeight", [Opening(6, "cycle")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 1: SpartanOuter
# ═══════════════════════════════════════════════════════════════════
#
# This is the FIRST and most complex sumcheck in Jolt.  It proves
# that the entire execution trace satisfies all 19 R1CS constraints
# (plus 1 zero-padded) in a single batched sumcheck.
#
# The integrand has a fixed structure:
#
#     eq((τ_t, τ_b), (X_t, X_b)) · L_{τ_c}(X_c) · Az(X_t,X_b,X_c) · Bz(X_t,X_b,X_c)
#
# Three summation axes:
#   X_t ∈ {0,1}^{log₂ T}  — cycle (which timestep)
#   X_b ∈ {0,1}           — group selector (two constraint groups)
#   X_c ∈ {-5, ..., 4}    — constraint index within group
#
# eq is the standard multilinear Lagrange basis over (X_t, X_b).
# L_{τ_c} is a UNIVARIATE Lagrange interpolant over the 10-element
# domain {-5,...,4} — this is the "univariate skip" optimisation.
#
# Az and Bz are tables of linear combinations of virtual polynomials.
# For each constraint (b, c):
#   Az[b,c] is the "guard" — typically boolean, selects when active
#   Bz[b,c] is the "value" — the equality to enforce when guard is on
#   Az · Bz = 0 means: "if guard is on, then value = 0"
#
# The constraints are split into two groups for prover efficiency:
#   Group 0 (X_b = 0): Bz values fit in ~64 bits  → faster arithmetic
#   Group 1 (X_b = 1): Bz values need ~128 bits   → wider but fewer
#
# After the sumcheck, the prover opens all 37 R1CS input virtual
# polynomials at r_cycle^(1), from which the verifier reconstructs
# Az and Bz at the random point.
#
# Source: jolt-core/src/zkvm/spartan/outer.rs
#         jolt-core/src/zkvm/r1cs/evaluation.rs (Az/Bz definitions)
#         jolt-core/src/zkvm/r1cs/constraints.rs (group assignments)
# Spec:   references/stage1.md
# ═══════════════════════════════════════════════════════════════════

def stage1_spartan_outer() -> SpartanSpec:
    # ── Variables ──
    X_t = Var("X_t", "log2(T)")    # cycle / timestep
    X_b = Var("X_b", "1")          # constraint group selector

    # All constraint polynomials are virtual, evaluated at the cycle var.
    # This helper avoids repeating X_t on every line.
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
        openings=[(name, [Opening(1, "cycle")]) for name in r1cs_inputs],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 2: Product Virtualization
# ═══════════════════════════════════════════════════════════════════
#
# Proves that 5 virtual "product" polynomials really are the
# product of their two factor polynomials.  Uses a batched
# sumcheck over the domain {-2, -1, 0, 1, 2} with a univariate
# Lagrange selector, same trick as Stage 1.
#
#     Σ_{X_t, X_c} eq(r_cycle^(1), X_t) · L(τ_c, X_c)
#                     · Left(X_t, X_c) · Right(X_t, X_c)
#     = Σ_{X_c} L(τ_c, X_c) · Output(r_cycle^(1), X_c)
#
# Source: jolt-core/src/zkvm/spartan/product_virtual.rs
# Spec:   references/stage2.md § Product Constraints
# ═══════════════════════════════════════════════════════════════════

def stage2_product_virtualization() -> ProductVirtSpec:
    X_t = Var("X_t", "log2(T)")

    def v(name: str) -> VirtualPoly:
        return vp(name, X_t)

    constraints = [
        # c = -2: Product = LeftInstructionInput · RightInstructionInput
        ProductConstraint(
            "Product",
            left=v("LeftInstructionInput"),
            right=v("RightInstructionInput"),
            output=v("Product"),
        ),
        # c = -1: WriteLookupOutputToRD = IsRdNotZero · OpFlags(WriteLookupOutputToRD)
        ProductConstraint(
            "WriteLookupOutputToRD",
            left=v("InstructionFlags(IsRdNotZero)"),
            right=v("OpFlags(WriteLookupOutputToRD)"),
            output=v("WriteLookupOutputToRD"),
        ),
        # c = 0: WritePCtoRD = IsRdNotZero · OpFlags(Jump)
        ProductConstraint(
            "WritePCtoRD",
            left=v("InstructionFlags(IsRdNotZero)"),
            right=v("OpFlags(Jump)"),
            output=v("WritePCtoRD"),
        ),
        # c = 1: ShouldBranch = LookupOutput · InstructionFlags(Branch)
        ProductConstraint(
            "ShouldBranch",
            left=v("LookupOutput"),
            right=v("InstructionFlags(Branch)"),
            output=v("ShouldBranch"),
        ),
        # c = 2: ShouldJump = OpFlags(Jump) · (1 - NextIsNoop)
        ProductConstraint(
            "ShouldJump",
            left=v("OpFlags(Jump)"),
            right=sub(Const(1), v("NextIsNoop")),
            output=v("ShouldJump"),
        ),
    ]

    # After the sumcheck, the prover opens the 9 unique factor polys
    factor_polys = [
        "LeftInstructionInput", "RightInstructionInput",
        "InstructionFlags(IsRdNotZero)",
        "OpFlags(WriteLookupOutputToRD)", "OpFlags(Jump)",
        "LookupOutput", "InstructionFlags(Branch)",
        "NextIsNoop", "OpFlags(VirtualInstruction)",
    ]

    return ProductVirtSpec(
        name="SpartanProductVirtualization",
        cycle_var=X_t,
        constraint_domain=list(range(-2, 3)),  # [-2, -1, 0, 1, 2]
        constraints=constraints,
        openings=[
            (name, [Opening(2, "cycle", "log2(T)")]) for name in factor_polys
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 2: RAM Read/Write Checking
# ═══════════════════════════════════════════════════════════════════
#
# Decomposes the virtual RamReadValue and RamWriteValue into
# address-indicator (RamRa) times value (RamVal) sums.
# Batched with γ into a single sumcheck.
#
#     Σ_{X_k, X_j} eq(r_cycle^(1), X_j) · RamRa(X_k, X_j)
#         · (RamVal(X_k, X_j) + γ · (RamVal(X_k, X_j) + RamInc(X_j)))
#     = RamReadValue(r_cycle^(1)) + γ · RamWriteValue(r_cycle^(1))
#
# Source: jolt-core/src/zkvm/ram/read_write.rs
# Spec:   references/stage2.md § RAM Read/Write Checking
# ═══════════════════════════════════════════════════════════════════

def stage2_ram_read_write() -> SumcheckSpec:
    X_k = Var("X_k", "log2(K_ram)")
    X_j = Var("X_j", "log2(T)")
    r_cycle = Opening(1, "cycle", "log2(T)")
    gamma = Const("γ")

    ram_ra  = vp("RamRa", X_k, X_j)
    ram_val = vp("RamVal", X_k, X_j)
    ram_inc = cp("RamInc", X_j)

    # RamVal + γ · (RamVal + RamInc)
    inner = add(ram_val, Mul(gamma, add(ram_val, ram_inc)))

    integrand = Mul(Mul(eq(r_cycle, X_j), ram_ra), inner)

    # RHS: RamReadValue(r^(1)) + γ · RamWriteValue(r^(1))
    rhs = add(
        vp("RamReadValue", r_cycle),
        Mul(gamma, vp("RamWriteValue", r_cycle)),
    )

    return SumcheckSpec(
        name="RamReadWriteChecking",
        sum_vars=[X_k, X_j],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(K_ram) + log2(T)",
        openings=[
            ("RamVal",  [Opening(2, "K_ram", "log2(K_ram)"), Opening(2, "cycle", "log2(T)")]),
            ("RamRa",   [Opening(2, "K_ram", "log2(K_ram)"), Opening(2, "cycle", "log2(T)")]),
            ("RamInc",  [Opening(2, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 2: Instruction Claim Reduction
# ═══════════════════════════════════════════════════════════════════
#
# Aggregates 3 instruction lookup claims into a single opening
# point using γ-batching.
#
#     Σ_{X_j} eq(r_cycle^(1), X_j)
#       · (LookupOutput + γ · LeftLookupOp + γ² · RightLookupOp)
#     = LookupOutput(r^(1)) + γ · LeftLookupOp(r^(1))
#       + γ² · RightLookupOp(r^(1))
#
# Source: jolt-core/src/zkvm/instruction_lookups/claim_reduction.rs
# Spec:   references/stage2.md § Instruction Claim Reduction
# ═══════════════════════════════════════════════════════════════════

def stage2_instruction_claim_reduction() -> SumcheckSpec:
    X_j = Var("X_j", "log2(T)")
    r_cycle = Opening(1, "cycle", "log2(T)")
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

    integrand = Mul(eq(r_cycle, X_j), batch)

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
        rounds="log2(T)",
        openings=[
            ("LookupOutput",       [Opening(2, "cycle", "log2(T)")]),
            ("LeftLookupOperand",   [Opening(2, "cycle", "log2(T)")]),
            ("RightLookupOperand",  [Opening(2, "cycle", "log2(T)")]),
            ("LeftInstructionInput", [Opening(2, "cycle", "log2(T)")]),
            ("RightInstructionInput",[Opening(2, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 2: RAM RAF Evaluation
# ═══════════════════════════════════════════════════════════════════
#
# Proves that the RamRa polynomial actually encodes the RAM
# address, by summing RamRa · unmap(X_k) over the address space.
#
#     Σ_{X_k} RamRa(X_k, r_cycle^(1)) · unmap(X_k)
#     = RamAddress(r_cycle^(1))
#
# Source: jolt-core/src/zkvm/ram/raf_evaluation.rs
# Spec:   references/stage2.md § RAM RAF Evaluation
# ═══════════════════════════════════════════════════════════════════

def stage2_ram_raf_evaluation() -> SumcheckSpec:
    X_k = Var("X_k", "log2(K_ram)")
    r_cycle = Opening(1, "cycle", "log2(T)")

    ram_ra = vp("RamRa", X_k, r_cycle)
    unmap  = VerifierPoly("unmap", [X_k])

    integrand = Mul(ram_ra, unmap)

    rhs = vp("RamAddress", r_cycle)

    return SumcheckSpec(
        name="RamRafEvaluation",
        sum_vars=[X_k],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(K_ram)",
        openings=[
            ("RamRa", [Opening(2, "K_ram", "log2(K_ram)"), Opening(1, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 2: RAM Output Check
# ═══════════════════════════════════════════════════════════════════
#
# Zero-check: final RAM state matches the claimed I/O values.
#
#     Σ_{X_k} eq(r_K_ram^(2), X_k) · io_mask(X_k)
#       · (RamValFinal(X_k) - ValIO(X_k))
#     = 0
#
# Source: jolt-core/src/zkvm/ram/output_check.rs
# Spec:   references/stage2.md § RAM Output Check
# ═══════════════════════════════════════════════════════════════════

def stage2_ram_output_check() -> SumcheckSpec:
    X_k = Var("X_k", "log2(K_ram)")
    r_k_ram = Opening(2, "K_ram", "log2(K_ram)")

    ram_final = vp("RamValFinal", X_k)
    val_io    = VerifierPoly("ValIO", [X_k])
    io_mask   = VerifierPoly("io_mask", [X_k])

    integrand = Mul(
        Mul(eq(r_k_ram, X_k), io_mask),
        sub(ram_final, val_io),
    )

    return SumcheckSpec(
        name="RamOutputCheck",
        sum_vars=[X_k],
        integrand=integrand,
        input_claim=Const(0),
        rounds="log2(K_ram)",
        openings=[
            ("RamValFinal", [Opening(2, "K_ram", "log2(K_ram)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 3: Shift + InstructionInput + RegistersClaimReduction
# ═══════════════════════════════════════════════════════════════════

def stage3_shift() -> SumcheckSpec:
    X_j = Var("X_j", "log2(T)")
    r1_cycle = Opening(1, "cycle", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
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
        rounds="log2(T)",
        openings=[
            ("UnexpandedPC",                [Opening(3, "cycle", "log2(T)")]),
            ("PC",                          [Opening(3, "cycle", "log2(T)")]),
            ("OpFlags(VirtualInstruction)",  [Opening(3, "cycle", "log2(T)")]),
            ("OpFlags(IsFirstInSequence)",   [Opening(3, "cycle", "log2(T)")]),
            ("InstructionFlags(IsNoop)",     [Opening(3, "cycle", "log2(T)")]),
        ],
    )


def stage3_instruction_input() -> SumcheckSpec:
    X_j = Var("X_j", "log2(T)")
    r1_cycle = Opening(1, "cycle", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
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
        add(eq(r1_cycle, X_j), Mul(Pow(gamma, 2), eq(r2_cycle, X_j))),
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
        rounds="log2(T)",
        openings=[
            ("InstructionFlags(LeftOperandIsRs1Value)",   [Opening(3, "cycle", "log2(T)")]),
            ("Rs1Value",                                  [Opening(3, "cycle", "log2(T)")]),
            ("InstructionFlags(LeftOperandIsPC)",          [Opening(3, "cycle", "log2(T)")]),
            ("UnexpandedPC",                              [Opening(3, "cycle", "log2(T)")]),
            ("InstructionFlags(RightOperandIsRs2Value)",   [Opening(3, "cycle", "log2(T)")]),
            ("Rs2Value",                                  [Opening(3, "cycle", "log2(T)")]),
            ("InstructionFlags(RightOperandIsImm)",        [Opening(3, "cycle", "log2(T)")]),
            ("Imm",                                       [Opening(3, "cycle", "log2(T)")]),
        ],
    )


def stage3_registers_claim_reduction() -> SumcheckSpec:
    X_j = Var("X_j", "log2(T)")
    r1_cycle = Opening(1, "cycle", "log2(T)")
    gamma = Const("γ")

    batch = add(
        vp("RdWriteValue", X_j),
        Mul(gamma, vp("Rs1Value", X_j)),
        Mul(Pow(gamma, 2), vp("Rs2Value", X_j)),
    )

    integrand = Mul(eq(r1_cycle, X_j), batch)

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
        rounds="log2(T)",
        openings=[
            ("RdWriteValue", [Opening(3, "cycle", "log2(T)")]),
            ("Rs1Value",     [Opening(3, "cycle", "log2(T)")]),
            ("Rs2Value",     [Opening(3, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 4: RegistersReadWriteChecking + RamValCheck
# ═══════════════════════════════════════════════════════════════════

def stage4_registers_read_write() -> SumcheckSpec:
    X_k = Var("X_k", "log2(K_reg)")
    X_t = Var("X_t", "log2(T)")
    r3_cycle = Opening(3, "cycle", "log2(T)")
    gamma = Const("γ")

    rd_wa   = vp("RdWa", X_k, X_t)
    rs1_ra  = vp("Rs1Ra", X_k, X_t)
    rs2_ra  = vp("Rs2Ra", X_k, X_t)
    reg_val = vp("RegistersVal", X_k, X_t)
    rd_inc  = cp("RdInc", X_t)

    # eq(r3, X_t) · (RdWa·(RdInc+Val) + γ·Rs1Ra·Val + γ²·Rs2Ra·Val)
    integrand = Mul(
        eq(r3_cycle, X_t),
        add(
            Mul(rd_wa, add(rd_inc, reg_val)),
            Mul(gamma, Mul(rs1_ra, reg_val)),
            Mul(Pow(gamma, 2), Mul(rs2_ra, reg_val)),
        ),
    )

    rhs = add(
        vp("RdWriteValue", r3_cycle),
        Mul(gamma, vp("Rs1Value", r3_cycle)),
        Mul(Pow(gamma, 2), vp("Rs2Value", r3_cycle)),
    )

    return SumcheckSpec(
        name="RegistersReadWriteChecking",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(K_reg) + log2(T)",
        openings=[
            ("RegistersVal", [Opening(4, "K_reg", "log2(K_reg)"), Opening(4, "cycle", "log2(T)")]),
            ("Rs1Ra",        [Opening(4, "K_reg", "log2(K_reg)"), Opening(4, "cycle", "log2(T)")]),
            ("Rs2Ra",        [Opening(4, "K_reg", "log2(K_reg)"), Opening(4, "cycle", "log2(T)")]),
            ("RdWa",         [Opening(4, "K_reg", "log2(K_reg)"), Opening(4, "cycle", "log2(T)")]),
            ("RdInc",        [Opening(4, "cycle", "log2(T)")]),
        ],
    )


def stage4_ram_val_check() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
    r2_k_ram = Opening(2, "K_ram", "log2(K_ram)")
    gamma = Const("γ")

    ram_inc = cp("RamInc", X_t)
    ram_ra  = vp("RamRa", r2_k_ram, X_t)
    lt      = VerifierPoly("LT_tilde", [X_t, r2_cycle])

    # RamInc(X_t) · RamRa(r2_K, X_t) · (LT(X_t, r2_cycle) + γ)
    integrand = Mul(ram_inc, Mul(ram_ra, add(lt, gamma)))

    rhs = add(
        sub(
            vp("RamVal", r2_k_ram, r2_cycle),
            vp("RamValInit", r2_k_ram),
        ),
        Mul(gamma, sub(
            vp("RamValFinal", r2_k_ram),
            vp("RamValInit", r2_k_ram),
        )),
    )

    return SumcheckSpec(
        name="RamValCheck",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(T)",
        openings=[
            ("RamInc", [Opening(4, "cycle", "log2(T)")]),
            ("RamRa",  [r2_k_ram, Opening(4, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 5: InstructionReadRaf
# ═══════════════════════════════════════════════════════════════════
#
# Decomposes the three batched instruction lookup claims
# (LookupOutput, LeftLookupOperand, RightLookupOperand) into the
# product of virtual RA chunks times table/operand evaluations.
#
# Parameters (hardcoded):
#   d_v = 16      virtual RA chunks (128 / log2(N_v), N_v = 256)
#   N_tables = 42 lookup tables
#
# The integrand factors as:
#   eq(r_cycle^(2), X_t)
#     · Ra(X_k, X_t)                        — product of d_v chunks
#     · (val(X_k, X_t) + γ · raf(X_k, X_t)) — table + operand
#
# Ra(X_k, X_t) = Π_{i=0}^{d_v-1} InstructionRa(i)(X_k^(i), X_t)
# val(X_k, X_t) = Σ_{i=0}^{N_tables-1} T_i(X_k) · TableFlag_i(X_t)
# raf(X_k, X_t) = (1-RafFlag) · (LeftOp(X_k) + γ·RightOp(X_k))
#                 + RafFlag · γ · unmap(X_k)
#
# Source: jolt-core/src/zkvm/instruction_lookups/read_raf.rs
# Spec:   references/stage5.md § InstructionReadRafSumcheckProver
# ═══════════════════════════════════════════════════════════════════

D_V = 16
N_TABLES = 42

def stage5_instruction_read_raf() -> SumcheckSpec:
    # The address variable spans the full instruction address space:
    # X_k = (X_k^(0), ..., X_k^(d_v-1)), each chunk in {0,1}^log2(N_v)
    X_k = Var("X_k", "log2(K_instr)")  # 128 bits total
    X_t = Var("X_t", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
    gamma = Const("γ")

    # ── Ra: product of d_v virtual RA chunks ──
    # Π_{i=0}^{d_v-1} InstructionRa(i)(X_k^(i), X_t)
    ra = Prod("i", D_V, vp("InstructionRa(i)", X_k, X_t))

    # ── val: Σ_{j=0}^{N_tables-1} T_j(X_k) · TableFlag_j(X_t) ──
    val = FSum("j", "N_tables",
               Mul(VerifierPoly("T_j", [X_k]), vp("TableFlag(j)", X_t)))

    # ── raf: operand extraction ──
    # (1 - RafFlag) · (LeftOp(X_k) + γ · RightOp(X_k))
    # + RafFlag · γ · unmap(X_k)
    raf_flag = vp("InstructionRafFlag", X_t)
    left_op  = VerifierPoly("LeftOp", [X_k])
    right_op = VerifierPoly("RightOp", [X_k])
    unmap    = VerifierPoly("unmap", [X_k])

    raf = add(
        Mul(sub(Const(1), raf_flag), add(left_op, Mul(gamma, right_op))),
        Mul(raf_flag, Mul(gamma, unmap)),
    )

    # ── Full integrand ──
    integrand = Mul(
        Mul(eq(r2_cycle, X_t), ra),
        add(val, Mul(gamma, raf)),
    )

    # ── Openings produced ──
    r5_cycle = Opening(5, "cycle", "log2(T)")
    openings = [
        # d_v virtual RA chunks, each at (r_addr_chunk_i, r_cycle^(5))
        ("InstructionRa(i) for i=0..d_v-1",
         [Opening(5, "K_instr^(i)", "log2(N_v)"), r5_cycle]),
        # N_tables table flags, each at r_cycle^(5)
        ("TableFlag(j) for j=0..N_tables-1", [r5_cycle]),
        # RafFlag
        ("InstructionRafFlag", [r5_cycle]),
    ]

    return SumcheckSpec(
        name="InstructionReadRaf",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=add(
            vp("LookupOutput", r2_cycle),
            Mul(gamma, vp("LeftLookupOperand", r2_cycle)),
            Mul(Pow(gamma, 2), vp("RightLookupOperand", r2_cycle)),
        ),
        rounds="128 + log2(T)",
        openings=openings,
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 5: RamRaClaimReduction + RegistersValEvaluation
# ═══════════════════════════════════════════════════════════════════

def stage5_ram_ra_claim_reduction() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r1_cycle = Opening(1, "cycle", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
    r4_cycle = Opening(4, "cycle", "log2(T)")
    r2_k_ram = Opening(2, "K_ram", "log2(K_ram)")
    gamma = Const("γ")

    # Batches 3 RamRa openings at different cycle points:
    # (eq(r1, X_t) + γ·eq(r2, X_t) + γ²·eq(r4, X_t)) · RamRa(r2_K, X_t)
    eq_batch = add(
        eq(r1_cycle, X_t),
        Mul(gamma, eq(r2_cycle, X_t)),
        Mul(Pow(gamma, 2), eq(r4_cycle, X_t)),
    )

    integrand = Mul(eq_batch, vp("RamRa", r2_k_ram, X_t))

    rhs = add(
        vp("RamRa", r2_k_ram, r1_cycle),
        Mul(gamma, vp("RamRa", r2_k_ram, r2_cycle)),
        Mul(Pow(gamma, 2), vp("RamRa", r2_k_ram, r4_cycle)),
    )

    return SumcheckSpec(
        name="RamRaClaimReduction",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(T)",
        openings=[
            ("RamRa", [r2_k_ram, Opening(5, "cycle", "log2(T)")]),
        ],
    )


def stage5_registers_val_evaluation() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r4_cycle = Opening(4, "cycle", "log2(T)")
    r4_k_reg = Opening(4, "K_reg", "log2(K_reg)")

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
        rounds="log2(T)",
        openings=[
            ("RdInc", [Opening(5, "cycle", "log2(T)")]),
            ("RdWa",  [r4_k_reg, Opening(5, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 6: RamHammingBooleanity (already defined above),
#           IncClaimReduction
# ═══════════════════════════════════════════════════════════════════
#
# (BytecodeReadRaf, InstructionRa/RamRa Virtualization, and
#  Booleanity are parametric — depend on d_instr, d_ram, M.)

def stage6_inc_claim_reduction() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r2_cycle = Opening(2, "cycle", "log2(T)")
    r4_cycle = Opening(4, "cycle", "log2(T)")
    r5_cycle = Opening(5, "cycle", "log2(T)")
    gamma = Const("γ")

    ram_inc = cp("RamInc", X_t)
    rd_inc  = cp("RdInc", X_t)

    # RamInc · (eq(r2, X_t) + γ·eq(r4, X_t))
    # + γ² · RdInc · (eq(r4, X_t) + γ·eq(r5, X_t))
    integrand = add(
        Mul(ram_inc, add(eq(r2_cycle, X_t), Mul(gamma, eq(r4_cycle, X_t)))),
        Mul(Pow(gamma, 2), Mul(rd_inc, add(eq(r4_cycle, X_t), Mul(gamma, eq(r5_cycle, X_t))))),
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
        rounds="log2(T)",
        openings=[
            ("RamInc", [Opening(6, "cycle", "log2(T)")]),
            ("RdInc",  [Opening(6, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 6: BytecodeReadRaf
# ═══════════════════════════════════════════════════════════════════
#
# Bytecode consistency check.  The prover reads a bytecode row at
# each cycle and proves that the read values match the per-stage
# polynomial openings.  Five sub-stages batch different sets of
# instruction fields (PC, flags, register indices, etc.), plus two
# RAF terms for PC consistency.
#
# The integrand factors as:
#   Ra(X_k, X_t)  ·  Σ_{s=0}^{4} γ^s · eq(r_cycle^(s+1), X_t) · W_{s+1}(X_k)
#
# Ra = Π_{i=0}^{d_bc-1} BytecodeRa(i)(X_k^(i), X_t)
# W_s(X_k) = Val_s(X_k) + δ_s · Int(X_k)  (verifier-computable from bytecode)
#
# Degree: d_bc + 1 (Ra contributes d_bc, eq adds 1; W is verifier-computable)
#
# Source: jolt-core/src/zkvm/bytecode/read_raf_checking.rs
# Spec:   references/stage6.md § BytecodeReadRafSumcheck
# ═══════════════════════════════════════════════════════════════════

def stage6_bytecode_read_raf() -> SumcheckSpec:
    X_k = Var("X_k", "log2(K_bc)")
    X_t = Var("X_t", "log2(T)")
    gamma = Const("γ")

    # Ra = Π_{i=0}^{d_bc-1} BytecodeRa(i)(X_k^(i), X_t)
    ra = Prod("i", "d_bc", cp("BytecodeRa(i)", X_k, X_t))

    # 5 sub-stages, each with a concrete cycle opening point:
    #   s=1: SpartanOuter          → r_cycle^(1)
    #   s=2: ProductVirtualization → r_cycle^(2)
    #   s=3: Shift                 → r_cycle^(3)
    #   s=4: RegistersReadWrite    → r_cycle^(4)
    #   s=5: RegistersValEval      → r_cycle^(5)
    #
    # W_s(X_k) = Val_s(X_k) + δ_s · Int(X_k)  (verifier-computable from bytecode)
    # δ_1 = γ^5, δ_3 = γ^4, δ_s = 0 for s ∈ {2, 4, 5}
    batch = add(
        Mul(eq(Opening(1, "cycle", "log2(T)"), X_t),
            VerifierPoly("W_1", [X_k])),
        Mul(gamma,
            Mul(eq(Opening(2, "cycle", "log2(T)"), X_t),
                VerifierPoly("W_2", [X_k]))),
        Mul(Pow(gamma, 2),
            Mul(eq(Opening(3, "cycle", "log2(T)"), X_t),
                VerifierPoly("W_3", [X_k]))),
        Mul(Pow(gamma, 3),
            Mul(eq(Opening(4, "cycle", "log2(T)"), X_t),
                VerifierPoly("W_4", [X_k]))),
        Mul(Pow(gamma, 4),
            Mul(eq(Opening(5, "cycle", "log2(T)"), X_t),
                VerifierPoly("W_5", [X_k]))),
    )

    integrand = Mul(ra, batch)

    # RHS: batched per-stage rv-claims + RAF contributions
    # raf_1 = PC(r_cycle^(1)), raf_3 = PC(r_cycle^(3))
    rhs = add(
        Const("rv₁"),
        Mul(gamma, Const("rv₂")),
        Mul(Pow(gamma, 2), Const("rv₃")),
        Mul(Pow(gamma, 3), Const("rv₄")),
        Mul(Pow(gamma, 4), Const("rv₅")),
        Mul(Pow(gamma, 5), vp("PC", Opening(1, "cycle", "log2(T)"))),
        Mul(Pow(gamma, 6), vp("PC", Opening(3, "cycle", "log2(T)"))),
    )

    r6_cycle = Opening(6, "cycle", "log2(T)")

    return SumcheckSpec(
        name="BytecodeReadRaf",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(K_bc) + log2(T)",
        openings=[
            ("BytecodeRa(i) for i=0..d_bc-1",
             [Opening(6, "K_bc^(i)", "log2(N_instr)"), r6_cycle]),
        ],
        _degree_override="d_bc + 1",
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 6: InstructionRa Virtualization
# ═══════════════════════════════════════════════════════════════════
#
# Reduces the d_v virtual InstructionRa(i) openings from Stage 5
# (InstructionReadRaf) to openings of the d_instr committed
# InstructionRa(j) polynomials.  Each virtual chunk is the product
# of M committed chunks.
#
# Integrand:
#   eq(r_cycle^(5), X_t) · Σ_{i=0}^{d_v-1} γ^i
#     · Π_{j=0}^{M-1} InstructionRa(iM+j)(r_{K(iM+j)}, X_t)
#
# Degree: M + 1
#
# Source: jolt-core/src/zkvm/instruction_lookups/ra_virtual.rs
# Spec:   references/stage6.md § InstructionRaSumcheckParams
# ═══════════════════════════════════════════════════════════════════

def stage6_instruction_ra_virtualization() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r5_cycle = Opening(5, "cycle", "log2(T)")
    gamma = Const("γ")

    # Σ_{i=0}^{d_v-1} γ^i · Π_{j=0}^{M-1} InstructionRa(iM+j)(r_{K(iM+j)}, X_t)
    inner = FSum("i", "d_v",
        Mul(Const("γ^i"),
            Prod("j", "M",
                 cp("InstructionRa(iM+j)", Opening(5, "K^(iM+j)"), X_t))))

    integrand = Mul(eq(r5_cycle, X_t), inner)

    # RHS: Σ_{i=0}^{d_v-1} γ^i · vp:InstructionRa(i)(r_{K(i)}, r_cycle^(5))
    rhs = FSum("i", "d_v",
        Mul(Const("γ^i"),
            vp("InstructionRa(i)", Opening(5, "K^(i)"), r5_cycle)))

    return SumcheckSpec(
        name="InstructionRaVirtualization",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(T)",
        openings=[
            ("InstructionRa(j) for j=0..d_instr-1",
             [Opening(5, "K^(j)", "log2(N_instr)"), Opening(6, "cycle", "log2(T)")]),
        ],
        _degree_override="M + 1",
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 6: RamRa Virtualization
# ═══════════════════════════════════════════════════════════════════
#
# Reduces the virtual RamRa opening from Stage 5 (RamRaClaimReduction)
# to openings of the d_ram committed RamRa(i) polynomials.
#
# Integrand:
#   eq(r_cycle^(5), X_t) · Π_{i=0}^{d_ram-1} RamRa(i)(r_{K(i)}, X_t)
#
# Degree: d_ram + 1
#
# Source: jolt-core/src/zkvm/ram/ra_virtual.rs
# Spec:   references/stage6.md § RamRaVirtualParams
# ═══════════════════════════════════════════════════════════════════

def stage6_ram_ra_virtualization() -> SumcheckSpec:
    X_t = Var("X_t", "log2(T)")
    r5_cycle = Opening(5, "cycle", "log2(T)")

    # Π_{i=0}^{d_ram-1} RamRa(i)(r_{K_ram^(i)}, X_t)
    ra = Prod("i", "d_ram",
              cp("RamRa(i)", Opening(2, "K_ram^(i)", "log2(N_instr)"), X_t))

    integrand = Mul(eq(r5_cycle, X_t), ra)

    rhs = vp("RamRa", Opening(2, "K_ram", "log2(K_ram)"), r5_cycle)

    return SumcheckSpec(
        name="RamRaVirtualization",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        rounds="log2(T)",
        openings=[
            ("RamRa(i) for i=0..d_ram-1",
             [Opening(2, "K_ram^(i)", "log2(N_instr)"), Opening(6, "cycle", "log2(T)")]),
        ],
        _degree_override="d_ram + 1",
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 6: Booleanity
# ═══════════════════════════════════════════════════════════════════
#
# Proves that ALL committed RA polynomials (InstructionRa, BytecodeRa,
# RamRa — d = d_instr + d_bc + d_ram total) are Boolean-valued.
# Uses the booleanity trick: p is boolean iff p^2 - p = 0.
#
# The eq polynomial binds over the concatenated (address, cycle) space.
# Batching uses even powers γ^{2j} to separate the d polynomials.
#
# Integrand:
#   eq((r_addr, r_cycle), (X_k, X_t))
#     · Σ_{j=0}^{d-1} γ^{2j} · (Ra_j(X_k, X_t)^2 - Ra_j(X_k, X_t))
#
# Degree: 3 (eq=1, Ra^2-Ra=2)
#
# Source: jolt-core/src/zkvm/booleanity/mod.rs
# Spec:   references/stage6.md § BooleanitySumcheck
# ═══════════════════════════════════════════════════════════════════

def stage6_booleanity() -> SumcheckSpec:
    X_k = Var("X_k", "log2(N_instr)")
    X_t = Var("X_t", "log2(T)")
    r_addr = Opening(5, "addr", "log2(N_instr)")
    r_cycle = Opening(5, "cycle", "log2(T)")

    # eq over concatenated space: eq((r_addr, r_cycle), (X_k, X_t))
    # Represented as a single VerifierPoly with 4 args to get degree 1
    eq_bind = VerifierPoly("eq", [r_addr, r_cycle, X_k, X_t])

    # Σ_{j=0}^{d-1} γ^{2j} · (Ra_j^2 - Ra_j)
    # d = d_instr + d_bc + d_ram
    ra_j = cp("Ra_j", X_k, X_t)
    batch = FSum("j", "d",
        Mul(Const("γ^{2j}"), sub(Pow(ra_j, 2), ra_j)))

    integrand = Mul(eq_bind, batch)

    return SumcheckSpec(
        name="Booleanity",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=Const(0),
        rounds="log2(N_instr) + log2(T)",
        openings=[
            ("Ra_j for j=0..d-1 (d = d_instr + d_bc + d_ram)",
             [Opening(6, "addr", "log2(N_instr)"), Opening(6, "cycle", "log2(T)")]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# Stage 7: HammingWeightClaimReduction
# ═══════════════════════════════════════════════════════════════════
#
# The final sumcheck in the pipeline.  Reduces three families of
# claims about each committed RA polynomial — hamming weight (HW),
# booleanity (Bool), and virtualization (Virt) — into a single
# opening per polynomial at a fresh address point.
#
# For each j = 0..N-1 (N = d_instr + d_bc + d_ram):
#   G_j(X_k) = Ra_j(X_k, r_6_cycle)  (marginalised over cycles)
#   HW claim:   Σ G_j = H_j  (1 for instr/bc, RamHammingWeight for ram)
#   Bool claim:  Σ eq(r_6_addr, X_k) · G_j = B_j
#   Virt claim:  Σ eq(r_6_addr^(j), X_k) · G_j = V_j
#
# Integrand:
#   Σ_{j=0}^{N-1} G_j(X_k) · (γ^{3j} + γ^{3j+1}·eq(r_addr, X_k)
#                              + γ^{3j+2}·eq_j(X_k))
#
# Degree: 2 (G_j=1, eq=1)
#
# Source: jolt-core/src/zkvm/hamming_weight/claim_reduction.rs
# Spec:   references/stage7.md § HammingWeightClaimReduction
# ═══════════════════════════════════════════════════════════════════

def stage7_hamming_weight_claim_reduction() -> SumcheckSpec:
    X_k = Var("X_k", "log2(N_instr)")
    r6_addr = Opening(6, "addr", "log2(N_instr)")
    r6_cycle = Opening(6, "cycle", "log2(T)")

    # G_j(X_k) = Ra_j(X_k, r_6_cycle)
    g_j = cp("Ra_j", X_k, r6_cycle)

    # Three terms per polynomial, batched with γ^{3j}, γ^{3j+1}, γ^{3j+2}:
    #   γ^{3j}   · 1            (hamming weight — no eq selector)
    #   γ^{3j+1} · eq(r_addr, X_k)   (booleanity — shared address point)
    #   γ^{3j+2} · eq_j(X_k)         (virtualization — per-poly address point)
    batch = add(
        Const("γ^{3j}"),
        Mul(Const("γ^{3j+1}"), eq(r6_addr, X_k)),
        Mul(Const("γ^{3j+2}"), VerifierPoly("eq_j", [X_k])),
    )

    inner = FSum("j", "N", Mul(g_j, batch))

    # RHS: Σ_j (γ^{3j}·H_j + γ^{3j+1}·B_j + γ^{3j+2}·V_j)
    rhs = Const("Σ_j (γ^{3j}·H_j + γ^{3j+1}·B_j + γ^{3j+2}·V_j)")

    return SumcheckSpec(
        name="HammingWeightClaimReduction",
        sum_vars=[X_k],
        integrand=inner,
        input_claim=rhs,
        rounds="log2(N_instr)",
        openings=[
            ("Ra_j for j=0..N-1 (N = d_instr + d_bc + d_ram)",
             [Opening(7, "addr", "log2(N_instr)"), r6_cycle]),
        ],
    )


# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print_sumcheck(stage6_ram_hamming_booleanity())
    print()
    print_spartan(stage1_spartan_outer())
