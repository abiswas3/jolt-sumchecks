"""
Sumcheck specifications — wraps the expression AST with metadata.

An AST expression (ast.py) describes *what* is being computed inside
a sum.  A *specification* adds the surrounding context: which
variables are summed over, what the claimed total is, how many
rounds the protocol runs, and what polynomial openings it produces.

This module defines two spec types, corresponding to the two
structural patterns found across Jolt's seven proving stages:


SumcheckSpec — a single-integrand sumcheck (Stages 2–7)
───────────────────────────────────────────────────────
Most sumchecks in Jolt have this shape:

    Σ_{X ∈ {0,1}^n}  f(X)  =  input_claim      (the "RHS")

where f is a single expression tree (the integrand).  After the
protocol, the verifier checks:

    f(r)  =  expected_output_claim               (the "LHS")

where r is the random opening point produced during the sumcheck.

Fields:
  name        — human label, e.g. "RamHammingBooleanity"
  sum_vars    — the variables being summed out (determines round count)
  integrand   — the Expr tree inside the Σ
  input_claim — the claimed total (RHS); often Const(0)
  degree      — max degree of the univariate round polynomials
  rounds      — symbolic round count, e.g. "log2(T)"
  openings    — polynomial openings produced: [(poly_name, [arg, ...])]


SpartanSpec — R1CS constraint-table sumcheck (Stage 1)
──────────────────────────────────────────────────────
Stage 1 (SpartanOuter) is structurally different.  Instead of one
integrand, it has a *table* of R1CS constraints.  The integrand is:

    eq((τ_t, τ_b), (X_t, X_b)) · L_{τ_c}(X_c) · Az(X_t,X_b,X_c) · Bz(X_t,X_b,X_c)

where:
  - eq is the multilinear Lagrange basis (verifier-computable)
  - L_{τ_c} is a *univariate* Lagrange interpolant over a finite
    non-hypercube domain {-5, -4, ..., 4} (the "constraint index")
  - Az and Bz are *tables* — for each (group b, constraint index c),
    they are specific linear combinations of virtual polynomials

The constraints are grouped:
  Group 0 (X_b = 0): 10 constraints with boolean Az guards, ~64-bit Bz
  Group 1 (X_b = 1): 9 constraints with boolean Az guards, ~128-bit Bz
                      + 1 zero-padded constraint

Each constraint row is a Constraint(label, az, bz) where az and bz
are Expr trees over virtual polynomials evaluated at the cycle
variable X_t.

The sumcheck proves that Az · Bz = 0 for every constraint row at
every timestep — i.e. the execution trace satisfies all R1CS
constraints.
"""

from __future__ import annotations
from dataclasses import dataclass, field

from .defs import Var, Arg, Opening
from .ast import Expr, degree


# ═══════════════════════════════════════════════════════════════════
# Single sumcheck (Stages 2–7)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SumcheckSpec:
    """A single-integrand sumcheck: Σ_{vars} integrand = input_claim.

    Fields:
      sum_vars      — the variables being summed out
      integrand     — the expression inside the Σ (LHS)
      input_claim   — the claimed total (RHS)
      opening_point — the fresh random point produced by the protocol
                      (one Opening per sum_var)
      rounds        — symbolic round count, e.g. "log2(T)"
      degree        — stated degree; cross-check with inferred_degree
      openings      — polynomial openings produced after the sumcheck

    The degree is also auto-inferred from the integrand via
    inferred_degree, so specs can be validated:
        assert sc.degree == sc.inferred_degree  (for non-parametric)
    """
    name: str
    sum_vars: list[Var]
    integrand: Expr
    input_claim: Expr                               # RHS
    opening_point: list[Opening]                    # fresh point (one per sum_var)
    rounds: str                                     # e.g. "log2(T)"
    degree: int | str                               # stated degree for cross-checking
    openings: list[tuple[str, list[Arg]]] = field(default_factory=list)

    @property
    def inferred_degree(self) -> int:
        """Auto-computed from the integrand's MLE structure."""
        return degree(self.integrand)


# ═══════════════════════════════════════════════════════════════════
# R1CS constraint row (for Spartan)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Constraint:
    """One row of the R1CS constraint table.

    The Spartan sumcheck enforces Az · Bz = 0 for every row
    at every timestep.

    Az is the "guard" — typically a boolean expression that selects
    when this constraint is active.  When Az = 0, the constraint
    is trivially satisfied regardless of Bz.

    Bz is the "value" — the equality that must hold when the guard
    is active.  When Az = 1, we need Bz = 0.

    Together, Az · Bz = 0 means: "if the guard is on, then Bz = 0."

    Example:
        Constraint(
            label = "RamReadEqRamWriteIfLoad",
            az    = vp:OpFlags(Load)(X_t),
            bz    = vp:RamReadValue(X_t) - vp:RamWriteValue(X_t),
        )
        # meaning: IF it's a Load instruction, THEN RamRead == RamWrite
    """
    label: str
    az: Expr        # Guard expression (typically boolean-valued)
    bz: Expr        # Value expression (must be zero when guard is on)


