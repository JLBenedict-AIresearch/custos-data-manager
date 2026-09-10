# src.pipeline.handlers.staging.py

from pathlib import Path
from typing import Callable

import structlog

from src.bootstrap.dependencies import get_uow
from src.files.domain import File, FileStatus
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.file_registry import FileTypeRegistry
from src.infrastructure.logging import log_domain_error
from src.infrastructure.wrappers.safety_wrappers import (
    with_infrastructure_safety,
    with_logging_context,
)
from src.pipeline.commands import AuditCSVCommand, StageFileCommand
from src.pipeline.events import (
    BadFileDetected,
    DuplicateFileDetected,
    FileProcessingAborted,
    FileStaged,
)
from src.shared.errors import EmptyFileError
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.messages import Message

logger = structlog.get_logger(__name__)



@with_logging_context
@with_infrastructure_safety(max_retries=3)
def stage_file(
    command: StageFileCommand, 
    registry: FileTypeRegistry,
    storage: AbstractFileStorageManager, 
    directory: CustosDirectoryManager
    ) -> list[Message]:
    """Moves the file from 'incoming' to a matching subfolder in 'processing'."""
    source_path = Path(command.original_filepath)
    ostensible_type = source_path.parent.name 
    
    destination_path = directory.get_processing_path(source_path.name)

    storage.move(source_path, destination_path)    

    new_path = str(destination_path)
    acceptable_mime = storage.validate_csv_mime(new_path)
    
    if acceptable_mime: 
        try:
            headers = storage.check_headers_for_type(destination_path)
        except StopIteration as e:
            domain_error =  EmptyFileError(f"File {new_path} is empty") 
            log_domain_error(domain_error)
            return [FileProcessingAborted(
                file_id=None, 
                filepath=str(destination_path),
                reason="File is empty"
            )]
    
        assumed_type = registry.identify_from_headers(ostensible_type, headers) 
        if isinstance (assumed_type, tuple):
            potential_types = assumed_type[1]
            assumed_type = assumed_type[0]
        else: 
            potential_types = None
        config = registry.get(assumed_type) 
                

        return [FileStaged(
            filepath=str(destination_path), 
            filename=source_path.name,
            assumed_type=assumed_type, 
            potential_types=potential_types,
            is_ambiguous=True if potential_types else False
        )]

    return [BadFileDetected(
    filepath=str(destination_path),
    filename=str(destination_path.name)        
)]



@with_logging_context    
@with_infrastructure_safety(max_retries=3)
def file_staged_handler(
        event: FileStaged, 
        uow_factory: Callable, 
        storage: AbstractFileStorageManager
    ) -> list[Message]:
    """Reacts to a new file landing in the processing folder. Fast and non-blocking."""
    
    actual_path = Path(event.filepath)
    file_hash = storage.get_file_hash(actual_path)
      
    with uow_factory() as uow:
        existing_file = uow.files.check_exists(file_hash)
        
        if existing_file: 
            return [DuplicateFileDetected(
                filepath=event.filepath, 
                filename=event.filename
            )]          
            
        
        types = event.potential_types
        if not types: 
            types = []
            types.append(event.assumed_type)
        
        new_file = File(
            filename=event.filename,
            hashed_file=file_hash,
            assumed_type=event.assumed_type,
            is_ambiguous=event.is_ambiguous, 
            potential_types=types,
            status=FileStatus.PENDING 
        )            
                
        uow.files.add(new_file)
        uow.commit() 
        
    return []

    

