# Jolt Sumcheck Specs

Formal AST-based specifications of all 21 sumchecks in Jolt's proving pipeline.

## Usage

```bash
# Print all stages (terminal)
python3 -m sumcheck

# Print a single stage (1–7)
python3 -m sumcheck --stage 5

# Generate HTML site (all stages)
python3 -m sumcheck html

# Generate HTML for a single stage
python3 -m sumcheck html --stage 5

# Generate HTML to custom directory
python3 -m sumcheck html --out ./docs

# Generate LaTeX document (all stages)
python3 -m sumcheck latex

# Generate LaTeX for a single stage
python3 -m sumcheck latex --stage 3

# Generate LaTeX to custom file
python3 -m sumcheck latex --out specs.tex

# Print the polynomial registry
python3 -m sumcheck registry

# Filter registry by kind
python3 -m sumcheck registry --cp    # committed only
python3 -m sumcheck registry --vp    # virtual only
python3 -m sumcheck registry --rp    # verifier-computable only

# Resolution tracker — walks stages, shows resolved/unresolved polys
python3 -m sumcheck resolve
```

## Per-node format system

The expression AST uses a per-node formatting architecture. 
Each AST node type (`Const`, `CommittedPoly`, `Add`, `Mul`, `Prod`, ...) has a corresponding method on the
`Format` base class. 
To add a new output format, subclass `Format` and implement each method:

```python
from sumcheck.format import Format, render
from sumcheck.ast import vp, eq, mul

class MyFormat(Format):
    def fmt_var(self, v):        ...
    def fmt_opening(self, o):    ...
    def fmt_const(self, value):  ...
    # ... one method per node type

expr = mul(eq(...), vp("H", X_t))
print(render(expr, MyFormat()))
```

Built-in formats:
- **TextFormat** — plain-text terminal output (`cp:Name(X_t)`, `·`, `Σ`, `Π`)
- **LatexFormat** — LaTeX math (`\textcolor{ForestGreen}{\textsf{Name}}`, `\cdot`, `\sum`, `\prod`)

