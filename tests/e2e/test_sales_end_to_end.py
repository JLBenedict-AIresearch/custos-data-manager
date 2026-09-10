# tests.e2e.test_sales_end_to_end

# run command: poetry run python -m pytest tests/e2e/test_sales_end_to_end.py

import pytest
import shutil
import time

from src.files.domain import FileStatus
from src.infrastructure.adapters.apscheduler_runner import APSchedulerAdapter
from src.infrastructure.adapters.file_storage_manager import CustosFileStorageManager
from src.infrastructure.directory import CustosDirectoryManager
from src.bootstrap.bootstrapper import bootstrap_bus

def test_apscheduler_processes_perfect_file(
    tmp_path, 
    write_good_sales_csv, 
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

    filename = "perfect_sales.csv"
    test_file = write_good_sales_csv(filename=filename, row_count=50, include_errors=False)
    incoming_dir = directory.incoming / "sales"
    expected_path = directory.get_clean_completed_path(filename)

    adapter = APSchedulerAdapter(
        incoming_directory=str(incoming_dir),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    adapter.start()
    
    try:
        timeout = 60.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."
        
        with real_uow_factory() as uow:
            file = uow.files.get(1)
            sales = uow.sales.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
            
        assert file is not None
        assert file.status == FileStatus.PROCESSED_CLEAN
        assert file.total_rows == 50
        assert file.total_processed_rows == 50
        assert file.quarantined_rows == 0
        assert not quarantine
        assert len(sales) == 50
                    
    finally:

        adapter.stop()
        
def test_apscheduler_processes_file_w_quarantine(
    tmp_path, 
    write_good_sales_csv, 
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

    filename = "acceptable_sales.csv"
    test_file = write_good_sales_csv(filename=filename, row_count=50, include_errors=True)
    incoming_dir = directory.incoming / "sales"
    expected_path = directory.get_quarantine_completed_path(filename)

    adapter = APSchedulerAdapter(
        incoming_directory=str(incoming_dir),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    adapter.start()
    
    try:
        timeout = 60.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."
        
        with real_uow_factory() as uow:
            file = uow.files.get(1)
            sales = uow.sales.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
            
        assert file is not None
        assert file.status == FileStatus.PROCESSED_W_QUARANTINE
        assert file.total_rows == 50
        assert file.total_processed_rows == 50
        assert file.quarantined_rows == 4
        assert len(quarantine) == 4
        assert len(sales) == 46
                    
    finally:

        adapter.stop()

        
def test_apscheduler_processes_tricky_sales(
    tmp_path, 
    write_tricky_sales_csv, 
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

    filename = "tricky_sales.csv"
    test_file = write_tricky_sales_csv(filename=filename, row_count=50)
    incoming_dir = directory.incoming / "sales"
    expected_path = directory.get_clean_completed_path(filename)

    adapter = APSchedulerAdapter(
        incoming_directory=str(incoming_dir),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    adapter.start()
    
    try:
        timeout = 30.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."
        
        with real_uow_factory() as uow:
            file = uow.files.get(1)
            sales = uow.sales.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
            
        assert file is not None
        assert file.status == FileStatus.PROCESSED_CLEAN
        assert file.total_rows == 54
        assert file.total_processed_rows == 54
        assert file.quarantined_rows == 0
        assert not quarantine
        assert len(sales) == 50     # 4 rows are duplicates and should be ignored
                    
    finally:
        adapter.stop()
        
def test_apscheduler_fails_bad_sales(
    tmp_path, 
    write_failing_sales_csv, 
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

    filename = "failure_sales.csv"
    test_file = write_failing_sales_csv(filename=filename, row_count=50)
    incoming_dir = directory.incoming / "sales"
    expected_path = directory.get_schema_failure_path(filename)

    adapter = APSchedulerAdapter(
        incoming_directory=str(incoming_dir),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    adapter.start()
    
    try:
        timeout = 60.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."
        
        with real_uow_factory() as uow:
            file = uow.files.get(1)
            sales = uow.sales.get_by_source_file(1)
            quarantine = uow.quarantine.get_by_source_file(1)
            
        assert file is not None
        assert file.status == FileStatus.FAILURE_SCHEMA
        assert "Pandas" in file.status_reason
        assert file.total_rows == 0
        assert file.total_processed_rows == 0
        assert file.quarantined_rows == 0
        assert not quarantine
        assert not sales
                    
    finally:

        adapter.stop()
        
def test_apscheduler_processes_duplicate_file(
    tmp_path, 
    write_good_sales_csv, 
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

    filename = "perfect_sales.csv"
    test_file = write_good_sales_csv(filename=filename, row_count=50, include_errors=False)
    incoming_dir = directory.incoming / "sales"
    expected_path = directory.get_clean_completed_path(filename)

    adapter = APSchedulerAdapter(
        incoming_directory=str(incoming_dir),
        bus=bus,
        uow_factory=real_uow_factory,
        directory=directory,
        storage=storage_manager,
        interval_seconds=1
    )
    adapter.start()
    
    try:
        timeout = 60.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."
        
        dupe_path = directory.incoming / "sales" / "duplicate_sales.csv"
        shutil.move(expected_path, dupe_path)
        expected_dupe_path = directory.get_duplicate_file_path("duplicate_sales.csv")
        
        timeout = 60.0
        start_time = time.time()
        file_done = False
        
        while time.time() - start_time < timeout:
            if expected_dupe_path.exists():
                file_done = True
                break
            time.sleep(0.5)

        assert file_done is True, "Pipeline timed out; file never reached destination."

        assert (directory.duplicate_files / "duplicate_sales.csv").exists()
                    
    finally:
        adapter.stop()