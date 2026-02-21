"""
Stage 6: RAM RA Virtualization

Reduces the virtual RamRa opening from Stage 5 (RamRaClaimReduction)
to openings of the d_ram committed RamRa(i) polynomials.

Integrand:
  eq(r_cycle^(5), X_t) · Π_{i=0}^{d_ram-1} RamRa(i)(r_{K(i)}, X_t)

Degree: d_ram + 1

Source: jolt-core/src/zkvm/ram/ra_virtual.rs
Spec:   references/stage6.md § RamRaVirtualParams
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_RAM, DIM_ADDR
from ...ast import (
    Mul, Prod,
    vp, cp,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage6_ram_ra_virtualization() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r5_cycle = Opening(5, DIM_CYCLE)

    # Π_{i=0}^{d_ram-1} RamRa(i)(r_{K_ram^(i)}, X_t)
    ra = Prod("i", "d_ram",
              cp("RamRa(i)", Opening(2, DIM_ADDR, "K_ram^(i)"), X_t))

    integrand = Mul(verifier.eq(r5_cycle, X_t), ra)

    rhs = vp("RamRa", Opening(2, DIM_K_RAM), r5_cycle)

    return SumcheckSpec(
        name="RamRaVirtualization",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(6, DIM_CYCLE)],
        rounds="log2(T)",
        degree="d_ram + 1",
        openings=[
            ("RamRa(i) for i=0..d_ram-1",
             [Opening(2, DIM_ADDR, "K_ram^(i)"), Opening(6, DIM_CYCLE)]),
        ],
    )
