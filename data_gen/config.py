"""Configuration and presets for the synthetic retail data generator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date


@dataclass(frozen=True)
class GeneratorConfig:
    """All knobs that control the size and shape of the synthetic dataset.

    The same config + seed always produces byte-identical tables.
    """

    seed: int = 42
    start_date: date = date(2024, 1, 1)
    end_date: date = date(2025, 12, 31)
    n_stores: int = 8
    n_products: int = 120
    n_customers: int = 12_000
    # Average number of anonymous (non-loyalty) orders per store per day
    # for a "standard" format store on an average day.
    guest_orders_per_store_day: float = 25.0
    # Mean orders per day for a loyalty member while active (~1 every 30 days).
    member_order_rate: float = 1 / 30
    # Mean active lifetime of a loyalty member, in days.
    mean_customer_lifetime_days: float = 365.0
    # Probability that a basket line pulls in its "companion" product.
    companion_probability: float = 0.30
    # Fraction of products with thin safety stock (these stock out more).
    fragile_product_share: float = 0.15
    # Probability that a replenishment order arrives late.
    supplier_delay_probability: float = 0.05

    @property
    def n_days(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start_date"] = self.start_date.isoformat()
        d["end_date"] = self.end_date.isoformat()
        return d


PRESETS: dict[str, GeneratorConfig] = {
    # ~2 years, 8 stores, 120 products: roughly 270k orders / 750k lines.
    "default": GeneratorConfig(),
    # Tiny dataset for tests and CI: 3 stores, 30 products, 90 days.
    "small": GeneratorConfig(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
        n_stores=3,
        n_products=30,
        n_customers=400,
        guest_orders_per_store_day=6.0,
    ),
}


def get_config(preset: str = "default", **overrides) -> GeneratorConfig:
    """Return a preset config, optionally overriding individual fields."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}; choose from {sorted(PRESETS)}")
    overrides = {k: v for k, v in overrides.items() if v is not None}
    return replace(PRESETS[preset], **overrides)
