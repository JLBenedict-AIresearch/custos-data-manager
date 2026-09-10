# tests.e2e.test_leads_end_to_end

# run command: poetry run python -m pytest -s -v tests/e2e/test_leads_end_to_end.py


import pytest
import shutil
import time

from src.files.domain import FileStatus
from src.infrastructure.adapters.apscheduler_runner import APSchedulerAdapter
from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.adapters.watchdog_runner import WatchdogAdapter
from src.infrastructure.directory import CustosDirectoryManager
from src.bootstrap.bootstrapper import bootstrap_bus


def test_watchdog_processes_perfect_leads(    
    tmp_path, 
    write_good_leads_csv, 
    real_uow_factory, 
    test_registry  
    ): 
    
    directory = CustosDirectoryManager(tmp_path)
    directory.setup_directories()
    storage_manager = CustosFileStorageManager()
    
    bus = bootstrap_bus(
    uow_factory=real_uow_factory, 
    registry=test_registry,
    storage_manager=storage_manager,
    directory=directory
)    
    
    temp_path = tmp_path     
    leads_incoming = directory.incoming / "leads"
    leads_incoming.mkdir(parents=True, exist_ok=True)
    
    watcher = WatchdogAdapter(
        incoming_directory=str(leads_incoming),
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=str(directory.incoming / "sales"),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    scheduler.start()
    watcher.start()
    
    try:

        filename = "perfect_leads.csv"
        test_file = write_good_leads_csv(filename=filename, row_count=50, include_errors=False)
        shutil.move(temp_path / filename, leads_incoming / filename)

        expected_path = directory.completed_clean / filename
        
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)
            
        assert file_done is True, "Pipeline timed out; Leads file never reached archive."
        
        with real_uow_factory() as uow: 
            file = uow.files.get(1)
            leads = uow.leads.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
        
        assert file.status == FileStatus.PROCESSED_CLEAN
        assert file.total_rows == 50
        assert file.total_processed_rows == 50
        assert file.quarantined_rows == 0
        assert len(leads) == 50
        assert not quarantine   
    finally:
        watcher.stop()
        scheduler.stop()


