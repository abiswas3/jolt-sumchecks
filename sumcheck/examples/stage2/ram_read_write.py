"""
Stage 2: RAM Read/Write Checking

Decomposes the virtual RamReadValue and RamWriteValue into
address-indicator (RamRa) times value (RamVal) sums.
Batched with γ into a single sumcheck.

    Σ_{X_k, X_j} eq(r_cycle^(1), X_j) · RamRa(X_k, X_j)
        · (RamVal(X_k, X_j) + γ · (RamVal(X_k, X_j) + RamInc(X_j)))
    = RamReadValue(r_cycle^(1)) + γ · RamWriteValue(r_cycle^(1))

Source: jolt-core/src/zkvm/ram/read_write.rs
Spec:   references/stage2.md § RAM Read/Write Checking
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_RAM
from ...ast import (
    Const, Mul,
    vp, cp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage2_ram_read_write() -> SumcheckSpec:
    X_k = Var("X_k", DIM_K_RAM)
    X_j = Var("X_j", DIM_CYCLE)
    r_cycle = Opening(1, DIM_CYCLE)
    gamma = Const("γ")

    ram_ra  = vp("RamRa", X_k, X_j)
    ram_val = vp("RamVal", X_k, X_j)
    ram_inc = cp("RamInc", X_j)

    # RamVal + γ · (RamVal + RamInc)
    inner = add(ram_val, Mul(gamma, add(ram_val, ram_inc)))

    integrand = Mul(Mul(verifier.eq(r_cycle, X_j), ram_ra), inner)

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
        opening_point=[Opening(2, DIM_K_RAM), Opening(2, DIM_CYCLE)],
        rounds="log2(K_ram) + log2(T)",
        degree=3,
        openings=[
            ("RamVal",  [Opening(2, DIM_K_RAM), Opening(2, DIM_CYCLE)]),
            ("RamRa",   [Opening(2, DIM_K_RAM), Opening(2, DIM_CYCLE)]),
            ("RamInc",  [Opening(2, DIM_CYCLE)]),
        ],
    )
