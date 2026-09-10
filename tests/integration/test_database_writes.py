# tests.integration.test_database_writes

# run command: poetry run python -m pytest -s tests/integration/test_database_writes.py

from sqlalchemy import select

from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.directory import CustosDirectoryManager
from src.pipeline.commands import SaveValidatedDataCommand, AuditCSVCommand, ValidateDataCommand
from src.pipeline.events import FileProcessingAborted
from src.pipeline.handlers import persistence, auditing, validation, finishing
from src.sales.orm import DimCustomerORM, DimDateORM, DimProductORM, FactSaleORM

from tests.fakes import dummies
from tests.fakes.fake_storage_manager import FakeFileStorageManager


from src.leads.orm import LeadORM


def test_persists_to_database_writes_to_postgres(tmp_path, real_uow, configured_registry):
    
    file = dummies.get_dummy_leads_file()
    with real_uow as uow: 
        file.expected_batches = {1, 2, 3}
        file.update_total_rows(7)
        exists = uow.files.check_exists(file)
        if exists: 
            existing_file = uow.files.get_file_by_hash(file.hashed_file)
            file_id = existing_file.id
            uow.files.update(file)
        else: 
            file_id = uow.files.add(file)
        uow.commit()
        
    filepath = tmp_path / file.filename 
    payload = dummies.get_dummy_lead_dtos("good")
    
    command = SaveValidatedDataCommand(
    file_id=file_id, 
    filepath=str(filepath),
    filename=file.filename,
    assumed_type=file.assumed_type,
    payload=payload,
    batch_number=1
    )
    
    messages = persistence.persist_to_database(
        command=command,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    
    with real_uow as uow:

        saved_file = uow.files.get(file_id)
        assert saved_file.total_processed_rows == 2
        
        saved_leads = uow.leads.get_by_source_file(file_id)
        assert len(saved_leads) == 2
        
        emails = [lead.email for lead in saved_leads]
        assert "jbark@example.com" in emails
    
def test_persist_to_db_creates_star_sales(tmp_path, real_uow, configured_registry):
        
        file = dummies.get_dummy_sales_file()
        with real_uow as uow: 
            file.expected_batches = {1, 2, 3}
            file.update_total_rows(7)
            exists = uow.files.check_exists(file)
            if exists: 
                existing_file = uow.files.get_file_by_hash(file.hashed_file)
                file_id = existing_file.id
                uow.files.update(file)
            else: 
                file_id = uow.files.add(file)
            uow.commit()
            
        filepath = tmp_path / file.filename 
        payload = dummies.get_dummy_sales_dtos("good")
        
        command = SaveValidatedDataCommand(
        file_id=file_id, 
        filepath=str(filepath),
        filename=file.filename,
        assumed_type=file.assumed_type,
        payload=payload,
        batch_number=1
        )
        
        messages = persistence.persist_to_database(
            command=command,
            uow_factory=lambda: real_uow,
            registry=configured_registry
        )
        
        with real_uow as uow:
    
            saved_file = uow.files.get(file_id)
            assert saved_file.total_processed_rows == 2
            
            saved_sales = uow.sales.get_by_source_file(file_id)
            assert saved_sales is not None
            assert len(saved_sales) == 2
            tchotchke_sale = next((sale for sale in saved_sales if sale.transaction_id == "TXN-001"), None)
            sofa_sale = next((sale for sale in saved_sales if sale.transaction_id == "TXN-002"), None)
            assert tchotchke_sale is not None
            assert sofa_sale is not None
            
            stmt_1 = select(DimProductORM).where(DimProductORM.id == sofa_sale.product_id)
            sofa = uow.session.execute(stmt_1).scalar_one_or_none()
            assert sofa is not None
            assert "Squishy" in sofa.name
            
            stmt_2 = select(DimCustomerORM).where(DimCustomerORM.id == tchotchke_sale.customer_id)                      
            tchotchke_buyer = uow.session.execute(stmt_2).scalar_one_or_none()
            assert tchotchke_buyer is not None
            assert tchotchke_buyer.region == "Northwest"
            
            stmt_3 = select(DimDateORM).where(DimDateORM.id == tchotchke_sale.date_id)
            tchotchke_date = uow.session.execute(stmt_3).scalar_one_or_none()
            assert tchotchke_date is not None
            assert tchotchke_date.is_holiday == True
                    
    
def test_auditing_persists_quarantine(tmp_path, real_uow, configured_registry):

    fake_csv = dummies.get_quarantined_row_for_pandas("lead")
    fake_file = dummies.get_dummy_leads_file()
    with real_uow as uow: 
        uow.files.add(fake_file)
        fake_file.start_auditing()
        uow.files.update(fake_file)
        uow.commit()

    test_file = tmp_path / fake_file.filename
    for item in fake_csv: 
        test_file.write_text(item)
    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    command = AuditCSVCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=fake_file.filename,
        original_assumed_type=fake_file.assumed_type,
        assumed_type=fake_file.assumed_type,
        potential_types=fake_file.potential_types,
        is_ambiguous=False,
        attempted_types=[]
        )
    
    messages = auditing.audit_csv(command=command, uow_factory=lambda: real_uow, registry=configured_registry)
    
    with real_uow as uow: 
        saved_file = uow.files.get_file_by_hash(fake_file.hashed_file)
        assert saved_file.total_processed_rows == 1
        assert saved_file.quarantined_rows == 1
        quarantined = uow.quarantine.get_by_source_file(saved_file.id)
        assert quarantined is not None
        assert len(quarantined) == 1
        assert "Email_Address" in quarantined[0].raw_payload
        assert quarantined[0].raw_payload.get("Email_Address") == "jbark@example.com"
        
        
        
