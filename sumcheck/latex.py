"""
LaTeX document generator for sumcheck specifications.

Generates a .tex file with \\section{Stage N} and \\subsection{SumcheckName}.

Usage:
    python3 -m sumcheck latex                     # all stages → sumcheck_specs.tex
    python3 -m sumcheck latex --stage 5           # just stage 5
    python3 -m sumcheck latex --out specs.tex     # custom output file
"""

from __future__ import annotations

from pathlib import Path

from .defs import Arg, Var, Opening
from .ast import Expr
from .spec import SumcheckSpec, SpartanSpec, ProductVirtSpec
from .format import render, LatexFormat, latex_dim_expr, latex_opening_entry

_FMT = LatexFormat()


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _escape(s: str) -> str:
    """Escape LaTeX special characters in plain text."""
    for ch, esc in [("&", r"\&"), ("%", r"\%"), ("#", r"\#"), ("_", r"\_")]:
        s = s.replace(ch, esc)
    return s


def _opening_list(openings: list[tuple[str, list[Arg]]]) -> str:
    """Render the 'Openings produced' itemize."""
    if not openings:
        return ""
    items = []
    for name, args in openings:
        entry = latex_opening_entry(name, args, _FMT)
        items.append(f"  \\item ${entry}$")
    return (
        "\\paragraph{Openings produced}\n"
        "\\begin{itemize}\n"
        + "\n".join(items) + "\n"
        "\\end{itemize}\n"
    )


# ═══════════════════════════════════════════════════════════════════
# Spec renderers
# ═══════════════════════════════════════════════════════════════════

def _render_sumcheck(sc: SumcheckSpec) -> str:
    """Render a SumcheckSpec as a LaTeX subsection."""
    vars_str = ", ".join(
        f"{v.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(v.log_size)}}}" for v in sc.sum_vars
    )
    opening_pt = ""
    if sc.opening_point:
        pt_str = ", ".join(_FMT.fmt_arg(o) for o in sc.opening_point)
        opening_pt = f"  \\item[Opening point] $({pt_str})$\n"

    integrand_latex = render(sc.integrand, _FMT)
    claim_latex = render(sc.input_claim, _FMT)

    return f"""\\subsection{{{_escape(sc.name)}}}

\\begin{{description}}
  \\item[Degree] {_escape(str(sc.degree))}
  \\item[Rounds] ${latex_dim_expr(str(sc.rounds))}$
  \\item[Sum over] ${vars_str}$
{opening_pt}\\end{{description}}

\\paragraph{{RHS (input claim)}}
\\[
  {claim_latex}
\\]

\\paragraph{{Integrand}}
\\[
  {integrand_latex}
\\]

{_opening_list(sc.openings)}"""


def _render_spartan(sp: SpartanSpec) -> str:
    """Render a SpartanSpec as a LaTeX subsection."""
    parts = [f"""\\subsection{{{_escape(sp.name)}}}

\\begin{{description}}
  \\item[Constraints] {sp.num_constraints} in {len(sp.groups)} groups
  \\item[Cycle var] ${sp.cycle_var.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(sp.cycle_var.log_size)}}}$
  \\item[Group var] ${sp.group_var.name} \\in \\{{0,1\\}}$
  \\item[Constraint domain] ${sp.constraint_domain}$
\\end{{description}}

\\paragraph{{Integrand structure}}
\\[
  \\widetilde{{\\text{{eq}}}}((\\tau_t, \\tau_b), ({sp.cycle_var.name}, {sp.group_var.name}))
  \\cdot L_{{\\tau_c}}(X_c)
  \\cdot A_z({sp.cycle_var.name}, {sp.group_var.name}, X_c)
  \\cdot B_z({sp.cycle_var.name}, {sp.group_var.name}, X_c)
\\]

\\paragraph{{RHS}}
\\[
  {render(sp.input_claim, _FMT)}
\\]
"""]

    for gi, group in enumerate(sp.groups):
        parts.append(f"\\paragraph{{Group {gi} (${sp.group_var.name} = {gi}$)}}\n")
        parts.append("\\noindent\\small\n")
        parts.append("\\begin{tabular}{cl>{$}l<{$}>{$}l<{$}}\n\\toprule\n")
        parts.append("$c$ & Label & \\multicolumn{1}{c}{$A_z$ (guard)} & \\multicolumn{1}{c}{$B_z$ (value)} \\\\\n\\midrule\n")

        for ci, c in enumerate(group):
            idx = sp.constraint_domain[ci] if ci < len(sp.constraint_domain) else ci
            az_latex = render(c.az, _FMT)
            bz_latex = render(c.bz, _FMT)
            label = _escape(c.label)
            parts.append(f"${idx}$ & \\texttt{{{label}}} & {az_latex} & {bz_latex} \\\\\n")

        parts.append("\\bottomrule\n\\end{tabular}\n\\normalsize\n\n")

    parts.append(_opening_list(sp.openings))
    return "".join(parts)


