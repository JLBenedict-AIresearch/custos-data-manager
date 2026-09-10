# src.pipeline.handlers.persistence

from datetime import datetime, timezone
from typing import Callable, Sequence

import structlog

from src.files.domain import FileStatus
from src.infrastructure.file_registry import FileTypeRegistry
from src.infrastructure.logging import log_domain_error
from src.infrastructure.wrappers.safety_wrappers import (
    with_infrastructure_safety,
    with_logging_context,
)
from src.pipeline.commands import SaveValidatedDataCommand
from src.pipeline.events import (
    BatchProcessed,
    FileProcessingAborted,
    FileSuccessfullyProcessed,
)
from src.shared.errors import (
    RequiresAdditionalArgsError,
    ResourceNotFoundError,
    SchemaCorruptionError,
    WrongTypeError,
)
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.messages import Command, DomainEvent, Message

logger = structlog.get_logger(__name__)



@with_logging_context
@with_infrastructure_safety(max_retries=3)
def persist_to_database(
    command: SaveValidatedDataCommand, 
    uow_factory: Callable, 
    registry: FileTypeRegistry
    ) -> Sequence[Message]:
    

    config = registry.get(command.assumed_type)
        
    with uow_factory() as uow:
        file_entity = uow.files.get(command.file_id)
                
        wrong_statuses = {
            FileStatus.FINISHING, 
            FileStatus.PROCESSED_CLEAN,
            FileStatus.PROCESSED_W_QUARANTINE,
            FileStatus.FAILURE_SCHEMA,
            FileStatus.REJECTED,
            FileStatus.SYSTEM_FAULT
        }
        
        if file_entity.status in wrong_statuses:
            return []
        
        elif command.batch_number in file_entity.completed_batches:
            return []
        
        else: 
            file_entity.persist()
            uow.files.update(file_entity)
       
        
        if not hasattr(uow, config.repo_name):
            domain_error = ResourceNotFoundError("NotFound", f"UoW missing repository: {config.repo_name}")
            log_domain_error(domain_error, assumed_type=command.assumed_type)
            return [FileProcessingAborted(
                file_id=command.file_id, 
                filepath=command.filepath,
                reason=f"No repository found for {command.assumed_type}"
            )]
            
        target_repo = getattr(uow, config.repo_name)
        seen_in_batch = set()
        custos_timestamp = datetime.now(timezone.utc)
        
        for dto in command.payload:
            missing_fields = []
            fields_to_check = [config.id_fields] if isinstance(config.id_fields, str) else config.id_fields
            
            for field in fields_to_check:
                if not hasattr(dto, field):
                    missing_fields.append(field)
            

            if missing_fields:
                domain_error = SchemaCorruptionError(
                    message=f"DTO {type(dto).__name__} is missing ID fields: {missing_fields}"
                )
                log_domain_error(domain_error, file_id=command.file_id)
                return [FileProcessingAborted(
                                    file_id=command.file_id,
                                    filepath=command.filepath, 
                                    reason=domain_error.message
                                )]

            if isinstance(config.id_fields, tuple):
                entity_id = tuple(getattr(dto, field) for field in config.id_fields)
            else:
                entity_id = getattr(dto, config.id_fields)  
                
                        
            try: 
                exists = target_repo.check_exists(entity_id)
                
            except RequiresAdditionalArgsError as e: 
                log_domain_error(e)
                return [FileProcessingAborted(
                        file_id=command.file_id,
                        filepath=command.filepath, 
                        reason=e.message
                    )]
            except WrongTypeError as e: 
                log_domain_error(e)
                return [FileProcessingAborted(
                        file_id=command.file_id,
                        filepath=command.filepath, 
                        reason=e.message
                    )]
    
            if not exists and config.allows_updates: 
                args = config.helper(command.file_id, custos_timestamp=custos_timestamp, dto=dto)                
                target_repo.add(*args)
                entity = args[0]                # this is true for our current updatable entity, Lead
                entity.apply_update(
                    source_file_id=command.file_id, 
                    custos_timestamp=custos_timestamp,
                    incoming_data=dto                    
                    )
                target_repo.update(entity)
            
            elif not exists and entity_id not in seen_in_batch and not config.allows_updates:
                args = config.helper(command.file_id, dto)                
                target_repo.add(*args)
            
            elif (exists or entity_id in seen_in_batch) and not config.allows_updates:
                pass
                        
            # TODO for v.2 -- elif exists and not config.allows_updates: 
            # save the "divergent duplicate" as a new type of Quarantined Row
            # with the ORM object id of its counterpart that exists in the database.
            # i.e. there shouldn't be two "FactSale" records that have the same transaction id and product SKU
            # but which differ on other attributes; this would require manual review.
            
            
            elif exists and config.allows_updates:
                entity = target_repo.get(entity_id)
                entity.apply_update(
                    source_file_id=command.file_id, 
                    incoming_data=dto, 
                    custos_timestamp=custos_timestamp
                )
                target_repo.update(entity)

            seen_in_batch.add(entity_id)
            
        num_rows = len(command.payload)
        file_entity.process_row_success(num_rows)   
        uow.files.update(file_entity) 
        uow.commit()
        
    return [BatchProcessed(
        file_id=command.file_id, 
        filepath=command.filepath, 
        filename=command.filename, 
        batch_number=command.batch_number
        )]


@with_logging_context
@with_infrastructure_safety(max_retries=3)
def check_file_completion(
    event: BatchProcessed, 
    uow_factory: Callable,
    ) -> Sequence[Message]:
    """Checks if the processed batch was the last one expected for the particular file,"""
    with uow_factory() as uow:
        file_entity = uow.files.get(event.file_id)             

        finished_statuses = {
            FileStatus.FINISHING,
            FileStatus.PROCESSED_CLEAN,
            FileStatus.PROCESSED_W_QUARANTINE,
            FileStatus.FAILURE_SCHEMA,
            FileStatus.REJECTED,
            FileStatus.SYSTEM_FAULT,
        }
        if file_entity.status not in finished_statuses:
            file_entity.completed_batches.add(event.batch_number)
        if file_entity.completed_batches == file_entity.expected_batches and file_entity.status not in finished_statuses:            
            file_entity.finish()  
            return [FileSuccessfullyProcessed(
                file_id=event.file_id,
                filepath=event.filepath,
                filename=event.filename
            )]

        uow.files.update(file_entity)
        uow.commit()
        
    return []


