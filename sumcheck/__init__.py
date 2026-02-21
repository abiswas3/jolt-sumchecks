"""
Sumcheck AST library for the Jolt zk-VM specification.

Modules:
    defs     — core types: DimDef, Var, Opening, PolyKind, PolyDef, ParamDef
    ast      — expression tree nodes and helper builders
    spec     — SumcheckSpec, SpartanSpec, Constraint
    printer  — fmt(), print_sumcheck(), print_spartan()
    registry — polynomial and parameter catalogs
    examples — pre-built specs for all 21 Jolt sumchecks
"""

from .defs import (
    DimDef, Var, Opening, Arg,
    DIM_CYCLE, DIM_K_RAM, DIM_K_REG, DIM_ADDR,
    DIM_K_INSTR, DIM_K_BC, DIM_N_V, DIM_GROUP,
    PolyKind, PolyDef, ParamDef,
)
from .ast import (
    Const, CommittedPoly, VirtualPoly, VerifierPoly,
    Add, Mul, Pow, Neg, Sum, FSum, Prod, Expr,
    degree, vp, cp, eq, add, sub, mul, scale,
)
from .spec import SumcheckSpec, Constraint, SpartanSpec, ProductConstraint, ProductVirtSpec
from .printer import fmt, print_sumcheck, print_spartan
from .format import Format, render, TextFormat, LatexFormat
from .registry import (
    COMMITTED_POLYS, VIRTUAL_POLYS, VERIFIER_POLYS, ALL_POLYS, PARAMS,
    print_registry,
)
