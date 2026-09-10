import csv
import pandas as pd
import pytest
from testcontainers.community.postgres import PostgresContainer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database import Base
from src.infrastructure.adapters.uow_adapter import SQLAlchemyUnitOfWork

from datetime import datetime, timezone
from src.infrastructure.file_registry import FileTypeRegistry
from src.sales.schemas import SalesRowSchema, SalesData
from src.sales.domain import FactSale, ProductDetails, CustomerDetails
from src.sales.services import process_sales_record
from src.leads.domain import Lead, LeadSnapshot
from src.leads.schemas import LeadRowSchema, LeadData
from src.leads.services import process_lead_record
from tests.fakes import fake_lead_csv as leads
from tests.fakes import fake_sales_csv as sales
from tests.fakes.fake_sale_dto import FakeSalesData
from tests.fakes.fake_uow import FakeUnitOfWork

@pytest.fixture
def clean_uow():
    """Resets the unit of work for tests"""
    uow = FakeUnitOfWork()

    return uow



@pytest.fixture
def configured_registry() -> FileTypeRegistry:
    """Provides a real registry pre-loaded with the sales domain configuration."""
    registry = FileTypeRegistry()
    
    registry.register(
        file_type="sales",
        key_fields={"transaction_id", "Transaction_id", "Transaction_ID", "Transaction_Id"},
        id_fields=("transaction_id", "sku"),
        schema=SalesRowSchema,
        data=SalesData,
        entity=FactSale, 
        associated_entities=[ProductDetails, CustomerDetails],
        repo_name="sales",
        allows_updates=False,
        update_model=None,
        helper=process_sales_record,
        requires_timestamp=False, 
        required_fields={
             "SKU_Code", 
              "Product_Name",
              "Category",
              "Customer_ID",
              "Region",
              "Industry",
              "Quantity",
              "Revenue",
              "Transaction_Date",
              "Transaction_ID"
          }, 
        batch_size=3
    )
    
    registry.register(
        file_type="leads",
        key_fields={"lead_score", "Lead_Score", "Lead_score"},
        id_fields="email",
        schema=LeadRowSchema,
        data=LeadData, 
        entity=Lead, 
        associated_entities=None,
        repo_name="leads",
        allows_updates=True,
        update_model=LeadSnapshot,
        helper=process_lead_record,
        requires_timestamp=True, 
        required_fields={
            "First_Name",
           "Last_Name",
           "Email_Address",
           "Phone_Number",
           "Lead_Score"
        }, 
        batch_size=2
    )
    
    return registry

@pytest.fixture
def trap_registry() -> FileTypeRegistry:
    """Provides a real registry pre-loaded with the sales domain configuration."""
    registry = FileTypeRegistry()
    
    registry.register(
        file_type="sales",
        key_fields={"transaction_id", "Transaction_id", "Transaction_ID", "Transaction_Id"},
        id_fields=("transaction_id"),
        schema=SalesRowSchema,
        data=SalesData,
        entity=FactSale, 
        associated_entities=[ProductDetails, CustomerDetails],
        repo_name="sales",
        allows_updates=False,
        update_model=None,
        helper=process_sales_record,
        requires_timestamp=False, 
        required_fields={
             "SKU_Code", 
              "Product_Name",
              "Category",
              "Customer_ID",
              "Region",
              "Industry",
              "Quantity",
              "Revenue",
              "Transaction_Date",
              "Transaction_ID"
          }, 
        batch_size=3
    )
    
    registry.register(
        file_type="leads",
        key_fields={"lead_score", "Lead_Score", "Lead_score"},
        id_fields="email",
        schema=LeadRowSchema,
        data=LeadData, 
        entity=Lead, 
        associated_entities=None,
        repo_name="leads",
        allows_updates=True,
        update_model=LeadSnapshot,
        helper=process_lead_record,
        requires_timestamp=True, 
        required_fields={
            "First_Name",
           "Last_Name",
           "Email_Address",
           "Phone_Number",
           "Lead_Score"
        }, 
        batch_size=2
    )
    
    return registry

