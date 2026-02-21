"""
Stage 2: RAM Output Check

Zero-check: final RAM state matches the claimed I/O values.

    Σ_{X_k} eq(r_K_ram^(2), X_k) · io_mask(X_k)
      · (RamValFinal(X_k) - ValIO(X_k))
    = 0

Source: jolt-core/src/zkvm/ram/output_check.rs
Spec:   references/stage2.md § RAM Output Check
"""

from ...defs import Var, Opening, DIM_K_RAM
from ...ast import (
    Const, Mul, VerifierPoly,
    vp, sub,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage2_ram_output_check() -> SumcheckSpec:
    X_k = Var("X_k", DIM_K_RAM)
    r_k_ram = Opening(2, DIM_K_RAM)

    ram_final = vp("RamValFinal", X_k)
    val_io    = VerifierPoly("ValIO", [X_k])
    io_mask   = VerifierPoly("io_mask", [X_k])

    integrand = Mul(
        Mul(verifier.eq(r_k_ram, X_k), io_mask),
        sub(ram_final, val_io),
    )

    return SumcheckSpec(
        name="RamOutputCheck",
        sum_vars=[X_k],
        integrand=integrand,
        input_claim=Const(0),
        opening_point=[Opening(2, DIM_K_RAM)],
        rounds="log2(K_ram)",
        degree=2,
        openings=[
            ("RamValFinal", [Opening(2, DIM_K_RAM)]),
        ],
    )
