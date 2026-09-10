# tests.unit.handlers.test_persistence_handlers

# run command: poetry run python -m pytest tests/unit/handlers/test_persistence_handlers.py

import datetime
from datetime import timezone

from src.files.domain import File, FileStatus
from src.leads.schemas import LeadData
from src.leads.status_enum import LeadStatus
from src.sales.schemas import SalesData
from src.leads.domain import Lead, LeadSnapshot
from src.sales.domain import ProductDetails, CustomerDetails, FactSale

from src.pipeline.handlers.persistence import persist_to_database, check_file_completion
from src.pipeline.events import BatchProcessed, FileSuccessfullyProcessed, FileProcessingAborted
from src.pipeline.commands import SaveValidatedDataCommand

from tests.fakes.fake_uow import FakeUnitOfWork
from tests.fakes.fake_sale_dto import FakeSalesData




lead_dtos =     [
    LeadData(first_name='John', last_name='Barker', email='jbark@example.com', phone='8005556498', status=LeadStatus.MQL, score=63, incoming_timestamp=datetime.datetime(2023, 10, 24, 14, 30, tzinfo=timezone.utc), company='Super 9 Motels', sector='Hospitality', position='Buyer'),  
    LeadData(first_name='Lisa', last_name='Rodriguez', email='lisa_rodriguez@decor4u.com', phone='8005559243', status=LeadStatus.QUALIFIED, score=74, incoming_timestamp=datetime.datetime(2025, 11, 14, 11, 32, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer'), 
    LeadData(first_name='Sandra', last_name='Washington', email='s.washington@example.gov.us', phone='8005556601', status=LeadStatus.NEW, score=22, incoming_timestamp=datetime.datetime(2024, 8, 13, 6, 31, tzinfo=timezone.utc), company='HUD', sector='Public Sector', position=None), 
    LeadData(first_name='Lisa', last_name='Rodriguez', email='lisa_rodriguez@decor4u.com', phone='8005559243', status=LeadStatus.NEW, score=38, incoming_timestamp=datetime.datetime(2025, 12, 24, 13, 6, tzinfo=timezone.utc), company='Decor For You', sector='Home Goods', position='Buyer'), 
    LeadData(first_name='Omar', last_name='Halb', email='omar.s.halb@toney.furniture.com', phone='8005554059', status=LeadStatus.REJECTED, score=14, incoming_timestamp=datetime.datetime(2025, 6, 9, 15, 55, tzinfo=timezone.utc), company='Toney Furnishings Ltd.', sector='Furniture', position='Chief Purchasing Officer'),
    ]

sales_dtos = [
    SalesData(sku='UGLY_TCHOTCHKE', product_name='Ugly Tchotchke', category='Decor', customer_identifier='CUST-598741', region='Northwest', industry='Home Goods', quantity_sold=56, revenue_amount=670.12, sale_timestamp=datetime.datetime(2023, 10, 24, 0, 0), transaction_id='TXN-001 '), 
    SalesData(sku='SQUISH_SOFA_BEIGE', product_name='Squishy Sofa (Beige)', category='Furniture', customer_identifier='CUST-639500', region='Southeast', industry='Office', quantity_sold=4, revenue_amount=998.0, sale_timestamp=datetime.datetime(2025, 3, 29, 0, 0), transaction_id='TXN-002'), 
    SalesData(sku='ERSATZ_ENDTABLE', product_name='Ersatz End Table', category='Furniture', customer_identifier='CUST-913527', region='Northeast', industry='Hospitality', quantity_sold=40, revenue_amount=1320.0, sale_timestamp=datetime.datetime(2024, 2, 6, 0, 0), transaction_id='TXN-003'), 
    SalesData(sku='SAD_CLOWN_PTG', product_name='Sad Clown Painting', category='Decor', customer_identifier='CUST-546358', region='Southwest', industry='Public Sector', quantity_sold=5, revenue_amount=250.0, sale_timestamp=datetime.datetime(2024, 7, 31, 0, 0), transaction_id='TXN-004'), 
    SalesData(sku='ERSATZ_ENDTABLE', product_name='Ersatz End Table', category='Furniture', customer_identifier='CUST-913527', region='Northeast', industry='Hospitality', quantity_sold=40, revenue_amount=1320.0, sale_timestamp=datetime.datetime(2024, 2, 6, 0, 0), transaction_id='TXN-003'),
    FakeSalesData(sku=None, product_name='Ugly Tchotchke', category='Decor', customer_identifier='CUST-598741', region='Northwest', industry='Home Goods', quantity_sold=56, revenue_amount=670.12, sale_timestamp=datetime.datetime(2023, 10, 24, 0, 0), transaction_id='TXN-001 ')
    ]




def test_persist_to_db_ignores_finished_files(tmp_path, configured_registry):
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.FINISHING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_dtos[0], sales_dtos[1]],
        batch_number=1
    )

    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # should return nothing
    
    assert not messages

    
def test_persist_to_db_stops_if_batch_already_processed(tmp_path, configured_registry):
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        file.completed_batches = {1}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_dtos[0], sales_dtos[1]],
        batch_number=1
    )
    
    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # should return nothing
    
    assert not messages


def test_persist_to_db_catches_schema_config(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.PERSISTING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        file.completed_batches = {2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[lead_dtos[0], lead_dtos[1]],
        batch_number=1
    )
    
    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)

    assert len(messages) == 1
    assert isinstance(messages[0], FileProcessingAborted)
    assert "is missing ID fields:" in messages[0].reason


