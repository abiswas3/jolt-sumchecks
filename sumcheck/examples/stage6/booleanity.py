"""
Stage 6: Booleanity

Proves that ALL committed RA polynomials (InstructionRa, BytecodeRa,
RamRa — d = d_instr + d_bc + d_ram total) are Boolean-valued.
Uses the booleanity trick: p is boolean iff p^2 - p = 0.

The eq polynomial binds over the concatenated (address, cycle) space.
Batching uses even powers γ^{2j} to separate the d polynomials.

Integrand:
  eq((r_addr, r_cycle), (X_k, X_t))
    · Σ_{j=0}^{d-1} γ^{2j} · (Ra_j(X_k, X_t)^2 - Ra_j(X_k, X_t))

Degree: 3 (eq=1, Ra^2-Ra=2)

Source: jolt-core/src/zkvm/booleanity/mod.rs
Spec:   references/stage6.md § BooleanitySumcheck
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_ADDR
from ...ast import (
    Const, Mul, Pow, FSum, VerifierPoly,
    cp, sub,
)
from ...spec import SumcheckSpec


def stage6_booleanity() -> SumcheckSpec:
    X_k = Var("X_k", DIM_ADDR)
    X_t = Var("X_t", DIM_CYCLE)
    r_addr = Opening(5, DIM_ADDR)
    r_cycle = Opening(5, DIM_CYCLE)

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
        opening_point=[Opening(6, DIM_ADDR), Opening(6, DIM_CYCLE)],
        rounds="log2(N_instr) + log2(T)",
        degree=3,
        openings=[
            ("Ra_j for j=0..d-1 (d = d_instr + d_bc + d_ram)",
             [Opening(6, DIM_ADDR), Opening(6, DIM_CYCLE)]),
        ],
    )
