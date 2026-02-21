"""
Stage 7: Hamming Weight Claim Reduction

The final sumcheck in the pipeline.  Reduces three families of
claims about each committed RA polynomial — hamming weight (HW),
booleanity (Bool), and virtualization (Virt) — into a single
opening per polynomial at a fresh address point.

N_ra = d_instr + d_bc + d_ram  (total number of committed RA polynomials)

For each j = 0..N_ra-1:
  G_j(X_k) = Ra_j(X_k, r_6_cycle)  (marginalised over cycles)
  HW claim:   Σ G_j = H_j  (1 for instr/bc via eq normalization, RamHammingWeight for ram)
  Bool claim:  Σ eq(r_6_addr, X_k) · G_j = B_j
  Virt claim:  Σ eq(r_6_addr^(j), X_k) · G_j = V_j

Integrand:
  Σ_{j=0}^{N_ra-1} G_j(X_k) · (γ^{3j} + γ^{3j+1}·eq(r_addr, X_k)
                                + γ^{3j+2}·eq_j(X_k))

Degree: 2 (G_j=1, eq=1)

Source: jolt-core/src/zkvm/hamming_weight/claim_reduction.rs
Spec:   references/stage7.md § HammingWeightClaimReduction
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_ADDR
from ...ast import (
    Const, Mul, FSum,
    cp, vp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage7_hamming_weight_claim_reduction() -> SumcheckSpec:
    X_k = Var("X_k", DIM_ADDR)
    r6_addr = Opening(6, DIM_ADDR)
    r6_cycle = Opening(6, DIM_CYCLE)

    # G_j(X_k) = Ra_j(X_k, r_6_cycle)
    g_j = cp("Ra_j", X_k, r6_cycle)

    # Three terms per polynomial, batched with γ^{3j}, γ^{3j+1}, γ^{3j+2}:
    #   γ^{3j}   · 1            (hamming weight — no eq selector)
    #   γ^{3j+1} · eq(r_addr, X_k)   (booleanity — shared address point)
    #   γ^{3j+2} · eq(r_addr_j, X_k)  (virtualization — per-poly address point)
    r6_addr_j = Opening(6, DIM_ADDR, "addr_j")
    batch = add(
        Const("γ^{3j}"),
        Mul(Const("γ^{3j+1}"), verifier.eq(r6_addr, X_k)),
        Mul(Const("γ^{3j+2}"), verifier.eq(r6_addr_j, X_k)),
    )

    inner = FSum("j", "N_ra", Mul(g_j, batch))

    # ── RHS: Σ_j (γ^{3j}·H_j + γ^{3j+1}·B_j + γ^{3j+2}·V_j) ──
    #
    # H_j = hamming weight of G_j = Σ_{X_k} Ra_j(X_k, r_cycle^(6)):
    #   instruction/bytecode: H_j = 1  (Ra is one-hot over X_k, eq normalization)
    #   RAM: H_j = RamHammingWeight(r_cycle^(6))  (virtual poly from S6)
    #
    # B_j = booleanity opening: Ra_j(r_addr^(6), r_cycle^(6))  [cp from S6 Booleanity]
    #
    # V_j = virtualization opening: Ra_j(r_addr_j, r_cycle^(6))  [cp from S6 virtualizations]
    #   instruction RA: addr_j = r_K^(j) from InstructionRaVirtualization
    #   bytecode RA:    addr_j = r_K_bc^(j) from BytecodeReadRaf
    #   RAM RA:         addr_j = r_K_ram^(j) from RamRaVirtualization

    # Hamming weight terms
    hw = add(
        Const("Σ_{j∈instr∪bc} γ^{3j}"),                     # H_j = 1 (eq normalization)
        Mul(Const("Σ_{j∈ram} γ^{3j}"),
            vp("RamHammingWeight", r6_cycle)),               # H_j = RamHammingWeight
    )

    # Booleanity terms: B_j = Ra_j(r_addr^(6), r_cycle^(6))
    bool_claims = FSum("j", "N_ra",
        Mul(Const("γ^{3j+1}"),
            cp("Ra_j", r6_addr, r6_cycle)))

    # Virtualization terms: V_j = Ra_j(r_addr_j, r_cycle^(6))
    virt_claims = FSum("j", "N_ra",
        Mul(Const("γ^{3j+2}"),
            cp("Ra_j", Opening(6, DIM_ADDR, "addr_j"), r6_cycle)))

    rhs = add(hw, bool_claims, virt_claims)

    return SumcheckSpec(
        name="HammingWeightClaimReduction",
        sum_vars=[X_k],
        integrand=inner,
        input_claim=rhs,
        opening_point=[Opening(7, DIM_ADDR)],
        rounds="log2(N_instr)",
        degree=2,
        openings=[
            ("Ra_j for j=0..N_ra-1 (N_ra = d_instr + d_bc + d_ram)",
             [Opening(7, DIM_ADDR), r6_cycle]),
        ],
    )
