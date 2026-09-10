# src.pipeline.handlers.auditing

import json
from datetime import datetime, timezone
from typing import Callable, Sequence

import pandas as pd
import structlog

from src.infrastructure.file_registry import FileTypeRegistry
from src.infrastructure.utils import calculate_row_hash_from_dict
from src.infrastructure.wrappers.safety_wrappers import (
    with_infrastructure_safety,
    with_logging_context,
)
from src.pipeline.commands import AuditCSVCommand, ValidateDataCommand
from src.pipeline.events import PandasAuditFailed, SchemaDriftDetected
from src.quarantine.domain import QuarantinedRow
from src.shared.errors import UnknownTypeError
from src.shared.messages import Message

logger = structlog.get_logger(__name__)


@with_logging_context
@with_infrastructure_safety(max_retries=3)
def audit_csv(
    command: AuditCSVCommand, 
    uow_factory: Callable, 
    registry: FileTypeRegistry
    ) -> Sequence[Message]:
    """
    Handles all pure data cleansing; does preparatory audit of data. 
    """
    df = pd.read_csv(command.filepath)
    df.columns = df.columns.astype(str)
    
    df["csv_line_number"] = df.index + 2
    data_columns = [col for col in df.columns if col != "csv_line_number"]
    
    df = df.dropna(how="all", subset=data_columns)
    processable_rows = len(df)
        
    config = registry.get(command.assumed_type)
    
    required_cols = config.required_fields   
    try:          
        invalid_mask = df[list(config.required_fields)].isna().any(axis=1)
    
    except KeyError as e:
        return [PandasAuditFailed(
            file_id=command.file_id,
            filepath=command.filepath,
            filename=command.filename,       
            original_assumed_type=command.original_assumed_type,
            assumed_type=command.assumed_type,
            potential_types=command.potential_types, 
            is_ambiguous=command.is_ambiguous,
            attempted_types=command.attempted_types
        )
    ]
    
    if config.requires_timestamp: 
    
        created_at = {"created_at", "Created_at", "Created_At", "CreatedAt"}
        updated_at = {"modified_at", "Modified_At", "Modified_at", "ModifiedAt", "updated_at", "Updated_at", "Updated_At", "UpdatedAt"}
    
        created_fields = [col for col in df.columns if col in created_at]
        updated_fields = [col for col in df.columns if col in updated_at]
    
        if len(created_fields) > 1 or len(updated_fields) > 1:
            
            return [SchemaDriftDetected(
            file_id=command.file_id, 
            filename=command.filename, 
            filepath=command.filepath, 
            assumed_type=command.original_assumed_type,
            reason="Extra timestamp fields."          
        )]

        elif len(created_fields) == 0 and len(updated_fields) == 0:
            return [SchemaDriftDetected(
            file_id=command.file_id, 
            filename=command.filename, 
            filepath=command.filepath, 
            assumed_type=command.original_assumed_type,
            reason="Missing required timestamp field(s) for file."          
        )]

        if created_fields:
            created_str = str(created_fields[0])
            df["Created_At"] = pd.to_datetime(df[created_str], errors="coerce")  
        else: 
            updated_str = str(updated_fields[0])            
            df["Created_At"] = pd.to_datetime(df[updated_str], errors="coerce")
        if updated_fields: 
            updated_str = str(updated_fields[0])
            df["Modified_At"] = pd.to_datetime(df[updated_str], errors="coerce")
        else: 
            df["Modified_At"] = df["Created_At"]
            
        df["incoming_timestamp"] = df["Modified_At"].fillna(df["Created_At"])
        anomalous_timeline_mask = df["Modified_At"] < df["Created_At"]        
        missing_dates_mask = df["incoming_timestamp"].isnull() 
        
        combined_invalid_mask = invalid_mask | anomalous_timeline_mask | missing_dates_mask
                
        
    else: 
        combined_invalid_mask = invalid_mask
        
    quarantined_df = df[combined_invalid_mask]
    valid_df = df[~combined_invalid_mask]
    
    total_complete_lines = len(valid_df)
    total_naughty_lines = len(quarantined_df)
    processable_rows = len(df)
    
    
    # Sad Path: more than 20% of actual lines failed initial audit
    if total_naughty_lines > (processable_rows / 5):    

        return [PandasAuditFailed(
            file_id=command.file_id,
            filepath=command.filepath,
            filename=command.filename,       
            original_assumed_type=command.original_assumed_type,
            assumed_type=command.assumed_type,
            potential_types=command.potential_types, 
            is_ambiguous=command.is_ambiguous,
            attempted_types=command.attempted_types
        )
    ]
        
    # Happy Path: at least 80% of actual lines pass the initial audit.
    else: 

        clean_quarantined_df = quarantined_df[data_columns].astype(object).where(
            pd.notnull(quarantined_df[data_columns]), None
        )
        quarantined_records = clean_quarantined_df.to_dict(orient="records")
        line_numbers = quarantined_df["csv_line_number"].tolist()

        
        with uow_factory() as uow: 
            file_entity = uow.files.get_file_by_id(command.file_id)
            file_entity.total_rows = processable_rows
                                
            if total_naughty_lines > 0:
                file_entity.add_quarantined_row(total_naughty_lines)

            for index, (line_num, row_dict) in enumerate(zip(line_numbers, quarantined_records)):
                safe_row_dict = json.loads(json.dumps(row_dict, default=str))
                quarantine_record = QuarantinedRow(
                    file_id=command.file_id,
                    assumed_type=command.assumed_type,
                    raw_payload=safe_row_dict,   
                    payload_hash=calculate_row_hash_from_dict(row_dict),          
                    error_reason="Missing required data", 
                    line_number=line_num, 
                    quarantined_at=datetime.now(timezone.utc)
                )
                uow.quarantine.add(quarantine_record)                

                # Batch processing
                if (index + 1) % 1000 == 0:
                    uow.files.update(file_entity)
                    uow.commit()


            uow.files.update(file_entity)
            uow.commit()


            datetime_columns = valid_df.select_dtypes(include=['datetime64', 'datetimetz']).columns
            for col in datetime_columns:
                valid_df[col] = valid_df[col].dt.strftime('%Y-%m-%dT%H:%M:%SZ')
                
            clean_valid_df = valid_df.astype(object).where(pd.notnull(valid_df), None)
               
            valid_records = clean_valid_df.to_dict(orient="records")
            
            CHUNK_SIZE = int(config.batch_size) if config.batch_size else 1000  # Adjust based on memory and Pydantic performance and your own needs
            commands = []
            
            for index, i in enumerate(range(0, len(valid_records), CHUNK_SIZE)):
                batch = valid_records[i:i + CHUNK_SIZE]
                batch_number = index + 1
                
                commands.append(ValidateDataCommand(
                    file_id=command.file_id,
                    filepath=command.filepath,
                    filename=command.filename,
                    assumed_type=command.assumed_type,
                    payload=batch, 
                    batch_number=batch_number
                ))
                
                file_entity.expected_batches.add(batch_number)
            file_entity.validate()
            uow.files.update(file_entity)
            uow.commit()
        
    return commands  
      
