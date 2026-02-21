"""
Core type definitions for the Jolt sumcheck AST.

This module contains the foundational types shared across the AST,
registry, and specification modules:

  DimDef    — a dimension of a polynomial's hypercube domain
  Var       — a free variable being summed over in a sumcheck
  Opening   — a fixed opening point produced by a prior-stage sumcheck
  Arg       — union type: Var | Opening
  PolyKind  — enum: COMMITTED, VIRTUAL, VERIFIER
  PolyDef   — one polynomial in the Jolt system
  ParamDef  — one system parameter
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Union


# ═══════════════════════════════════════════════════════════════════
# Domain dimension
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DimDef:
    """One dimension of a polynomial's hypercube domain.

    A polynomial over {0,1}^(log2(size1)) × {0,1}^(log2(size2)) × ...
    has one DimDef per factor of that product.

    Fields:
        size        — symbolic parameter name: "T", "K_ram", "N_instr", or "2"
        label       — short symbol used in opening labels: "cycle", "K_ram", "addr"
        description — human-readable name for display: "RAM address", "one-hot chunk"
    """
    size: str
    label: str
    description: str = ""


# ── Standard dimensions used across Jolt ──

DIM_CYCLE   = DimDef("T",       "cycle",   "cycle/timestep")
DIM_K_RAM   = DimDef("K_ram",   "K_ram",   "RAM address")
DIM_K_REG   = DimDef("K_reg",   "K_reg",   "register index")
DIM_ADDR    = DimDef("N_instr", "addr",    "one-hot chunk")
DIM_K_INSTR = DimDef("K_instr", "K_instr", "instruction address")
DIM_K_BC    = DimDef("K_bc",    "K_bc",    "bytecode address")
DIM_N_V     = DimDef("N_v",     "N_v",     "virtual chunk")
DIM_GROUP   = DimDef("2",       "group",   "constraint group")


# ═══════════════════════════════════════════════════════════════════
# Argument types — what a polynomial is evaluated at
# ═══════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Var:
    """A free variable being summed over in the sumcheck.

    Example:
        X_t = Var("X_t", DIM_CYCLE)
        # represents X_t ∈ {0,1}^{log₂ T}  (the cycle variable)
    """
    name: str       # Display name: "X_t", "X_k", "X_b"
    dim: DimDef     # Which domain dimension this variable ranges over

    @property
    def log_size(self) -> str:
        """Log₂ of the domain size, as a string.

        For numeric sizes (e.g. "2"), computes the actual log₂ (→ "1").
        For symbolic sizes (e.g. "T"), returns "log2(T)".
        """
        try:
            n = int(self.dim.size)
            return str(int(math.log2(n)))
        except (ValueError, TypeError):
            return f"log2({self.dim.size})"


@dataclass(frozen=True)
class Opening:
    """A fixed opening point produced by a prior-stage sumcheck.

    After a sumcheck over n variables completes, the verifier has
    sent n random challenges forming an "opening point."  Later
    stages reference these fixed points.

    The dim field ties this opening to a specific domain dimension
    of the polynomial being opened.  For example, RamRa has domain
    [DIM_K_RAM, DIM_CYCLE] and its opening might be:
        [Opening(2, DIM_K_RAM), Opening(4, DIM_CYCLE)]
    — the addr part from stage 2, the cycle part from stage 4.

    Example:
        Opening(5, DIM_CYCLE)
        # = r_cycle^(5): the cycle opening from Stage 5
    """
    stage: int
    dim: DimDef
    label: str = ""   # Override print label; defaults to dim.label

    @property
    def print_label(self) -> str:
        """The label used in r_label^(stage) rendering."""
        return self.label or self.dim.label


# A polynomial argument is either a free variable or a fixed opening.
Arg = Union[Var, Opening]


# ═══════════════════════════════════════════════════════════════════
# Polynomial kinds
# ═══════════════════════════════════════════════════════════════════


class PolyKind(Enum):
    """How a polynomial is verified.

    COMMITTED — committed to PCS, verifier can check openings (green in spec)
    VIRTUAL   — prover claims openings, reduced to committed via sumchecks (orange)
    VERIFIER  — verifier computes directly from public data
    """
    COMMITTED = auto()
    VIRTUAL = auto()
    VERIFIER = auto()


# ═══════════════════════════════════════════════════════════════════
# Polynomial definition
# ═══════════════════════════════════════════════════════════════════


@dataclass
class PolyDef:
    """One polynomial in the Jolt system.

    Every polynomial is an MLE:  {0,1}^n → F
    where n = Σ log2(dim.size) over all domain dimensions.

    Callable: a PolyDef can be called with arguments to produce the
    corresponding AST node, using its kind to pick the right type:

        from sumcheck.registry import poly
        Rs1Ra = poly("Rs1Ra")
        Rs1Ra(X_k, X_t)   # → VirtualPoly("Rs1Ra", [X_k, X_t])

    Fields:
        name        — spec name, e.g. "InstructionRa(i)", "LookupOutput"
        kind        — COMMITTED, VIRTUAL, or VERIFIER
        domain      — list of dimensions, e.g. [DIM_K_RAM, DIM_CYCLE]
        description — how the polynomial is constructed / defined
        category    — grouping for display, e.g. "Program counter", "RAM"
    """
    name: str
    kind: PolyKind
    domain: list[DimDef]
    description: str
    category: str = ""

    def __call__(self, *args: Arg):
        """Build an AST node from this polynomial definition.

        Returns CommittedPoly, VirtualPoly, or VerifierPoly based on kind.
        """
        # Lazy import to avoid circular dependency (ast imports defs)
        from .ast import CommittedPoly, VirtualPoly, VerifierPoly
        cls = {
            PolyKind.COMMITTED: CommittedPoly,
            PolyKind.VIRTUAL: VirtualPoly,
            PolyKind.VERIFIER: VerifierPoly,
        }[self.kind]
        return cls(self.name, list(args))


# ═══════════════════════════════════════════════════════════════════
# Parameter definition
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ParamDef:
    """One system parameter.

    Fields:
        symbol      — LaTeX-ish symbol, e.g. "d_instr", "N_instr"
        name        — code-level name, e.g. "instruction_d", "k_chunk"
        description — one-line description
        formula     — derivation formula, or "" if primitive
    """
    symbol: str
    name: str
    description: str
    formula: str = ""
