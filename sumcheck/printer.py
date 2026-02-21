"""
Pretty-printer for sumcheck AST and specifications.

Two entry points:

    fmt(expr)              →  str
        Render an expression tree as a single-line string.
        Delegates to the per-node TextFormat via format.render().

    print_sumcheck(spec)   →  None
        Print a full SumcheckSpec to stdout.

    print_spartan(spec)    →  None
        Print a SpartanSpec to stdout.

See format.py for the per-node formatting system (TextFormat, LatexFormat, etc.).
"""

from __future__ import annotations

from .defs import Arg, Var, Opening
from .ast import Expr
from .spec import SumcheckSpec, SpartanSpec, ProductVirtSpec
from .format import render, TextFormat

_TEXT = TextFormat()


# ═══════════════════════════════════════════════════════════════════
# Public helpers — kept for backward compatibility
# ═══════════════════════════════════════════════════════════════════

def _fmt_arg(a: Arg) -> str:
    """Format a polynomial argument (Var or Opening) as a string."""
    return _TEXT.fmt_arg(a)


def fmt(expr: Expr) -> str:
    """Render an expression tree as a single-line string.

    Delegates to render(expr, TextFormat()).
    """
    return render(expr, _TEXT)


# ═══════════════════════════════════════════════════════════════════
# SumcheckSpec printer
# ═══════════════════════════════════════════════════════════════════

def print_sumcheck(sc: SumcheckSpec) -> None:
    """Pretty-print a single-integrand sumcheck specification.

    Output format:
        ============================================================
          RamHammingBooleanity
        ============================================================
          Degree : 3
          Rounds : log2(T)

          Σ over : X_t ∈ {0,1}^log2(T)

          RHS (input claim):
            0

          Integrand:
            eq:eq(...) · (vp:H(X_t)^2 - vp:H(X_t))

          Openings produced:
            RamHammingWeight(r_cycle^(6))
    """
    w = 60
    print("=" * w)
    print(f"  {sc.name}")
    print("=" * w)
    print(f"  Degree : {sc.degree}")
    print(f"  Rounds : {sc.rounds}")
    print()

    vars_str = ", ".join(
        f"{v.name} ∈ {{0,1}}^{v.log_size}" for v in sc.sum_vars
    )
    print(f"  Σ over : {vars_str}")
    if sc.opening_point:
        pt_str = ", ".join(_fmt_arg(o) for o in sc.opening_point)
        print(f"  Opening: ({pt_str})")
    print()
    print(f"  RHS (input claim):")
    print(f"    {fmt(sc.input_claim)}")
    print()
    print(f"  Integrand:")
    print(f"    {fmt(sc.integrand)}")
    print()
    if sc.openings:
        print(f"  Openings produced:")
        for name, args in sc.openings:
            arg_str = ", ".join(_fmt_arg(a) for a in args)
            print(f"    {name}({arg_str})")
    print()


# ═══════════════════════════════════════════════════════════════════
# SpartanSpec printer
# ═══════════════════════════════════════════════════════════════════

