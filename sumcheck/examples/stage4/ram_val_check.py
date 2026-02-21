"""
Stage 4: RAM Val Check

Proves that RamVal is consistent with the RAM increments via
a less-than ordering check.

    Σ_{X_t} RamInc(X_t) · RamRa(r2_K, X_t) · (LT(X_t, r2_cycle) + γ)
    = (RamVal(r2_K, r2_cycle) - RamValInit(r2_K))
      + γ · (RamValFinal(r2_K) - RamValInit(r2_K))

Source: jolt-core/src/zkvm/ram/val_check.rs
Spec:   references/stage4.md § RamValCheck
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_RAM
from ...ast import (
    Const, Mul, VerifierPoly,
    vp, cp, add, sub,
)
from ...spec import SumcheckSpec


def stage4_ram_val_check() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r2_cycle = Opening(2, DIM_CYCLE)
    r2_k_ram = Opening(2, DIM_K_RAM)
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
        opening_point=[Opening(4, DIM_CYCLE)],
        rounds="log2(T)",
        degree=3,
        openings=[
            ("RamInc", [Opening(4, DIM_CYCLE)]),
            ("RamRa",  [r2_k_ram, Opening(4, DIM_CYCLE)]),
        ],
    )
