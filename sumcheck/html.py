"""
HTML site generator for sumcheck specifications.

Generates one page per stage with KaTeX-rendered math expressions.

Usage:
    python3 -m sumcheck html                # all stages → docs/
    python3 -m sumcheck html --stage 5      # just stage 5
    python3 -m sumcheck html --out ./out    # custom output dir
"""

from __future__ import annotations

import html as html_mod
from pathlib import Path

from .defs import Arg, Var, Opening, PolyKind
from .ast import Expr
from .spec import SumcheckSpec, SpartanSpec, ProductVirtSpec
from .format import (
    render, LatexFormat, latex_dim_expr, latex_opening_entry,
    _latex_poly_name, _latex_param,
)

_FMT = LatexFormat()


# ═══════════════════════════════════════════════════════════════════
# Expression / argument helpers
# ═══════════════════════════════════════════════════════════════════

def _math(expr: Expr) -> str:
    """Render an expression as a KaTeX display-math block."""
    latex = render(expr, _FMT)
    return f'<div class="math-block">$${latex}$$</div>'


def _inline(expr: Expr) -> str:
    """Render an expression as inline KaTeX."""
    return f"${render(expr, _FMT)}$"


def _arg(a: Arg) -> str:
    """Render an argument as inline KaTeX."""
    return f"${_FMT.fmt_arg(a)}$"


def _opening_list(openings: list[tuple[str, list[Arg]]]) -> str:
    """Render the 'Openings produced' list."""
    if not openings:
        return ""
    items = []
    for name, args in openings:
        entry = latex_opening_entry(name, args, _FMT)
        items.append(f'<li>${entry}$</li>')
    return f"""
    <div class="spec-section">
      <h4>Openings produced</h4>
      <ul class="openings">{chr(10).join(items)}</ul>
    </div>"""


# ═══════════════════════════════════════════════════════════════════
# Spec renderers — one function per spec type
# ═══════════════════════════════════════════════════════════════════

def _render_sumcheck(sc: SumcheckSpec) -> str:
    """Render a SumcheckSpec as an HTML section."""
    vars_str = ", ".join(
        f"{v.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(v.log_size)}}}" for v in sc.sum_vars
    )
    opening_pt = ""
    if sc.opening_point:
        pt_str = ", ".join(_FMT.fmt_arg(o) for o in sc.opening_point)
        opening_pt = f'<div class="meta-item"><span class="meta-label">Opening point</span> $({pt_str})$</div>'

    anchor = html_mod.escape(sc.name)
    return f"""
    <section class="sumcheck-card" id="{anchor}">
      <h3>{anchor}</h3>
      <div class="metadata">
        <div class="meta-item"><span class="meta-label">Degree</span> {sc.degree}</div>
        <div class="meta-item"><span class="meta-label">Rounds</span> ${latex_dim_expr(sc.rounds)}$</div>
      </div>
      <div class="sum-over">
        $\\displaystyle\\sum$ over: ${vars_str}$
      </div>
      {opening_pt}
      <div class="spec-section">
        <h4>RHS (input claim)</h4>
        {_math(sc.input_claim)}
      </div>
      <div class="spec-section">
        <h4>Integrand</h4>
        {_math(sc.integrand)}
      </div>
      {_opening_list(sc.openings)}
    </section>"""


