"""
Stage 5: RAM RA Claim Reduction

Batches 3 RamRa openings at different cycle points into a
single opening using γ-batching with eq selectors.

    Σ_{X_t} (eq(r1, X_t) + γ·eq(r2, X_t) + γ²·eq(r4, X_t))
             · RamRa(r2_K, X_t)
    = RamRa(r2_K, r1) + γ·RamRa(r2_K, r2) + γ²·RamRa(r2_K, r4)

Source: jolt-core/src/zkvm/ram/ra_claim_reduction.rs
Spec:   references/stage5.md § RamRaClaimReduction
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_RAM
from ...ast import (
    Const, Mul, Pow,
    vp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage5_ram_ra_claim_reduction() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r1_cycle = Opening(1, DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
    r4_cycle = Opening(4, DIM_CYCLE)
    r2_k_ram = Opening(2, DIM_K_RAM)
    gamma = Const("γ")

    # Batches 3 RamRa openings at different cycle points:
    # (eq(r1, X_t) + γ·eq(r2, X_t) + γ²·eq(r4, X_t)) · RamRa(r2_K, X_t)
    eq_batch = add(
        verifier.eq(r1_cycle, X_t),
        Mul(gamma, verifier.eq(r2_cycle, X_t)),
        Mul(Pow(gamma, 2), verifier.eq(r4_cycle, X_t)),
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
        opening_point=[Opening(5, DIM_CYCLE)],
        rounds="log2(T)",
        degree=2,
        openings=[
            ("RamRa", [r2_k_ram, Opening(5, DIM_CYCLE)]),
        ],
    )
