"""
Stage 6: Bytecode Read RAF

Bytecode consistency check.  The prover reads a bytecode row at
each cycle and proves that the read values match the per-stage
polynomial openings.  Five sub-stages batch different sets of
instruction fields (PC, flags, register indices, etc.), plus two
RAF terms for PC consistency.

The integrand factors as:
  Ra(X_k, X_t)  ·  Σ_{s=0}^{4} γ^s · eq(r_cycle^(s+1), X_t) · W_{s+1}(X_k)

Ra = Π_{i=0}^{d_bc-1} BytecodeRa(i)(X_k^(i), X_t)
W_s(X_k) = Val_s(X_k) + δ_s · Int(X_k)  (verifier-computable from bytecode)

Degree: d_bc + 1 (Ra contributes d_bc, eq adds 1; W is verifier-computable)

Source: jolt-core/src/zkvm/bytecode/read_raf_checking.rs
Spec:   references/stage6.md § BytecodeReadRafSumcheck
"""

from ...ast import Const, FSum, Mul, Pow, Prod, VerifierPoly, add, cp, vp
from ...defs import DIM_ADDR, DIM_CYCLE, DIM_K_BC, DIM_K_REG, Opening, Var
from ...registry import verifier
from ...spec import SumcheckSpec


def stage6_bytecode_read_raf() -> SumcheckSpec:
    X_k = Var("X_k", DIM_K_BC)
    X_t = Var("X_t", DIM_CYCLE)
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
        Mul(verifier.eq(Opening(1, DIM_CYCLE), X_t),
            VerifierPoly("W_1", [X_k])),
        Mul(gamma,
            Mul(verifier.eq(Opening(2, DIM_CYCLE), X_t),
                VerifierPoly("W_2", [X_k]))),
        Mul(Pow(gamma, 2),
            Mul(verifier.eq(Opening(3, DIM_CYCLE), X_t),
                VerifierPoly("W_3", [X_k]))),
        Mul(Pow(gamma, 3),
            Mul(verifier.eq(Opening(4, DIM_CYCLE), X_t),
                VerifierPoly("W_4", [X_k]))),
        Mul(Pow(gamma, 4),
            Mul(verifier.eq(Opening(5, DIM_CYCLE), X_t),
                VerifierPoly("W_5", [X_k]))),
    )

    integrand = Mul(ra, batch)

    # ── Per-stage rv-claims ──
    # Each rv_s is verifier-computable from prior-stage openings.
    # γ_s is the per-stage batching challenge (distinct from the global γ).

    # rv_1: SpartanOuter (Stage 1)
    r1 = Opening(1, DIM_CYCLE)
    rv_1 = add(
        vp("UnexpandedPC", r1),
        Mul(Const("γ_1"), vp("Imm", r1)),
        FSum("i", "N_cflags",
             Mul(Const("γ_1^{2+i}"), vp("OpFlags(cf_i)", r1))),
    )

    # rv_2: SpartanProductVirtualization (Stage 2)
    r2 = Opening(2, DIM_CYCLE)
    rv_2 = add(
        vp("OpFlags(Jump)", r2),
        Mul(Const("γ_2"), vp("InstructionFlags(Branch)", r2)),
        Mul(Pow(Const("γ_2"), 2), vp("InstructionFlags(IsRdNotZero)", r2)),
        Mul(Pow(Const("γ_2"), 3), vp("OpFlags(WriteLookupOutputToRD)", r2)),
        Mul(Pow(Const("γ_2"), 4), vp("OpFlags(VirtualInstruction)", r2)),
    )

    # rv_3: SpartanShift (Stage 3)
    r3 = Opening(3, DIM_CYCLE)
    rv_3 = add(
        vp("Imm", r3),
        Mul(Const("γ_3"), vp("UnexpandedPC", r3)),
        Mul(Pow(Const("γ_3"), 2), vp("InstructionFlags(LeftOperandIsRs1Value)", r3)),
        Mul(Pow(Const("γ_3"), 3), vp("InstructionFlags(LeftOperandIsPC)", r3)),
        Mul(Pow(Const("γ_3"), 4), vp("InstructionFlags(RightOperandIsRs2Value)", r3)),
        Mul(Pow(Const("γ_3"), 5), vp("InstructionFlags(RightOperandIsImm)", r3)),
        Mul(Pow(Const("γ_3"), 6), vp("InstructionFlags(IsNoop)", r3)),
        Mul(Pow(Const("γ_3"), 7), vp("OpFlags(VirtualInstruction)", r3)),
        Mul(Pow(Const("γ_3"), 8), vp("OpFlags(IsFirstInSequence)", r3)),
    )

    # rv_4: RegistersReadWriteChecking (Stage 4)
    r4_K = Opening(4, DIM_K_REG)
    r4_c = Opening(4, DIM_CYCLE)
    rv_4 = add(
        vp("RdWa", r4_K, r4_c),
        Mul(Const("γ_4"), vp("Rs1Ra", r4_K, r4_c)),
        Mul(Pow(Const("γ_4"), 2), vp("Rs2Ra", r4_K, r4_c)),
    )

    # rv_5: RegistersValEval + InstructionReadRaf (Stage 5)
    r5_K = Opening(4, DIM_K_REG)
    r5_c = Opening(5, DIM_CYCLE)
    rv_5 = add(
        vp("RdWa", r5_K, r5_c),
        Mul(Const("γ_5"), vp("InstructionRafFlag", r5_c)),
        FSum("i", "N_tables",
             Mul(Const("γ_5^{2+i}"), vp("TableFlag(j)", r5_c))),
    )

    # RHS: Σ_{s=1}^{5} γ^{s-1} · rv_s + RAF contributions
    # raf_1 = PC(r_cycle^(1)), raf_3 = PC(r_cycle^(3))
    rhs = add(
        rv_1,
        Mul(gamma, rv_2),
        Mul(Pow(gamma, 2), rv_3),
        Mul(Pow(gamma, 3), rv_4),
        Mul(Pow(gamma, 4), rv_5),
        Mul(Pow(gamma, 5), vp("PC", Opening(1, DIM_CYCLE))),
        Mul(Pow(gamma, 6), vp("PC", Opening(3, DIM_CYCLE))),
    )

    r6_cycle = Opening(6, DIM_CYCLE)

    return SumcheckSpec(
        name="BytecodeReadRaf",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(6, DIM_K_BC), Opening(6, DIM_CYCLE)],
        rounds="log2(K_bc) + log2(T)",
        degree="d_bc + 1",
        openings=[
            ("BytecodeRa(i) for i=0..d_bc-1",
             [Opening(6, DIM_ADDR, "K_bc^(i)"), r6_cycle]),
        ],
    )