def _render_spartan(sp: SpartanSpec) -> str:
    """Render a SpartanSpec as an HTML section."""
    anchor = html_mod.escape(sp.name)
    parts = [f"""
    <section class="sumcheck-card" id="{anchor}">
      <h3>{anchor}</h3>
      <div class="metadata">
        <div class="meta-item"><span class="meta-label">Constraints</span> {sp.num_constraints} in {len(sp.groups)} groups</div>
        <div class="meta-item"><span class="meta-label">Cycle var</span> ${sp.cycle_var.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(sp.cycle_var.log_size)}}}$</div>
        <div class="meta-item"><span class="meta-label">Group var</span> ${sp.group_var.name} \\in \\{{0,1\\}}$</div>
        <div class="meta-item"><span class="meta-label">Constraint domain</span> {sp.constraint_domain}</div>
      </div>

      <div class="spec-section">
        <h4>Integrand structure</h4>
        <div class="math-block">$$
          \\widetilde{{\\text{{eq}}}}((\\tau_t, \\tau_b), ({sp.cycle_var.name}, {sp.group_var.name}))
          \\cdot L_{{\\tau_c}}(X_c)
          \\cdot A_z({sp.cycle_var.name}, {sp.group_var.name}, X_c)
          \\cdot B_z({sp.cycle_var.name}, {sp.group_var.name}, X_c)
        $$</div>
      </div>

      <div class="spec-section">
        <h4>RHS</h4>
        {_math(sp.input_claim)}
      </div>"""]

    for gi, group in enumerate(sp.groups):
        rows = []
        for ci, c in enumerate(group):
            idx = sp.constraint_domain[ci] if ci < len(sp.constraint_domain) else ci
            az_latex = render(c.az, _FMT)
            bz_latex = render(c.bz, _FMT)
            rows.append(f"""
            <tr>
              <td class="idx">{idx}</td>
              <td class="label">{html_mod.escape(c.label)}</td>
              <td class="math-cell">${az_latex}$</td>
              <td class="math-cell">${bz_latex}$</td>
            </tr>""")

        parts.append(f"""
      <div class="spec-section">
        <h4>Group {gi} (${sp.group_var.name} = {gi}$)</h4>
        <div class="table-wrap">
        <table class="constraint-table">
          <thead>
            <tr><th>c</th><th>Label</th><th>$A_z$ (guard)</th><th>$B_z$ (value)</th></tr>
          </thead>
          <tbody>{"".join(rows)}
          </tbody>
        </table>
        </div>
      </div>""")

    parts.append(_opening_list(sp.openings))
    parts.append("</section>")
    return "".join(parts)


def _render_product_virt(pv: ProductVirtSpec) -> str:
    """Render a ProductVirtSpec as an HTML section."""
    rows = []
    for ci, c in enumerate(pv.constraints):
        idx = pv.constraint_domain[ci]
        out_latex = render(c.output, _FMT)
        left_latex = render(c.left, _FMT)
        right_latex = render(c.right, _FMT)
        rows.append(f"""
            <tr>
              <td class="idx">{idx}</td>
              <td class="label">{html_mod.escape(c.label)}</td>
              <td class="math-cell">${out_latex}$</td>
              <td class="math-cell">${left_latex}$</td>
              <td class="math-cell">${right_latex}$</td>
            </tr>""")

    anchor = html_mod.escape(pv.name)
    return f"""
    <section class="sumcheck-card" id="{anchor}">
      <h3>{anchor}</h3>
      <div class="metadata">
        <div class="meta-item"><span class="meta-label">Constraints</span> {len(pv.constraints)} product constraints</div>
        <div class="meta-item"><span class="meta-label">Cycle var</span> ${pv.cycle_var.name} \\in \\{{0,1\\}}^{{{latex_dim_expr(pv.cycle_var.log_size)}}}$</div>
        <div class="meta-item"><span class="meta-label">Constraint domain</span> {pv.constraint_domain}</div>
        <div class="meta-item"><span class="meta-label">Rounds</span> ${latex_dim_expr(pv.rounds)}$</div>
      </div>

      <div class="spec-section">
        <h4>Integrand structure</h4>
        <div class="math-block">$$
          \\widetilde{{\\text{{eq}}}}(r_{{\\text{{cycle}}}}^{{(1)}}, {pv.cycle_var.name})
          \\cdot L_{{\\tau_c}}(X_c)
          \\cdot \\text{{Left}}({pv.cycle_var.name}, X_c)
          \\cdot \\text{{Right}}({pv.cycle_var.name}, X_c)
        $$</div>
      </div>

      <div class="spec-section">
        <h4>Constraint table</h4>
        <div class="table-wrap">
        <table class="constraint-table">
          <thead>
            <tr><th>c</th><th>Label</th><th>Output</th><th>Left</th><th>Right</th></tr>
          </thead>
          <tbody>{"".join(rows)}
          </tbody>
        </table>
        </div>
      </div>
      {_opening_list(pv.openings)}
    </section>"""


