# src.infrastructure.bootstrapper

import time
from functools import partial
from typing import Callable

from src.bootstrap.dependencies import get_uow
from src.infrastructure.adapters.apscheduler_runner import APSchedulerAdapter
from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.adapters.message_bus import MessageBus
from src.infrastructure.adapters.watchdog_runner import WatchdogAdapter
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.file_registry import FileTypeRegistry
from src.leads.domain import Lead, LeadSnapshot
from src.leads.schemas import LeadRowSchema, LeadData
from src.leads.services import process_lead_record
from src.pipeline import commands 
from src.pipeline import events
from src.pipeline.handlers import (
    staging, 
    auditing, 
    validation, 
    persistence, 
    finishing
)
from src.sales.schemas import SalesRowSchema, SalesData
from src.sales.domain import FactSale, ProductDetails, CustomerDetails
from src.sales.services import process_sales_record
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.interfaces.runner_interface import AbstractBackgroundRunner


def bootstrap_registry():
    """Establishes registry configuration for domains/file types"""
    registry = FileTypeRegistry()
        
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
        batch_size=500
    )
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
        batch_size=1000
    )
    return registry


def bootstrap_bus(
    uow_factory: Callable,     
    registry: FileTypeRegistry,   
    storage_manager: AbstractFileStorageManager | None = None,
    directory: CustosDirectoryManager | None = None   
):
    """Bootstraps the message bus with all commands and events."""

    bus = MessageBus()
    uow_factory=uow_factory
    registry = registry
    
    if storage_manager == None: 
        storage_manager = CustosFileStorageManager()
    
    if directory == None: 
        directory = CustosDirectoryManager()

    stage_file_strapped = partial(
        staging.stage_file, 
        registry=registry, 
        storage=storage_manager,
        directory=directory
    )
        
    file_staged_strapped = partial(
        staging.file_staged_handler, 
        uow_factory=uow_factory, 
        storage=storage_manager
    )
    
    # --- Auditing Handlers
    
    audit_csv_strapped = partial(
        auditing.audit_csv, 
        uow_factory=uow_factory, 
        registry=registry
    )
    
    attempt_retry_strapped = partial(
        auditing.attempt_retry,
        uow_factory=uow_factory
    )
    
    # --- Validation Handlers
    validate_data_strapped = partial(
        validation.validate_data, 
        uow_factory=uow_factory, 
        registry=registry
    )   
    
    handle_pydantic_failure_strapped = partial(
        validation.handle_pydantic_failure, 
        uow_factory=uow_factory
    )
    
    # --- Persistence Handlers
    
    persist_to_database_strapped = partial(
        persistence.persist_to_database,
        uow_factory=uow_factory, 
        registry=registry
    )

    check_file_completion_strapped = partial(
        persistence.check_file_completion, 
        uow_factory=uow_factory
    )

    # --- Finishing Handlers
    
    handle_bad_file_strapped = partial(
        finishing.handle_bad_file, 
        storage=storage_manager, 
        directory=directory
    )
    
    handle_duplicate_file_strapped = partial(
        finishing.handle_duplicate_file, 
        storage=storage_manager,
        directory=directory
    )
    handle_schema_drift_strapped = partial(
        finishing.handle_schema_drift, 
        uow_factory=uow_factory, 
        storage=storage_manager,
        directory=directory, 
        registry=registry
    )
    
    file_completion_handler_strapped = partial(
        finishing.file_completed_handler, 
        uow_factory=uow_factory, 
        storage=storage_manager,
        directory=directory
    )

    file_processing_aborted_strapped = partial(
        finishing.handle_processing_aborted, 
        uow_factory=uow_factory,
        storage=storage_manager,
        directory=directory, 
        registry=registry
    )   
    
    handle_system_fault_strapped = partial(
        finishing.handle_system_fault, 
        storage=storage_manager,
        directory=directory
    )

    bus.register_command(commands.StageFileCommand, stage_file_strapped)
    bus.subscribe_event(events.FileStaged, file_staged_strapped)
    bus.register_command(commands.AuditCSVCommand, audit_csv_strapped)
    bus.subscribe_event(events.PandasAuditFailed, attempt_retry_strapped)
    bus.register_command(commands.ValidateDataCommand, validate_data_strapped)
    bus.subscribe_event(events.PydanticAuditFailed, handle_pydantic_failure_strapped)
    bus.register_command(commands.SaveValidatedDataCommand, persist_to_database_strapped)
    bus.subscribe_event(events.BatchProcessed, check_file_completion_strapped)
    
    bus.subscribe_event(events.FileSuccessfullyProcessed, file_completion_handler_strapped) 
    bus.subscribe_event(events.BadFileDetected, handle_bad_file_strapped)
    bus.subscribe_event(events.DuplicateFileDetected, handle_duplicate_file_strapped)
    bus.subscribe_event(events.FileProcessingAborted, file_processing_aborted_strapped)
    bus.subscribe_event(events.SchemaDriftDetected, handle_schema_drift_strapped )
    bus.subscribe_event(events.SystemFaultEvent, handle_system_fault_strapped)
    
    return bus

  