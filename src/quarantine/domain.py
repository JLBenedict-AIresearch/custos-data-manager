# src.quarantine.domain

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, unsafe_hash=False)
class QuarantinedRow:
    """Base Value Object for a row that failed structural validation."""
    file_id: int | None
    assumed_type: str 
    raw_payload: dict[str, Any]
    payload_hash: str
    error_reason: str
    line_number: int
    quarantined_at: datetime

    def __hash__(self):
        return hash(self.payload_hash)

    def __eq__(self, other):
        if not isinstance(other, QuarantinedRow):
            return False
        return self.payload_hash == other.payload_hash