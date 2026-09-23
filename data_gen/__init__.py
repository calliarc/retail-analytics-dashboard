"""Deterministic synthetic retail data generator (all output is synthetic)."""

from .config import PRESETS, GeneratorConfig, get_config
from .generator import TABLES, RetailDataset, generate
from .writer import SYNTHETIC_NOTICE, write_dataset

__all__ = [
    "PRESETS",
    "SYNTHETIC_NOTICE",
    "TABLES",
    "GeneratorConfig",
    "RetailDataset",
    "generate",
    "get_config",
    "write_dataset",
]
__version__ = "0.1.0"
