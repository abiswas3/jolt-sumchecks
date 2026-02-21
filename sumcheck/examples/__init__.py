"""
Per-stage sumcheck encodings from the Jolt specification.

Each stage sub-package contains one file per sumcheck, named after
the sumcheck it encodes.  All functions are re-exported here.

Usage:
    from sumcheck.examples import stage6_ram_hamming_booleanity
    from sumcheck.examples.stage7.hamming_weight_claim_reduction import (
        stage7_hamming_weight_claim_reduction,
    )
"""

from .stage1.spartan_outer import stage1_spartan_outer
from .stage2.product_virtualization import stage2_product_virtualization
from .stage2.ram_read_write import stage2_ram_read_write
from .stage2.instruction_claim_reduction import stage2_instruction_claim_reduction
from .stage2.ram_raf_evaluation import stage2_ram_raf_evaluation
from .stage2.ram_output_check import stage2_ram_output_check
from .stage3.shift import stage3_shift
from .stage3.instruction_input import stage3_instruction_input
from .stage3.registers_claim_reduction import stage3_registers_claim_reduction
from .stage4.registers_read_write import stage4_registers_read_write
from .stage4.ram_val_check import stage4_ram_val_check
from .stage5.instruction_read_raf import stage5_instruction_read_raf
from .stage5.ram_ra_claim_reduction import stage5_ram_ra_claim_reduction
from .stage5.registers_val_evaluation import stage5_registers_val_evaluation
from .stage6.ram_hamming_booleanity import stage6_ram_hamming_booleanity
from .stage6.inc_claim_reduction import stage6_inc_claim_reduction
from .stage6.bytecode_read_raf import stage6_bytecode_read_raf
from .stage6.instruction_ra_virtualization import stage6_instruction_ra_virtualization
from .stage6.ram_ra_virtualization import stage6_ram_ra_virtualization
from .stage6.booleanity import stage6_booleanity
from .stage7.hamming_weight_claim_reduction import stage7_hamming_weight_claim_reduction

__all__ = [
    "stage1_spartan_outer",
    "stage2_product_virtualization",
    "stage2_ram_read_write",
    "stage2_instruction_claim_reduction",
    "stage2_ram_raf_evaluation",
    "stage2_ram_output_check",
    "stage3_shift",
    "stage3_instruction_input",
    "stage3_registers_claim_reduction",
    "stage4_registers_read_write",
    "stage4_ram_val_check",
    "stage5_instruction_read_raf",
    "stage5_ram_ra_claim_reduction",
    "stage5_registers_val_evaluation",
    "stage6_ram_hamming_booleanity",
    "stage6_inc_claim_reduction",
    "stage6_bytecode_read_raf",
    "stage6_instruction_ra_virtualization",
    "stage6_ram_ra_virtualization",
    "stage6_booleanity",
    "stage7_hamming_weight_claim_reduction",
]
