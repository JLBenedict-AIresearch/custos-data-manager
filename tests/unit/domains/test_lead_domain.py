# tests.unit.test_lead_domain

# run command: poetry run python -m pytest tests/unit/domains/test_lead_domain.py

import datetime
from datetime import timezone
from src.infrastructure.utils import calculate_email_row_hash
from src.leads.domain import Lead
from src.leads.status_enum import LeadStatus
from src.leads.schemas import LeadData
from tests.fakes import dummies



def test_lead_apply_update_modifies_fields_and_adds_update_record():
    
    base_lead = Lead(
    source_file_id=1,
    first_name="Hannibal",
    last_name="Lecter",
    email="hannibalcannibal@chomp.com",
    email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
    phone="800-555-4039",
    status=LeadStatus.NEW,
    score=26,
    incoming_timestamp=datetime.datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
    company="Lector Therapy",
    sector="Psychology/Fine Dining",
    position="Therapist", 
    custos_timestamp=datetime.datetime(2026, 9, 2, 3, 3, tzinfo=timezone.utc)            
    )

    incoming = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.REJECTED,
        score=7,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist" 
        )
        
    
    update_timestamp = datetime.datetime.now(timezone.utc)
    
    base_update = base_lead.apply_update(
        source_file_id=1, 
        incoming_data=dummies.lead_to_dto(base_lead),
        custos_timestamp=datetime.datetime(2026, 9, 6, 5, 4, tzinfo=timezone.utc)
    )

    was_updated = base_lead.apply_update(
        source_file_id=2,
        incoming_data=incoming,
        custos_timestamp=update_timestamp
    )
    
    assert was_updated is not None
    assert base_lead.score == 7
    assert base_lead.status == "REJECTED"
    
    assert len(base_lead.updates) == 2


def test_lead_deletes_updates():
    
    base_lead = Lead(
    source_file_id=1,
    first_name="Hannibal",
    last_name="Lecter",
    email="hannibalcannibal@chomp.com",
    email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
    phone="800-555-4039",
    status=LeadStatus.NEW,
    score=26,
    incoming_timestamp=datetime.datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
    company="Lector Therapy",
    sector="Psychology/Fine Dining",
    position="Therapist",
    custos_timestamp=datetime.datetime(2026, 9, 2, 3, 4, tzinfo=timezone.utc)                
    )

    incoming1 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.CONTACTED,
        score=67,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist"
        )
    
    incoming2 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.REJECTED,
        score=2,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 21, 45, tzinfo=timezone.utc),
        company="Federal Prison",
        sector="Solitary",
        position="High-Risk Prisoner"
        )
        
    
    update1_timestamp = datetime.datetime(2025, 11, 18, 19, 16, tzinfo=timezone.utc)
    update2_timestamp = datetime.datetime.now(timezone.utc)
    base_update = base_lead.apply_update(
        source_file_id=1, 
        incoming_data=dummies.lead_to_dto(base_lead),
        custos_timestamp=base_lead.custos_timestamp
        
    )
    update_1 = base_lead.apply_update(
        source_file_id=2,
        incoming_data=incoming1,
        custos_timestamp=update1_timestamp
    )
    update_2 = base_lead.apply_update(
        source_file_id=3,
        incoming_data=incoming2,
        custos_timestamp=update2_timestamp
    )
    
    if base_update and (update_1 and update_2):
        base_lead.rollback(2)
    
    assert update_1
    assert update_2
    assert base_lead.company == "Federal Prison"
    assert len(base_lead.updates) == 2  
    update = base_lead.updates[1]   # There should be the original base_update and one other (update2 from file 3)
    assert update.source_file_id == 3
    rolled_back_update = next((u for u in base_lead.updates if u.source_file_id == 2), None)
    assert not rolled_back_update
    assert update.data.score == 2
    assert update.data.sector == "Solitary"
    
    
def test_lead_deletes_original_update_for_file():
    
    base_lead = Lead(
    source_file_id=1,
    first_name="Hannibal",
    last_name="Lecter",
    email="hannibalcannibal@chomp.com",
    email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
    phone="800-555-4039",
    status=LeadStatus.NEW,
    score=26,
    incoming_timestamp=datetime.datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
    company="Lector Therapy",
    sector="Psychology/Fine Dining",
    position="Therapist",
    custos_timestamp=datetime.datetime(2026, 9, 2, 3, 4, tzinfo=timezone.utc)                
    )

    incoming1 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.CONTACTED,
        score=67,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist"
        )
    
    update1_timestamp = datetime.datetime(2025, 11, 18, 19, 16, tzinfo=timezone.utc)
    base_update = base_lead.apply_update(
        source_file_id=1, 
        incoming_data=dummies.lead_to_dto(base_lead),       # The pipeline consumes a DTO and transforms it to a Lead/LeadSnapshot
        custos_timestamp=datetime.datetime(2026, 9, 2, 1, 8, tzinfo=timezone.utc)
    )
    update_1 = base_lead.apply_update(
        source_file_id=2,
        incoming_data=incoming1,
        custos_timestamp=update1_timestamp
    )
    
    if update_1 and base_update:
        base_lead.rollback(1)
    
    assert len(base_lead.updates) == 1
    assert base_lead.score == 67
    assert base_lead.updates[0].data.score == 67
    
    
    
def test_lead_rolls_back_last_update():
    base_lead = Lead(
        source_file_id=1,
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
        phone="800-555-4039",
        status=LeadStatus.NEW,
        score=26,
        incoming_timestamp=datetime.datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
        company="Lector Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist",
        custos_timestamp=datetime.datetime(2026, 9, 2, 3, 4, tzinfo=timezone.utc)                
        )
    
    incoming1 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.CONTACTED,
        score=67,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist"
        )
    
    incoming2 = LeadData(
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        phone="800-555-4039",
        status=LeadStatus.REJECTED,
        score=2,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 21, 45, tzinfo=timezone.utc),
        company="Federal Prison",
        sector="Solitary",
        position="High-Risk Prisoner"
        )
        
    
    update1_timestamp = datetime.datetime(2025, 11, 18, 19, 16, tzinfo=timezone.utc)
    update2_timestamp = datetime.datetime.now(timezone.utc)
    base_update = base_lead.apply_update(
        source_file_id=1, 
        incoming_data=dummies.lead_to_dto(base_lead),
        custos_timestamp=base_lead.custos_timestamp
        
    )
    update_1 = base_lead.apply_update(
        source_file_id=2,
        incoming_data=incoming1,
        custos_timestamp=update1_timestamp
    )
    update_2 = base_lead.apply_update(
        source_file_id=3,
        incoming_data=incoming2,
        custos_timestamp=update2_timestamp
    )    
    
    if base_update and (update_1 and update_2):
        base_lead.rollback(3)
        
    assert len(base_lead.updates) == 2
    assert base_lead.score == 67
    assert base_lead.updates[0].data.score == 26

    
def test_mql_qualifies_leads():
    
    
    update = Lead(
        source_file_id=1,
        first_name="Hannibal",
        last_name="Lecter",
        email="hannibalcannibal@chomp.com",
        email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
        phone="800-555-4039",
        status=LeadStatus.NEW,
        score=53,
        incoming_timestamp=datetime.datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
        company="Carthage Therapy",
        sector="Psychology/Fine Dining",
        position="Therapist",
        custos_timestamp=datetime.datetime(2026, 9, 2, 3, 5, tzinfo=timezone.utc)    
    )

    lead_entity = update
    
    lead_entity.marketing_qualify()
    
    assert lead_entity.status == LeadStatus.MQL
    
    


    
