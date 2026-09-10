import time
from src.bootstrap.bootstrapper import bootstrap_bus, bootstrap_registry
from src.bootstrap.dependencies import get_uow
from src.infrastructure.adapters.apscheduler_runner import APSchedulerAdapter
from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.adapters.watchdog_runner import WatchdogAdapter
from src.infrastructure.directory import CustosDirectoryManager


def main():
    
    directory = CustosDirectoryManager()
    storage_manager = CustosFileStorageManager()
    uow_factory = get_uow
    registry = bootstrap_registry()
    bus = bootstrap_bus(uow_factory=get_uow, directory=directory, storage_manager=storage_manager, registry=registry)
    
    watchdog_incoming_dir: str = "./data/incoming/leads"
    ap_scheduler_incoming_dir: str = "./data/incoming/sales"
    
    watcher = WatchdogAdapter(
        incoming_directory=watchdog_incoming_dir,
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=ap_scheduler_incoming_dir,
        bus=bus,
        uow_factory=uow_factory, 
        directory=directory, 
        storage=storage_manager,
        interval_seconds=60 # Or whatever interval you prefer
    )
          
    watcher.start()
    scheduler.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
       
        watcher.stop()
        scheduler.stop()
        

if __name__ == "__main__":
    main()