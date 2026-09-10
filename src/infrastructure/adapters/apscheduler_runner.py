# src.infrastructure.adapters.apscheduler_runner

import os
from pathlib import Path
from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bootstrap.dependencies import get_uow
from src.infrastructure.directory import CustosDirectoryManager
from src.infrastructure.handlers.maintenance import handle_file_archiving, handle_quarantine_alerts
from src.infrastructure.logging import logger
from src.infrastructure.wrappers.system_check_wrapper import system_halt_check
from src.pipeline.commands import StageFileCommand, AuditCSVCommand
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.interfaces.message_bus_interface import AbstractMessageBus
from src.shared.interfaces.runner_interface import AbstractBackgroundRunner


class APSchedulerAdapter(AbstractBackgroundRunner):
    def __init__(
        self, 
        incoming_directory: str, 
        bus: AbstractMessageBus,         
        uow_factory: Callable, 
        directory: CustosDirectoryManager,
        storage: AbstractFileStorageManager,
        interval_seconds: int = 60, 
        
    ):

        super().__init__(incoming_directory, bus) 
        self.scheduler = BackgroundScheduler()
        self.interval_seconds = interval_seconds
        self.seen_files: set[str] = set()
        
        self.bus = bus
        self.uow_factory = uow_factory
        self.directory = directory
        self.storage = storage


    def start(self):
        """Schedules the directory polling job and starts the scheduler."""
        self.scheduler.add_job(
            self._poll_directory, 
            'interval', 
            seconds=self.interval_seconds,
            max_instances=1
        )
        self.scheduler.add_job(
            self.dispatch_pending_files,
            'interval',
            seconds=self.interval_seconds,
            max_instances=1
        )
        
        self.scheduler.add_job(
            func=handle_file_archiving,
            trigger=CronTrigger(hour=2, minute=0), 
            kwargs={
                "directory_manager": self.directory,
                "storage_manager": self.storage,
                "days_old": 30
            },
            id="nightly_file_archiver",
            name="Archive files older than 30 days",
            replace_existing=True
        )

        self.scheduler.add_job(
            func=handle_quarantine_alerts,
            trigger=CronTrigger(hour=8, minute=0), 
            kwargs={
                "directory_manager": self.directory,
                "uow_factory": self.uow_factory,
                "schema_file_threshold": 5,
                "db_row_threshold": 500
            },
            id="daily_quarantine_alerts",
            name="Check for excessive quarantined data",
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("scheduler_started", directory=self.incoming_directory)


    def stop(self):
        """Gracefully shuts down the listener."""
        self.scheduler.shutdown(wait=True)
        logger.info("scheduler_stopped")


    @system_halt_check
    def _poll_directory(self):
        """Scans the directory for CSVs and queues them for staging."""        
        
        target_path = Path(self.incoming_directory)
        if not target_path.exists():
            return

        for filepath in target_path.glob("*.csv"):
            str_path = str(filepath)
            if str_path in self.seen_files: 
                continue
            else: 
                self.seen_files.add(str_path)
                logger.info("file_detected_by_scheduler", file_name=filepath.name)
                command = StageFileCommand(original_filepath=str(filepath))
                # NB: infrastrcture safety wrapper for individual pipeline handlers takes care of exceptions
                self.bus.handle(command)


    @system_halt_check
    def dispatch_pending_files(self):
        """Runs on a timer via APScheduler to drip-feed files into the pipeline."""        
            
        with self.uow_factory() as uow:

            if uow.files.check_for_busy_files():
                return 

            next_file = uow.files.get_oldest_pending_file()
            if not next_file:
                return 
                
            next_file.start_auditing()
            uow.files.update(next_file)
            uow.commit()
            
            command = AuditCSVCommand(
                file_id=next_file.id,
                filepath=str(self.directory.get_processing_path(next_file.filename)), 
                filename=next_file.filename,
                original_assumed_type=next_file.assumed_type,
                assumed_type=next_file.assumed_type,
                is_ambiguous=next_file.is_ambiguous,
                potential_types=next_file.potential_types,                
                attempted_types=[]
                )

        self.bus.handle(command)


 
                
    



