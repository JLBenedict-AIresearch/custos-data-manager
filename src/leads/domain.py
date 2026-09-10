from dataclasses import dataclass, fields
from datetime import datetime
from enum import Enum
from typing import Any
from src.leads.schemas import LeadData
from src.leads.status_enum import LeadStatus
from src.infrastructure.utils import calculate_email_row_hash

@dataclass
class LeadSnapshot:
    id: int | None
    source_file_id: int
    incoming_timestamp: datetime
    custos_timestamp: datetime
    email_hash: str | None
    data: LeadData


class Lead:
    def __init__(
        self, 
        custos_timestamp: datetime, 
        source_file_id: int, 
        first_name: str, 
        last_name: str, 
        email: str, 
        phone: str, 
        status: LeadStatus,
        score: int,
        incoming_timestamp: datetime,
        company: str | None = None, 
        sector: str | None = None,
        position: str | None = None,  
        email_hash: str | None = None, 
        id: int | None = None
    ):

        self.id = id if id else None
        self.custos_timestamp = custos_timestamp
        self.source_file_id = source_file_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.email_hash = email_hash if email_hash is not None else calculate_email_row_hash(self.email)   
        self.phone = phone    
        self.status = status
        self.score = score
        self.incoming_timestamp = incoming_timestamp
        self.company = company
        self.sector = sector
        self.position = position

        self.updates: list[LeadSnapshot] = []
        
                
    def marketing_qualify(self): 
        if self.score >= 50 and self.status == LeadStatus.NEW: 
            self.status = LeadStatus.MQL


    def apply_update(
        self, 
        source_file_id: int, 
        incoming_data: "LeadData", 
        custos_timestamp: datetime
    ) -> LeadSnapshot:
                
        if incoming_data.incoming_timestamp > self.incoming_timestamp: 
            
            for field in fields(incoming_data):
                field_name = field.name
                
                if field_name == "incoming_timestamp":
                    self.incoming_timestamp = incoming_data.incoming_timestamp
                
                new_value = getattr(incoming_data, field_name)
                current_value = getattr(self, field_name)
            
                if current_value != new_value:
                    setattr(self, field_name, new_value)
                    
        self.marketing_qualify()
        update = LeadSnapshot(
            id=None,
            source_file_id=source_file_id,
            incoming_timestamp=incoming_data.incoming_timestamp,
            custos_timestamp=custos_timestamp,
            email_hash=calculate_email_row_hash(incoming_data.email),
            data=incoming_data
        )
        
        self.updates.append(update)
        
        return update

        
    def rollback(self, file_id: int) -> bool:
        """
        Reverses the effects of a specific file on this lead.
        Returns True if the lead survives, False if it should be completely deleted.
        """
        history = sorted(self.updates, key=lambda u: u.incoming_timestamp)
        new_base = next((u for u in reversed(history) if u.source_file_id != file_id), None)
        
        if not new_base: 
            return False
                   
        self.source_file_id=new_base.source_file_id
        self.incoming_timestamp=new_base.incoming_timestamp
        self.custos_timestamp=new_base.custos_timestamp
        for field in fields(new_base.data):
            field_name = field.name
            new_value = getattr(new_base.data, field_name)
            current_value = getattr(self, field_name)
                        
            if current_value != new_value:
                setattr(self, field_name, new_value)  
        self.updates = [u for u in self.updates if u.source_file_id != file_id]
        self.marketing_qualify()
            
        return True


@dataclass
class MQLAlert: 
    """Value object for an alert sent about an MQL"""
    
    id: int
    lead_id: int
    alert_timestamp: datetime


# Technically, this should have its own domain, but in this version, the team exists only for the sake
# of alerts about leads, which is why it is here in the leads domain.

class AlertTeam:
    """Entity for an SD team member responsible for contacting Leads; recipients of MQL alerts"""
    def __init__(
        self,
        first_name: str,
        last_name: str,
        email: str,
        email_hash: str,
        sectors: list | None, 
        id: int | None = None
        ):
        
        self.id = id if id else None
        self.first_name = first_name
        self.last_name = last_name
        self.email = email.strip().lower()
        self.email_hash = email_hash if email_hash else calculate_email_row_hash(self.email)
        self.sectors = sectors if sectors else []
        
    def add_sector(self, sector: str): 
        self.sectors.append(sector)