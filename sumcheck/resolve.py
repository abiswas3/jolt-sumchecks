"""
Resolution tracker — walks sumcheck stages and tracks opening claims.

The sumcheck protocol flow:
  1. The LHS integrand contains polynomials evaluated at summation variables.
  2. After the sumcheck, those variables bind to random challenges (the opening point).
  3. This produces opening CLAIMS — the prover claims P(r) = v for each poly P.
  4. A claim is UNRESOLVED until it is consumed on the RHS of a later sumcheck.
  5. Committed (cp) claims are always resolved by PCS verification.
  6. Verifier polynomials are always known — never produce claims.
  7. Virtual (vp) claims MUST appear on a later RHS to be resolved.

Usage:
    python3 -m sumcheck resolve
"""

from __future__ import annotations
import re

from .defs import Var, Opening, Arg
from .ast import (
    Expr, Const, CommittedPoly, VirtualPoly, VerifierPoly,
    Add, Mul, Pow, Neg, Sum, FSum, Prod,
)
from .spec import SumcheckSpec, SpartanSpec, ProductVirtSpec
from .printer import _fmt_arg
from .registry import ALL_POLYS


# ═══════════════════════════════════════════════════════════════════
# AST walker
# ═══════════════════════════════════════════════════════════════════

def _collect(expr: Expr, out: list[tuple[str, str, tuple]]) -> None:
    """Recursively collect (kind, name, args) from an expression."""
    if isinstance(expr, CommittedPoly):
        out.append(("cp", expr.name, tuple(expr.args)))
    elif isinstance(expr, VirtualPoly):
        out.append(("vp", expr.name, tuple(expr.args)))
    elif isinstance(expr, VerifierPoly):
        out.append(("verifier", expr.name, tuple(expr.args)))
    elif isinstance(expr, Const):
        pass
    elif isinstance(expr, Add):
        _collect(expr.left, out)
        _collect(expr.right, out)
    elif isinstance(expr, Mul):
        _collect(expr.left, out)
        _collect(expr.right, out)
    elif isinstance(expr, Pow):
        _collect(expr.base, out)
    elif isinstance(expr, Neg):
        _collect(expr.expr, out)
    elif isinstance(expr, Sum):
        _collect(expr.body, out)
    elif isinstance(expr, (FSum, Prod)):
        _collect(expr.body, out)


def collect_polys(expr: Expr) -> list[tuple[str, str, tuple]]:
    """Extract unique (kind, name, args) triples from an expression."""
    raw: list[tuple[str, str, tuple]] = []
    _collect(expr, raw)
    seen: set[tuple[str, str, tuple]] = set()
    result = []
    for item in raw:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


# ═══════════════════════════════════════════════════════════════════
# Extract from spec types
# ═══════════════════════════════════════════════════════════════════

def _rhs_polys(spec) -> list[tuple[str, str, tuple]]:
    """Polys referenced on the RHS (input_claim)."""
    if isinstance(spec, SpartanSpec):
        return collect_polys(spec.input_claim)
    elif isinstance(spec, ProductVirtSpec):
        if spec.input_claim is not None:
            return collect_polys(spec.input_claim)
        raw: list[tuple[str, str, tuple]] = []
        for c in spec.constraints:
            _collect(c.output, raw)
        seen: set[tuple[str, str, tuple]] = set()
        return [x for x in raw if not (x in seen or seen.add(x))]
    elif isinstance(spec, SumcheckSpec):
        return collect_polys(spec.input_claim)
    return []


def _opened_claims(spec) -> list[tuple[str, str, list[Arg]]]:
    """Claims produced by this sumcheck: (kind, name, point).

    kind is inferred: names starting with known committed patterns → 'cp',
    otherwise 'vp'. The `openings` field gives (name, [args]).
    """
    if not hasattr(spec, 'openings'):
        return []
    results = []
    for name, args in spec.openings:
        # Infer kind from the spec's integrand/constraints
        kind = _infer_opened_kind(spec, name)
        results.append((kind, name, args))
    return results