@pytest.fixture
def test_registry() -> FileTypeRegistry:
    """Provides a real registry configured with smaller batch sizes for e2e tests."""
    registry = FileTypeRegistry()
    
    registry.register(
        file_type="sales",
        key_fields={"transaction_id", "Transaction_id", "Transaction_ID", "Transaction_Id"},
        id_fields=("transaction_id", "sku"),
        schema=SalesRowSchema,
        data=FakeSalesData,
        entity=FactSale, 
        associated_entities=[ProductDetails, CustomerDetails],
        repo_name="sales",
        allows_updates=False,
        update_model=None,
        helper=process_sales_record,
        requires_timestamp=False, 
        required_fields={
             "SKU_Code", 
              "Product_Name",
              "Category",
              "Customer_ID",
              "Region",
              "Industry",
              "Quantity",
              "Revenue",
              "Transaction_Date",
              "Transaction_ID"
          }, 
        batch_size=10
    )
    
    registry.register(
        file_type="leads",
        key_fields={"lead_score", "Lead_Score", "Lead_score"},
        id_fields="email",
        schema=LeadRowSchema,
        data=LeadData, 
        entity=Lead, 
        associated_entities=None,
        repo_name="leads",
        allows_updates=True,
        update_model=LeadSnapshot,
        helper=process_lead_record,
        requires_timestamp=True, 
        required_fields={
            "First_Name",
           "Last_Name",
           "Email_Address",
           "Phone_Number",
           "Lead_Score"
        }, 
        batch_size=10
    )
    
    return registry

@pytest.fixture(scope="module")
def postgres_url():
    """Spins up a real PostgreSQL container once per test module."""
    with PostgresContainer("postgres:15-alpine") as postgres:

        yield postgres.get_connection_url(driver="psycopg")
        