def test_validate_persists_quarantine(tmp_path, real_uow, configured_registry):
    
    fake_dto = dummies.get_quarantined_row_for_pydantic("sales")
    fake_file = dummies.get_dummy_sales_file()
    with real_uow as uow: 
        uow.files.add(fake_file)
        fake_file.total_rows = 35
        fake_file.validate()
        uow.files.update(fake_file)
        uow.commit()

    test_file = tmp_path / fake_file.filename

    
    fake_storage = FakeFileStorageManager()
    fake_storage.known_files.add(test_file)
    
    
    command = ValidateDataCommand(
        file_id=1, 
        filepath=str(test_file), 
        filename=fake_file.filename,
        assumed_type=fake_file.assumed_type,
        payload=fake_dto,
        batch_number=1
        )
    
    messages = validation.validate_data(command=command, uow_factory=lambda: real_uow, registry=configured_registry)
    
    with real_uow as uow: 
        saved_file = uow.files.get_file_by_hash(fake_file.hashed_file)
        assert saved_file.total_processed_rows == 1
        assert saved_file.quarantined_rows == 1
        quarantined = uow.quarantine.get_by_source_file(saved_file.id)
        assert quarantined is not None
        assert len(quarantined) == 1
        assert "SKU_Code" in quarantined[0].raw_payload
        assert quarantined[0].raw_payload.get("SKU_Code") == "COL_RUG"
        assert "CUST" in quarantined[0].error_reason
    
    
    
