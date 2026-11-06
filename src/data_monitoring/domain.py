"""Provider-independent scalar measurement contract, with no IO side effects."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Measurement:
    source: str
    entity_key: str
    metric: str
    observed_at: datetime
    collected_at: datetime
    value: Decimal
    unit: str

    def __post_init__(self) -> None:
        for name in ("source", "entity_key", "metric", "unit"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("observed_at", "collected_at"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.utcoffset() is None:
                raise ValueError(f"{name} must be a timezone-aware datetime")
        if not isinstance(self.value, Decimal) or not self.value.is_finite():
            raise ValueError("value must be a finite Decimal constructed from source text")
        if self.metric == "price" and (self.value < 0 or self.unit != "EUR"):
            raise ValueError("price must be non-negative and expressed in EUR")
