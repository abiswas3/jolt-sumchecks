"""
Entry point for:  python3 -m sumcheck

Usage:
    python3 -m sumcheck                 # all stages (terminal)
    python3 -m sumcheck --stage 5       # just stage 5
    python3 -m sumcheck registry        # polynomial registry
    python3 -m sumcheck registry --vp   # just virtual polys
    python3 -m sumcheck resolve         # polynomial resolution tracker
    python3 -m sumcheck html            # generate HTML site → docs/
    python3 -m sumcheck html --stage 5  # just stage 5
    python3 -m sumcheck latex           # generate LaTeX → sumcheck_specs.tex
    python3 -m sumcheck latex --stage 3 # just stage 3
"""

import sys

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
from .printer import print_sumcheck, print_spartan, print_product_virt
from .registry import print_registry


def _box(title: str) -> None:
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print(f"║  {title:<58} ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


STAGES = {
    1: ("STAGE 1 — SPARTAN", lambda: [
        print_spartan(stage1_spartan_outer()),
    ]),
    2: ("STAGE 2 — VIRTUALIZATION & RAM", lambda: [
        print_product_virt(stage2_product_virtualization()),
        print_sumcheck(stage2_ram_read_write()),
        print_sumcheck(stage2_instruction_claim_reduction()),
        print_sumcheck(stage2_ram_raf_evaluation()),
        print_sumcheck(stage2_ram_output_check()),
    ]),
    3: ("STAGE 3 — SHIFT & INSTRUCTION INPUT", lambda: [
        print_sumcheck(stage3_shift()),
        print_sumcheck(stage3_instruction_input()),
        print_sumcheck(stage3_registers_claim_reduction()),
    ]),
    4: ("STAGE 4 — REGISTERS & RAM VAL", lambda: [
        print_sumcheck(stage4_registers_read_write()),
        print_sumcheck(stage4_ram_val_check()),
    ]),
    5: ("STAGE 5 — INSTRUCTION READ RAF & REDUCTIONS", lambda: [
        print_sumcheck(stage5_instruction_read_raf()),
        print_sumcheck(stage5_ram_ra_claim_reduction()),
        print_sumcheck(stage5_registers_val_evaluation()),
    ]),
    6: ("STAGE 6 — BOOLEANITY, BYTECODE & VIRTUALIZATION", lambda: [
        print_sumcheck(stage6_ram_hamming_booleanity()),
        print_sumcheck(stage6_inc_claim_reduction()),
        print_sumcheck(stage6_bytecode_read_raf()),
        print_sumcheck(stage6_instruction_ra_virtualization()),
        print_sumcheck(stage6_ram_ra_virtualization()),
        print_sumcheck(stage6_booleanity()),
    ]),
    7: ("STAGE 7 — HAMMING WEIGHT CLAIM REDUCTION", lambda: [
        print_sumcheck(stage7_hamming_weight_claim_reduction()),
    ]),
}


def _parse_args(argv: list[str]) -> tuple[set[int], dict[str, str]]:
    """Parse --stage N and --out PATH from argv. Returns (stages, opts)."""
    selected = set()
    opts = {}
    i = 0
    while i < len(argv):
        if argv[i] in ("--stage", "-s") and i + 1 < len(argv):
            selected.add(int(argv[i + 1]))
            i += 2
        elif argv[i] in ("--out", "-o") and i + 1 < len(argv):
            opts["out"] = argv[i + 1]
            i += 2
        else:
            i += 1
    return selected, opts


# ── Dispatch ──

cmd = sys.argv[1] if len(sys.argv) > 1 else None

if cmd == "registry":
    kinds = set()
    for a in sys.argv[2:]:
        flag = a.lstrip("-").lower()
        if flag in ("committed", "cp"):
            kinds.add("committed")
        elif flag in ("virtual", "vp"):
            kinds.add("virtual")
        elif flag in ("verifier", "vr"):
            kinds.add("verifier")
    print_registry(kinds or None)

elif cmd == "resolve":
    from .resolve import print_resolution
    print_resolution()

elif cmd == "html":
    from .html import generate_html, _default_stages
    selected, opts = _parse_args(sys.argv[2:])
    all_stages = _default_stages()
    if selected:
        all_stages = {s: all_stages[s] for s in selected if s in all_stages}
    out_dir = opts.get("out", "docs")
    generate_html(out_dir=out_dir, stages=all_stages)

elif cmd == "latex":
    from .latex import generate_latex, _default_stages
    selected, opts = _parse_args(sys.argv[2:])
    all_stages = _default_stages()
    if selected:
        all_stages = {s: all_stages[s] for s in selected if s in all_stages}
    out_file = opts.get("out", "sumcheck_specs.tex")
    generate_latex(out_file=out_file, stages=all_stages)

else:
    # Default: terminal text output
    selected, _ = _parse_args(sys.argv[1:])
    stages_to_print = sorted(selected) if selected else sorted(STAGES.keys())

    for s in stages_to_print:
        if s in STAGES:
            title, fn = STAGES[s]
            _box(title)
            fn()
