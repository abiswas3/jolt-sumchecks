"""
Stage 2: Product Virtualization

Proves that 5 virtual "product" polynomials really are the
product of their two factor polynomials.  Uses a batched
sumcheck over the domain {-2, -1, 0, 1, 2} with a univariate
Lagrange selector, same trick as Stage 1.

    Σ_{X_t, X_c} eq(r_cycle^(1), X_t) · L(τ_c, X_c)
                    · Left(X_t, X_c) · Right(X_t, X_c)
    = Σ_{X_c} L(τ_c, X_c) · Output(r_cycle^(1), X_c)

Source: jolt-core/src/zkvm/spartan/product_virtual.rs
Spec:   references/stage2.md § Product Constraints
"""

from ...defs import Var, Opening, DIM_CYCLE
from ...ast import (
    Const, VirtualPoly,
    vp, sub, add,
)
from ...spec import ProductConstraint, ProductVirtSpec


def stage2_product_virtualization() -> ProductVirtSpec:
    X_t = Var("X_t", DIM_CYCLE)

    def v(name: str) -> VirtualPoly:
        return vp(name, X_t)

    constraints = [
        # c = -2: Product = LeftInstructionInput · RightInstructionInput
        ProductConstraint(
            "Product",
            left=v("LeftInstructionInput"),
            right=v("RightInstructionInput"),
            output=v("Product"),
        ),
        # c = -1: WriteLookupOutputToRD = IsRdNotZero · OpFlags(WriteLookupOutputToRD)
        ProductConstraint(
            "WriteLookupOutputToRD",
            left=v("InstructionFlags(IsRdNotZero)"),
            right=v("OpFlags(WriteLookupOutputToRD)"),
            output=v("WriteLookupOutputToRD"),
        ),
        # c = 0: WritePCtoRD = IsRdNotZero · OpFlags(Jump)
        ProductConstraint(
            "WritePCtoRD",
            left=v("InstructionFlags(IsRdNotZero)"),
            right=v("OpFlags(Jump)"),
            output=v("WritePCtoRD"),
        ),
        # c = 1: ShouldBranch = LookupOutput · InstructionFlags(Branch)
        ProductConstraint(
            "ShouldBranch",
            left=v("LookupOutput"),
            right=v("InstructionFlags(Branch)"),
            output=v("ShouldBranch"),
        ),
        # c = 2: ShouldJump = OpFlags(Jump) · (1 - NextIsNoop)
        ProductConstraint(
            "ShouldJump",
            left=v("OpFlags(Jump)"),
            right=sub(Const(1), v("NextIsNoop")),
            output=v("ShouldJump"),
        ),
    ]

    # After the sumcheck, the prover opens the 9 unique factor polys
    factor_polys = [
        "LeftInstructionInput", "RightInstructionInput",
        "InstructionFlags(IsRdNotZero)",
        "OpFlags(WriteLookupOutputToRD)", "OpFlags(Jump)",
        "LookupOutput", "InstructionFlags(Branch)",
        "NextIsNoop", "OpFlags(VirtualInstruction)",
    ]

    # RHS: the 5 output polys evaluated at the prior stage's opening point
    r1_cycle = Opening(1, DIM_CYCLE)
    rhs = add(
        vp("Product", r1_cycle),
        vp("WriteLookupOutputToRD", r1_cycle),
        vp("WritePCtoRD", r1_cycle),
        vp("ShouldBranch", r1_cycle),
        vp("ShouldJump", r1_cycle),
    )

    return ProductVirtSpec(
        name="SpartanProductVirtualization",
        cycle_var=X_t,
        constraint_domain=list(range(-2, 3)),  # [-2, -1, 0, 1, 2]
        constraints=constraints,
        input_claim=rhs,
        openings=[
            (name, [Opening(2, DIM_CYCLE)]) for name in factor_polys
        ],
    )