def _infer_opened_kind(spec, name: str) -> str:
    """Infer whether an opened poly is cp or vp from the integrand."""
    # Walk the integrand to find the poly
    if isinstance(spec, SumcheckSpec):
        polys = collect_polys(spec.integrand)
    elif isinstance(spec, SpartanSpec):
        raw: list[tuple[str, str, tuple]] = []
        for g in spec.groups:
            for c in g:
                _collect(c.az, raw)
                _collect(c.bz, raw)
        polys = raw
    elif isinstance(spec, ProductVirtSpec):
        raw = []
        for c in spec.constraints:
            _collect(c.left, raw)
            _collect(c.right, raw)
        polys = raw
    else:
        polys = []

    for kind, pname, _ in polys:
        if pname == name and kind in ("cp", "vp"):
            return kind
    # If the name contains a parametric pattern, try base match
    for kind, pname, _ in polys:
        if kind in ("cp", "vp") and _name_matches(pname, name):
            return kind
    return "vp"  # default to vp


def _name_matches(integrand_name: str, opening_name: str) -> bool:
    """Check if an integrand poly name matches an opening name.

    Handles cases like integrand 'Ra_j' matching opening 'Ra_j for j=0..d-1'.
    """
    # Exact match
    if integrand_name == opening_name:
        return True
    # Opening name might be descriptive: "Ra_j for j=0..d-1 (...)"
    if opening_name.startswith(integrand_name):
        return True
    # Strip parametric suffixes
    base_i = integrand_name.split("(")[0] if "(" in integrand_name else integrand_name
    base_o = opening_name.split("(")[0] if "(" in opening_name else opening_name
    base_o = base_o.split(" ")[0]  # strip "for j=0..." descriptions
    return base_i == base_o


def _spec_name(spec) -> str:
    return spec.name


# ═══════════════════════════════════════════════════════════════════
# Claim key for matching
# ═══════════════════════════════════════════════════════════════════

def _is_parametric(name: str) -> tuple[str, str] | None:
    """Check if a name is parametric: 'Base(param)' where param starts lowercase.

    Parametric:     OpFlags(cf_i), TableFlag(j), InstructionRa(i)
    Non-parametric: OpFlags(AddOperands), InstructionFlags(Branch)

    Returns (base, param) or None.
    """
    m = re.match(r'^(.+)\(([a-z][a-z0-9_]*)\)$', name)
    if m:
        return m.group(1), m.group(2)
    return None


def _claim_key(name: str, args: list[Arg] | tuple) -> str:
    """Create a hashable key for matching claims: 'name@point'.

    Only Opening args contribute to the point (Vars are summation vars,
    not part of the opening point).
    """
    point_parts = []
    for a in args:
        if isinstance(a, Opening):
            point_parts.append(_fmt_arg(a))
    point = ", ".join(point_parts)
    # Normalize name: strip descriptive suffixes like "for j=0..."
    base = name.split(" for ")[0].strip()
    return f"{base}@({point})" if point else f"{base}@()"


def _fmt_claim(kind: str, name: str, args) -> str:
    """Format a claim for display."""
    clr = _CLR.get(kind, "")
    point_parts = [_fmt_arg(a) for a in args if isinstance(a, Opening)]
    point = ", ".join(point_parts)
    base = name.split(" for ")[0].strip()
    if point:
        return f"{clr}{kind}:{base}{_RST}({point})"
    return f"{clr}{kind}:{base}{_RST}"


# ═══════════════════════════════════════════════════════════════════
# Registry check
# ═══════════════════════════════════════════════════════════════════

_REGISTRY_NAMES: set[str] | None = None

