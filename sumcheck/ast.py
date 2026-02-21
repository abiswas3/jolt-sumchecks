"""
Expression AST for sumcheck integrands.

A sumcheck proves a claim of the form:

    Σ_{x ∈ {0,1}^n}  f(x)  =  claimed_sum

where f(x) is the "integrand" — an algebraic expression built from
polynomial evaluations and arithmetic.  This module defines an AST
(abstract syntax tree) that can represent any such f(x).


Key simplification: all polynomials are MLEs
────────────────────────────────────────────

In Jolt, every polynomial is the **multilinear extension** (MLE) of
a function  {0,1}^n → F.  This means every polynomial leaf has
degree ≤ 1 in each variable — it is *multilinear*.

This makes degree analysis trivial: the degree of a product of k
MLEs is exactly k (each contributes degree 1).  We exploit this to
auto-compute the sumcheck degree from the expression tree via
degree(expr), so you never need to specify it by hand.


The tree has two kinds of nodes:

  LEAVES — polynomial evaluations and constants.  These are the
  atomic building blocks.  Every leaf carries an argument list
  describing *what* it is evaluated at (free variables being summed
  over, or fixed opening points from prior stages).

  INTERNAL NODES — arithmetic combinators (Add, Mul, Pow, Neg) and
  hypercube summation (Sum).  They combine sub-expressions into
  larger ones.


Leaf taxonomy
─────────────

All polynomial leaves are MLEs of functions {0,1}^n → F.
They differ in *who* can evaluate them:

  Const          A field element.  May be numeric (0, 1, 4) or
                 symbolic ("gamma", "2^64").

  CommittedPoly  An MLE that is *committed* to the polynomial
                 commitment scheme (PCS).  The verifier can ask the
                 PCS to confirm any claimed evaluation.  Printed in
                 GREEN in the spec (the \\cp{} macro).
                 Examples: cp:InstructionRa(i), cp:RamInc

  VirtualPoly    An MLE the prover *claims* evaluations of, but
                 that is NOT directly committed.  Instead it is
                 derived from committed polynomials (e.g. a product
                 of committed one-hot chunks).  Printed in ORANGE
                 in the spec (the \\vp{} macro).
                 Examples: vp:LookupOutput, vp:RamRa

  VerifierPoly   An MLE the verifier can compute on its own — no
                 prover help needed.
                 Examples: eq(r, x)  (multilinear Lagrange basis),
                           T_i(x)   (lookup-table MLE),
                           LT(x, r) (less-than MLE),
                           unmap(x) (bit-vector → integer MLE)


Argument types
──────────────

Every polynomial evaluation needs to know *where* it is evaluated.
Arguments are either:

  Var(name, log_size)
      A free variable that the sumcheck sums over.
      name     — display name, e.g. "X_t" (cycle), "X_k" (address)
      log_size — log₂ of the domain size, e.g. "log2(T)"

  Opening(stage, label)
      A fixed field-element vector produced by a prior sumcheck.
      stage — which stage produced it (1–7)
      label — human name, e.g. "cycle", "addr", "K_instr^(i)"

When pretty-printed, Var shows its name ("X_t") and Opening shows
as "r_label^(stage)" — e.g. "r_cycle^(5)".


Helper constructors
───────────────────

Building deeply nested Add/Mul/Neg trees by hand is tedious.
Use the helpers at the bottom of this file:

  vp("name", arg1, arg2)   →  VirtualPoly("name", [arg1, arg2])
  cp("name", arg1)          →  CommittedPoly("name", [arg1])
  eq(fixed, free)           →  VerifierPoly("eq", [fixed, free])
  add(a, b, c)              →  Add(Add(a, b), c)
  sub(a, b, c)              →  a + (-b) + (-c)
  mul(a, b, c)              →  Mul(Mul(a, b), c)
  scale(2, expr)            →  Mul(Const(2), expr)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Union

from .defs import (  # noqa: F401 — re-exported
    DimDef, Var, Opening, Arg,
    DIM_CYCLE, DIM_K_RAM, DIM_K_REG, DIM_ADDR,
    DIM_K_INSTR, DIM_K_BC, DIM_N_V, DIM_GROUP,
)


# ═══════════════════════════════════════════════════════════════════
# Leaf nodes — the terminals of the expression tree
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Const:
    """A field constant.

    Numeric values (0, 1, 4) are stored as int.
    Symbolic values ("gamma", "gamma^{3j}", "2^64") are stored as str
    — they represent quantities known at proving time but not hard-coded.

    Examples:
        Const(0)           — the zero element
        Const(1)           — the identity
        Const("gamma")     — a Fiat-Shamir challenge
        Const("2^64")      — a large constant from the ISA
    """
    value: Union[int, float, str]


@dataclass
class CommittedPoly:
    """An MLE committed to the PCS (polynomial commitment scheme).

    Multilinear: degree ≤ 1 in each variable.
    The prover sends a commitment at the start of the protocol.
    The verifier can later ask the PCS to verify any claimed
    evaluation p(r) = v.

    In the Jolt spec these are printed in GREEN via the \\cp{} macro.

    Examples:
        CommittedPoly("InstructionRa(0)", [X_k, X_t])
        CommittedPoly("RamInc", [X_t])

    Fields:
        name — polynomial name, matching the spec notation
        args — evaluation point: list of Var and/or Opening
    """
    name: str
    args: list[Arg]


@dataclass
class VirtualPoly:
    """A virtual MLE — derived from committed ones, NOT committed.

    Multilinear: degree ≤ 1 in each variable.
    The prover claims evaluations, but correctness is enforced by
    later sumchecks that decompose virtuals into committed pieces.
    For example, vp:InstructionRa(i) is a *product* of several
    committed one-hot chunks cp:InstructionRa(j).

    In the Jolt spec these are printed in ORANGE via the \\vp{} macro.

    Examples:
        VirtualPoly("LookupOutput", [X_t])
        VirtualPoly("RamRa", [Opening(2, "K_ram"), X_t])

    Fields:
        name — polynomial name, matching the spec notation
        args — evaluation point: list of Var and/or Opening
    """
    name: str
    args: list[Arg]


@dataclass
class VerifierPoly:
    """A verifier-computable MLE — no prover help needed.

    Multilinear: degree ≤ 1 in each variable.
    The verifier can evaluate these from public data alone.

    Examples:
        VerifierPoly("eq", [Opening(1, "cycle"), Var("X_t", "log2(T)")])
            — the multilinear eq polynomial: eq(r, x) = Π_i (r_i·x_i + (1-r_i)(1-x_i))
              equals 1 when x = r on the hypercube, 0 otherwise.

        VerifierPoly("T_3", [Var("X_k", "log2(K_instr)")])
            — MLE of lookup table #3

        VerifierPoly("LT", [Var("X_t", "log2(T)"), Opening(4, "cycle")])
            — MLE of the less-than function

    Fields:
        name — polynomial name
        args — evaluation point: list of Var and/or Opening
    """
    name: str
    args: list[Arg]


# ═══════════════════════════════════════════════════════════════════
# Internal nodes — arithmetic over sub-expressions
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Add:
    """Sum of two expressions: left + right.

    For n-ary sums, chain:  Add(Add(a, b), c)
    or use the helper:      add(a, b, c)
    """
    left: Expr
    right: Expr


@dataclass
class Mul:
    """Product of two expressions: left · right.

    For n-ary products, chain:  Mul(Mul(a, b), c)
    or use the helper:          mul(a, b, c)
    """
    left: Expr
    right: Expr


@dataclass
class Pow:
    """Integer power: base^exponent.

    Used for the booleanity check pattern p^2 - p,
    where exponent = 2.
    """
    base: Expr
    exponent: int


@dataclass
class Neg:
    """Additive negation: −expr.

    Subtraction a - b is represented as Add(a, Neg(b)).
    The pretty-printer detects this pattern and prints "a - b".
    """
    expr: Expr


@dataclass
class Sum:
    """Hypercube summation: Σ_{var ∈ {0,1}^n} body.

    This is the sum that a sumcheck *proves* — the prover convinces
    the verifier of the total without the verifier evaluating every
    term.  After the protocol, var is bound to a random opening point.

    Fields:
        var  — the variable being summed out
        body — the expression inside the sum
    """
    var: Var
    body: Expr


@dataclass
class FSum:
    """Symbolic finite sum: Σ_{var=0}^{n-1} body.

    Like Prod but additive. Represents a sum of n copies of body
    where the index variable appears literally in polynomial names.

    Fields:
        var  — index variable name, e.g. "i"
        n    — number of terms: int (42) or symbolic str ("N_tables")
        body — expression template (one term of the sum)

    Degree: degree(body) (addition doesn't increase degree).
    """
    var: str
    n: Union[int, str]
    body: Expr


@dataclass
class Prod:
    """Symbolic product: Π_{var=0}^{n-1} body.

    Represents a product of n copies of body, where the index variable
    appears literally in polynomial names inside body. The body is a
    *template* — e.g. vp("InstructionRa(i)", X_k, X_t) where "i" in
    the name matches the index var.

    Fields:
        var  — index variable name, e.g. "i"
        n    — fan-in: int (16) or symbolic str ("d_v", "d_ram")
        body — expression template (one factor of the product)

    Degree: n · degree(body) when n is int.

    Examples:
        Prod("i", 16, vp("InstructionRa(i)", X_k, X_t))
            → Π_{i=0}^{15} vp:InstructionRa(i)(X_k, X_t)
            degree = 16

        Prod("i", "d_ram", cp("RamRa(i)", X_k, X_t))
            → Π_{i=0}^{d_ram-1} cp:RamRa(i)(X_k, X_t)
            degree = d_ram (symbolic)
    """
    var: str
    n: Union[int, str]
    body: Expr


# The union of all expression node types.
# Every field typed "Expr" accepts any node from this union.
Expr = Union[
    Const, CommittedPoly, VirtualPoly, VerifierPoly,
    Add, Mul, Pow, Neg, Sum, FSum, Prod,
]


# ═══════════════════════════════════════════════════════════════════
# Degree computation — auto-derived from the MLE property
# ═══════════════════════════════════════════════════════════════════

def degree(expr: Expr) -> int:
    """Compute the degree of a sumcheck integrand expression.

    Since every polynomial in Jolt is an MLE (multilinear extension
    of a function {0,1}^n → F), each polynomial leaf has degree
    exactly 1.  The degree of the full expression is determined by
    how these degree-1 leaves are combined:

        Const               → 0   (no variables)
        CommittedPoly       → 1   (MLE, degree 1)
        VirtualPoly         → 1   (MLE, degree 1)
        VerifierPoly        → 1   (MLE, degree 1)
        Add(a, b)           → max(deg(a), deg(b))
        Mul(a, b)           → deg(a) + deg(b)
        Pow(base, k)        → k · deg(base)
        Neg(a)              → deg(a)
        Sum(var, body)      → deg(body)

    This gives the maximum degree of the univariate round polynomial
    that the prover must send in any round of the sumcheck protocol.

    Examples:
        degree(Const(0))                  →  0
        degree(vp("H", X_t))             →  1
        degree(Pow(vp("H", X_t), 2))     →  2
        degree(Mul(eq_node, Pow(H, 2)))   →  3  (eq + H^2)
    """
    if isinstance(expr, Const):
        return 0
    if isinstance(expr, (CommittedPoly, VirtualPoly, VerifierPoly)):
        return 1
    if isinstance(expr, Add):
        return max(degree(expr.left), degree(expr.right))
    if isinstance(expr, Mul):
        return degree(expr.left) + degree(expr.right)
    if isinstance(expr, Pow):
        return expr.exponent * degree(expr.base)
    if isinstance(expr, Neg):
        return degree(expr.expr)
    if isinstance(expr, Sum):
        return degree(expr.body)
    if isinstance(expr, FSum):
        return degree(expr.body)
    if isinstance(expr, Prod):
        if isinstance(expr.n, int):
            return expr.n * degree(expr.body)
        return degree(expr.body)  # symbolic n: return body degree (caller handles)
    raise TypeError(f"Unknown expression type: {type(expr)}")


# ═══════════════════════════════════════════════════════════════════
# Helper constructors — shortcuts for building expression trees
# ═══════════════════════════════════════════════════════════════════

def vp(name: str, *args: Arg) -> VirtualPoly:
    """Build a VirtualPoly node.

    Example:
        vp("LookupOutput", X_t)
        # → VirtualPoly("LookupOutput", [Var("X_t", "log2(T)")])
    """
    return VirtualPoly(name, list(args))


def cp(name: str, *args: Arg) -> CommittedPoly:
    """Build a CommittedPoly node.

    Example:
        cp("InstructionRa(0)", X_k, X_t)
        # → CommittedPoly("InstructionRa(0)", [X_k, X_t])
    """
    return CommittedPoly(name, list(args))


def eq(fixed: Arg, free: Arg) -> VerifierPoly:
    """Build an eq-polynomial node: eq(fixed_point, free_variable).

    The multilinear Lagrange basis polynomial:
        eq(r, x) = Π_i (r_i · x_i + (1 - r_i)(1 - x_i))

    On the hypercube, eq(r, x) = 1 iff x = r, else 0.
    Its key property: Σ_{x ∈ {0,1}^n} eq(r, x) = 1  for all r.

    Example:
        eq(Opening(1, "cycle"), Var("X_t", "log2(T)"))
    """
    return VerifierPoly("eq", [fixed, free])


def add(*terms: Expr) -> Expr:
    """Left-associative sum: a + b + c + ...

    Example:
        add(a, b, c)  →  Add(Add(a, b), c)
    """
    result = terms[0]
    for t in terms[1:]:
        result = Add(result, t)
    return result


def sub(a: Expr, *rest: Expr) -> Expr:
    """Subtraction chain: a - b - c - ...

    Represented as Add(Add(a, Neg(b)), Neg(c)).
    The pretty-printer renders this as "a - b - c".

    Example:
        sub(v("RamReadValue", X_t), v("RamWriteValue", X_t))
        # prints: vp:RamReadValue(X_t) - vp:RamWriteValue(X_t)
    """
    result = a
    for t in rest:
        result = Add(result, Neg(t))
    return result


def mul(*factors: Expr) -> Expr:
    """Left-associative product: a · b · c · ...

    Example:
        mul(eq_term, ra_term, val_term)
        →  Mul(Mul(eq_term, ra_term), val_term)
    """
    result = factors[0]
    for f in factors[1:]:
        result = Mul(result, f)
    return result


def scale(coeff: int | str, expr: Expr) -> Expr:
    """Scalar multiplication: coeff · expr.

    Smart shortcuts:
        scale(1, e)   →  e        (identity)
        scale(-1, e)  →  Neg(e)   (negation)
        scale(k, e)   →  Mul(Const(k), e)  (general case)

    Example:
        scale(2, v("OpFlags(IsCompressed)", X_t))
        # prints: 2 · vp:OpFlags(IsCompressed)(X_t)
    """
    if coeff == 1:
        return expr
    if coeff == -1:
        return Neg(expr)
    return Mul(Const(coeff), expr)
