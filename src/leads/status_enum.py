# src.leads.status_enum 

from enum import StrEnum


class LeadStatus(StrEnum):
    NEW = "NEW"
    MQL = "MQL"
    CONTACTED = "CONTACTED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"