@pytest.fixture(scope="function")
def clean_db_engine(postgres_url):
    """Provides a clean database for every single test."""
    engine = create_engine(postgres_url)
    
    Base.metadata.create_all(engine)
    
    yield engine
    
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def real_uow(postgres_url, clean_db_engine):
    """Provides a fresh SQLAlchemy Unit of Work backed by the Postgres container, 
    tearing down all tables after each test function.
    """
    engine = clean_db_engine
    
    Base.metadata.create_all(engine)
    
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    uow = SQLAlchemyUnitOfWork(session_factory=TestSessionLocal)
    
    yield uow
    
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture(scope="function")
def real_uow_factory(clean_db_engine):
    """Returns a factory function that generates fresh UoWs."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=clean_db_engine)
    
    def _factory():
        return SQLAlchemyUnitOfWork(session_factory=TestSessionLocal)
        
    yield _factory


@pytest.fixture
def write_good_sales_csv(tmp_path, row_count: int = 50, include_errors: bool = False):
    """Creates a CSV file for sales from factory dicts in tmp_path for e2e tests -- passes with or w/o quarantined rows."""
    
    def _write(filename: str = "sales_01.csv", row_count = row_count, include_errors=include_errors):

        headers = sales.generate_headers()
        rows = sales.generate_good_rows(row_count)
        
        if include_errors:
            rows = sales.inject_bad_quantity(rows, n=2)
            rows = sales.inject_bad_customer_identifiers(rows, n=2)

        incoming_dir = tmp_path / "incoming" / "sales"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        file_path = incoming_dir / filename
        
        df = pd.DataFrame(rows, columns=headers)
        df.to_csv(file_path, index=False)

            
        return file_path
        
    return _write

@pytest.fixture
def write_tricky_sales_csv(tmp_path, row_count: int = 50):
    """Makes a CSV file for sales for e2e tests; tricky because it has multiple duplicate rows (should be ignored)"""
    def _write(filename: str = "tricky_sales_01.csv", row_count: int = row_count):

        headers = sales.generate_headers()
        rows = sales.generate_good_rows(row_count)
        rows = sales.inject_exact_duplicates(rows=rows, n=4)

        incoming_dir = tmp_path / "incoming" / "sales"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        file_path = incoming_dir / filename

        df = pd.DataFrame(rows, columns=headers)
        df.to_csv(file_path, index=False)
            
        return file_path
        
    return _write
    

@pytest.fixture
def write_failing_sales_csv(tmp_path, row_count: int = 50):
    """Creates a CSV file for sales from factory dicts in tmp_path for e2e tests -- this will fail for schema drift at AUDIT"""
    def _write(filename: str = "failing_sales_01.csv", row_count: int = row_count):

        headers = sales.generate_missing_headers()
        rows = sales.missing_headers_rows(row_count)


        incoming_dir = tmp_path / "incoming" / "sales"
        incoming_dir.mkdir(parents=True, exist_ok=True)
        file_path = incoming_dir / filename

        df = pd.DataFrame(rows, columns=headers)
        df.to_csv(file_path, index=False)
            
        return file_path
        
    return _write


@pytest.fixture
def write_good_leads_csv(tmp_path):
    """Creates a CSV file for leads from factory dicts in tmp_path for e2e tests"""
    def _write(filename: str = "leads_01.csv", row_count: int = 85, include_errors: bool = False):

        headers = leads.generate_headers()
        rows = leads.generate_good_rows(row_count)
        
        if include_errors:
            rows = leads.inject_bad_phone_number(rows, n=2)
            rows = leads.inject_missing_required_field(rows, n=2)
        
        temp_path = tmp_path / filename
        
        df = pd.DataFrame(rows)
        df.to_csv(temp_path, index=False)
            
        return temp_path
        
    return _write

@pytest.fixture
def write_tricky_leads_csv(tmp_path, row_count: int = 40, include_errors: bool = False):
    """Creates an actual CSV file for leads for e2e tests; tricky because it has only one time column"""
    def _write(filename: str = "tricky_leads_01.csv", row_count: int = 85, include_errors=include_errors):
        headers = leads.generate_missing_time_header()
        rows = leads.generate_good_rows(n=row_count)
        rows = leads.strip_created_column(rows=rows, keep="Modified_At")
        
        if include_errors:
            rows = leads.inject_bad_phone_number(rows, n=2)
            rows = leads.inject_missing_required_field(rows, n=2)
            

        temp_path = tmp_path / filename
        
        df = pd.DataFrame(rows)
        df.to_csv(temp_path, index=False)
            
        return temp_path
        
    return _write

@pytest.fixture
def write_failing_leads_csv(tmp_path, row_count: int = 50):
    """Creates a CSV file for leads that should fail at the VALIDATION layer"""
    def _write(filename: str = "failing_leads_01.csv", row_count=row_count):
        headers = leads.generate_headers()
        rows = leads.generate_good_rows(n=row_count)    
        rows = leads.inject_bad_phone_number(rows, n=5)
        rows = leads.inject_missing_required_field(rows, n=6)

        temp_path = tmp_path / filename
        
        df = pd.DataFrame(rows)
        df.to_csv(temp_path, index=False)
            
        return temp_path
        
    return _write


@pytest.fixture
def write_update_leads_csv(tmp_path, row_count: int = 25):
        
    def _write(filename: str = "leads_w_updates.csv", row_count=row_count):
        headers = leads.generate_headers()
        rows=leads.generate_good_rows(row_count)        
        
        rows, originals, email_keys = leads.create_updates(rows, n=5)
        
        temp_path = tmp_path / filename
        
        df = pd.DataFrame(rows)
        df.to_csv(temp_path, index=False)     

        return temp_path, originals, email_keys 

    return _write

@pytest.fixture
def write_special_updates_leads_csv(tmp_path, special_rows, row_count: int = 25):
    
    def _write(filename: str = "leads_w_special_updates.csv", row_count=row_count, special_rows=special_rows):
        headers = leads.generate_headers()
        rows = leads.generate_good_rows(row_count)
        rows.extend(special_rows)

        
        temp_path = tmp_path / filename
        
        df = pd.DataFrame(rows)
        df.to_csv(temp_path, index=False)
        
        return temp_path
    
    return _write
