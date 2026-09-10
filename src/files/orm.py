# src.files.orm

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import JSON, TypeDecorator

from src.files.domain import FileStatus
from src.infrastructure.database import Base


class JSONSet(TypeDecorator):
    """
    Translates a Python set into a JSON list for database storage, 
    and back into a Python set upon retrieval.
    """

    impl = JSON 
    cache_ok = True 

    def process_bind_param(self, value, dialect):
        """Runs when SAVING to the database (Python -> DB)"""
        if value is not None:
            return list(value)
        return []

    def process_result_value(self, value, dialect):
        """Runs when LOADING from the database (DB -> Python)"""
        if value is not None:
            return set(value)
        return set()
    
    
class FileORM(Base):
    """
    ORM model representing an ingestion file batch.
    Maps exactly to the File domain aggregate root.
    """
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String, index=True)
    hashed_file: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=True)
    assumed_type: Mapped[str] = mapped_column(String)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    potential_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=True)
    
    status: Mapped[FileStatus] = mapped_column(
        SQLEnum(FileStatus), 
        default=FileStatus.PROCESSING, 
        index=True
    )
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    total_processed_rows: Mapped[int] = mapped_column(Integer, default=0)
    quarantined_rows: Mapped[int] = mapped_column(Integer, default=0)
    expected_batches: Mapped[set[int]] = mapped_column(JSONSet, default=set)
    validated_batches: Mapped[set[int]] = mapped_column(JSONSet, default=set)
    completed_batches: Mapped[set[int]] = mapped_column(JSONSet, default=set)
    
    processing_begun: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_finished:Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempted_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())