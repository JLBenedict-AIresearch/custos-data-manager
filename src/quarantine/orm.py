# src.quarantine.orm.py

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database import Base


class QuarantinedRowORM(Base):
    """Abstract base class. No table will be created for this."""
    __tablename__ = "quarantined_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey("files.id"), index=True)
    assumed_type: Mapped[str] = mapped_column(String, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False) 
    payload_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)    
    error_reason: Mapped[str] = mapped_column(Text, nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=True)
    quarantined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


    


