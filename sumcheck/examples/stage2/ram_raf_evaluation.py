"""
Stage 2: RAM RAF Evaluation

Proves that the RamRa polynomial actually encodes the RAM
address, by summing RamRa · unmap(X_k) over the address space.

    Σ_{X_k} RamRa(X_k, r_cycle^(1)) · unmap(X_k)
    = RamAddress(r_cycle^(1))

Source: jolt-core/src/zkvm/ram/raf_evaluation.rs
Spec:   references/stage2.md § RAM RAF Evaluation
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_RAM
from ...ast import (
    Mul, VerifierPoly,
    vp,
)
from ...spec import SumcheckSpec


def stage2_ram_raf_evaluation() -> SumcheckSpec:
    X_k = Var("X_k", DIM_K_RAM)
    r_cycle = Opening(1, DIM_CYCLE)

    ram_ra = vp("RamRa", X_k, r_cycle)
    unmap  = VerifierPoly("unmap", [X_k])

    integrand = Mul(ram_ra, unmap)

    rhs = vp("RamAddress", r_cycle)

    return SumcheckSpec(
        name="RamRafEvaluation",
        sum_vars=[X_k],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(2, DIM_K_RAM)],
        rounds="log2(K_ram)",
        degree=2,
        openings=[
            ("RamRa", [Opening(2, DIM_K_RAM), Opening(1, DIM_CYCLE)]),
        ],
    )
