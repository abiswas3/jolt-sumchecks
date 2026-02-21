"""
Stage 4: Registers Read/Write Checking

Decomposes the register read/write values into address-indicator
times value sums, batched with γ.

    Σ_{X_k, X_t} eq(r3_cycle, X_t) · (
        RdWa·(RdInc + Val) + γ·Rs1Ra·Val + γ²·Rs2Ra·Val
    )
    = RdWriteValue(r3) + γ·Rs1Value(r3) + γ²·Rs2Value(r3)

Source: jolt-core/src/zkvm/registers/read_write.rs
Spec:   references/stage4.md § RegistersReadWriteChecking
"""

from ...defs import Var, Opening, DIM_CYCLE, DIM_K_REG
from ...ast import (
    Const, Mul, Pow,
    vp, cp, add,
)
from ...registry import verifier
from ...spec import SumcheckSpec


def stage4_registers_read_write() -> SumcheckSpec:
    X_k = Var("X_k", DIM_K_REG)
    X_t = Var("X_t", DIM_CYCLE)
    r3_cycle = Opening(3, DIM_CYCLE)
    gamma = Const("γ")

    rd_wa   = vp("RdWa", X_k, X_t)
    rs1_ra  = vp("Rs1Ra", X_k, X_t)
    rs2_ra  = vp("Rs2Ra", X_k, X_t)
    reg_val = vp("RegistersVal", X_k, X_t)
    rd_inc  = cp("RdInc", X_t)

    # eq(r3, X_t) · (RdWa·(RdInc+Val) + γ·Rs1Ra·Val + γ²·Rs2Ra·Val)
    integrand = Mul(
        verifier.eq(r3_cycle, X_t),
        add(
            Mul(rd_wa, add(rd_inc, reg_val)),
            Mul(gamma, Mul(rs1_ra, reg_val)),
            Mul(Pow(gamma, 2), Mul(rs2_ra, reg_val)),
        ),
    )

    rhs = add(
        vp("RdWriteValue", r3_cycle),
        Mul(gamma, vp("Rs1Value", r3_cycle)),
        Mul(Pow(gamma, 2), vp("Rs2Value", r3_cycle)),
    )

    return SumcheckSpec(
        name="RegistersReadWriteChecking",
        sum_vars=[X_k, X_t],
        integrand=integrand,
        input_claim=rhs,
        opening_point=[Opening(4, DIM_K_REG), Opening(4, DIM_CYCLE)],
        rounds="log2(K_reg) + log2(T)",
        degree=3,
        openings=[
            ("RegistersVal", [Opening(4, DIM_K_REG), Opening(4, DIM_CYCLE)]),
            ("Rs1Ra",        [Opening(4, DIM_K_REG), Opening(4, DIM_CYCLE)]),
            ("Rs2Ra",        [Opening(4, DIM_K_REG), Opening(4, DIM_CYCLE)]),
            ("RdWa",         [Opening(4, DIM_K_REG), Opening(4, DIM_CYCLE)]),
            ("RdInc",        [Opening(4, DIM_CYCLE)]),
        ],
    )