def _render_product_virt(pv: ProductVirtSpec) -> str:
    """Render a ProductVirtSpec as a LaTeX subsection."""
    parts = [f"""\\subsection{{{_escape(pv.name)}}}

\\begin{{description}}
  \\item[Constraints] {len(pv.constraints)} product constraints
  \\item[Cycle var] ${pv.cycle_var.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(pv.cycle_var.log_size)}}}$
  \\item[Constraint domain] ${pv.constraint_domain}$
  \\item[Rounds] ${latex_dim_expr(pv.rounds)}$
\\end{{description}}

\\paragraph{{Integrand structure}}
\\[
  \\widetilde{{\\text{{eq}}}}(r_{{\\text{{cycle}}}}^{{(1)}}, {pv.cycle_var.name})
  \\cdot L_{{\\tau_c}}(X_c)
  \\cdot \\text{{Left}}({pv.cycle_var.name}, X_c)
  \\cdot \\text{{Right}}({pv.cycle_var.name}, X_c)
\\]

\\paragraph{{Constraint table}}
\\begin{{center}}
\\small
\\begin{{tabular}}{{cl>{{}}{{}}{{}}<{{}}>{{}}{{}}{{}}<{{}}>{{}}{{}}{{}}<{{}}}}
"""]
    # Column spec: c, l, then 3 math columns
    parts[-1] = f"""\\paragraph{{Constraint table}}
\\begin{{center}}
\\adjustbox{{max width=\\textwidth}}{{
\\small
\\begin{{tabular}}{{cl>{{{chr(36)}}}l<{{{chr(36)}}}>{{{chr(36)}}}l<{{{chr(36)}}}>{{{chr(36)}}}l<{{{chr(36)}}}}}
\\toprule
$c$ & Label & \\multicolumn{{1}}{{c}}{{Output}} & \\multicolumn{{1}}{{c}}{{Left}} & \\multicolumn{{1}}{{c}}{{Right}} \\\\
\\midrule
"""

    for ci, c in enumerate(pv.constraints):
        idx = pv.constraint_domain[ci]
        out_latex = render(c.output, _FMT)
        left_latex = render(c.left, _FMT)
        right_latex = render(c.right, _FMT)
        label = _escape(c.label)
        parts.append(f"${idx}$ & \\texttt{{{label}}} & {out_latex} & {left_latex} & {right_latex} \\\\\n")

    parts.append("\\bottomrule\n\\end{tabular}\n}\n\\end{center}\n\n")
    parts.append(_opening_list(pv.openings))
    return "".join(parts)


def _render_spec(spec) -> str:
    """Dispatch to the right renderer based on spec type."""
    if isinstance(spec, SpartanSpec):
        return _render_spartan(spec)
    if isinstance(spec, ProductVirtSpec):
        return _render_product_virt(spec)
    if isinstance(spec, SumcheckSpec):
        return _render_sumcheck(spec)
    return f"% Unknown spec type: {type(spec)}\n"


# ═══════════════════════════════════════════════════════════════════
# Document template
# ═══════════════════════════════════════════════════════════════════

_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb}
\usepackage[dvipsnames]{xcolor}
\usepackage{booktabs}
\usepackage{array}
\usepackage[margin=1in]{geometry}
\usepackage{hyperref}
\usepackage{adjustbox}

\hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}

\title{Jolt Sumcheck Specifications}
\author{Auto-generated from sumcheck AST}
\date{}

\begin{document}
\maketitle
\tableofcontents
\newpage
"""

_POSTAMBLE = r"""
\end{document}
"""


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def generate_latex(out_file: str | Path = "sumcheck_specs.tex", stages: dict | None = None) -> None:
    """Generate the LaTeX document.

    Args:
        out_file:  output .tex file path
        stages:    dict mapping stage_num -> (title, [spec_objects])
                   If None, builds all stages from examples.
    """
    if stages is None:
        stages = _default_stages()

    parts = [_PREAMBLE]

    for s in sorted(stages.keys()):
        title, specs = stages[s]
        parts.append(f"\n\\section{{Stage {s} --- {_escape(title)}}}\n\n")
        for spec in specs:
            parts.append(_render_spec(spec))
            parts.append("\n")

    parts.append(_POSTAMBLE)

    out = Path(out_file)
    out.write_text("".join(parts))
    print(f"  wrote {out}")


def _default_stages() -> dict[int, tuple[str, list]]:
    """Build all stages from examples."""
    from .examples import (
        stage1_spartan_outer,
        stage2_product_virtualization,
        stage2_ram_read_write,
        stage2_instruction_claim_reduction,
        stage2_ram_raf_evaluation,
        stage2_ram_output_check,
        stage3_shift,
        stage3_instruction_input,
        stage3_registers_claim_reduction,
        stage4_registers_read_write,
        stage4_ram_val_check,
        stage5_instruction_read_raf,
        stage5_ram_ra_claim_reduction,
        stage5_registers_val_evaluation,
        stage6_ram_hamming_booleanity,
        stage6_inc_claim_reduction,
        stage6_bytecode_read_raf,
        stage6_instruction_ra_virtualization,
        stage6_ram_ra_virtualization,
        stage6_booleanity,
        stage7_hamming_weight_claim_reduction,
    )
    return {
        1: ("Spartan", [stage1_spartan_outer()]),
        2: ("Virtualization & RAM", [
            stage2_product_virtualization(),
            stage2_ram_read_write(),
            stage2_instruction_claim_reduction(),
            stage2_ram_raf_evaluation(),
            stage2_ram_output_check(),
        ]),
        3: ("Shift & Instruction Input", [
            stage3_shift(),
            stage3_instruction_input(),
            stage3_registers_claim_reduction(),
        ]),
        4: ("Registers & RAM Val", [
            stage4_registers_read_write(),
            stage4_ram_val_check(),
        ]),
        5: ("Instruction Read RAF & Reductions", [
            stage5_instruction_read_raf(),
            stage5_ram_ra_claim_reduction(),
            stage5_registers_val_evaluation(),
        ]),
        6: ("Booleanity, Bytecode & Virtualization", [
            stage6_ram_hamming_booleanity(),
            stage6_inc_claim_reduction(),
            stage6_bytecode_read_raf(),
            stage6_instruction_ra_virtualization(),
            stage6_ram_ra_virtualization(),
            stage6_booleanity(),
        ]),
        7: ("Hamming Weight Claim Reduction", [
            stage7_hamming_weight_claim_reduction(),
        ]),
    }
