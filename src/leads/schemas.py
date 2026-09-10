# src.leads.schemas

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from src.leads.status_enum import LeadStatus
from src.shared.errors import PhoneNumberError


class LeadRowSchema(BaseModel):
    
    # Input as 'alias' the particular column header name(s) used in your very own CSV files
    # Make sure to adjust these in the registry configuration and for tests, however.
    
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="ignore")
        

    first_name: str = Field(..., alias="First_Name")
    last_name: str = Field(..., alias="Last_Name")
    email: EmailStr = Field(..., alias="Email_Address") 
    phone: str = Field(..., alias="Phone_Number")
    company: Optional[str] = Field(None, alias="Company_Name")
    sector: Optional[str] = Field(None, alias="Industry_Sector")
    position: Optional[str] = Field(None, alias="Job_Title")
    status: LeadStatus = Field(..., alias="Lead_Status") 
    score: int = Field(..., ge=0, alias="Lead_Score")

    incoming_timestamp: datetime = Field(..., alias="incoming_timestamp")
    
    @field_validator('status', mode='before')
    @classmethod
    def coerce_enum(cls, v: str) -> str: 
        """Ensures that the status is in all caps"""
        if isinstance(v, str):
            return v.strip().upper()

    @field_validator('phone')
    @classmethod
    def clean_and_validate_phone(cls, v: str) -> str:
        """Strips dashes/parentheses and ensures the number is valid length."""
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise PhoneNumberError("PHONE_ERR", "Phone number has incorrect number of digits.")
        return cleaned
    
    @field_validator('email')
    @classmethod
    def clean_and_validate_email(cls, v: str) -> str: 
        """Strips whitespace and normalizes email address to lowercase."""
        cleaned = v.strip().lower()
        return cleaned
    
@dataclass(frozen=True)
class LeadData:
    """Strictly typed Value Object for incoming ETL payload (already validated by Pydantic)."""
    first_name: str
    last_name: str
    email: str
    phone: str
    status: LeadStatus
    score: int
    incoming_timestamp: datetime
    company: str | None = None
    sector: str | None = None
    position: str | None = None

@dataclass(frozen=True)
class LeadContact:
    """A DTO formatted for contacting qualified leads"""
    first_name: str
    last_name: str
    email: str
    phone: str
    score: int
    company: str | None = None
    sector: str | None = None
    position: str | None = None
    