def test_persist_to_db_catches_missing_args(tmp_path, trap_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)      
        file.expected_batches = {1, 2}
        file.completed_batches = {2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_dtos[5]],
        batch_number=1
    )
    
    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=trap_registry)
    
    assert len(messages) == 1
    assert isinstance(messages[0], FileProcessingAborted)
    assert "SalesRepository requires a composite identifier (tuple)" in messages[0].reason


def test_persist_to_db_idempotent_leads(tmp_path, configured_registry):
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "leads.csv"

    with fake_uow as uow: 
        file = File(
        filename="leads.csv", 
        hashed_file="123", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=["leads"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="leads",
        payload=[lead_dtos[0], lead_dtos[0]],
        batch_number=1
    )
    
    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    # these are exactly the same and only one should be saved
    
    with fake_uow as uow: 
        leads_saved = uow.leads.get_by_source_file(1)
    
    assert len(leads_saved) == 1
    
        
def test_persist_to_db_idempotent_sales(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_dtos[2], sales_dtos[4]],
        batch_number=1
    )

    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # these are exactly the same but only one should be saved
    
    with fake_uow as uow: 
        sales_saved = uow.sales.get_by_source_file(1)
    
    assert len(sales_saved) == 1



def test_persist_to_db_saves_leads(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "leads.csv"

    with fake_uow as uow: 
        file = File(
        filename="leads.csv", 
        hashed_file="123", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=["leads"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="leads",
        payload=[lead_dtos[0], lead_dtos[1]],
        batch_number=1
    )

    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        new_leads = uow.leads.get_by_source_file(1)
        
    assert len(new_leads) == 2
    assert new_leads[0].email == "jbark@example.com" or new_leads[1].email == 'jbark@example.com'
    assert new_leads[1].email == 'lisa_rodriguez@decor4u.com' or new_leads[0].email == 'lisa_rodriguez@decor4u.com'

def test_persist_to_db_saves_sales(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        
        # product for sales dto at index 2
        product = ProductDetails(sku='ERSATZ_ENDTABLE', name='Ersatz End Table', category='Furniture')
        test_product_id = int(uow.sales.get_or_create_product(product))
        
        # customer for sales dto at index 1
        customer = CustomerDetails(identifier='CUST-639500', region='Southeast', industry='Office')
        test_customer_id = int(uow.sales.get_or_create_customer(customer))
        
        # date for sales dto at index 0
        sale_timestamp=datetime.datetime(2023, 10, 24, 0, 0)
        test_date_id = int(uow.sales.get_or_create_date(sale_timestamp))           
            
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_dtos[0], sales_dtos[1], sales_dtos[2]],
        batch_number=1
    )
    
    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        new_sales = uow.sales.get_by_source_file(1)

    assert len(new_sales) == 3
    
    sale_1 = next(s for s in new_sales if s.transaction_id == "TXN-001 ") # TXN from index 0
    sale_2 = next(s for s in new_sales if s.transaction_id == "TXN-002")  # TXN from index 1
    sale_3 = next(s for s in new_sales if s.transaction_id == "TXN-003")  # TXN from index 2

    assert sale_1.date_id == test_date_id
    assert sale_1.product_id == test_product_id + 1
    assert sale_1.customer_id == test_customer_id + 1

    assert sale_2.date_id == test_date_id + 1
    assert sale_2.customer_id == test_customer_id
    assert sale_2.product_id == test_product_id + 2

    assert sale_3.date_id == test_date_id + 2
    assert sale_3.customer_id == test_customer_id + 2
    assert sale_3.product_id == test_product_id
    
    

def test_persist_to_db_updates_leads(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "leads.csv"

    with fake_uow as uow: 
        file = File(
        filename="leads.csv", 
        hashed_file="123", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=["leads"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = SaveValidatedDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="leads",
        payload=[lead_dtos[1], lead_dtos[3]],
        batch_number=1
    )

    messages = persist_to_database(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # index 3 should update index 1 -- status goes from QUALIFIED to NEW and score from 74 to 38 (not likely but still...)
    
    with fake_uow as uow: 
        new_leads = uow.leads.get_by_source_file(1)
        
    assert len(new_leads) == 1
    assert len(new_leads[0].updates) == 2    
    update = new_leads[0].updates[1].data
    assert update.status == LeadStatus.NEW or "NEW"
    assert update.score == 38



def check_file_completion_completes_persistence(tmp_path):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        file.completed_batches = {2}
        uow.files.update(file)
        uow.commit()

    event = BatchProcessed(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
        )

    messages = check_file_completion(event=event, uow_factory=lambda: fake_uow)
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
    
    assert len(messages) == 1
    assert isinstance(messages[0], FileSuccessfullyProcessed)
    assert file_entity.status == FileStatus.FINISHING
    assert 1 in file_entity.completed_batches
    

def check_file_completion_ignores_finished_files(tmp_path):
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.FINISHING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    event = BatchProcessed(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
        )


    messages = check_file_completion(event=event, uow_factory=lambda: fake_uow)
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
    
    assert file_entity.status == FileStatus.FINISHING
    assert 1 not in file_entity.completed_batches
    assert not messages
        

def check_file_completion_ignores_incomplete_file(tmp_path):
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)  
        file.expected_batches = {1, 2}
        file.completed_batches = {1}
        uow.files.update(file)
        uow.commit()

    event = BatchProcessed(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
        )

    
    messages = check_file_completion(event=event, uow_factory=lambda: fake_uow)
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
    
    assert file_entity.status == FileStatus.VALIDATING    
    assert not messages