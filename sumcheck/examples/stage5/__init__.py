from .instruction_read_raf import stage5_instruction_read_raf
from .ram_ra_claim_reduction import stage5_ram_ra_claim_reduction
from .registers_val_evaluation import stage5_registers_val_evaluation

__all__ = [
    "stage5_instruction_read_raf",
    "stage5_ram_ra_claim_reduction",
    "stage5_registers_val_evaluation",
]
