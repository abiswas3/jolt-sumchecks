"""
Polynomial and parameter registry for Jolt.

Every polynomial in Jolt is an MLE (multilinear extension) of a
function  {0,1}^n → F.  This module provides a structured catalog
of all polynomials and system parameters, intended as the single
source of truth for the web interface, the AST, and the spec docs.

Source: jolt-docs/content/references/polynomials.md
        jolt-docs/content/references/parameters.md
"""

from __future__ import annotations

from .defs import (
    DimDef, PolyKind, PolyDef, ParamDef,
    DIM_CYCLE, DIM_K_RAM, DIM_K_REG, DIM_ADDR,
    DIM_K_INSTR, DIM_K_BC, DIM_N_V,
)


# ═══════════════════════════════════════════════════════════════════
# Parameters
# ═══════════════════════════════════════════════════════════════════

PARAMS: list[ParamDef] = [
    ParamDef(
        "T",
        "trace_length",
        "Number of execution cycles (padded to power of 2)",
    ),
    ParamDef(
        "log_2 N_chunk",
        "log_k_chunk",
        "Committed one-hot chunk bit-size (4 or 8)",
    ),
    ParamDef(
        "N_chunk",
        "k_chunk",
        "Committed one-hot chunk size",
        formula="2^log_k_chunk",
    ),
    ParamDef(
        "log_2 N_virtual",
        "lookups_ra_virtual_log_k_chunk",
        "Virtual RA chunk bit-size",
        formula="LOG_K/8 if log_T < 25 else LOG_K/4",
    ),
    ParamDef(
        "d_instr",
        "instruction_d",
        "Number of committed RA chunks (instruction)",
        formula="ceil(128 / log_2 N_instr)",
    ),
    ParamDef(
        "d_virutal_instr",
        "n_virtual_ra_polys",
        "Number of virtual RA chunks (instruction)",
        formula="128 / log_2 N_v",
    ),
    ParamDef(
        "M",
        "n_committed_per_virtual",
        "Fan-in: committed chunks per virtual chunk",
        formula="d_instr / d_v",
    ),
    ParamDef(
        "K_bc",
        "bytecode_k",
        "Bytecode table size (program-dependent, padded to power of 2)",
    ),
    ParamDef(
        "d_bc",
        "bytecode_d",
        "Number of committed RA chunks (bytecode)",
        formula="ceil(log_2 K_bc / log_2 N_instr)",
    ),
    ParamDef(
        "K_ram",
        "ram_k",
        "RAM address-space size",
    ),
    ParamDef(
        "d_ram",
        "ram_d",
        "Number of committed RA chunks (RAM)",
        formula="ceil(log_2 K_ram / log_2 N_instr)",
    ),
    ParamDef(
        "K_reg",
        "",
        "Register file size (32 for RV32, 64 for RV64)",
    ),
    ParamDef(
        "N_tables",
        "",
        "Number of lookup tables (42)",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# Committed polynomials
# ═══════════════════════════════════════════════════════════════════

_C = PolyKind.COMMITTED
_V = PolyKind.VIRTUAL
_R = PolyKind.VERIFIER

COMMITTED_POLYS: list[PolyDef] = [
    PolyDef(
        "RdInc",
        _C,
        [DIM_CYCLE],
        "rd_write_timestamp[t] - rd_write_timestamp[t-1]",
        "Registers",
    ),
    PolyDef(
        "RamInc", _C, [DIM_CYCLE], "ram_write_timestamp[t] - ram_write_timestamp[t-1]", "RAM"
    ),
    PolyDef(
        "InstructionRa(i)",
        _C,
        [DIM_ADDR, DIM_CYCLE],
        "one-hot over N_instr values; 1 iff chunk i of instruction address = k at cycle t. i in 0..d_instr-1",
        "Instruction lookup",
    ),
    PolyDef(
        "BytecodeRa(i)",
        _C,
        [DIM_ADDR, DIM_CYCLE],
        "one-hot over N_instr values; 1 iff chunk i of bytecode row index = k at cycle t. i in 0..d_bc-1",
        "Bytecode",
    ),
    PolyDef(
        "RamRa(i)",
        _C,
        [DIM_ADDR, DIM_CYCLE],
        "one-hot over N_instr values; 1 iff chunk i of RAM address = k at cycle t. i in 0..d_ram-1",
        "RAM",
    ),
    PolyDef(
        "TrustedAdvice",
        _C,
        [],
        "committed before proving; verifier has the commitment",
        "Advice",
    ),
    PolyDef(
        "UntrustedAdvice",
        _C,
        [],
        "committed during proving; commitment included in proof",
        "Advice",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# Virtual polynomials
# ═══════════════════════════════════════════════════════════════════

VIRTUAL_POLYS: list[PolyDef] = [
    # Program counter
    PolyDef("PC", _V, [DIM_CYCLE], "trace[t].pc (expanded ELF address)", "Program counter"),
    PolyDef(
        "UnexpandedPC",
        _V,
        [DIM_CYCLE],
        "trace[t].unexpanded_pc (raw ELF address)",
        "Program counter",
    ),
    PolyDef(
        "NextPC",
        _V,
        [DIM_CYCLE],
        "PC(t+1); left-shift of PC by one cycle",
        "Program counter",
    ),
    PolyDef(
        "NextUnexpandedPC",
        _V,
        [DIM_CYCLE],
        "UnexpandedPC(t+1); left-shift of UnexpandedPC by one cycle",
        "Program counter",
    ),
    # Instruction lookup
    PolyDef(
        "LookupOutput",
        _V,
        [DIM_CYCLE],
        "T_{table(t)}(address(t)); the lookup table output at cycle t",
        "Instruction lookup",
    ),
    PolyDef(
        "LeftLookupOperand",
        _V,
        [DIM_CYCLE],
        "LeftOp(address(t)) if interleaved, else 0",
        "Instruction lookup",
    ),
    PolyDef(
        "RightLookupOperand",
        _V,
        [DIM_CYCLE],
        "RightOp(address(t)) if interleaved, else unmap(address(t))",
        "Instruction lookup",
    ),
    PolyDef(
        "LeftInstructionInput",
        _V,
        [DIM_CYCLE],
        "left operand to the ALU: rs1_val, pc, or imm depending on flags",
        "Instruction lookup",
    ),
    PolyDef(
        "RightInstructionInput",
        _V,
        [DIM_CYCLE],
        "right operand to the ALU: rs2_val or imm depending on flags",
        "Instruction lookup",
    ),
    PolyDef(
        "InstructionRa(i)",
        _V,
        [DIM_N_V, DIM_CYCLE],
        "prod_{j=0}^{M-1} cp:InstructionRa(i*M+j)(k_j, t); product of M committed chunks",
        "Instruction lookup",
    ),
    PolyDef(
        "InstructionRafFlag",
        _V,
        [DIM_CYCLE],
        "OpFlags(Add) + OpFlags(Sub) + OpFlags(Mul); 1 iff single-value range check",
        "Instruction lookup",
    ),
    PolyDef(
        "LookupTableFlag_i",
        _V,
        [DIM_CYCLE],
        "1 iff lookup table i is active at cycle t; at most one flag is 1 per cycle",
        "Instruction lookup",
    ),
    # Product constraints — each is a product of two witness polynomials
    PolyDef(
        "Product",
        _V,
        [DIM_CYCLE],
        "LeftInstructionInput(t) * RightInstructionInput(t)",
        "Product constraints",
    ),
    PolyDef(
        "ShouldJump",
        _V,
        [DIM_CYCLE],
        "OpFlags(Jump)(t) * (1 - NextIsNoop(t))",
        "Product constraints",
    ),
    PolyDef(
        "ShouldBranch",
        _V,
        [DIM_CYCLE],
        "LookupOutput(t) * InstructionFlags(Branch)(t)",
        "Product constraints",
    ),
    PolyDef(
        "WritePCtoRD",
        _V,
        [DIM_CYCLE],
        "InstructionFlags(IsRdNotZero)(t) * OpFlags(Jump)(t)",
        "Product constraints",
    ),
    PolyDef(
        "WriteLookupOutputToRD",
        _V,
        [DIM_CYCLE],
        "InstructionFlags(IsRdNotZero)(t) * OpFlags(WriteLookupOutputToRD)(t)",
        "Product constraints",
    ),
    # Registers — directly from execution trace
    PolyDef("Rd", _V, [DIM_CYCLE], "trace[t].rd; destination register index", "Registers"),
    PolyDef("Imm", _V, [DIM_CYCLE], "trace[t].imm; immediate value", "Registers"),
    PolyDef(
        "Rs1Value", _V, [DIM_CYCLE], "registers[trace[t].rs1] before cycle t", "Registers"
    ),
    PolyDef(
        "Rs2Value", _V, [DIM_CYCLE], "registers[trace[t].rs2] before cycle t", "Registers"
    ),
    PolyDef(
        "RdWriteValue",
        _V,
        [DIM_CYCLE],
        "value written to registers[rd] at cycle t",
        "Registers",
    ),
    PolyDef(
        "Rs1Ra", _V, [DIM_K_REG, DIM_CYCLE], "one-hot: 1 iff k = trace[t].rs1", "Registers"
    ),
    PolyDef(
        "Rs2Ra", _V, [DIM_K_REG, DIM_CYCLE], "one-hot: 1 iff k = trace[t].rs2", "Registers"
    ),
    PolyDef(
        "RdWa", _V, [DIM_K_REG, DIM_CYCLE], "one-hot: 1 iff k = trace[t].rd", "Registers"
    ),
    PolyDef(
        "RegistersVal",
        _V,
        [DIM_K_REG, DIM_CYCLE],
        "registers[k] right before cycle t",
        "Registers",
    ),
    # RAM — directly from execution trace
    PolyDef(
        "RamAddress",
        _V,
        [DIM_CYCLE],
        "trace[t].ram_address (rs1 + imm if load/store, else 0)",
        "RAM",
    ),
    PolyDef(
        "RamRa",
        _V,
        [DIM_K_RAM, DIM_CYCLE],
        "prod_{i=0}^{d_ram-1} cp:RamRa(i)(k_i, t); product of committed chunks",
        "RAM",
    ),
    PolyDef("RamReadValue", _V, [DIM_CYCLE], "memory[ram_address] before cycle t", "RAM"),
    PolyDef("RamWriteValue", _V, [DIM_CYCLE], "memory[ram_address] after cycle t", "RAM"),
    PolyDef("RamVal", _V, [DIM_K_RAM, DIM_CYCLE], "memory[k] right before cycle t", "RAM"),
    PolyDef(
        "RamValInit", _V, [DIM_K_RAM], "memory[k] at t=0 (initial memory image)", "RAM"
    ),
    PolyDef(
        "RamValFinal", _V, [DIM_K_RAM], "memory[k] at t=T (final memory image)", "RAM"
    ),
    PolyDef(
        "RamHammingWeight",
        _V,
        [DIM_CYCLE],
        "sum_k RamRa(k, t); number of active RAM chunks at cycle t (0 or 1)",
        "RAM",
    ),
    # Circuit flags — decoded from instruction opcode
    PolyDef(
        "OpFlags(AddOperands)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) computes x+y (ADD, ADDI, AUIPC, ...)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(SubtractOperands)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) computes x-y (SUB)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(MultiplyOperands)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) computes x*y (MUL, MULH, ...)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(Load)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is LB/LH/LW/LBU/LHU/LD/LWU",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(Store)", _V, [DIM_CYCLE], "1 iff instr(t) is SB/SH/SW/SD", "Circuit flags"
    ),
    PolyDef("OpFlags(Jump)", _V, [DIM_CYCLE], "1 iff instr(t) is JAL/JALR", "Circuit flags"),
    PolyDef(
        "OpFlags(WriteLookupOutputToRD)",
        _V,
        [DIM_CYCLE],
        "1 iff lookup output is written to rd",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(VirtualInstruction)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is a Jolt virtual instruction",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(Assert)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is an assert (lookup output must be 1)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(DoNotUpdateUnexpandedPC)",
        _V,
        [DIM_CYCLE],
        "1 iff unexpanded PC should not advance (mid-virtual-sequence)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(Advice)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is a virtual advice instruction",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(IsCompressed)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is a 16-bit compressed instruction (PC += 2)",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(IsFirstInSequence)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is the first in a virtual instruction sequence",
        "Circuit flags",
    ),
    PolyDef(
        "OpFlags(IsLastInSequence)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is the last in a virtual instruction sequence",
        "Circuit flags",
    ),
    # Instruction flags — decoded from instruction encoding
    PolyDef(
        "InstructionFlags(LeftOperandIsPC)",
        _V,
        [DIM_CYCLE],
        "1 iff left ALU operand = PC (e.g. AUIPC, JAL)",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(RightOperandIsImm)",
        _V,
        [DIM_CYCLE],
        "1 iff right ALU operand = imm (I-type instructions)",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(LeftOperandIsRs1Value)",
        _V,
        [DIM_CYCLE],
        "1 iff left ALU operand = rs1_val",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(RightOperandIsRs2Value)",
        _V,
        [DIM_CYCLE],
        "1 iff right ALU operand = rs2_val",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(Branch)",
        _V,
        [DIM_CYCLE],
        "1 iff instr(t) is BEQ/BNE/BLT/BGE/BLTU/BGEU",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(IsNoop)",
        _V,
        [DIM_CYCLE],
        "1 iff cycle t is a padding no-op",
        "Instruction flags",
    ),
    PolyDef(
        "InstructionFlags(IsRdNotZero)",
        _V,
        [DIM_CYCLE],
        "1 iff trace[t].rd != x0",
        "Instruction flags",
    ),
    # Shift-derived — left-shift of another polynomial by one cycle
    PolyDef(
        "NextIsNoop",
        _V,
        [DIM_CYCLE],
        "InstructionFlags(IsNoop)(t+1); left-shift by one cycle",
        "Shift-derived",
    ),
    PolyDef(
        "NextIsVirtual",
        _V,
        [DIM_CYCLE],
        "OpFlags(VirtualInstruction)(t+1); left-shift by one cycle",
        "Shift-derived",
    ),
    PolyDef(
        "NextIsFirstInSequence",
        _V,
        [DIM_CYCLE],
        "OpFlags(IsFirstInSequence)(t+1); left-shift by one cycle",
        "Shift-derived",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# Verifier-computable polynomials
# ═══════════════════════════════════════════════════════════════════

VERIFIER_POLYS: list[PolyDef] = [
    PolyDef(
        "T_i",
        _R,
        [DIM_K_INSTR],
        "MLE of lookup table i",
        "Lookup tables",
    ),
    PolyDef(
        "LeftOp",
        _R,
        [DIM_K_INSTR],
        "MLE of left operand extraction from interleaved address bits",
        "Operand extraction",
    ),
    PolyDef(
        "RightOp",
        _R,
        [DIM_K_INSTR],
        "MLE of right operand extraction from interleaved address bits",
        "Operand extraction",
    ),
    PolyDef(
        "unmap",
        _R,
        [DimDef("K", "K", "address")],
        "MLE of identity function: {0,1}^n -> {0, ..., 2^n - 1}",
        "Operand extraction",
    ),
    PolyDef(
        "LT",
        _R,
        [DimDef("T", "a", "point a"), DimDef("T", "b", "point b")],
        "MLE of less-than: 1 iff a < b",
        "Comparison",
    ),
    PolyDef(
        "EqPlusOne",
        _R,
        [DimDef("T", "a", "point a"), DimDef("T", "b", "point b")],
        "MLE of successor: 1 iff b = a + 1",
        "Comparison",
    ),
    PolyDef(
        "eq",
        _R,
        [DimDef("n", "r", "point r"), DimDef("n", "x", "hypercube x")],
        "Multilinear Lagrange basis: eq(r,x) = prod_i (r_i*x_i + (1-r_i)(1-x_i))",
        "Lagrange basis",
    ),
    PolyDef(
        "L",
        _R,
        [DimDef("|S|", "τ", "challenge point"), DimDef("|S|", "x", "constraint index")],
        "Univariate Lagrange selector over domain S ⊂ F: L(τ,x) = Σ_{s∈S} ℓ_s(τ)·ℓ_s(x). "
        "Used in Stage 1 (S={-5,...,4}) and Stage 2 (S={-2,...,2}) for the 'univariate skip'",
        "Lagrange basis",
    ),
]


# ═══════════════════════════════════════════════════════════════════
# Convenience: all polynomials in one list
# ═══════════════════════════════════════════════════════════════════

ALL_POLYS: list[PolyDef] = COMMITTED_POLYS + VIRTUAL_POLYS + VERIFIER_POLYS


# ═══════════════════════════════════════════════════════════════════
# Callable PolyDef lookup
# ═══════════════════════════════════════════════════════════════════

class _PolyNamespace:
    """Attribute access to PolyDefs by name.

    Names with parentheses are accessible with underscores:
        OpFlags(Load)     → ns.OpFlags_Load
        InstructionRa(i)  → ns.InstructionRa_i
    """
    def __init__(self, polys: list[PolyDef]):
        self._by_name: dict[str, PolyDef] = {}
        for p in polys:
            safe = p.name.replace("(", "_").replace(")", "")
            self._by_name[safe] = p

    def __getattr__(self, name: str) -> PolyDef:
        try:
            return self._by_name[name]
        except KeyError:
            raise AttributeError(f"No polynomial named {name!r}")

    def __dir__(self):
        return list(self._by_name.keys())


committed = _PolyNamespace(COMMITTED_POLYS)
virtual   = _PolyNamespace(VIRTUAL_POLYS)
verifier  = _PolyNamespace(VERIFIER_POLYS)


def poly(name: str) -> PolyDef:
    """Look up a PolyDef by exact name.

    Searches all polynomials (committed, virtual, verifier).
    Raises KeyError if not found.

        from sumcheck.registry import poly

        Rs1Ra = poly("Rs1Ra")
        Rs1Ra(X_k, X_t)   # → VirtualPoly("Rs1Ra", [X_k, X_t])
    """
    for p in ALL_POLYS:
        if p.name == name:
            return p
    raise KeyError(f"No polynomial named {name!r}")


def print_registry(kinds: set[str] | None = None) -> None:
    """Pretty-print the polynomial registry."""
    _KIND_MAP = {
        "committed": PolyKind.COMMITTED,
        "virtual": PolyKind.VIRTUAL,
        "verifier": PolyKind.VERIFIER,
    }
    allowed = {_KIND_MAP[k] for k in kinds} if kinds else None

    _CLR = {
        PolyKind.COMMITTED: "\033[32m",  # green
        PolyKind.VIRTUAL: "\033[33m",  # yellow/orange
        PolyKind.VERIFIER: "\033[34m",  # blue
    }
    _RST = "\033[0m"
    _DIM = "\033[2m"

    current_kind = None
    current_cat = None

    for p in ALL_POLYS:
        if allowed and p.kind not in allowed:
            continue
        if p.kind != current_kind:
            current_kind = p.kind
            label = {
                PolyKind.COMMITTED: "COMMITTED (green, cp:)",
                PolyKind.VIRTUAL: "VIRTUAL (orange, vp:)",
                PolyKind.VERIFIER: "VERIFIER-COMPUTABLE",
            }[p.kind]
            print()
            print(f"{'=' * 60}")
            print(f"  {label}")
            print(f"{'=' * 60}")

        if p.category != current_cat:
            current_cat = p.category
            if current_cat:
                print(f"\n  -- {current_cat} --")

        clr = _CLR[p.kind]
        if p.domain:
            dims = " × ".join(f"{{0,1}}^log₂({d.size})" for d in p.domain)
            labels = " × ".join(d.description or d.label for d in p.domain)
            domain = f" : {_DIM}{dims} → F   [{labels}]{_RST}"
        else:
            domain = ""
        print(f"    {clr}{p.name}{_RST}{domain}")
        print(f"      {_DIM}{p.description}{_RST}")

    print()
    print(f"{'=' * 60}")
    print(f"  PARAMETERS")
    print(f"{'=' * 60}")
    for p in PARAMS:
        formula = f" = {p.formula}" if p.formula else ""
        code = f" ({p.name})" if p.name else ""
        print(f"    {p.symbol}{code}{formula}")
        print(f"      {p.description}")
