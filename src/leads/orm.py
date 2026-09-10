# src.leads.orm

from datetime import datetime
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from src.core.config import settings
from src.infrastructure.database import Base
from src.leads.status_enum import LeadStatus

# Extract the string value from SecretStr and encode it for Fernet
ENCRYPTION_KEY = settings.custos_encryption_key.get_secret_value().encode('utf-8')

class EncryptedString(TypeDecorator):
    """
    Custom SQLAlchemy type that encrypts data on the way into the DB 
    and decrypts it on the way out.
    """
    impl = String
    cache_ok = True

    def __init__(self, key: bytes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fernet = Fernet(key)

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.fernet.encrypt(value.encode('utf-8')).decode('utf-8')
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.fernet.decrypt(value.encode('utf-8')).decode('utf-8')
        return value


class LeadORM(Base):
    """ORM model representing a customer lead with encrypted PII."""
    __tablename__ = "leads"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"),  index=True)
    first_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    last_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False, unique=True)
    email_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)    
    company: Mapped[str | None] = mapped_column(String)
    sector: Mapped[str | None] = mapped_column(String)
    position: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(SQLEnum(LeadStatus), nullable=False)
    incoming_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    custos_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    update_history: Mapped[list["LeadSnapshotORM"]] = relationship(
        back_populates="lead", 
        cascade="all, delete-orphan"
    )

class LeadSnapshotORM(Base): 
    """
    ORM recording snapshots of a Lead over time.
    """

    __tablename__ = "lead_snapshots"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_file_id: Mapped[int] = mapped_column(ForeignKey("files.id"), index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"))
    incoming_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    custos_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    last_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    email_hash: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    phone: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)    
    company: Mapped[str | None] = mapped_column(String)
    sector: Mapped[str | None] = mapped_column(String)
    position: Mapped[str | None] = mapped_column(String)
    status: Mapped[str] = mapped_column(SQLEnum(LeadStatus), nullable=False)

    lead: Mapped["LeadORM"] = relationship(back_populates="update_history")


class LeadAlertORM(Base):
    """This ORM just tracks Leads about whom an MQL alert has been sent."""

    __tablename__ = "lead_alerts"
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey('leads.id'))
    alert_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    
class AlertTeamORM(Base):
    """This ORM stores the information on SD employees responsible for leads in different sectors
    for the purposes of directing MQL alerts."""
   
    __tablename__ = "lead_alerts_team"
    
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    last_name: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False)
    email: Mapped[str] = mapped_column(EncryptedString(ENCRYPTION_KEY), nullable=False, unique=True)
    email_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    sectors: Mapped[list] = mapped_column(JSON, nullable=False)