@with_logging_context
@with_infrastructure_safety(max_retries=3)
def attempt_retry(
    event: PandasAuditFailed, 
    uow_factory: Callable
    ) -> Sequence[Message]:
    """Sets up a retry in the weird case that a csv field had a preliminary match to multiple schemas."""
    
    with uow_factory() as uow: 
        current_file = uow.files.get_file_by_id(event.file_id)              
        if event.is_ambiguous and event.potential_types: 
            tried_set = set(event.attempted_types)
            trial_set = set(event.potential_types)
            tried_set.add(event.assumed_type)
            trial_set.discard(event.assumed_type)
            new_assumed_type = next((t for t in trial_set if t not in tried_set), None)
            
            if new_assumed_type: 
                current_file.retry()
                uow.files.update(current_file)
                uow.commit()
                
                return [AuditCSVCommand(
                    file_id=event.file_id, 
                    filename=event.filename, 
                    filepath=event.filepath, 
                    original_assumed_type=event.original_assumed_type, 
                    assumed_type=new_assumed_type,
                    potential_types=list(trial_set),
                    is_ambiguous=event.is_ambiguous,
                    attempted_types=list(tried_set)
                )]
            else:   
                current_file.finish()
                uow.files.update(current_file)
                uow.commit()

                return [SchemaDriftDetected(
                    file_id=event.file_id, 
                    filename=event.filename, 
                    filepath=event.filepath, 
                    assumed_type=event.original_assumed_type,  
                    reason="Ambiguously typed data failed Pandas audit for all potential types."        
                )]
            
        else: 
            current_file.finish()
            uow.files.update(current_file)
            uow.commit()
            return [SchemaDriftDetected(
                file_id=event.file_id, 
                filename=event.filename, 
                filepath=event.filepath, 
                assumed_type=event.assumed_type,  
                reason=f"Pandas audit failed for unambiguously typed data: {event.assumed_type}."        
            )]
        

