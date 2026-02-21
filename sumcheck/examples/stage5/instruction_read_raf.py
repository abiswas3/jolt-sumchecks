"""
Stage 5: Instruction Read RAF

Decomposes the three batched instruction lookup claims
(LookupOutput, LeftLookupOperand, RightLookupOperand) into the
product of virtual RA chunks times table/operand evaluations.

Parameters (hardcoded):
  d_v = 16      virtual RA chunks (128 / log2(N_v), N_v = 256)
  N_tables = 42 lookup tables

The integrand factors as:
  eq(r_cycle^(2), X_t)
    · Ra(X_k, X_t)                        — product of d_v chunks
    · (val(X_k, X_t) + γ · raf(X_k, X_t)) — table + operand

Ra(X_k, X_t) = Π_{i=0}^{d_v-1} InstructionRa(i)(X_k^(i), X_t)
val(X_k, X_t) = Σ_{i=0}^{N_tables-1} T_i(X_k) · TableFlag_i(X_t)
raf(X_k, X_t) = (1-RafFlag) · (LeftOp(X_k) + γ·RightOp(X_k))
                + RafFlag · γ · unmap(X_k)

Source: jolt-core/src/zkvm/instruction_lookups/read_raf.rs
Spec:   references/stage5.md § InstructionReadRafSumcheckProver
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_INSTR, DIM_N_V
from ...ast import (
    Const, Mul, Pow, FSum, Prod, VerifierPoly,
    vp, add, sub,
)
from ...registry import verifier
from ...spec import SumcheckSpec

D_V = 16
N_TABLES = 42


def stage5_instruction_read_raf() -> SumcheckSpec:
    # The address variable spans the full instruction address space:
    # X_k = (X_k^(0), ..., X_k^(d_v-1)), each chunk in {0,1}^log2(N_v)
    X_k = Var("X_k", DIM_K_INSTR)  # 128 bits total
    X_t = Var("X_t", DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
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
        Mul(verifier.eq(r2_cycle, X_t), ra),
        add(val, Mul(gamma, raf)),
    )

    # ── Openings produced ──
    r5_cycle = Opening(5, DIM_CYCLE)
    openings = [
        # d_v virtual RA chunks, each at (r_addr_chunk_i, r_cycle^(5))
        ("InstructionRa(i) for i=0..d_v-1",
         [Opening(5, DIM_N_V, "K_instr^(i)"), r5_cycle]),
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
        opening_point=[Opening(5, DIM_K_INSTR), Opening(5, DIM_CYCLE)],
        rounds="log2(K_instr) + log2(T)",
        degree=19,
        openings=openings,
    )