def test_persist_to_db_creates_updates(tmp_path, real_uow, configured_registry):
    file1, file2, file3 = dummies.get_three_lead_files()
    base_lead, lead1_dto, lead2_dto = dummies.get_base_and_updates()
    filepath1, filepath2, filepath3 = (tmp_path / f.filename for f in (file1, file2, file3))
    with real_uow as uow: 
        for file in (file1, file2, file3):
            file.update_total_rows(75)
            file.expected_batches = {1, 2, 3, 4, 5}
            exists = uow.files.check_exists(file)
            if exists: 
                existing_file = uow.files.get_file_by_hash(file.hashed_file)
                file_id = existing_file.id
                uow.files.update(file)
            else: 
                file_id = uow.files.add(file)
                uow.files.add(file)
            uow.files.add(file)
        uow.commit()
        
    
    command1 = SaveValidatedDataCommand(
        file_id=1,
        filepath=str(filepath1),
        filename=file1.filename,
        assumed_type=file1.assumed_type,
        payload=[base_lead],
        batch_number=1
        )
        
    command2 = SaveValidatedDataCommand(
        file_id=2, 
        filepath=str(filepath2),
        filename=file2.filename,
        assumed_type=file2.assumed_type,
        payload=[lead1_dto],
        batch_number=1
        )      
    
    command3 = SaveValidatedDataCommand(
        file_id=3, 
        filepath=str(filepath3),
        filename=file3.filename,
        assumed_type=file3.assumed_type,
        payload=[lead2_dto],
        batch_number=1
        )
    
    messages1 = persistence.persist_to_database(
        command=command1,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    messages2 = persistence.persist_to_database(
        command=command2,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    messages3 = persistence.persist_to_database(
        command=command3,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    
    with real_uow as uow:
        saved_lead = uow.leads.get(base_lead.email)        
        assert saved_lead is not None
        
        assert saved_lead.company == lead2_dto.company 
        assert saved_lead.score == lead2_dto.score      

        assert len(saved_lead.updates) == 3

        update_from_file_3 = next((u for u in saved_lead.updates if u.source_file_id == 3), None)
        assert update_from_file_3 is not None
        
        assert update_from_file_3.data.score == lead2_dto.score



        
def test_finishing_deletes_single_source_leads(tmp_path, real_uow, configured_registry):
    """This tests whether the repo correctly rolls back -- i.e., deletes -- a Lead when it was 
    created and updated solely by a single file -- i.e., the one subject to rollback."""
    
    
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()

    file1, file2, file3 = dummies.get_three_lead_files()        # don't actually need all three for this test
    base_lead, lead1_dto, lead2_dto = dummies.get_base_and_updates()

    filepath = directory.get_processing_path(file1.filename)
    storage.known_files.add(filepath)
    with real_uow as uow: 
        file1.update_total_rows(75)
        file1.expected_batches = {1, 2, 3, 4, 5}
        exists = uow.files.check_exists(file1)
        if exists: 
            existing_file = uow.files.get_file_by_hash(file1.hashed_file)
            file_id = existing_file.id
            uow.files.update(file1)
        else: 
            file_id = uow.files.add(file1)
            uow.files.add(file1)
        uow.files.add(file1)
        uow.commit()
        
    
    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=str(filepath),
        filename=file1.filename,
        assumed_type=file1.assumed_type,
        payload=[base_lead, lead1_dto, lead2_dto],
        batch_number=1
        )
    
    event = FileProcessingAborted(
        file_id=1,
        filepath=str(filepath),
        reason="File is totally screwed up."
    )
        
    messages1 = persistence.persist_to_database(
        command=command,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    
    
    with real_uow as uow:
        saved_lead = uow.leads.get(base_lead.email)        
        assert saved_lead is not None
        
        assert saved_lead.company == lead2_dto.company 
        assert saved_lead.score == lead2_dto.score      

        assert len(saved_lead.updates) == 3

        
    messages2 = finishing.handle_processing_aborted(
        event=event, 
        uow_factory=lambda: real_uow,
        directory=directory,
        storage=storage, 
        registry=configured_registry            
    )
    with real_uow as uow:
        saved_lead = uow.leads.get(base_lead.email)        
        assert not saved_lead
        

def test_finishing_rolls_back_updates(tmp_path, real_uow, configured_registry):
    """This tests whether the finishing function correctly rolls back data/updates from one source
    file among multiple sources responsible for data in the Lead entity."""
    
    directory = CustosDirectoryManager(base_dir=tmp_path)
    storage = FakeFileStorageManager()

    file1, file2, file3 = dummies.get_three_lead_files()        # we DO need all three here
    base_lead, lead1_dto, lead2_dto = dummies.get_base_and_updates()
    filepath1, filepath2, filepath3 = (directory.get_processing_path(f.filename) for f in (file1, file2, file3))
    for path in (filepath1, filepath2, filepath3):
        storage.known_files.add(path)
   
    with real_uow as uow: 
        for file in (file1, file2, file3):
            file.update_total_rows(75)
            file.expected_batches = {1, 2, 3, 4, 5}
            exists = uow.files.check_exists(file)
            if exists: 
                existing_file = uow.files.get_file_by_hash(file.hashed_file)
                file_id = existing_file.id
                uow.files.update(file)
            else: 
                file_id = uow.files.add(file)
                uow.files.add(file)
            
        uow.commit()
        
    
    command1 = SaveValidatedDataCommand(
        file_id=1,
        filepath=str(filepath1),
        filename=file1.filename,
        assumed_type=file1.assumed_type,
        payload=[base_lead],
        batch_number=1
        )
        
    command2 = SaveValidatedDataCommand(
        file_id=2, 
        filepath=str(filepath2),
        filename=file2.filename,
        assumed_type=file2.assumed_type,
        payload=[lead1_dto],
        batch_number=1
        )      
    
    command3 = SaveValidatedDataCommand(
        file_id=3, 
        filepath=str(filepath3),
        filename=file3.filename,
        assumed_type=file3.assumed_type,
        payload=[lead2_dto],
        batch_number=1
        )
    
    messages1 = persistence.persist_to_database(
        command=command1,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    messages2 = persistence.persist_to_database(
        command=command2,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )
    messages3 = persistence.persist_to_database(
        command=command3,
        uow_factory=lambda: real_uow,
        registry=configured_registry
    )

    disastrous_event = FileProcessingAborted(
        file_id=2,
        filepath=str(filepath2),
        reason="File 2 was corporate espionage."
    )
    
    with real_uow as uow:
        all_leads = uow.session.execute(select(LeadORM)).scalars().all()
        saved_lead = uow.leads.get(base_lead.email)        
        assert saved_lead is not None
        
        assert saved_lead.company == lead2_dto.company 
        assert saved_lead.score == lead2_dto.score      

        assert len(saved_lead.updates) == 3
    
    
    messages4 = finishing.handle_processing_aborted(
        event=disastrous_event,
        uow_factory=lambda: real_uow,
        directory=directory,
        storage=storage, 
        registry=configured_registry        
    )
    
    
    with real_uow as uow:
        saved_lead = uow.leads.get(base_lead.email)        
        assert saved_lead is not None
        
        assert saved_lead.company == lead2_dto.company 
        assert saved_lead.score == lead2_dto.score      

        assert len(saved_lead.updates) == 2
        update_from_file_2 = next((u for u in saved_lead.updates if u.source_file_id == 2), None)
        assert not update_from_file_2
        update_from_file_3 = next((u for u in saved_lead.updates if u.source_file_id == 3), None)
        assert update_from_file_3 is not None
        
        assert update_from_file_3.data.score == 2
