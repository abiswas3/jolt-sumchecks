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
- **LaTeX output** is not super stable — some expressions may not render correctly.

## Generating the GitHub Pages site

```bash
python3 -m sumcheck html   # writes to docs/
git add docs/
git commit -m "Regenerate specs"
git push
```

GitHub Pages is configured to serve from `docs/` on the `main` branch.

## Resolution trace

```
$ python3 -m sumcheck resolve

========================================================================
  STAGE 1 — SPARTAN
========================================================================

  SpartanOuter (Stage 1)
  ────────────────────────────────────────────────────────────────────
  RHS = constant
  Produces (new opening claims):
    ○ vp:LeftInstructionInput(r_cycle^(1)) → unresolved
    ○ vp:RightInstructionInput(r_cycle^(1)) → unresolved
    ○ vp:Product(r_cycle^(1)) → unresolved
    ○ vp:WriteLookupOutputToRD(r_cycle^(1)) → unresolved
    ○ vp:WritePCtoRD(r_cycle^(1)) → unresolved
    ○ vp:ShouldBranch(r_cycle^(1)) → unresolved
    ○ vp:PC(r_cycle^(1)) → unresolved
    ○ vp:UnexpandedPC(r_cycle^(1)) → unresolved
    ○ vp:Imm(r_cycle^(1)) → unresolved
    ○ vp:RamAddress(r_cycle^(1)) → unresolved
    ○ vp:Rs1Value(r_cycle^(1)) → unresolved
    ○ vp:Rs2Value(r_cycle^(1)) → unresolved
    ○ vp:RdWriteValue(r_cycle^(1)) → unresolved
    ○ vp:RamReadValue(r_cycle^(1)) → unresolved
    ○ vp:RamWriteValue(r_cycle^(1)) → unresolved
    ○ vp:LeftLookupOperand(r_cycle^(1)) → unresolved
    ○ vp:RightLookupOperand(r_cycle^(1)) → unresolved
    ○ vp:NextUnexpandedPC(r_cycle^(1)) → unresolved
    ○ vp:NextPC(r_cycle^(1)) → unresolved
    ○ vp:NextIsVirtual(r_cycle^(1)) → unresolved
    ○ vp:NextIsFirstInSequence(r_cycle^(1)) → unresolved
    ○ vp:LookupOutput(r_cycle^(1)) → unresolved
    ○ vp:ShouldJump(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(AddOperands)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(SubtractOperands)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(MultiplyOperands)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(Load)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(Store)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(Jump)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(WriteLookupOutputToRD)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(VirtualInstruction)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(Assert)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(DoNotUpdateUnexpandedPC)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(Advice)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(IsCompressed)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(IsFirstInSequence)(r_cycle^(1)) → unresolved
    ○ vp:OpFlags(IsLastInSequence)(r_cycle^(1)) → unresolved

========================================================================
  STAGE 2 — VIRTUALIZATION & RAM
========================================================================

  SpartanProductVirtualization
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:Product(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:WriteLookupOutputToRD(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:WritePCtoRD(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:ShouldBranch(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:ShouldJump(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  Produces (new opening claims):
    ○ vp:LeftInstructionInput(r_cycle^(2)) → unresolved
    ○ vp:RightInstructionInput(r_cycle^(2)) → unresolved
    ○ vp:InstructionFlags(IsRdNotZero)(r_cycle^(2)) → unresolved
    ○ vp:OpFlags(WriteLookupOutputToRD)(r_cycle^(2)) → unresolved
    ○ vp:OpFlags(Jump)(r_cycle^(2)) → unresolved
    ○ vp:LookupOutput(r_cycle^(2)) → unresolved
    ○ vp:InstructionFlags(Branch)(r_cycle^(2)) → unresolved
    ○ vp:NextIsNoop(r_cycle^(2)) → unresolved
    ○ vp:OpFlags(VirtualInstruction)(r_cycle^(2)) → unresolved

  RamReadWriteChecking
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamReadValue(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:RamWriteValue(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  Produces (new opening claims):
    ○ vp:RamVal(r_K_ram^(2), r_cycle^(2)) → unresolved
    ○ vp:RamRa(r_K_ram^(2), r_cycle^(2)) → unresolved
    ● cp:RamInc(r_cycle^(2)) → PCS-verified

  InstructionClaimReduction
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:LookupOutput(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:LeftLookupOperand(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:RightLookupOperand(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  Produces (new opening claims):
    ○ vp:LookupOutput(r_cycle^(2)) → unresolved
    ○ vp:LeftLookupOperand(r_cycle^(2)) → unresolved
    ○ vp:RightLookupOperand(r_cycle^(2)) → unresolved
    ○ vp:LeftInstructionInput(r_cycle^(2)) → unresolved
    ○ vp:RightInstructionInput(r_cycle^(2)) → unresolved

  RamRafEvaluation
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamAddress(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  Produces (new opening claims):
    ○ vp:RamRa(r_K_ram^(2), r_cycle^(1)) → unresolved

  RamOutputCheck
  ────────────────────────────────────────────────────────────────────
  RHS = constant
  Produces (new opening claims):
    ○ vp:RamValFinal(r_K_ram^(2)) → unresolved

========================================================================
  STAGE 3 — SHIFT & INSTRUCTION INPUT
========================================================================

  Shift
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:NextUnexpandedPC(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:NextPC(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:NextIsVirtual(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:NextIsFirstInSequence(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:NextIsNoop(r_cycle^(2)) ← S2 SpartanProductVirtualization
  Produces (new opening claims):
    ○ vp:UnexpandedPC(r_cycle^(3)) → unresolved
    ○ vp:PC(r_cycle^(3)) → unresolved
    ○ vp:OpFlags(VirtualInstruction)(r_cycle^(3)) → unresolved
    ○ vp:OpFlags(IsFirstInSequence)(r_cycle^(3)) → unresolved
    ○ vp:InstructionFlags(IsNoop)(r_cycle^(3)) → unresolved

  InstructionInput
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RightInstructionInput(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:LeftInstructionInput(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:RightInstructionInput(r_cycle^(2)) ← S2 InstructionClaimReduction
  ✓ vp:LeftInstructionInput(r_cycle^(2)) ← S2 InstructionClaimReduction
  Produces (new opening claims):
    ○ vp:InstructionFlags(LeftOperandIsRs1Value)(r_cycle^(3)) → unresolved
    ○ vp:Rs1Value(r_cycle^(3)) → unresolved
    ○ vp:InstructionFlags(LeftOperandIsPC)(r_cycle^(3)) → unresolved
    ○ vp:UnexpandedPC(r_cycle^(3)) → unresolved
    ○ vp:InstructionFlags(RightOperandIsRs2Value)(r_cycle^(3)) → unresolved
    ○ vp:Rs2Value(r_cycle^(3)) → unresolved
    ○ vp:InstructionFlags(RightOperandIsImm)(r_cycle^(3)) → unresolved
    ○ vp:Imm(r_cycle^(3)) → unresolved

  RegistersClaimReduction
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RdWriteValue(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:Rs1Value(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:Rs2Value(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  Produces (new opening claims):
    ○ vp:RdWriteValue(r_cycle^(3)) → unresolved
    ○ vp:Rs1Value(r_cycle^(3)) → unresolved
    ○ vp:Rs2Value(r_cycle^(3)) → unresolved

========================================================================
  STAGE 4 — REGISTERS & RAM VAL
========================================================================

  RegistersReadWriteChecking
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RdWriteValue(r_cycle^(3)) ← S3 RegistersClaimReduction
  ✓ vp:Rs1Value(r_cycle^(3)) ← S3 RegistersClaimReduction
  ✓ vp:Rs2Value(r_cycle^(3)) ← S3 RegistersClaimReduction
  Produces (new opening claims):
    ○ vp:RegistersVal(r_K_reg^(4), r_cycle^(4)) → unresolved
    ○ vp:Rs1Ra(r_K_reg^(4), r_cycle^(4)) → unresolved
    ○ vp:Rs2Ra(r_K_reg^(4), r_cycle^(4)) → unresolved
    ○ vp:RdWa(r_K_reg^(4), r_cycle^(4)) → unresolved
    ● cp:RdInc(r_cycle^(4)) → PCS-verified

  RamValCheck
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamVal(r_K_ram^(2), r_cycle^(2)) ← S2 RamReadWriteChecking
  ✓ vp:RamValFinal(r_K_ram^(2)) ← S2 RamOutputCheck
  RHS (public inputs / constants):
    vp:RamValInit(r_K_ram^(2))
  Produces (new opening claims):
    ● cp:RamInc(r_cycle^(4)) → PCS-verified
    ○ vp:RamRa(r_K_ram^(2), r_cycle^(4)) → unresolved

========================================================================
  STAGE 5 — INSTRUCTION READ RAF & REDUCTIONS
========================================================================

  InstructionReadRaf
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:LookupOutput(r_cycle^(2)) ← S2 InstructionClaimReduction
  ✓ vp:LeftLookupOperand(r_cycle^(2)) ← S2 InstructionClaimReduction
  ✓ vp:RightLookupOperand(r_cycle^(2)) ← S2 InstructionClaimReduction
  Produces (new opening claims):
    ○ vp:InstructionRa(i)(r_K_instr^(i)^(5), r_cycle^(5)) → unresolved
    ○ vp:TableFlag(j)(r_cycle^(5)) → unresolved
    ○ vp:InstructionRafFlag(r_cycle^(5)) → unresolved

  RamRaClaimReduction
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamRa(r_K_ram^(2), r_cycle^(1)) ← S2 RamRafEvaluation
  ✓ vp:RamRa(r_K_ram^(2), r_cycle^(2)) ← S2 RamReadWriteChecking
  ✓ vp:RamRa(r_K_ram^(2), r_cycle^(4)) ← S4 RamValCheck
  Produces (new opening claims):
    ○ vp:RamRa(r_K_ram^(2), r_cycle^(5)) → unresolved

  RegistersValEvaluation
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RegistersVal(r_K_reg^(4), r_cycle^(4)) ← S4 RegistersReadWriteChecking
  Produces (new opening claims):
    ● cp:RdInc(r_cycle^(5)) → PCS-verified
    ○ vp:RdWa(r_K_reg^(4), r_cycle^(5)) → unresolved

========================================================================
  STAGE 6 — BOOLEANITY, BYTECODE & VIRTUALIZATION
========================================================================

  RamHammingBooleanity
  ────────────────────────────────────────────────────────────────────
  RHS = constant
  Produces (new opening claims):
    ○ vp:RamHammingWeight(r_cycle^(6)) → unresolved

  IncClaimReduction
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ cp:RamInc(r_cycle^(2)) ← S2 RamReadWriteChecking
  ✓ cp:RamInc(r_cycle^(4)) ← S4 RamValCheck
  ✓ cp:RdInc(r_cycle^(4)) ← S4 RegistersReadWriteChecking
  ✓ cp:RdInc(r_cycle^(5)) ← S5 RegistersValEvaluation
  Produces (new opening claims):
    ● cp:RamInc(r_cycle^(6)) → PCS-verified
    ● cp:RdInc(r_cycle^(6)) → PCS-verified

  BytecodeReadRaf
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:UnexpandedPC(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:Imm(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(AddOperands)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Advice)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Assert)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(DoNotUpdateUnexpandedPC)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(IsCompressed)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(IsFirstInSequence)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(IsLastInSequence)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Jump)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Load)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(MultiplyOperands)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Store)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(SubtractOperands)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(VirtualInstruction)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(WriteLookupOutputToRD)(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:OpFlags(Jump)(r_cycle^(2)) ← S2 SpartanProductVirtualization
  ✓ vp:InstructionFlags(Branch)(r_cycle^(2)) ← S2 SpartanProductVirtualization
  ✓ vp:InstructionFlags(IsRdNotZero)(r_cycle^(2)) ← S2 SpartanProductVirtualization
  ✓ vp:OpFlags(WriteLookupOutputToRD)(r_cycle^(2)) ← S2 SpartanProductVirtualization
  ✓ vp:OpFlags(VirtualInstruction)(r_cycle^(2)) ← S2 SpartanProductVirtualization
  ✓ vp:Imm(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:UnexpandedPC(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:InstructionFlags(LeftOperandIsRs1Value)(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:InstructionFlags(LeftOperandIsPC)(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:InstructionFlags(RightOperandIsRs2Value)(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:InstructionFlags(RightOperandIsImm)(r_cycle^(3)) ← S3 InstructionInput
  ✓ vp:InstructionFlags(IsNoop)(r_cycle^(3)) ← S3 Shift
  ✓ vp:OpFlags(VirtualInstruction)(r_cycle^(3)) ← S3 Shift
  ✓ vp:OpFlags(IsFirstInSequence)(r_cycle^(3)) ← S3 Shift
  ✓ vp:RdWa(r_K_reg^(4), r_cycle^(4)) ← S4 RegistersReadWriteChecking
  ✓ vp:Rs1Ra(r_K_reg^(4), r_cycle^(4)) ← S4 RegistersReadWriteChecking
  ✓ vp:Rs2Ra(r_K_reg^(4), r_cycle^(4)) ← S4 RegistersReadWriteChecking
  ✓ vp:RdWa(r_K_reg^(4), r_cycle^(5)) ← S5 RegistersValEvaluation
  ✓ vp:InstructionRafFlag(r_cycle^(5)) ← S5 InstructionReadRaf
  ✓ vp:TableFlag(j)(r_cycle^(5)) ← S5 InstructionReadRaf
  ✓ vp:PC(r_cycle^(1)) ← S1 SpartanOuter (Stage 1)
  ✓ vp:PC(r_cycle^(3)) ← S3 Shift
  Produces (new opening claims):
    ● cp:BytecodeRa(i)(r_K_bc^(i)^(6), r_cycle^(6)) → PCS-verified

  InstructionRaVirtualization
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:InstructionRa(i)(r_K_instr^(i)^(5), r_cycle^(5)) ← S5 InstructionReadRaf
  Produces (new opening claims):
    ● cp:InstructionRa(j)(r_K^(j)^(5), r_cycle^(6)) → PCS-verified

  RamRaVirtualization
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamRa(r_K_ram^(2), r_cycle^(5)) ← S5 RamRaClaimReduction
  Produces (new opening claims):
    ● cp:RamRa(i)(r_K_ram^(i)^(2), r_cycle^(6)) → PCS-verified

  Booleanity
  ────────────────────────────────────────────────────────────────────
  RHS = constant
  Produces (new opening claims):
    ● cp:Ra_j(r_addr^(6), r_cycle^(6)) → PCS-verified

========================================================================
  STAGE 7 — HAMMING WEIGHT CLAIM REDUCTION
========================================================================

  HammingWeightClaimReduction
  ────────────────────────────────────────────────────────────────────
  Consumes (resolves prior claims):
  ✓ vp:RamHammingWeight(r_cycle^(6)) ← S6 RamHammingBooleanity
  ✓ cp:Ra_j(r_addr^(6), r_cycle^(6)) ← S6 Booleanity
  RHS (public inputs / constants):
    cp:Ra_j(r_addr_j^(6), r_cycle^(6))
  Produces (new opening claims):
    ● cp:Ra_j(r_addr^(7), r_cycle^(6)) → PCS-verified

========================================================================
  SUMMARY
========================================================================
  Claims resolved across stages: 81
  Committed claims (PCS-verified): 6

  All virtual claims resolved ✓
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