# ═══════════════════════════════════════════════════════════════════
# Product constraint row (for Stage 2 product virtualization)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProductConstraint:
    """One product constraint: output = left · right.

    Stage 2's product virtualization proves that certain virtual
    polynomials are products of two factor polynomials.  Each row
    of the product table states:

        output(X_t) = left(X_t) · right(X_t)   for all timesteps

    Example:
        ProductConstraint(
            label="Product",
            left=vp("LeftInstructionInput", X_t),
            right=vp("RightInstructionInput", X_t),
            output=vp("Product", X_t),
        )
    """
    label: str
    left: Expr
    right: Expr
    output: Expr


# ═══════════════════════════════════════════════════════════════════
# Product virtualization spec (Stage 2)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class ProductVirtSpec:
    """Product virtualization sumcheck — proves output = left · right.

    The integrand has the structure:

        eq(r_cycle^(1), X_t) · L(τ_c, X_c) · Left(X_t, X_c) · Right(X_t, X_c)

    RHS = Σ_{X_c} L(τ_c, X_c) · Output(r_cycle^(1), X_c)

    The sum runs over X_t ∈ {0,1}^{log₂ T} and X_c ∈ constraint_domain.
    """
    name: str
    cycle_var: Var
    constraint_domain: list[int]
    constraints: list[ProductConstraint]
    input_claim: Expr | None = None                    # RHS (output polys at prior opening)
    openings: list[tuple[str, list[Arg]]] = field(default_factory=list)

    @property
    def rounds(self) -> str:
        return f"{self.cycle_var.log_size} + {len(self.constraint_domain)}"


# ═══════════════════════════════════════════════════════════════════
# Spartan outer sumcheck (Stage 1)
# ═══════════════════════════════════════════════════════════════════

@dataclass
class SpartanSpec:
    """Spartan outer sumcheck — batched R1CS constraint satisfaction.

    This represents Stage 1 of Jolt's proving pipeline.  The prover
    demonstrates that the entire execution trace satisfies all R1CS
    constraints simultaneously, via a single sumcheck.

    The integrand has a fixed structure:

        eq((τ_t, τ_b), (X_t, X_b)) · L_{τ_c}(X_c) · Az · Bz

    where τ_t, τ_b, τ_c are Schwartz-Zippel randomness from the
    verifier, and Az/Bz are looked up from the constraint table
    by the pair (X_b, X_c).

    The sum runs over three axes:
        X_t ∈ {0,1}^{log₂ T}    — cycle (timestep)
        X_b ∈ {0,1}             — constraint group selector
        X_c ∈ {-5, ..., 4}      — constraint index within group

    Note: X_c lives on a NON-HYPERCUBE domain {-5,...,4}, so the
    Lagrange polynomial L_{τ_c}(X_c) is a univariate Lagrange
    interpolant, not the multilinear eq polynomial.

    Fields:
        name              — display name
        cycle_var         — the X_t variable (the main "timestep" axis)
        group_var         — the X_b variable (binary group selector)
        constraint_domain — the finite domain for X_c, e.g. [-5,...,4]
        groups            — groups[b] is a list of Constraint objects,
                            one per element of constraint_domain
        input_claim       — the RHS (= 0 for R1CS satisfaction)
        openings          — polynomial openings produced by this stage
    """
    name: str
    cycle_var: Var                          # X_t ∈ {0,1}^{log₂ T}
    group_var: Var                          # X_b ∈ {0,1}
    constraint_domain: list[int]            # e.g. [-5, -4, ..., 4]
    groups: list[list[Constraint]]          # groups[b][i] = constraint at domain[i]
    input_claim: Expr                       # RHS (= 0 for R1CS satisfaction)
    openings: list[tuple[str, list[Arg]]] = field(default_factory=list)

    @property
    def num_constraints(self) -> int:
        """Total constraint count across all groups."""
        return sum(len(g) for g in self.groups)

    @property
    def rounds(self) -> str:
        """Symbolic round count: log₂(T) cycle rounds + 1 group + |domain| constraint."""
        return f"{self.cycle_var.log_size} + 1 + {len(self.constraint_domain)}"
