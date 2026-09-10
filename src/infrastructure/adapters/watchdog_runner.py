# src.infrastructure.adapters.watchdog_runner

import os
import time
from pathlib import Path
from typing import Callable, Literal

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from src.infrastructure.adapters.message_bus import MessageBus
from src.infrastructure.logging import logger
from src.infrastructure.wrappers.system_check_wrapper import system_halt_check
from src.pipeline.commands import StageFileCommand
from src.pipeline.events import BadFileDetected
from src.shared.interfaces.message_bus_interface import AbstractMessageBus
from src.shared.interfaces.runner_interface import AbstractBackgroundRunner


def wait_for_file_ready(file_path: Path, timeout: int = 60) -> bool:
    """
    Waits until the OS releases the file lock. 
    Returns True if ready, False if it timed out.
    This keeps watchdog from barking incessantly while files download
    or triggering the pipeline prematurely.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Attempting to rename it to itself checks for OS-level write locks
            os.rename(file_path, file_path)
            return True
        except (PermissionError, OSError):
            time.sleep(1)
    return False

class CSVFileHandler(FileSystemEventHandler):
    def __init__(self, bus: AbstractMessageBus):
        self.bus = bus
        self.seen_files: set[Path] = set()

    @system_halt_check
    def on_created(self, event: FileSystemEvent):        
               
        if event.is_directory:
            return
        

        str_path = os.fsdecode(event.src_path)
        file_path = Path(str_path)
        
        if file_path in self.seen_files: 
            return
        self.seen_files.add(file_path)
        
        file_name = file_path.name
        
        if not str_path.endswith('.csv'):
            message = BadFileDetected(
                filepath=str_path,
                filename=file_name
            )
            self.bus.handle(message)
            return
        
        if wait_for_file_ready(file_path):
            command = StageFileCommand(original_filepath=str(file_path))
            # NB -- no "try/except" here because @with_infrastructure_safety decorator for individual handlers manages exceptions
            self.bus.handle(command)                
        else:
            logger.error("file_lock_timeout", file_name=file_path.name)
            
            
class WatchdogAdapter(AbstractBackgroundRunner):
    def __init__(self, incoming_directory: str, message_bus: AbstractMessageBus):
        super().__init__(incoming_directory, message_bus)
        self.observer = Observer()

    def start(self):
        handler = CSVFileHandler(self.bus)
        self.observer.schedule(handler, self.incoming_directory, recursive=False)
        self.observer.start()
        
    def stop(self):
        self.observer.stop()
        self.observer.join()