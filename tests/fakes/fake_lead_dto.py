from dataclasses import dataclass
from datetime import datetime
from src.leads.status_enum import LeadStatus

@dataclass(frozen=True)
class FakeLeadData:
    """Strictly typed Value Object for incoming ETL payload (already validated by Pydantic)."""
    first_name: str
    last_name: str
    phone: str
    status: LeadStatus
    score: int
    incoming_timestamp: datetime
    company: str | None = None
    sector: str | None = None
    position: str | None = None
