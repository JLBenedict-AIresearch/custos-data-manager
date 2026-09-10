# src.infrastructure.handlers.maintenance

from datetime import datetime
from pathlib import Path
import time
from typing import Callable

from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.logging import logger
from src.infrastructure.wrappers.safety_wrappers import (
    with_infrastructure_safety,
    with_logging_context,
)
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager


@with_logging_context
@with_infrastructure_safety(max_retries=3)
def handle_file_archiving(
    directory_manager: CustosDirectoryManager, 
    storage_manager: AbstractFileStorageManager, 
    days_old: int = 30
) -> None:
    """Scans completed and failure directories for old files and zips them into cold storage."""
    

    current_time = time.time()
    cutoff_time = current_time - (days_old * 86400) # 86400 seconds in a day

    target_directories = [
        directory_manager.completed_clean,
        directory_manager.completed_quarantine,
        directory_manager.bad_files,
        directory_manager.duplicate_files,
        directory_manager.rejected
    ]

    files_to_archive = []

    for dir_path in target_directories:
        if dir_path.exists():
            for filepath in dir_path.iterdir():
                if filepath.is_file() and filepath.stat().st_mtime < cutoff_time:
                    files_to_archive.append(filepath)

    if files_to_archive:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = directory_manager.cold_storage / f"archive_{timestamp_str}.zip"
        
        storage_manager.archive_files(
            file_paths=files_to_archive, 
            archive_destination=archive_name
        )

@with_logging_context
@with_infrastructure_safety(max_retries=3)       
def handle_quarantine_alerts(
    directory_manager: CustosDirectoryManager, 
    uow_factory, 
    schema_file_threshold: int = 5, 
    db_row_threshold: int = 1000
    ) -> None:
    """Alerts administrators if manual data intervention is required."""
    
    schema_dir = directory_manager.schema_failure
    if schema_dir.exists():
        file_count = sum(1 for item in schema_dir.iterdir() if item.is_file())
        
        if file_count >= schema_file_threshold:
            logger.warning(
                "schema_drift_alert", 
                message=f"Human intervention required: {file_count} files in schema_failure folder.",
                file_count=file_count
            )

    with uow_factory() as uow:
        total_quarantined_rows = uow.quarantine.count_all() 
        
        if total_quarantined_rows >= db_row_threshold:
            logger.warning(
                "quarantine_db_alert", 
                message=f"Human intervention required: {total_quarantined_rows} records isolated.",
                row_count=total_quarantined_rows
            )