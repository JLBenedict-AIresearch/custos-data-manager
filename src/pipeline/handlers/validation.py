# src.pipeline.handlers.validation

import json
import math
import structlog
from datetime import datetime, timezone
from typing import Sequence, Callable

from pydantic import BaseModel, ValidationError

from src.files.domain import FileStatus
from src.infrastructure.file_registry import FileTypeRegistry
from src.infrastructure.logging import log_domain_error
from src.infrastructure.utils import calculate_row_hash_from_dict
from src.infrastructure.wrappers.safety_wrappers import with_infrastructure_safety, with_logging_context
from src.pipeline.commands import ValidateDataCommand, SaveValidatedDataCommand
from src.pipeline.events import PydanticAuditFailed, SchemaDriftDetected, BatchValidated
from src.quarantine.domain import QuarantinedRow
from src.shared.errors import DataValidationError
from src.shared.messages import Message

logger = structlog.get_logger(__name__)

@with_logging_context
@with_infrastructure_safety(max_retries=2)
def validate_data(
    command: ValidateDataCommand, 
    uow_factory: Callable,
    registry: FileTypeRegistry
    ) -> Sequence[Message]:
    
    custos_timestamp = datetime.now(timezone.utc)
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
        
        elif command.batch_number in file_entity.validated_batches:
            return []
        
        else: 
            file_entity.validate()
            uow.files.update(file_entity)
            uow.commit()
    
    valid_dtos = []
    quarantined_records = []
    
    config = registry.get(command.assumed_type)
    required_id_fields = (
    (config.id_fields,) 
    if isinstance(config.id_fields, str) 
    else tuple(config.id_fields)
)              
    
    alias_map = {
        field_name: field_info.alias or field_name
        for field_name, field_info in config.schema.model_fields.items()
    } 
    
    for row_dict in command.payload:
        line_num = row_dict.pop("csv_line_number") 
        missing_fields = []

        for field in required_id_fields:
                csv_column_name = alias_map.get(field, field)
                val = row_dict.get(csv_column_name)
                
                if (
                    csv_column_name not in row_dict
                    or val is None
                    or (isinstance(val, str) and not val.strip())
                    or (isinstance(val, float) and math.isnan(val))
                ):

                    missing_fields.append(field)
                    
        if missing_fields: 
            q_record = QuarantinedRow(
            file_id=command.file_id,
            assumed_type=command.assumed_type,
            raw_payload=row_dict,
            payload_hash=calculate_row_hash_from_dict(row_dict),
            error_reason=f"Missing fields: {missing_fields}",
            line_number=line_num,
            quarantined_at=datetime.now(timezone.utc)
        )
            quarantined_records.append(q_record)
            continue
            
        try: 
            
            clean_data = config.schema(**row_dict)
            dto = config.data(**clean_data.model_dump())
            valid_dtos.append(dto)
                
        except ValidationError as e: 
            domain_error = DataValidationError(original_error=e, raw_data=row_dict)
            error_reason_json = json.dumps(domain_error.validation_details)
            log_domain_error(domain_error)
            
            q_record = QuarantinedRow(
                file_id=command.file_id,
                assumed_type=command.assumed_type,
                raw_payload=row_dict,
                payload_hash=calculate_row_hash_from_dict(row_dict),
                error_reason=error_reason_json,
                line_number=line_num,
                quarantined_at=datetime.now(timezone.utc)
            )
            quarantined_records.append(q_record)                    

    with uow_factory() as uow:
        file_entity = uow.files.get(command.file_id)
        
        projected_quarantine_total = file_entity.quarantined_rows + len(quarantined_records)
        
        # if the threshold will be surpassed, we don't save the quarantined records from this batch.
        if projected_quarantine_total > (file_entity.total_rows / 5):
            file_entity.finish()    
            uow.files.update(file_entity)
            uow.commit()
            return [PydanticAuditFailed(
                file_id=command.file_id,
                filepath=command.filepath, 
                filename=command.filename,
                assumed_type=command.assumed_type,
            )]
            
        if quarantined_records:
            for record in quarantined_records:
                uow.quarantine.add(record)
                    
            file_entity.add_quarantined_row(len(quarantined_records))         
   
        # If the file hasn't transgressed the schema drift threshold, it's OK to commit the quarantined rows
        uow.files.update(file_entity)
        uow.commit()
        
    messages = []
    messages.append(BatchValidated(
                file_id=command.file_id,
                filepath=command.filepath,
                filename=command.filename,
                batch_number=command.batch_number
            ))
    
    if valid_dtos:

        messages.append(SaveValidatedDataCommand(
            file_id=command.file_id,
            filepath=command.filepath,
            filename=command.filename,
            assumed_type=command.assumed_type,
            payload=valid_dtos, 
            batch_number=command.batch_number
        ))

    return messages

@with_logging_context
@with_infrastructure_safety(max_retries=3)
def handle_pydantic_failure(event: PydanticAuditFailed, uow_factory: Callable) -> Sequence[Message]:
    with uow_factory() as uow: 
        uow.quarantine.delete(event.file_id)

        file_entity = uow.files.get(event.file_id)
        if file_entity: 
            file_entity.finish()
            uow.files.update(file_entity)
        uow.commit()
    
    return [SchemaDriftDetected(
        file_id=event.file_id, 
        filepath=event.filepath,
        filename=event.filename,
        assumed_type=event.assumed_type, 
        reason="Pydantic Audit Failed"
    )]
    
@with_logging_context
@with_infrastructure_safety(max_retries=3)
def check_file_validation(
    event: BatchValidated, 
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
            file_entity.validated_batches.add(event.batch_number)
        if file_entity.validated_batches == file_entity.expected_batches and file_entity.status not in finished_statuses:            
            file_entity.persist()  
            uow.files.update(file_entity)
            uow.commit()
            
        uow.files.update(file_entity)
        uow.commit()
        
    return []