def test_watchdog_processes_leads_w_quarantine(    
    tmp_path, 
    write_good_leads_csv, 
    real_uow_factory, 
    test_registry  
    ): 
    
    directory = CustosDirectoryManager(tmp_path)
    directory.setup_directories()
    storage_manager = CustosFileStorageManager()
    
    bus = bootstrap_bus(
    uow_factory=real_uow_factory, 
    registry=test_registry,
    storage_manager=storage_manager,
    directory=directory
)    
    
    temp_path = tmp_path     
    leads_incoming = directory.incoming / "leads"
    leads_incoming.mkdir(parents=True, exist_ok=True)
    
    watcher = WatchdogAdapter(
        incoming_directory=str(leads_incoming),
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=str(directory.incoming / "sales"),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    scheduler.start()
    watcher.start()
    
    try:

        filename = "acceptable_leads.csv"
        test_file = write_good_leads_csv(filename=filename, row_count=50, include_errors=True)
        shutil.move(temp_path / filename, leads_incoming / filename)

        expected_path = directory.completed_quarantine / filename
        
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; Leads file never reached archive."
        
        with real_uow_factory() as uow: 
            file = uow.files.get(1)
            leads = uow.leads.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
        
        assert file.status == FileStatus.PROCESSED_W_QUARANTINE
        assert file.total_rows == 50
        assert file.total_processed_rows == 50
        assert file.quarantined_rows == 4
        assert len(leads) == 46
        assert len(quarantine) == 4  
        
        
    finally:
        watcher.stop()
        scheduler.stop()


def test_watchdog_processes_tricky_leads(    
    tmp_path, 
    write_tricky_leads_csv, 
    real_uow_factory, 
    test_registry  
    ): 
    
    directory = CustosDirectoryManager(tmp_path)
    directory.setup_directories()
    storage_manager = CustosFileStorageManager()
    
    bus = bootstrap_bus(
    uow_factory=real_uow_factory, 
    registry=test_registry,
    storage_manager=storage_manager,
    directory=directory
)    
    
    temp_path = tmp_path     
    leads_incoming = directory.incoming / "leads"
    leads_incoming.mkdir(parents=True, exist_ok=True)
    
    watcher = WatchdogAdapter(
        incoming_directory=str(leads_incoming),
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=str(directory.incoming / "sales"),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    scheduler.start()
    watcher.start()
    
    try:

        filename = "tricky_leads.csv"
        test_file = write_tricky_leads_csv(filename=filename, row_count=50, include_errors=True)
        shutil.move(temp_path / filename, leads_incoming / filename)

        expected_path = directory.completed_quarantine / filename
        
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)
            
        assert file_done is True, "Pipeline timed out; Leads file never reached archive."
        
        with real_uow_factory() as uow: 
            file = uow.files.get(1)
            leads = uow.leads.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
        
        assert file.status == FileStatus.PROCESSED_W_QUARANTINE
        assert file.total_rows == 50
        assert file.total_processed_rows == 50
        assert file.quarantined_rows == 4
        assert len(leads) == 46
        assert len(quarantine) == 4  

        
    finally:
        watcher.stop()
        scheduler.stop()
        
        
def test_watchdog_processes_failing_leads(    
    tmp_path, 
    write_failing_leads_csv, 
    real_uow_factory, 
    test_registry  
    ): 
    
    directory = CustosDirectoryManager(tmp_path)
    directory.setup_directories()
    storage_manager = CustosFileStorageManager()
    
    bus = bootstrap_bus(
    uow_factory=real_uow_factory, 
    registry=test_registry,
    storage_manager=storage_manager,
    directory=directory
)    
    
    temp_path = tmp_path     
    leads_incoming = directory.incoming / "leads"
    leads_incoming.mkdir(parents=True, exist_ok=True)
    
    watcher = WatchdogAdapter(
        incoming_directory=str(leads_incoming),
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=str(directory.incoming / "sales"),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    scheduler.start()
    watcher.start()
    
    try:

        filename = "failing_leads.csv"
        test_file = write_failing_leads_csv(filename=filename, row_count=50)
        shutil.move(temp_path / filename, leads_incoming / filename)

        expected_path = directory.schema_failure / filename
        
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)
            
        assert file_done is True, "Pipeline timed out; Leads file never reached archive."
        
        with real_uow_factory() as uow: 
            file = uow.files.get(1)
            leads = uow.leads.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
        
        assert file.status == FileStatus.FAILURE_SCHEMA
        assert file.total_rows == 50
        assert file.total_processed_rows == 0
        assert file.quarantined_rows == 0
        assert not leads
        assert "Pydantic" in file.status_reason
        
    finally:
        watcher.stop()
        scheduler.stop()


def test_watchdog_adds_lead_updates(
    tmp_path, 
    write_update_leads_csv, 
    real_uow_factory, 
    test_registry  
    ): 
    
    directory = CustosDirectoryManager(tmp_path)
    directory.setup_directories()
    storage_manager = CustosFileStorageManager()
    
    bus = bootstrap_bus(
    uow_factory=real_uow_factory, 
    registry=test_registry,
    storage_manager=storage_manager,
    directory=directory
)    
    
    temp_path = tmp_path     
    leads_incoming = directory.incoming / "leads"
    leads_incoming.mkdir(parents=True, exist_ok=True)
    
    watcher = WatchdogAdapter(
        incoming_directory=str(leads_incoming),
        message_bus=bus
    )
    scheduler = APSchedulerAdapter(
        incoming_directory=str(directory.incoming / "sales"),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    scheduler.start()
    watcher.start()
    
    try:

        filename = "leads_with_updates.csv"
        test_file, emails, originals = write_update_leads_csv(filename=filename, row_count=25)
        shutil.move(temp_path / filename, leads_incoming / filename)

        expected_path = directory.completed_clean / filename
        
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)
            
        assert file_done is True, "Pipeline timed out; Leads file never reached archive."
        
        with real_uow_factory() as uow: 
            file = uow.files.get(1)
            leads = uow.leads.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)            

            assert file.status == FileStatus.PROCESSED_CLEAN
            assert file.total_rows == 30
            assert file.total_processed_rows == 30
            assert file.quarantined_rows == 0
            assert len(leads) == 25
            assert not quarantine
            
            updated_leads = []
            
            for original in originals:
                updated_lead = uow.leads.get(original["Email_Address"])
                updated_leads.append(updated_lead)
                assert len(updated_lead.updates) == 2       # the original base lead counts as an "update"
                assert original["Job_Title"] != updated_lead.position
                assert original["Lead_Score"] != updated_lead.score
            assert len(updated_leads) == 5

    finally:
        watcher.stop()
        scheduler.stop()
 
