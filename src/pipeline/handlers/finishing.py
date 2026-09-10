# src.pipeline.handlers.finishing

from pathlib import Path
from typing import Callable, Sequence, Union

import structlog

from src.bootstrap.dependencies import get_uow
from src.files.domain import File, FileStatus
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.file_registry import FileTypeRegistry
from src.infrastructure.handlers.alerts import send_system_failure_alert
from src.infrastructure.logging import log_domain_error
from src.infrastructure.wrappers.safety_wrappers import (
    with_infrastructure_safety,
    with_logging_context,
)
from src.pipeline.events import (
    BadFileDetected,
    DuplicateFileDetected,
    FileProcessingAborted,
    FileSuccessfullyProcessed,
    SchemaDriftDetected,
    SystemFaultEvent,
)
from src.shared.errors import ResourceNotFoundError
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.interfaces.uow_interface import AbstractUnitOfWork
from src.shared.messages import Command, DomainEvent, Message

logger = structlog.get_logger(__name__)


def clean_up(
    file_id: int | None, 
    uow: AbstractUnitOfWork,
    registry: FileTypeRegistry
    ):
    

    if file_id: 
        for key, value in registry._registry.items():  
            if not hasattr(uow, value.repo_name):
                domain_error = ResourceNotFoundError(
                    "NotFound", 
                    f"UoW missing repository: {value.repo_name}"
                )
                log_domain_error(domain_error, missing_repo=value)
                continue
                
            target_repo = getattr(uow, value.repo_name)
            
            if hasattr(target_repo, "delete_by_source_file"):
                target_repo.delete_by_source_file(file_id)
        
        
        if hasattr(uow, "quarantine"):
            uow.quarantine.delete_by_source_file(file_id)
        uow.commit() 
        
    else: 

        domain_error = ResourceNotFoundError("NotFound", "No file found; no file id was input")
        log_domain_error(domain_error)



@with_logging_context
@with_infrastructure_safety(max_retries=3)
def handle_system_fault(
    event: SystemFaultEvent, 
    storage: AbstractFileStorageManager,
    directory: CustosDirectoryManager
        ):
    """Handles files being processed (at multiple stages) when a database system fault occurs."""
    
    lock_file = directory.incoming / "SYSTEM_HALTED.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.touch()
    
    source_path = Path(event.filepath)   
    destination_path = directory.get_system_failure_path(source_path.name)
    
    storage.move(source_path, destination_path)
    
    send_system_failure_alert(event, directory, storage)
    

@with_logging_context
@with_infrastructure_safety(max_retries=3)
def handle_bad_file(
    event: BadFileDetected, 
    storage: AbstractFileStorageManager,
    directory: CustosDirectoryManager
    ):
    """Handles bad files (invalid MiME types, detected in staging.)"""
    source_path = Path(event.filepath)
    destination_path = directory.get_bad_file_path(source_path.name)
    
    storage.move(source_path, destination_path)
    

@with_logging_context
@with_infrastructure_safety(max_retries=3)
def handle_duplicate_file(
    event: DuplicateFileDetected, 
    storage: AbstractFileStorageManager,
    directory: CustosDirectoryManager
    ):
    """Handles Files detetcted as duplicates (at staging, prior to creation of file entity.)"""  
    
    source_path = Path(event.filepath)
    destination_path = directory.get_duplicate_file_path(source_path.name)
    
    storage.move(source_path, destination_path)
    
    
@with_logging_context
@with_infrastructure_safety(max_retries=3)    
def handle_schema_drift(
    event: SchemaDriftDetected, 
    uow_factory: Callable, 
    storage: AbstractFileStorageManager, 
    directory: CustosDirectoryManager, 
    registry: FileTypeRegistry
        ): 

    """Handles files where schema drift is detected (at auditing or validation.)"""
    
    source_path = Path(event.filepath)
    destination_path = directory.get_schema_failure_path(source_path.name)
    storage.move(source_path, destination_path)


    with uow_factory() as uow: 
        clean_up(event.file_id, uow, registry)
        file_entity = uow.files.get_file_by_id(event.file_id)
        file_entity.reset()
        file_entity.failure_schema(event.reason)
        uow.files.update(file_entity)
        uow.commit()
        
        
@with_logging_context
@with_infrastructure_safety(max_retries=3)        
def handle_processing_aborted(
    event: FileProcessingAborted, 
    uow_factory: Callable, 
    storage: AbstractFileStorageManager, 
    directory: CustosDirectoryManager, 
    registry: FileTypeRegistry
    ):
    """Handles a file whose processing was halted due to error."""

    
    source_path = Path(event.filepath)
    destination_path = directory.get_rejected_path(source_path.name)
    storage.move(source_path, destination_path)
    
    with uow_factory() as uow: 
        clean_up(event.file_id, uow, registry)
        file_entity = uow.files.get_file_by_id(event.file_id)
        file_entity.reset()
        file_entity.reject(event.reason if event.reason else None)
        uow.files.update(file_entity)
        uow.commit()
        
    
@with_logging_context
@with_infrastructure_safety(max_retries=3)      
def file_completed_handler(
    event: FileSuccessfullyProcessed, 
    uow_factory: Callable, 
    storage: AbstractFileStorageManager, 
    directory: CustosDirectoryManager
    ):
    """
    Handles a file that finished processing successfully 
    (i.e., finishes persisting either without any quarantined rows OR with quarantined
    rows of a number below the threshold for schema drift).
    """
    
    source_path = Path(event.filepath)
    
    with uow_factory() as uow:
        finished_file = uow.files.get_file_by_id(event.file_id)
        quarantined_count = finished_file.quarantined_rows
        if quarantined_count == 0:           
            destination_path = directory.get_clean_completed_path(source_path.name)
            storage.move(source_path, destination_path)
            finished_file.clean_processed()
            
        else: 
            destination_path = directory.get_quarantine_completed_path(source_path.name)
            storage.move(source_path, destination_path)
            finished_file.quarantine_processed()
        uow.files.update(finished_file)
        uow.commit()