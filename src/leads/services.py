# src.leads.services

from datetime import datetime
from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import Lead
from src.leads.schemas import LeadData


def process_lead_record(file_id: int, custos_timestamp: datetime, dto: LeadData) -> list[object]:
    
    payload = []
    normalized_email = dto.email.strip().lower()
    
    new_lead = Lead(
        source_file_id=file_id,
        first_name=dto.first_name,
        last_name=dto.last_name,
        email=normalized_email,
        email_hash=calculate_email_row_hash(normalized_email),
        phone=dto.phone,    
        status=dto.status,
        score=dto.score,
        incoming_timestamp=dto.incoming_timestamp,
        company=dto.company,
        sector=dto.sector,
        position=dto.position, 
        custos_timestamp=custos_timestamp
        )
    payload.append(new_lead)
    return payload
