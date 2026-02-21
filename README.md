# Jolt Sumcheck Specs

Formal AST-based specifications of all 21 sumchecks in [Jolt](https://github.com/a16z/jolt)'s proving pipeline.

The sumchecks were hand-transcribed from the Rust source. Advice polynomials are not yet fully modelled — see caveats below.

## Requirements

Python 3.10+. No external dependencies.

## Quick start

```bash
git clone https://github.com/a16z/jolt-sumcheck-specs
cd jolt-sumcheck-specs
python3 -m sumcheck          # print all stages to terminal
```

## CLI reference

```bash
# Terminal output — all stages
python3 -m sumcheck

# Single stage (1–7)
python3 -m sumcheck --stage 5

# Generate HTML site (all stages → docs/)
python3 -m sumcheck html

# HTML for a single stage
python3 -m sumcheck html --stage 5

# HTML to a custom directory
python3 -m sumcheck html --out ./out

# LaTeX document (all stages)
# ⚠️  LaTeX output is not super stable — some expressions may not render correctly.
python3 -m sumcheck latex

# LaTeX for a single stage
python3 -m sumcheck latex --stage 3

# LaTeX to a custom file
python3 -m sumcheck latex --out specs.tex

# Polynomial registry
python3 -m sumcheck registry          # all polynomials
python3 -m sumcheck registry --cp     # committed only
python3 -m sumcheck registry --vp     # virtual only
python3 -m sumcheck registry --rp     # verifier-computable only

# Resolution tracker — shows which polynomial claims are consumed and which are open
python3 -m sumcheck resolve
```

The `html` command generates one page per stage plus three auxiliary pages:

- `openings.html` — all polynomial openings grouped by stage
- `polynomials.html` — full committed / virtual / verifier-computable registry
- `resolve.html` — interactive claim-flow DAG (Cytoscape.js)

## Project structure

```
sumcheck/
  __main__.py      CLI entry point (argparse)
  ast.py           Expression AST nodes and constructors
  defs.py          Dimension and variable definitions (T, m, C, …)
  spec.py          Spec types: SumcheckSpec, SpartanSpec, ProductVirtSpec
  format.py        Format ABC + render() tree walker
  printer.py       TextFormat  — plain-text terminal output
  latex.py         LatexFormat — LaTeX math output
  html.py          HTML site generator (also HtmlFormat)
  resolve.py       Resolution tracker + claim-flow DAG data extractor
  registry.py      Polynomial registry printer
  examples/        Per-stage sumcheck definitions (one file per stage)
```

## Adding a new output format

The expression AST uses a per-node formatting architecture. Subclass `Format` and implement one method per node type:

```python
from sumcheck.format import Format, render
from sumcheck.ast import vp, eq, mul
from sumcheck.defs import X_t

class MyFormat(Format):
    def fmt_var(self, v):           return str(v)
    def fmt_opening(self, o):       return str(o)
    def fmt_const(self, value):     return str(value)
    def fmt_committed(self, name, opening): ...
    def fmt_virtual(self, name, opening):   ...
    def fmt_verifier(self, name, opening):  ...
    def fmt_add(self, a, b):        return f"({a} + {b})"
    def fmt_mul(self, a, b):        return f"({a} * {b})"
    def fmt_neg(self, a):           return f"(-{a})"
    def fmt_pow(self, base, exp):   return f"({base}^{exp})"
    def fmt_sum(self, idx, body):   return f"Σ_{idx} {body}"
    def fmt_fsum(self, idxs, body): return f"Σ_{idxs} {body}"
    def fmt_prod(self, idx, body):  return f"Π_{idx} {body}"

expr = mul(eq(...), vp("H", X_t))
print(render(expr, MyFormat()))
```

Built-in formats:

| Format | Output | Module |
|--------|--------|--------|
| `TextFormat` | Plain-text terminal (`cp:Name(X_t)`, `·`, `Σ`) | `sumcheck/printer.py` |
| `LatexFormat` | LaTeX math (`\textcolor{ForestGreen}{\textsf{Name}}`, `\cdot`) | `sumcheck/latex.py` |
| `HtmlFormat` | Styled HTML spans | `sumcheck/html.py` |

## Adding a new sumcheck

1. Create (or edit) the relevant stage file in `sumcheck/examples/`.
2. Construct a `SumcheckSpec` (or `SpartanSpec`) using the AST constructors in `sumcheck/ast.py`.
3. Register it in `sumcheck/examples/__init__.py` in stage order.

## Caveats

- **Advice polynomials** are not yet fully modelled. They appear in the registry but their opening constraints are incomplete.
- **Stage 7** (Surge / offline memory) is a work in progress.
- **LaTeX output** is not super stable — some expressions may not render correctly.

## Generating the GitHub Pages site

```bash
python3 -m sumcheck html   # writes to docs/
git add docs/
git commit -m "Regenerate specs"
git push
```

GitHub Pages is configured to serve from `docs/` on the `main` branch.

## License

Apache 2.0 — see [LICENSE](LICENSE).