def _get_registry_names() -> set[str]:
    global _REGISTRY_NAMES
    if _REGISTRY_NAMES is None:
        _REGISTRY_NAMES = {p.name for p in ALL_POLYS}
    return _REGISTRY_NAMES


def _in_registry(name: str) -> bool:
    registry = _get_registry_names()
    if name in registry:
        return True
    if "(" in name:
        base = name[:name.index("(")]
        for rn in registry:
            if rn.startswith(base + "(") or rn == base:
                return True
    return False


# ═══════════════════════════════════════════════════════════════════
# ANSI colors
# ═══════════════════════════════════════════════════════════════════

_CLR = {
    "cp":       "\033[32m",  # green
    "vp":       "\033[33m",  # yellow/orange
    "verifier": "\033[34m",  # blue
}
_RST = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"


def _strip_ansi(s: str) -> str:
    return re.sub(r'\033\[[0-9;]*m', '', s)


# ═══════════════════════════════════════════════════════════════════
# Main printer
# ═══════════════════════════════════════════════════════════════════

def print_resolution() -> None:
    """Walk all stages, track opening claims, print resolution status."""
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

    stages: list[tuple[int, str, list]] = [
        (1, "SPARTAN", [stage1_spartan_outer()]),
        (2, "VIRTUALIZATION & RAM", [
            stage2_product_virtualization(),
            stage2_ram_read_write(),
            stage2_instruction_claim_reduction(),
            stage2_ram_raf_evaluation(),
            stage2_ram_output_check(),
        ]),
        (3, "SHIFT & INSTRUCTION INPUT", [
            stage3_shift(),
            stage3_instruction_input(),
            stage3_registers_claim_reduction(),
        ]),
        (4, "REGISTERS & RAM VAL", [
            stage4_registers_read_write(),
            stage4_ram_val_check(),
        ]),
        (5, "INSTRUCTION READ RAF & REDUCTIONS", [
            stage5_instruction_read_raf(),
            stage5_ram_ra_claim_reduction(),
            stage5_registers_val_evaluation(),
        ]),
        (6, "BOOLEANITY, BYTECODE & VIRTUALIZATION", [
            stage6_ram_hamming_booleanity(),
            stage6_inc_claim_reduction(),
            stage6_bytecode_read_raf(),
            stage6_instruction_ra_virtualization(),
            stage6_ram_ra_virtualization(),
            stage6_booleanity(),
        ]),
        (7, "HAMMING WEIGHT CLAIM REDUCTION", [
            stage7_hamming_weight_claim_reduction(),
        ]),
    ]

    # Outstanding claims: key → (kind, name, args, source_stage, source_name)
    outstanding: dict[str, tuple[str, str, list, int, str]] = {}
    # Resolved claims: key → (resolved_by_stage, resolved_by_name)
    resolved_log: list[tuple[str, str, str, int, str, int, str]] = []
    all_errors: list[str] = []

    for stage_num, stage_title, specs in stages:
        print()
        print(f"{'=' * 72}")
        print(f"  STAGE {stage_num} — {stage_title}")
        print(f"{'=' * 72}")

        for spec in specs:
            name = _spec_name(spec)
            rhs = _rhs_polys(spec)
            opened = _opened_claims(spec)

            print()
            print(f"  {_BOLD}{name}{_RST}")
            print(f"  {'─' * 68}")

            # ── Consumed: RHS polys that resolve outstanding claims ──
            consumed: list[str] = []
            rhs_unmatched: list[tuple[str, str, tuple]] = []

            for kind, pname, args in rhs:
                if kind == "verifier":
                    continue  # always known
                key = _claim_key(pname, args)
                if key in outstanding:
                    src = outstanding[key]
                    consumed.append(
                        f"  {_GREEN}✓{_RST} {_fmt_claim(kind, pname, args)}"
                        f" {_DIM}← S{src[3]} {src[4]}{_RST}"
                    )
                    resolved_log.append((
                        key, kind, pname,
                        src[3], src[4],
                        stage_num, name,
                    ))
                    del outstanding[key]
                else:
                    # Try parametric matching: OpFlags(cf_i) resolves all OpFlags(*)
                    base_name = pname.split(" for ")[0].strip()
                    param = _is_parametric(base_name)
                    if param:
                        base, _ = param
                        point_parts = [_fmt_arg(a) for a in args if isinstance(a, Opening)]
                        point_suffix = "@(" + ", ".join(point_parts) + ")"
                        matches = [
                            okey for okey in outstanding
                            if okey.endswith(point_suffix)
                            and okey[:-len(point_suffix)].startswith(base + "(")
                            and okey[:-len(point_suffix)].endswith(")")
                        ]
                        if matches:
                            for okey in sorted(matches):
                                src = outstanding[okey]
                                consumed.append(
                                    f"  {_GREEN}✓{_RST} {_fmt_claim(src[0], src[1], src[2])}"
                                    f" {_DIM}← S{src[3]} {src[4]}{_RST}"
                                )
                                resolved_log.append((
                                    okey, src[0], src[1],
                                    src[3], src[4],
                                    stage_num, name,
                                ))
                                del outstanding[okey]
                        else:
                            rhs_unmatched.append((kind, pname, args))
                    else:
                        # Not in outstanding — could be a public input or error
                        rhs_unmatched.append((kind, pname, args))

            if consumed:
                print(f"  {_DIM}Consumes (resolves prior claims):{_RST}")
                for line in consumed:
                    print(line)
            if rhs_unmatched:
                print(f"  {_DIM}RHS (public inputs / constants):{_RST}")
                for kind, pname, args in rhs_unmatched:
                    print(f"    {_fmt_claim(kind, pname, args)}")
            if not consumed and not rhs_unmatched:
                rhs_const = collect_polys(
                    spec.input_claim if hasattr(spec, 'input_claim') else Const(0)
                )
                if not any(k in ("vp", "cp") for k, _, _ in rhs_const):
                    print(f"  {_DIM}RHS = constant{_RST}")

            # ── Produced: new opening claims ──
            if opened:
                print(f"  {_DIM}Produces (new opening claims):{_RST}")
                for kind, oname, oargs in opened:
                    key = _claim_key(oname, oargs)
                    fmt = _fmt_claim(kind, oname, oargs)
                    if kind == "cp":
                        print(f"    {_GREEN}●{_RST} {fmt} {_DIM}→ PCS-verified{_RST}")
                    else:
                        print(f"    ○ {fmt} {_DIM}→ unresolved{_RST}")
                    outstanding[key] = (kind, oname, oargs, stage_num, name)

    # ── Summary ──
    print()
    print(f"{'=' * 72}")
    print(f"  SUMMARY")
    print(f"{'=' * 72}")
    print(f"  Claims resolved across stages: {len(resolved_log)}")

    # Check remaining outstanding
    remaining_vp = {k: v for k, v in outstanding.items() if v[0] == "vp"}
    remaining_cp = {k: v for k, v in outstanding.items() if v[0] == "cp"}

    if remaining_cp:
        print(f"  Committed claims (PCS-verified): {len(remaining_cp)}")
    if remaining_vp:
        print()
        print(f"  {_RED}UNRESOLVED virtual claims ({len(remaining_vp)}):{_RST}")
        for key, (kind, oname, oargs, src_s, src_n) in sorted(remaining_vp.items()):
            print(f"    ✗ {_fmt_claim(kind, oname, oargs)} from S{src_s} {src_n}")
        all_errors.extend(
            f"Unresolved vp: {v[1]} from S{v[3]} {v[4]}"
            for v in remaining_vp.values()
        )
    else:
        print(f"\n  {_GREEN}All virtual claims resolved ✓{_RST}")

    if all_errors:
        print(f"\n  {_RED}{len(all_errors)} issues found{_RST}")
    print()