def _render_spec(spec) -> str:
    """Dispatch to the right renderer based on spec type."""
    if isinstance(spec, SpartanSpec):
        return _render_spartan(spec)
    if isinstance(spec, ProductVirtSpec):
        return _render_product_virt(spec)
    if isinstance(spec, SumcheckSpec):
        return _render_sumcheck(spec)
    return f"<pre>Unknown spec type: {type(spec)}</pre>"


# ═══════════════════════════════════════════════════════════════════
# Page template
# ═══════════════════════════════════════════════════════════════════

_CSS = """
:root {
  --bg: #0d1117;
  --card-bg: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --text-muted: #8b949e;
  --accent: #58a6ff;
  --green: #3fb950;
  --orange: #d29922;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}
nav {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}
nav a {
  color: var(--accent);
  text-decoration: none;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  border: 1px solid var(--border);
  font-size: 0.85rem;
}
nav a:hover, nav a.active {
  background: var(--accent);
  color: var(--bg);
  border-color: var(--accent);
}
h1 {
  font-size: 1.8rem;
  margin-bottom: 1.5rem;
  color: var(--text);
}
.sumcheck-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.sumcheck-card h3 {
  font-size: 1.3rem;
  margin-bottom: 1rem;
  color: var(--accent);
}
.metadata {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.meta-item {
  font-size: 0.9rem;
}
.meta-label {
  color: var(--text-muted);
  margin-right: 0.3rem;
}
.meta-label::after { content: ":"; }
.sum-over {
  margin-bottom: 1rem;
  padding: 0.5rem 0.75rem;
  background: rgba(88, 166, 255, 0.05);
  border-left: 3px solid var(--accent);
  border-radius: 0 4px 4px 0;
}
.spec-section { margin-top: 1rem; }
.spec-section h4 {
  font-size: 0.85rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}
.math-block {
  overflow-x: auto;
  padding: 0.75rem 1rem;
  background: rgba(255,255,255,0.02);
  border-radius: 4px;
  border: 1px solid var(--border);
}
.table-wrap { overflow-x: auto; }
.constraint-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.constraint-table th, .constraint-table td {
  padding: 0.4rem 0.75rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  white-space: nowrap;
}
.constraint-table th {
  color: var(--text-muted);
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
}
.constraint-table .idx { text-align: right; color: var(--text-muted); }
.constraint-table .label { font-family: monospace; font-size: 0.8rem; }
.constraint-table .math-cell { font-size: 0.85rem; }
.openings { list-style: none; padding-left: 0; }
.openings li {
  padding: 0.2rem 0;
  font-size: 0.9rem;
}
.openings li::before {
  content: "\\2192 ";
  color: var(--text-muted);
}
"""


def _page(title: str, body: str, active_page: str, total_stages: int = 7) -> str:
    """Wrap body content in a full HTML page with KaTeX and nav.

    active_page: "index", "stage1".."stage7", "openings", or "polynomials"
    """
    nav_links = ['<a href="index.html"{}>{}</a>'.format(
        ' class="active"' if active_page == "index" else "", "Overview")]
    for s in range(1, total_stages + 1):
        cls = ' class="active"' if active_page == f"stage{s}" else ""
        nav_links.append(f'<a href="stage{s}.html"{cls}>Stage {s}</a>')
    for page, label in [("openings", "Openings"), ("polynomials", "Polynomials"), ("resolve", "Resolve")]:
        cls = ' class="active"' if active_page == page else ""
        nav_links.append(f'<a href="{page}.html"{cls}>{label}</a>')
    nav = "\n    ".join(nav_links)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html_mod.escape(title)}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{
      delimiters: [
        {{left: '$$', right: '$$', display: true}},
        {{left: '$', right: '$', display: false}}
      ],
      throwOnError: false
    }});"></script>
  <style>{_CSS}</style>
