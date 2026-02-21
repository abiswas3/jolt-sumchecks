"""
Per-node expression formatting system.

Each AST node type has a corresponding method on the Format class.
Implement a Format subclass to produce a new output format.

Built-in formats:
    TextFormat   — plain-text (terminal) rendering
    LatexFormat  — LaTeX math rendering (for KaTeX/MathJax/documents)

Usage:
    from sumcheck.format import render, TextFormat, LatexFormat

    text = render(expr, TextFormat())    # "eq:eq(r_cycle^(1), X_t) · vp:H(X_t)^2"
    latex = render(expr, LatexFormat())  # "\\widetilde{\\text{eq}}(...) \\cdot ..."
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Union

from .defs import Arg, Var, Opening, PolyKind
from .ast import (
    Expr,
    Const, CommittedPoly, VirtualPoly, VerifierPoly,
    Add, Mul, Pow, Neg, Sum, FSum, Prod,
)


# ═══════════════════════════════════════════════════════════════════
# Format protocol — one method per node type
# ═══════════════════════════════════════════════════════════════════

class Format(ABC):
    """Base class for per-node expression formatters.

    Subclass this and implement every abstract method to create a new
    output format.  Then call  render(expr, your_format)  to produce
    a string.
    """

    # ── Arguments ──

    @abstractmethod
    def fmt_var(self, v: Var) -> str: ...

    @abstractmethod
    def fmt_opening(self, o: Opening) -> str: ...

    def fmt_arg(self, a: Arg) -> str:
        """Dispatch an argument to fmt_var or fmt_opening."""
        if isinstance(a, Var):
            return self.fmt_var(a)
        if isinstance(a, Opening):
            return self.fmt_opening(a)
        return str(a)

    # ── Leaves ──

    @abstractmethod
    def fmt_const(self, value: Union[int, float, str]) -> str: ...

    @abstractmethod
    def fmt_committed_poly(self, name: str, args: list[str]) -> str: ...

    @abstractmethod
    def fmt_virtual_poly(self, name: str, args: list[str]) -> str: ...

    @abstractmethod
    def fmt_verifier_poly(self, name: str, args: list[str]) -> str: ...

    # ── Arithmetic ──

    @abstractmethod
    def fmt_add(self, left: str, right: str) -> str: ...

    @abstractmethod
    def fmt_sub(self, left: str, right: str) -> str: ...

    @abstractmethod
    def fmt_mul(self, left: str, right: str) -> str: ...

    @abstractmethod
    def fmt_pow(self, base: str, exponent: int) -> str: ...

    @abstractmethod
    def fmt_neg(self, inner: str) -> str: ...

    # ── Aggregations ──

    @abstractmethod
    def fmt_sum(self, var: Var, body: str) -> str: ...

    @abstractmethod
    def fmt_fsum(self, index_var: str, n: Union[int, str], body: str) -> str: ...

    @abstractmethod
    def fmt_prod(self, index_var: str, n: Union[int, str], body: str) -> str: ...

    # ── Wrapping ──

    @abstractmethod
    def fmt_parens(self, s: str) -> str: ...


# ═══════════════════════════════════════════════════════════════════
# Tree walker — dispatches to format methods
# ═══════════════════════════════════════════════════════════════════

def render(expr: Expr, fmt: Format) -> str:
    """Walk the AST and dispatch rendering to the format, per-node.

    Handles operator precedence (parenthesization) and subtraction
    detection (Add + Neg → sub) generically — formats only define
    *how* each node looks, not *when* to wrap.
    """

    def _r(e: Expr) -> str:
        # ── Leaves ──
        if isinstance(e, Const):
            return fmt.fmt_const(e.value)
        if isinstance(e, CommittedPoly):
            return fmt.fmt_committed_poly(e.name, [fmt.fmt_arg(a) for a in e.args])
        if isinstance(e, VirtualPoly):
            return fmt.fmt_virtual_poly(e.name, [fmt.fmt_arg(a) for a in e.args])
        if isinstance(e, VerifierPoly):
            return fmt.fmt_verifier_poly(e.name, [fmt.fmt_arg(a) for a in e.args])

        # ── Add / Sub ──
        if isinstance(e, Add):
            if isinstance(e.right, Neg):
                return fmt.fmt_sub(_r(e.left), _wrap(e.right.expr, "Mul"))
            return fmt.fmt_add(_r(e.left), _r(e.right))

        # ── Mul ──
        if isinstance(e, Mul):
            return fmt.fmt_mul(_wrap(e.left, "Mul"), _wrap(e.right, "Mul"))

        # ── Pow ──
        if isinstance(e, Pow):
            return fmt.fmt_pow(_wrap(e.base, "Pow"), e.exponent)

        # ── Neg ──
        if isinstance(e, Neg):
            inner = _r(e.expr)
            if isinstance(e.expr, (Add, Neg)):
                inner = fmt.fmt_parens(inner)
            return fmt.fmt_neg(inner)

        # ── Sum ──
        if isinstance(e, Sum):
            return fmt.fmt_sum(e.var, _r(e.body))

        # ── FSum ──
        if isinstance(e, FSum):
            return fmt.fmt_fsum(e.var, e.n, _r(e.body))

        # ── Prod ──
        if isinstance(e, Prod):
            return fmt.fmt_prod(e.var, e.n, _r(e.body))

        return repr(e)

    def _wrap(e: Expr, parent_op: str) -> str:
        """Render e, adding parens if needed inside parent_op."""
        s = _r(e)
        if isinstance(e, (Add, Neg)) and parent_op in ("Mul", "Pow"):
            return fmt.fmt_parens(s)
        return s

    return _r(expr)


# ═══════════════════════════════════════════════════════════════════
# TextFormat — plain-text (terminal) output
# ═══════════════════════════════════════════════════════════════════

class TextFormat(Format):
    """Plain-text rendering matching the original printer.fmt() output."""

    def fmt_var(self, v):
        return v.name

    def fmt_opening(self, o):
        return f"r_{o.print_label}^({o.stage})"

    def fmt_const(self, value):
        return str(value)

    def fmt_committed_poly(self, name, args):
        arg_str = ", ".join(args)
        return f"cp:{name}({arg_str})" if args else f"cp:{name}"

    def fmt_virtual_poly(self, name, args):
        arg_str = ", ".join(args)
        return f"vp:{name}({arg_str})" if args else f"vp:{name}"

    def fmt_verifier_poly(self, name, args):
        arg_str = ", ".join(args)
        return f"{name}:{name}({arg_str})" if args else f"{name}:{name}"

    def fmt_add(self, left, right):
        return f"{left} + {right}"

    def fmt_sub(self, left, right):
        return f"{left} - {right}"

    def fmt_mul(self, left, right):
        return f"{left} · {right}"

    def fmt_pow(self, base, exponent):
        return f"{base}^{exponent}"

    def fmt_neg(self, inner):
        return f"-{inner}"

    def fmt_sum(self, var, body):
        return f"Σ_{{{var.name}}} {body}"

    def fmt_fsum(self, index_var, n, body):
        upper = n - 1 if isinstance(n, int) else f"{n}-1"
        return f"Σ_{{{index_var}=0}}^{{{upper}}} {body}"

    def fmt_prod(self, index_var, n, body):
        upper = n - 1 if isinstance(n, int) else f"{n}-1"
        return f"Π_{{{index_var}=0}}^{{{upper}}} {body}"

    def fmt_parens(self, s):
        return f"({s})"


# ═══════════════════════════════════════════════════════════════════
# LatexFormat — LaTeX math output (for KaTeX / MathJax / .tex)
# ═══════════════════════════════════════════════════════════════════

# Unicode → LaTeX replacements for symbolic Const values
_UNICODE_TO_LATEX = [
    ("γ", "\\gamma"),
    ("·", "\\cdot "),
    ("∪", "\\cup "),
    ("∈", "\\in "),
    ("Σ", "\\sum"),
    ("Π", "\\prod"),
]


def _latex_poly_name(name: str) -> str:
    """Convert a polynomial name to LaTeX with proper subscript handling.

    The key rule: underscores become math subscripts OUTSIDE \\textsf{},
    so LaTeX doesn't choke on _ in text mode.

    Examples:
        Ra_j                → \\textsf{Ra}_j
        OpFlags(Load)       → \\textsf{OpFlags}(\\text{Load})
        InstructionRa(i)    → \\textsf{InstructionRa}(i)
        OpFlags(cf_i)       → \\textsf{OpFlags}(\\text{cf}_i)
        T_j                 → T_j            (single letter, already LaTeX)
        W_1                 → W_1
        io_mask             → \\textsf{io\\_mask}
    """
    # Single uppercase letter + subscript: T_j, W_1 — already valid LaTeX
    if re.match(r"^[A-Z]_[a-z0-9]+$", name):
        return name

    # Split Name(Qualifier) from base
    m = re.match(r"^([^(]+)\((.+)\)$", name)
    if m:
        base = _latex_base(m.group(1))
        qual = _latex_qualifier(m.group(2))
        return f"{base}({qual})"

    return _latex_base(name)


def _latex_base(name: str) -> str:
    """Render the base part of a polynomial name.

    Pulls trailing _X subscripts out of \\textsf so they're math subscripts.
        Ra_j  → \\textsf{Ra}_j
        Ra    → \\textsf{Ra}
    """
    m = re.match(r"^(.+?)_([a-z0-9])$", name)
    if m:
        return f"\\textsf{{{m.group(1)}}}_{{{m.group(2)}}}"
    escaped = name.replace("_", r"\_")
    return f"\\textsf{{{escaped}}}"


def _latex_qualifier(qual: str) -> str:
    """Render the parenthesized qualifier of a polynomial name.

    Single letter/var → math mode:  i, j
    Letter_subscript  → math mode:  cf_i
    Word              → \\text{}:   Load, Branch, LeftOperandIsRs1Value
    """
    # Single lowercase letter: i, j
    if re.match(r"^[a-z]$", qual):
        return qual
    # Variable with subscript: cf_i
    m = re.match(r"^([a-z]+)_([a-z0-9])$", qual)
    if m:
        return f"\\text{{{m.group(1)}}}_{{{m.group(2)}}}"
    # Word (starts with uppercase, or multi-char): Load, Branch, IsRdNotZero
    return f"\\text{{{qual}}}"


def _latex_verifier_name(name: str) -> str:
    """Convert a verifier polynomial name to LaTeX."""
    if name == "eq":
        return "\\widetilde{\\text{eq}}"
    if name.startswith("eq_"):
        suffix = name[3:]
        return f"\\widetilde{{\\text{{eq}}}}_{{{suffix}}}"
    if name.endswith("_tilde"):
        base = name[:-6]
        return f"\\widetilde{{{_latex_poly_name(base)}}}"
    return _latex_poly_name(name)


def _latex_param(s: str) -> str:
    """Format a parameter/dimension name for LaTeX.

    T         → T
    K_ram     → K_{\\text{ram}}
    N_instr   → N_{\\text{instr}}
    d_v       → d_v
    2         → 2
    """
    m = re.match(r'^([A-Za-z])_([a-z0-9]+)$', s)
    if m:
        base, sub = m.group(1), m.group(2)
        if len(sub) == 1:
            return f"{base}_{sub}"
        return f"{base}_{{\\text{{{sub}}}}}"
    return s


def _latex_opening_label(label: str) -> str:
    """Format an opening-point label for LaTeX.

    K_instr^(i) → K_{\\text{instr}}^{(i)}
    K_ram       → K_{\\text{ram}}
    cycle       → \\text{cycle}
    K^(j)       → K^{(j)}
    addr        → \\text{addr}
    """
    # Strip superscript: base^(content)
    sup = ""
    m = re.match(r'^(.+)\^(\(.+\))$', label)
    if m:
        label = m.group(1)
        sup = f"^{{{m.group(2)}}}"

    # Param_subscript: K_instr, N_v
    m2 = re.match(r'^([A-Z])_([a-z][a-z0-9]*)$', label)
    if m2:
        base, sub_text = m2.group(1), m2.group(2)
        if len(sub_text) == 1:
            return f"{base}_{sub_text}{sup}"
        return f"{base}_{{\\text{{{sub_text}}}}}{sup}"

    # Single uppercase letter
    if re.match(r'^[A-Z]$', label):
        return f"{label}{sup}"

    # word_subscript: addr_j
    m3 = re.match(r'^([a-z]+)_([a-z0-9])$', label)
    if m3:
        return f"\\text{{{m3.group(1)}}}_{{{m3.group(2)}}}{sup}"

    # Plain word
    return f"\\text{{{label}}}{sup}"


def _latex_for_clause(clause: str) -> str:
    """Format a 'for' clause with proper LaTeX parameter names.

    i=0..d_v-1           → i=0,\\ldots,d_v-1
    j=0..N_ra-1 (...)    → j=0,\\ldots,N_{\\text{ra}}-1 (...)
    """
    result = clause.replace("..", ",\\ldots,")
    result = re.sub(
        r'([A-Za-z])_([a-z][a-z0-9]*)',
        lambda m: _latex_param(m.group(0)),
        result,
    )
    return result


def latex_dim_expr(s: str) -> str:
    """Format a dimension/round expression for LaTeX.

    log2(T)                → \\log_2 T
    log2(K_instr)          → \\log_2 K_{\\text{instr}}
    log2(T) + log2(K_ram)  → \\log_2 T + \\log_2 K_{\\text{ram}}
    1                      → 1
    """
    def _replace_log2(m):
        inner = m.group(1)
        return f"\\log_2 {_latex_param(inner)}"
    return re.sub(r'log2\(([^)]+)\)', _replace_log2, s)


def latex_opening_entry(name: str, args: list, fmt: 'LatexFormat') -> str:
    """Format one opening entry as LaTeX math.

    Simple: "RamVal" → \\textcolor{BurntOrange}{\\textsf{RamVal}}(args)
    Parametric: "InstructionRa(i) for i=0..d_v-1" → formatted poly + clause
    """
    from .registry import ALL_POLYS

    # Split "PolyName for clause"
    poly_name = name
    for_clause = ""
    if " for " in name:
        poly_name, for_clause = name.split(" for ", 1)

    # Format the polynomial name
    latex_name = _latex_poly_name(poly_name)

    # Determine colour from registry (best-effort)
    _COLOUR = {
        PolyKind.COMMITTED: "ForestGreen",
        PolyKind.VIRTUAL: "BurntOrange",
    }
    matches = [p for p in ALL_POLYS if p.name == poly_name]
    if len(matches) == 1 and matches[0].kind in _COLOUR:
        latex_name = f"\\textcolor{{{_COLOUR[matches[0].kind]}}}{{{latex_name}}}"

    # Format args
    arg_str = ", ".join(fmt.fmt_arg(a) for a in args)

    result = f"{latex_name}({arg_str})"
    if for_clause:
        result += f" \\text{{ for }} {_latex_for_clause(for_clause)}"
    return result


class LatexFormat(Format):
    """LaTeX math rendering for KaTeX, MathJax, or .tex documents.

    Uses:
        \\textcolor{ForestGreen}{...} for committed polynomials
        \\textcolor{BurntOrange}{...} for virtual polynomials
        \\widetilde{\\text{eq}}       for the eq polynomial
    """

    def fmt_var(self, v):
        return v.name  # X_t, X_k — already valid LaTeX

    def fmt_opening(self, o):
        label = _latex_opening_label(o.print_label)
        return f"r_{{{label}}}^{{({o.stage})}}"

    def fmt_const(self, value):
        if isinstance(value, (int, float)):
            return str(value)
        s = str(value)
        for uchar, ltx in _UNICODE_TO_LATEX:
            s = s.replace(uchar, ltx)
        # Wrap bare multi-digit exponents: 2^64 → 2^{64}
        s = re.sub(r"\^(\d{2,})", r"^{\1}", s)
        return s

    def fmt_committed_poly(self, name, args):
        arg_str = ", ".join(args)
        latex_name = _latex_poly_name(name)
        colored = f"\\textcolor{{ForestGreen}}{{{latex_name}}}"
        return f"{colored}({arg_str})" if args else colored

    def fmt_virtual_poly(self, name, args):
        arg_str = ", ".join(args)
        latex_name = _latex_poly_name(name)
        colored = f"\\textcolor{{BurntOrange}}{{{latex_name}}}"
        return f"{colored}({arg_str})" if args else colored

    def fmt_verifier_poly(self, name, args):
        arg_str = ", ".join(args)
        latex_name = _latex_verifier_name(name)
        return f"{latex_name}({arg_str})" if args else latex_name

    def fmt_add(self, left, right):
        return f"{left} + {right}"

    def fmt_sub(self, left, right):
        return f"{left} - {right}"

    def fmt_mul(self, left, right):
        return f"{left} \\cdot {right}"

    def fmt_pow(self, base, exponent):
        return f"{base}^{{{exponent}}}"

    def fmt_neg(self, inner):
        return f"-{inner}"

    def fmt_sum(self, var, body):
        return f"\\sum_{{{var.name} \\in \\{{0,1\\}}^{{{var.log_size}}}}} {body}"

    def fmt_fsum(self, index_var, n, body):
        upper = n - 1 if isinstance(n, int) else f"{n}-1"
        return f"\\sum_{{{index_var}=0}}^{{{upper}}} {body}"

    def fmt_prod(self, index_var, n, body):
        upper = n - 1 if isinstance(n, int) else f"{n}-1"
        return f"\\prod_{{{index_var}=0}}^{{{upper}}} {body}"

    def fmt_parens(self, s):
        return f"\\left({s}\\right)"