def print_product_virt(pv: ProductVirtSpec) -> None:
    """Pretty-print a product virtualization sumcheck."""
    w = 72
    print("=" * w)
    print(f"  {pv.name}")
    print("=" * w)
    print(f"  {len(pv.constraints)} product constraints")
    print(f"  Cycle var : {pv.cycle_var.name} ∈ {{0,1}}^{pv.cycle_var.log_size}")
    print(f"  Constraint domain : {pv.constraint_domain}")
    print(f"  Rounds : {pv.rounds}")
    print()

    print(f"  Integrand: eq(r_cycle^(1), {pv.cycle_var.name})")
    print(f"           · L_{{τ_c}}(X_c)")
    print(f"           · Left({pv.cycle_var.name}, X_c)")
    print(f"           · Right({pv.cycle_var.name}, X_c)")
    print()
    print(f"  RHS: Σ_{{X_c}} L_{{τ_c}}(X_c) · Output(r_cycle^(1), X_c)")
    print()

    # Table
    out_strs  = [fmt(c.output) for c in pv.constraints]
    left_strs = [fmt(c.left) for c in pv.constraints]
    lbl_w = max(len(c.label) for c in pv.constraints)
    out_w = max(len(s) for s in out_strs)
    left_w = max(len(s) for s in left_strs)
    c_w = max(len(str(d)) for d in pv.constraint_domain)

    hdr = f"  {'c':>{c_w}}  {'label':<{lbl_w}}  {'Output':<{out_w}}  {'Left':<{left_w}}  Right"
    print(hdr)
    print(f"  {'─' * c_w}  {'─' * lbl_w}  {'─' * out_w}  {'─' * left_w}  {'─' * 30}")

    for ci, c in enumerate(pv.constraints):
        idx = pv.constraint_domain[ci]
        print(f"  {idx:>{c_w}}  {c.label:<{lbl_w}}  {out_strs[ci]:<{out_w}}  {left_strs[ci]:<{left_w}}  {fmt(c.right)}")
    print()

    if pv.openings:
        print(f"  Openings produced:")
        for name, args in pv.openings:
            arg_str = ", ".join(_fmt_arg(a) for a in args)
            print(f"    {name}({arg_str})")
    print()


def print_spartan(sp: SpartanSpec) -> None:
    """Pretty-print a Spartan constraint-table sumcheck.

    Shows the implicit integrand structure, then renders each
    constraint group as a table with columns:
        c (index) | label | Az (guard) | Bz (value)

    Column widths are auto-computed from content.
    """
    w = 72
    print("=" * w)
    print(f"  {sp.name}")
    print("=" * w)
    print(f"  {sp.num_constraints} constraints in {len(sp.groups)} groups")
    print(f"  Cycle var : {sp.cycle_var.name} ∈ {{0,1}}^{sp.cycle_var.log_size}")
    print(f"  Group var : {sp.group_var.name} ∈ {{0,1}}")
    print(f"  Constraint domain : {sp.constraint_domain}")
    print()

    # The integrand structure is fixed for Spartan — show it explicitly
    print(f"  Integrand: eq((τ_t, τ_b), ({sp.cycle_var.name}, {sp.group_var.name}))")
    print(f"           · L_{{τ_c}}(X_c)")
    print(f"           · Az({sp.cycle_var.name}, {sp.group_var.name}, X_c)")
    print(f"           · Bz({sp.cycle_var.name}, {sp.group_var.name}, X_c)")
    print()
    print(f"  RHS: {fmt(sp.input_claim)}")
    print()

    # Print each constraint group as a table
    for gi, group in enumerate(sp.groups):
        print(f"  ── Group {gi} ({sp.group_var.name} = {gi}) ──")
        print()

        # Pre-format all Az and Bz expressions
        az_strs = [fmt(c.az) for c in group]
        bz_strs = [fmt(c.bz) for c in group]

        # Auto-size columns
        lbl_w = max(len(c.label) for c in group)
        c_w = max(len(str(d)) for d in sp.constraint_domain)
        az_w = max(len(s) for s in az_strs)

        # Header
        hdr = f"  {'c':>{c_w}}  {'label':<{lbl_w}}  {'Az (guard)':<{az_w}}  Bz (value)"
        print(hdr)
        print(f"  {'─' * c_w}  {'─' * lbl_w}  {'─' * az_w}  {'─' * 30}")

        # Rows
        for ci, (c, az_s, bz_s) in enumerate(zip(group, az_strs, bz_strs)):
            idx = sp.constraint_domain[ci] if ci < len(sp.constraint_domain) else ci
            print(f"  {idx:>{c_w}}  {c.label:<{lbl_w}}  {az_s:<{az_w}}  {bz_s}")
        print()

    # Openings produced
    if sp.openings:
        print(f"  Openings produced:")
        for name, args in sp.openings:
            arg_str = ", ".join(_fmt_arg(a) for a in args)
            print(f"    {name}({arg_str})")
        print()