</head>
<body>
  <nav>
    {nav}
  </nav>
  <h1>{html_mod.escape(title)}</h1>
  {body}
</body>
</html>"""


def _index_page(stages: dict[int, tuple[str, list]], total_stages: int = 7) -> str:
    """Generate the overview/index page."""
    cards = []
    for s in sorted(stages.keys()):
        title, specs = stages[s]
        count = len(specs)
        cards.append(f"""
    <a href="stage{s}.html" class="stage-link">
      <div class="sumcheck-card">
        <h3>Stage {s}</h3>
        <p>{html_mod.escape(title)}</p>
        <p class="meta-item">{count} sumcheck{'s' if count != 1 else ''}</p>
      </div>
    </a>""")

    extra_css = """
    .stage-link { text-decoration: none; color: inherit; }
    .stage-link .sumcheck-card { transition: border-color 0.2s; }
    .stage-link:hover .sumcheck-card { border-color: var(--accent); }
    """

    body = f"""
  <p style="color: var(--text-muted); margin-bottom: 2rem;">
    Formal AST-based specifications of all 21 sumchecks in Jolt's proving pipeline.
  </p>
  {"".join(cards)}"""

    # Reuse _page with extra CSS injected into body
    return _page("Jolt Sumcheck Specifications", body, "index", total_stages).replace(
        f"<style>{_CSS}</style>",
        f"<style>{_CSS}{extra_css}</style>",
    )


# ═══════════════════════════════════════════════════════════════════
# Openings overview page
# ═══════════════════════════════════════════════════════════════════

def _openings_page(stages: dict[int, tuple[str, list]]) -> str:
    """Generate the openings overview page.

    Walks all specs and collects the openings produced by each,
    grouped by stage.  Each opening links back to the producing
    sumcheck on its stage page.
    """
    # Collect: [(stage, sumcheck_name, poly_name, args)]
    entries: list[tuple[int, str, str, list[Arg]]] = []
    for s in sorted(stages.keys()):
        _title, specs = stages[s]
        for spec in specs:
            for poly_name, args in spec.openings:
                entries.append((s, spec.name, poly_name, args))

    # Group by stage
    body_parts = []
    current_stage = None
    for stage, sc_name, poly_name, args in entries:
        if stage != current_stage:
            if current_stage is not None:
                body_parts.append("</div></section>")  # close prior card
            current_stage = stage
            stage_title = stages[stage][0]
            body_parts.append(f"""
    <section class="sumcheck-card">
      <h3>Stage {stage} — {html_mod.escape(stage_title)}</h3>
      <div class="openings-list">""")

        entry_latex = latex_opening_entry(poly_name, args, _FMT)
        link = f"stage{stage}.html#{html_mod.escape(sc_name)}"
        body_parts.append(f"""
        <div class="opening-row">
          <a href="{link}" class="opening-source">{html_mod.escape(sc_name)}</a>
          <span class="opening-arrow">→</span>
          <span class="opening-poly">${entry_latex}$</span>
        </div>""")

    if current_stage is not None:
        body_parts.append("</div></section>")

    extra_css = """
    .openings-list { display: flex; flex-direction: column; gap: 0.3rem; }
    .opening-row {
      display: flex;
      align-items: baseline;
      gap: 0.75rem;
      padding: 0.3rem 0;
      border-bottom: 1px solid var(--border);
    }
    .opening-row:last-child { border-bottom: none; }
    .opening-source {
      color: var(--accent);
      text-decoration: none;
      font-size: 0.85rem;
      min-width: 20ch;
      font-family: monospace;
    }
    .opening-source:hover { text-decoration: underline; }
    .opening-arrow { color: var(--text-muted); }
    .opening-poly { font-size: 0.9rem; }
    """

    body = "\n".join(body_parts)
    return _page("Openings Overview", body, "openings").replace(
        f"<style>{_CSS}</style>",
        f"<style>{_CSS}{extra_css}</style>",
    )


# ═══════════════════════════════════════════════════════════════════
# Polynomial registry page
# ═══════════════════════════════════════════════════════════════════

def _polynomials_page() -> str:
    """Generate the polynomial registry page.

    Shows all committed, virtual, and verifier-computable polynomials
    grouped by kind and category, plus the parameters table.
    """
    from .registry import COMMITTED_POLYS, VIRTUAL_POLYS, VERIFIER_POLYS, PARAMS

    _SECTIONS = [
        ("Committed Polynomials", "committed-header", COMMITTED_POLYS, "ForestGreen"),
        ("Virtual Polynomials", "virtual-header", VIRTUAL_POLYS, "BurntOrange"),
        ("Verifier-Computable Polynomials", "verifier-header", VERIFIER_POLYS, None),
    ]

    body_parts = []
    for section_title, css_class, polys, colour in _SECTIONS:
        body_parts.append(f'<h2 class="poly-section-header {css_class}">{section_title}</h2>')

        # Group by category
        current_cat = None
        for p in polys:
            if p.category != current_cat:
                current_cat = p.category
                if current_cat:
                    body_parts.append(
                        f'<h3 class="poly-category">{html_mod.escape(current_cat)}</h3>'
                    )

            # Name with colour
            latex_name = _latex_poly_name(p.name)
            if colour:
                latex_name = f"\\textcolor{{{colour}}}{{{latex_name}}}"

            # Domain
            if p.domain:
                dims = " \\times ".join(
                    f"\\{{0,1\\}}^{{\\log_2 {_latex_param(d.size)}}}" for d in p.domain
                )
                domain_html = f'<span class="poly-domain">$${dims} \\to \\mathbb{{F}}$$</span>'
            else:
                domain_html = '<span class="poly-domain">(no fixed domain)</span>'

            body_parts.append(f"""
        <div class="poly-entry">
          <div class="poly-name">${latex_name}$</div>
          {domain_html}
          <div class="poly-desc">{html_mod.escape(p.description)}</div>
        </div>""")

    # Parameters table
    body_parts.append('<h2 class="poly-section-header params-header">Parameters</h2>')
    body_parts.append("""
    <div class="table-wrap">
    <table class="constraint-table">
      <thead>
        <tr><th>Symbol</th><th>Code name</th><th>Description</th><th>Formula</th></tr>
      </thead>
      <tbody>""")
    for p in PARAMS:
        symbol_latex = _latex_param(p.symbol)
        formula = html_mod.escape(p.formula) if p.formula else "—"
        code = html_mod.escape(p.name) if p.name else "—"
        body_parts.append(f"""
        <tr>
          <td>${symbol_latex}$</td>
          <td class="label">{code}</td>
          <td>{html_mod.escape(p.description)}</td>
          <td>{formula}</td>
        </tr>""")
    body_parts.append("</tbody></table></div>")

    extra_css = """
    .poly-section-header {
      font-size: 1.4rem;
      margin: 2rem 0 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--border);
    }
    .committed-header { color: #3fb950; }
    .virtual-header { color: #d29922; }
    .verifier-header { color: var(--accent); }
    .params-header { color: var(--text-muted); }
    .poly-category {
      font-size: 1rem;
      color: var(--text-muted);
      margin: 1.2rem 0 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .poly-entry {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem 1rem;
      margin-bottom: 0.5rem;
    }
    .poly-name { font-size: 1rem; margin-bottom: 0.25rem; }
    .poly-domain {
      font-size: 0.85rem;
      color: var(--text-muted);
      display: block;
      margin-bottom: 0.25rem;
    }
    .poly-desc { font-size: 0.85rem; color: var(--text-muted); }
    """

    body = "\n".join(body_parts)
    return _page("Polynomial Registry", body, "polynomials").replace(
        f"<style>{_CSS}</style>",
        f"<style>{_CSS}{extra_css}</style>",
    )


# ═══════════════════════════════════════════════════════════════════
# Resolve DAG page — interactive claim-flow graph
# ═══════════════════════════════════════════════════════════════════

def _resolve_page() -> str:
    """Generate the interactive claim-flow DAG page using Cytoscape.js."""
    import json
    from .resolve import resolution_data

    data = resolution_data()
    data_json = json.dumps(data, indent=None)

    _STAGE_COLORS = {
        0: "#3fb950",  # PCS — green
        1: "#1f6feb",  # Stage 1 — blue
        2: "#8957e5",  # Stage 2 — purple
        3: "#d29922",  # Stage 3 — amber
        4: "#f0883e",  # Stage 4 — orange
        5: "#56d364",  # Stage 5 — light green
        6: "#79c0ff",  # Stage 6 — sky blue
        7: "#ff7b72",  # Stage 7 — salmon
    }
    stage_colors_js = json.dumps(_STAGE_COLORS)

    unresolved_note = ""
    if data["unresolved"]:
        n = len(data["unresolved"])
        unresolved_note = (
            f'<span style="color:#f85149;margin-left:1rem">'
            f'⚠ {n} unresolved virtual claim{"s" if n != 1 else ""}</span>'
        )

    extra_css = """
    .resolve-bar {
      display: flex;
      align-items: center;
      gap: 1.25rem;
      flex-wrap: wrap;
      margin-bottom: 1rem;
      padding: 0.6rem 1rem;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      font-size: 0.85rem;
    }
    .legend-item { display: flex; align-items: center; gap: 0.35rem; color: var(--text-muted); }
    .legend-dot { width: 14px; height: 4px; border-radius: 2px; display: inline-block; }
    .btn-ctrl {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 0.25rem 0.7rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.8rem;
    }
    .btn-ctrl:hover { border-color: var(--accent); color: var(--accent); }
    .resolve-wrap { display: flex; gap: 1rem; height: 700px; }
    #cy {
      flex: 1;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card-bg);
    }
    #info-panel {
      width: 270px;
      flex-shrink: 0;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: var(--card-bg);
      padding: 1rem;
      overflow-y: auto;
      font-size: 0.85rem;
    }
    #info-panel h3 { color: var(--accent); margin-bottom: 0.5rem; font-size: 1rem; }
    #info-panel .hint { color: var(--text-muted); font-size: 0.8rem; }
    .info-section { margin-top: 0.85rem; }
    .info-label {
      color: var(--text-muted);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.3rem;
    }
    .info-poly {
      font-family: monospace;
      font-size: 0.78rem;
      padding: 0.1rem 0;
      word-break: break-all;
    }
    .info-poly.vp { color: #d29922; }
    .info-poly.cp { color: #3fb950; }
    .stage-badge {
      display: inline-block;
      padding: 0.15rem 0.5rem;
      border-radius: 4px;
      font-size: 0.72rem;
      font-weight: 600;
    }
    """

    body = f"""
  <div class="resolve-bar">
    <button class="btn-ctrl" id="btn-fit">Fit all</button>
    <button class="btn-ctrl" id="btn-reset">Reset</button>
    <span class="legend-item">
      <span class="legend-dot" style="background:#d29922"></span> virtual poly claim
    </span>
    <span class="legend-item">
      <span class="legend-dot" style="background:#3fb950"></span> committed → PCS
    </span>
    {unresolved_note}
  </div>
  <div class="resolve-wrap">
    <div id="cy"></div>
    <div id="info-panel">
      <h3>Claim Flow DAG</h3>
      <p class="hint">Click a node or edge to explore claim flows between sumchecks.</p>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
  <script>
    const RESOLVE_DATA = {data_json};
    const STAGE_COLORS = {stage_colors_js};
    const STAGE_LABELS = {{
      0: 'PCS', 1: 'Stage 1', 2: 'Stage 2', 3: 'Stage 3',
      4: 'Stage 4', 5: 'Stage 5', 6: 'Stage 6', 7: 'Stage 7'
    }};

    cytoscape.use(cytoscapeDagre);

    const cyNodes = RESOLVE_DATA.nodes.map(n => ({{
      data: {{ ...n, color: STAGE_COLORS[n.stage] || '#888' }}
    }}));

    const cyEdges = RESOLVE_DATA.edges.map(e => {{
      const polys = e.poly_names;
      const shortLabel = polys.length <= 2
        ? polys.join(', ')
        : polys.slice(0, 2).join(', ') + ' +' + (polys.length - 2);
      return {{ data: {{ ...e, label: shortLabel }} }};
    }});

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: {{ nodes: cyNodes, edges: cyEdges }},
      style: [
        {{
          selector: 'node',
          style: {{
            'background-color': 'data(color)',
            'label': 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'padding': '10px',
            'font-size': '10px',
            'color': '#fff',
            'text-wrap': 'wrap',
            'text-max-width': '130px',
            'shape': 'round-rectangle',
            'border-width': 0,
          }}
        }},
        {{
          selector: 'node[?is_pcs]',
          style: {{
            'shape': 'ellipse',
            'font-weight': 'bold',
            'font-size': '12px',
            'padding': '18px',
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 2,
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'line-color': function(ele) {{
              return ele.data('kind') === 'cp' ? '#3fb950' : '#d29922';
            }},
            'target-arrow-color': function(ele) {{
              return ele.data('kind') === 'cp' ? '#3fb950' : '#d29922';
            }},
            'label': 'data(label)',
            'font-size': '8px',
            'color': '#8b949e',
            'text-rotation': 'autorotate',
            'text-background-color': '#161b22',
            'text-background-opacity': 0.85,
            'text-background-padding': '2px',
            'text-margin-y': -8,
          }}
        }},
        {{
          selector: '.highlighted',
          style: {{
            'border-width': 3,
            'border-color': '#58a6ff',
            'line-color': '#58a6ff',
            'target-arrow-color': '#58a6ff',
            'opacity': 1,
          }}
        }},
        {{
          selector: '.dimmed',
          style: {{ 'opacity': 0.15 }}
        }},
      ],
      layout: {{
        name: 'dagre',
        rankDir: 'LR',
        nodeSep: 40,
        rankSep: 110,
        edgeSep: 8,
        fit: true,
        padding: 30,
        ranker: 'longest-path',
      }}
    }});

    const panel = document.getElementById('info-panel');

    function defaultPanel() {{
      panel.innerHTML = '<h3>Claim Flow DAG</h3><p class="hint">Click a node or edge to explore claim flows between sumchecks.</p>';
    }}

    function showNodeInfo(node) {{
      const d = node.data();
      const color = d.color;
      const incoming = node.incomers('edge');
      const outgoing = node.outgoers('edge');

      let html = `<h3>${{d.label}}</h3>
        <span class="stage-badge" style="background:${{color}}22;color:${{color}};border:1px solid ${{color}}44">
          ${{STAGE_LABELS[d.stage] || ''}}
        </span>
        <div class="hint" style="margin-top:.4rem">${{d.stage_title}}</div>`;

      if (incoming.length) {{
        html += `<div class="info-section"><div class="info-label">Consumes (${{incoming.length}} flow${{incoming.length>1?'s':''}})</div>`;
        incoming.forEach(e => {{
          e.data('poly_names').forEach(p => {{
            html += `<div class="info-poly ${{e.data('kind')}}">${{e.data('kind')}}:${{p}}</div>`;
          }});
        }});
        html += '</div>';
      }}

      if (outgoing.length) {{
        html += `<div class="info-section"><div class="info-label">Produces (${{outgoing.length}} flow${{outgoing.length>1?'s':''}})</div>`;
        outgoing.forEach(e => {{
          const tgt = e.target().id() === 'PCS' ? ' → PCS' : '';
          e.data('poly_names').forEach(p => {{
            html += `<div class="info-poly ${{e.data('kind')}}">${{e.data('kind')}}:${{p}}${{tgt}}</div>`;
          }});
        }});
        html += '</div>';
      }}

      panel.innerHTML = html;
    }}

    function showEdgeInfo(edge) {{
      const d = edge.data();
      const src = edge.source().data();
      const tgt = edge.target().data();
      const kindLabel = d.kind === 'cp' ? 'Committed → PCS' : 'Virtual poly claim';
      const color = d.kind === 'cp' ? '#3fb950' : '#d29922';

      panel.innerHTML = `
        <h3 style="color:${{color}}">${{kindLabel}}</h3>
        <div class="info-section">
          <div class="info-label">From</div>
          <div>${{src.label}}</div>
        </div>
        <div class="info-section">
          <div class="info-label">To</div>
          <div>${{tgt.label}}</div>
        </div>
        <div class="info-section">
          <div class="info-label">Polynomials (${{d.poly_names.length}})</div>
          ${{d.poly_names.map(p => `<div class="info-poly ${{d.kind}}">${{d.kind}}:${{p}}</div>`).join('')}}
        </div>`;
    }}

    cy.on('tap', 'node', evt => {{
      const node = evt.target;
      const neighborhood = node.closedNeighborhood();
      cy.elements().addClass('dimmed');
      neighborhood.removeClass('dimmed').addClass('highlighted');
      node.removeClass('dimmed');
      showNodeInfo(node);
    }});

    cy.on('tap', 'edge', evt => {{
      const edge = evt.target;
      cy.elements().addClass('dimmed');
      edge.removeClass('dimmed').addClass('highlighted');
      edge.connectedNodes().removeClass('dimmed').addClass('highlighted');
      showEdgeInfo(edge);
    }});

    cy.on('tap', evt => {{
      if (evt.target === cy) {{
        cy.elements().removeClass('dimmed highlighted');
        defaultPanel();
      }}
    }});

    document.getElementById('btn-fit').addEventListener('click', () => cy.fit(30));
    document.getElementById('btn-reset').addEventListener('click', () => {{
      cy.elements().removeClass('dimmed highlighted');
      cy.fit(30);
      defaultPanel();
    }});
  </script>"""

    return _page("Resolve — Claim Flow DAG", body, "resolve").replace(
        f"<style>{_CSS}</style>",
        f"<style>{_CSS}{extra_css}</style>",
    )


# ═══════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════

def generate_html(out_dir: str | Path = "docs", stages: dict | None = None) -> None:
    """Generate the HTML site.

    Args:
        out_dir:  output directory (created if needed)
        stages:   dict mapping stage_num → (title, [spec_objects])
                  If None, builds all stages from examples.
    """
    if stages is None:
        stages = _default_stages()

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Index page
    (out / "index.html").write_text(_index_page(stages))
    print(f"  wrote {out / 'index.html'}")

    # Per-stage pages
    for s in sorted(stages.keys()):
        title, specs = stages[s]
        page_title = f"Stage {s} — {title}"
        body = "\n".join(_render_spec(spec) for spec in specs)
        html_content = _page(page_title, body, f"stage{s}")
        path = out / f"stage{s}.html"
        path.write_text(html_content)
        print(f"  wrote {path}")

    # Openings overview page
    (out / "openings.html").write_text(_openings_page(stages))
    print(f"  wrote {out / 'openings.html'}")

    # Polynomial registry page
    (out / "polynomials.html").write_text(_polynomials_page())
    print(f"  wrote {out / 'polynomials.html'}")

    # Resolve DAG page
    (out / "resolve.html").write_text(_resolve_page())
    print(f"  wrote {out / 'resolve.html'}")


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
