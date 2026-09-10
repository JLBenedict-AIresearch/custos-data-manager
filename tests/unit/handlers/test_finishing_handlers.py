# tests.unit.handlers.test_finishing_handlers

# run command: poetry run python -m pytest tests/unit/handlers/test_finishing_handlers.py

from datetime import datetime, timezone
from pathlib import Path

from src.pipeline.events import (
    SystemFaultEvent, 
    FileProcessingAborted, 
    DuplicateFileDetected, 
    BadFileDetected,
    SchemaDriftDetected, 
    FileSuccessfullyProcessed
)
from src.pipeline.handlers import finishing
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.utils import calculate_email_row_hash
from src.files.domain import File, FileStatus
from src.leads.domain import Lead, LeadSnapshot
from src.leads.status_enum import LeadStatus
from src.leads.schemas import LeadData

from tests.fakes.fake_file_repository import FakeFileRepository
from tests.fakes.fake_uow import FakeUnitOfWork
from tests.fakes.fake_storage_manager import FakeFileStorageManager 
from tests.fakes.dummies import get_dummy_interrupted_file, get_dummy_leads_file, get_dummy_lead_quar, get_dummy_lead


def test_handle_system_fault(tmp_path, clean_uow):
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    
    filepath = directory.get_processing_path("unfortunate.csv")
    storage.known_files.add(filepath)
    
    event = SystemFaultEvent(
            file_id=1,
            filename="unfortunate.csv",
            filepath=str(filepath),
            error_type="DatabaseConnectionError",
            message=f"DB failed after 3 attempts."                    
    )
    file = get_dummy_interrupted_file()
    with clean_uow as uow: 
        uow.files.add(file)
    
    finishing.handle_system_fault(event, storage, directory)

    expected_path = directory.get_system_failure_path(event.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    
    
def test_handle_bad_file(tmp_path):
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    
    filepath = directory.get_processing_path("evil.csv")
    storage.known_files.add(filepath)
    
    event = BadFileDetected(
        filepath=str(directory.processing / "evil.csv"),
        filename="evil.csv"
        )

    finishing.handle_bad_file(event, storage, directory)
    
    expected_path = directory.get_bad_file_path(event.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files


def test_handle_duplicate_file(tmp_path):
    
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    
    filepath = directory.get_processing_path("duplicate.csv")
    storage.known_files.add(filepath)
    
    event = DuplicateFileDetected(
        filepath=str(filepath),
        filename="duplicate.csv"
        )
    
    finishing.handle_duplicate_file(event, storage, directory)
    
    expected_path = directory.get_duplicate_file_path(event.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    
    
    
def test_handle_schema_drift_file(tmp_path, clean_uow, configured_registry):
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    file = get_dummy_interrupted_file()
    uow = clean_uow
    
    with uow as uow:            
        file_id = uow.files.add(file)   
        quar_row = get_dummy_lead_quar(file_id)
        uow.quarantine.add(quar_row)
        lead_entity = get_dummy_lead(file_id)
        uow.leads.add(lead_entity)
        file.update_total_rows(2)
        file.add_quarantined_row(1)
        file.process_row_success(1)
        uow.files.update(file)
        uow.commit()
    
    filepath = directory.get_processing_path(file.filename)
    storage.known_files.add(filepath)
    
    event = SchemaDriftDetected(
        file_id=file_id,
        filepath=str(filepath),
        filename=file.filename,
        assumed_type=file.assumed_type,
        reason="Super Bad Schema Drift"
    )
    
    finishing.handle_schema_drift(
        event=event,
        uow_factory=lambda: uow,
        storage=storage, 
        directory=directory, 
        registry=configured_registry
    )
    
    expected_path = directory.get_schema_failure_path(file.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    updated_file = uow.files.get_file_by_id(file_id)
    assert updated_file.status == FileStatus.FAILURE_SCHEMA
    assert updated_file.total_processed_rows == 0           # Clean-up script should run and reset values
    assert updated_file.quarantined_rows == 0
    assert updated_file.status_reason == event.reason
        
    

def test_handle_processing_aborted(tmp_path, clean_uow, configured_registry):
    
    directory = CustosDirectoryManager(base_dir=tmp_path)
    file = get_dummy_interrupted_file()
    storage = FakeFileStorageManager()
    uow = clean_uow
    
    with uow as uow:            
        file_id = uow.files.add(file)   
        quar_row = get_dummy_lead_quar(file_id)
        uow.quarantine.add(quar_row)
        lead_entity = get_dummy_lead(file_id)
        uow.leads.add(lead_entity)
        file.update_total_rows(35)
        file.add_quarantined_row(1)
        file.process_row_success(1)
        uow.files.update(file)
        uow.commit()

    filepath = directory.get_processing_path(file.filename)
    storage.known_files.add(filepath)

    event = FileProcessingAborted(
        file_id=file_id,
        filepath=str(filepath),
        reason="Something Bad Happened"
    )

    finishing.handle_processing_aborted(
        event=event, 
        uow_factory=lambda: uow,
        storage=storage, 
        directory=directory, 
        registry=configured_registry
    )
    
    expected_path = directory.get_rejected_path(file.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    updated_file = uow.files.get_file_by_id(file_id)
    assert updated_file.status == FileStatus.REJECTED
    assert updated_file.total_processed_rows == 0       # The cleanup script should run and reset values
    assert updated_file.quarantined_rows == 0
    assert updated_file.status_reason == event.reason
    
    

def test_handle_processing_clean(tmp_path, clean_uow):
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    file = get_dummy_leads_file()
    uow = clean_uow
    
    with uow as uow:            
        file_id = uow.files.add(file)   
        file.update_total_rows(35)
        file.process_row_success(35)
        uow.files.update(file)
        uow.commit()


    filepath = directory.get_processing_path(file.filename)
    storage.known_files.add(filepath)


    event = FileSuccessfullyProcessed(
        file_id=file_id, 
        filepath=str(filepath),
        filename=file.filename
    )
    
    finishing.file_completed_handler(
        event=event, 
        uow_factory=lambda: uow, 
        storage=storage, 
        directory=directory
    )
    

    expected_path = directory.get_clean_completed_path(file.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    updated_file = uow.files.get_file_by_id(file_id)
    assert updated_file.status == FileStatus.PROCESSED_CLEAN
    assert updated_file.total_processed_rows == 35
    assert updated_file.quarantined_rows == 0
    

def test_handle_processing_w_quar(tmp_path, clean_uow): 
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()
    file = get_dummy_leads_file()
    uow = clean_uow
    
    with uow as uow: 
        file_id = uow.files.add(file)
        file.update_total_rows(35)
        file.add_quarantined_row(2)
        file.process_row_success(33)
        uow.files.update(file)
        uow.commit()      
    
    filepath = directory.get_processing_path(file.filename)
    storage.known_files.add(filepath)
    
    event = FileSuccessfullyProcessed(
        file_id=file_id, 
        filepath=str(filepath),
        filename=file.filename
    )
    
    finishing.file_completed_handler(
        event=event,
        uow_factory=lambda: uow,
        storage=storage, 
        directory=directory
        )
    
    expected_path = directory.get_quarantine_completed_path(file.filename)
    assert expected_path in storage.known_files
    assert filepath not in storage.known_files
    
    updated_file = uow.files.get_file_by_id(file_id)
    assert updated_file.status == FileStatus.PROCESSED_W_QUARANTINE
    assert updated_file.total_processed_rows == 35
    assert updated_file.quarantined_rows == 2

def test_clean_up_performs_update_rollback(clean_uow, configured_registry):
    uow = clean_uow
    registry = configured_registry

    base_lead = Lead(
    source_file_id=1,
    first_name="Hannibal",
    last_name="Lecter",
    email="hannibalcannibal@chomp.com",
    email_hash=calculate_email_row_hash("hannibalcannibal@chomp.com"),
    phone="800-555-4039",
    status=LeadStatus.NEW,
    score=26,
    incoming_timestamp=datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc),
    company="Lector Therapy",
    sector="Psychology/Fine Dining",
    position="Therapist", 
    custos_timestamp=datetime(2026, 9, 4, 5, 6, tzinfo=timezone.utc)            
    )
    with uow as uow: 
        uow.leads.add(base_lead)
        
        incoming1 = LeadData(
            first_name="Hannibal",
            last_name="Lecter",
            email="hannibalcannibal@chomp.com",
            phone="800-555-4039",
            status=LeadStatus.CONTACTED,
            score=67,
            incoming_timestamp=datetime(2025, 11, 18, 17, 4, tzinfo=timezone.utc),
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
            incoming_timestamp=datetime(2025, 11, 18, 21, 45, tzinfo=timezone.utc),
            company="Federal Prison",
            sector="Solitary",
            position="High-Risk Prisoner"
            )
            
    
        update1_timestamp = datetime(2025, 11, 18, 19, 16, tzinfo=timezone.utc)
        update2_timestamp = datetime.now(timezone.utc)
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
        uow.leads.update(base_lead)
        uow.commit()
        

    finishing.clean_up(file_id=2, uow=uow, registry=registry)
    

    surviving_lead = uow.leads.get("hannibalcannibal@chomp.com")
    assert surviving_lead is not None
 
    assert len(surviving_lead.updates) == 1
    surviving_update = surviving_lead.updates[0]
    
    assert surviving_update.source_file_id == 3    
    assert surviving_update.data.score == 2
    assert surviving_lead.score == 2
