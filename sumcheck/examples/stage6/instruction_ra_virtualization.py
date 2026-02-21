"""
Stage 6: Instruction RA Virtualization

Reduces the d_v virtual InstructionRa(i) openings from Stage 5
(InstructionReadRaf) to openings of the d_instr committed
InstructionRa(j) polynomials.  Each virtual chunk is the product
of M committed chunks.

Integrand:
  eq(r_cycle^(5), X_t) · Σ_{i=0}^{d_v-1} γ^i
    · Π_{j=0}^{M-1} InstructionRa(iM+j)(r_{K(iM+j)}, X_t)

Degree: M + 1

Source: jolt-core/src/zkvm/instruction_lookups/ra_virtual.rs
Spec:   references/stage6.md § InstructionRaSumcheckParams
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_ADDR, DIM_N_V
from ...ast import (
    Const, Mul, FSum, Prod,
    cp,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage6_instruction_ra_virtualization() -> SumcheckSpec:
    X_t = Var("X_t", DIM_CYCLE)
    r5_cycle = Opening(5, DIM_CYCLE)
    gamma = Const("γ")

    # Σ_{i=0}^{d_v-1} γ^i · Π_{j=0}^{M-1} InstructionRa(iM+j)(r_{K(iM+j)}, X_t)
    inner = FSum("i", "d_v",
        Mul(Const("γ^i"),
            Prod("j", "M",
                 cp("InstructionRa(iM+j)", Opening(5, DIM_ADDR, "K^(iM+j)"), X_t))))

    integrand = Mul(verifier.eq(r5_cycle, X_t), inner)

    # RHS: Σ_{i=0}^{d_v-1} γ^i · vp:InstructionRa(i)(r_{K(i)}, r_cycle^(5))
    from ...ast import vp
    rhs = FSum("i", "d_v",
        Mul(Const("γ^i"),
            vp("InstructionRa(i)", Opening(5, DIM_N_V, "K_instr^(i)"), r5_cycle)))

    return SumcheckSpec(
        name="InstructionRaVirtualization",
        sum_vars=[X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(6, DIM_CYCLE)],
        rounds="log2(T)",
        degree="M + 1",
        openings=[
            ("InstructionRa(j) for j=0..d_instr-1",
             [Opening(5, DIM_ADDR, "K^(j)"), Opening(6, DIM_CYCLE)]),
        ],
    )
