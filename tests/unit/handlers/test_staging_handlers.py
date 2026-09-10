# tests.unit.handlers.test_staging_handlers

# run command: poetry run python -m pytest tests/unit/handlers/test_staging_handlers.py

from pathlib import Path
from src.files.domain import File, FileStatus
from src.infrastructure.directory import CustosDirectoryManager
from src.pipeline.commands import StageFileCommand
from src.pipeline.events import FileStaged, FileProcessingAborted, DuplicateFileDetected, BadFileDetected
from src.pipeline.handlers.staging import stage_file, file_staged_handler
from tests.fakes.fake_file_repository import FakeFileRepository
from tests.fakes.fake_uow import FakeUnitOfWork
from tests.fakes.fake_storage_manager import FakeFileStorageManager 


def test_stage_file_identifies_sales_correctly(tmp_path, configured_registry):

    fake_storage = FakeFileStorageManager()
    dir_manager = CustosDirectoryManager(base_dir=tmp_path)
    
    source_file = Path("data/incoming/sales/daily_batch.csv")
    fake_storage.known_files.add(source_file)
    
    expected_dest = dir_manager.get_processing_path("daily_batch.csv")
    fake_storage.mock_mimes[str(expected_dest)] = True
    
    # We use the exact aliases from your Pydantic schema
    fake_storage.mock_headers[str(expected_dest)] = [
        "SKU_Code", "Product_Name", "Category", "Customer_ID", 
        "Region", "Industry", "Quantity", "Revenue", 
        "Transaction_Date", "Transaction_ID"
    ]
    
    command = StageFileCommand(original_filepath=str(source_file))

    messages = stage_file(
        command=command, 
        registry=configured_registry, 
        storage=fake_storage, 
        directory=dir_manager
    )

    assert len(messages) == 1
    assert isinstance(messages[0], FileStaged)
    assert messages[0].filename == "daily_batch.csv"
    assert messages[0].assumed_type == "sales"
    
    
def test_stage_file_catches_ambiguous_type(tmp_path, configured_registry):
    fake_storage = FakeFileStorageManager()
    dir_manager = CustosDirectoryManager(base_dir=tmp_path)
    
    source_file = Path("data/incoming/sales/daily_batch.csv")
    fake_storage.known_files.add(source_file)
    
    expected_dest = dir_manager.get_processing_path("daily_batch.csv")
    fake_storage.mock_mimes[str(expected_dest)] = True
    
    # We use the exact aliases from your Pydantic schema
    fake_storage.mock_headers[str(expected_dest)] = [
        "SKU_Code", "Product_Name", "Lead_Score", "Category", "Customer_ID", 
        "Region", "Industry", "Quantity", "Revenue", 
        "Transaction_Date", "Transaction_ID"
    ]
    
    command = StageFileCommand(original_filepath=str(source_file))

    messages = stage_file(
        command=command, 
        registry=configured_registry, 
        storage=fake_storage, 
        directory=dir_manager
    )
    
    assert len(messages) == 1
    assert isinstance(messages[0], FileStaged)
    assert messages[0].assumed_type == "sales"
    assert messages[0].is_ambiguous == True
    assert len(messages[0].potential_types) == 2
    assert "sales" in messages[0].potential_types
    assert "leads" in messages[0].potential_types
    

def test_stage_file_catches_empty_file(tmp_path, configured_registry):
    fake_storage = FakeFileStorageManager()
    dir_manager = CustosDirectoryManager(base_dir=tmp_path)
    
    source_file = Path("data/incoming/sales/daily_batch.csv")
    fake_storage.known_files.add(source_file)
    
    expected_dest = dir_manager.get_processing_path("daily_batch.csv")
    fake_storage.mock_mimes[str(expected_dest)] = True
    
    fake_storage.mock_headers[str(expected_dest)] = []
      
    command = StageFileCommand(original_filepath=str(source_file))
    

    messages = stage_file(
        command=command, 
        registry=configured_registry, 
        storage=fake_storage, 
        directory=dir_manager
        )
    
    assert len(messages) == 1
    assert isinstance(messages[0], FileProcessingAborted)
    assert messages[0].reason == "File is empty"
    
def test_stage_file_catches_bad_file(tmp_path, configured_registry):
    fake_storage = FakeFileStorageManager()
    dir_manager = CustosDirectoryManager(base_dir=tmp_path)
    
    source_file = Path("data/incoming/sales/evil_batch.csv")
    fake_storage.known_files.add(source_file)
    
    expected_dest = dir_manager.get_processing_path("evil_batch.csv")
    fake_storage.mock_mimes[str(expected_dest)] = False
    command = StageFileCommand(original_filepath=str(source_file))
    
    messages = stage_file(
        command=command, 
        registry=configured_registry, 
        storage=fake_storage, 
        directory=dir_manager
        )
    
    assert len(messages) == 1
    assert isinstance(messages[0], BadFileDetected)
    assert messages[0].filename == "evil_batch.csv"

def test_stage_file_catches_misplaced_faile(tmp_path, configured_registry):
    
    fake_storage = FakeFileStorageManager()
    dir_manager = CustosDirectoryManager(base_dir=tmp_path)
    
    source_file = Path("data/incoming/leads/daily_batch.csv")
    fake_storage.known_files.add(source_file)
    
    expected_dest = dir_manager.get_processing_path("daily_batch.csv")
    fake_storage.mock_mimes[str(expected_dest)] = True
    
    # We use the exact aliases from your Pydantic schema
    fake_storage.mock_headers[str(expected_dest)] = [
        "SKU_Code", "Product_Name", "Category", "Customer_ID", 
        "Region", "Industry", "Quantity", "Revenue", 
        "Transaction_Date", "Transaction_ID"
    ]
    
    command = StageFileCommand(original_filepath=str(source_file))

    messages = stage_file(
        command=command, 
        registry=configured_registry, 
        storage=fake_storage, 
        directory=dir_manager
    )

    assert len(messages) == 1
    assert isinstance(messages[0], FileStaged)
    assert messages[0].assumed_type == "sales"
    assert messages[0].is_ambiguous == False
    assert messages[0].potential_types is None


def test_file_staged_handler_returns_duplicate_event():
    fake_storage = FakeFileStorageManager()
    fake_uow = FakeUnitOfWork()
    
    test_path = Path("data/processing/duplicate.csv")
    file_hash = "existing_hash_123"

    fake_storage.known_files.add(test_path)
    fake_storage.mock_hashes[test_path] = file_hash
    
    existing_file = File(
        filename="duplicate.csv",
        hashed_file=file_hash,
        assumed_type="sales",
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.PENDING
    )
    fake_uow.files.add(existing_file)
    
    event = FileStaged(
        filepath=str(test_path),
        filename="duplicate.csv",
        assumed_type="sales",
        potential_types=None,
        is_ambiguous=False
    )

    messages = file_staged_handler(
        event=event, 
        uow_factory=lambda: fake_uow, 
        storage=fake_storage
    )

    assert len(messages) == 1
    assert isinstance(messages[0], DuplicateFileDetected)
    assert messages[0].filename == "duplicate.csv"
    
def test_file_staged_handler_saves_new_file_and_commits():

    fake_storage = FakeFileStorageManager()
    fake_uow = FakeUnitOfWork() 
    
    test_path = Path("data/processing/new_batch.csv")
    file_hash = "new_hash_456"
    
    fake_storage.known_files.add(test_path)
    fake_storage.mock_hashes[test_path] = file_hash
    
    event = FileStaged(
        filepath=str(test_path),
        filename="new_batch.csv",
        assumed_type="sales",
        potential_types=None, 
        is_ambiguous=False
    )

    messages = file_staged_handler(
        event=event, 
        uow_factory=lambda: fake_uow, 
        storage=fake_storage
    )


    assert len(messages) == 0  # No failure events emitted
    assert fake_uow.committed is True  # Verify uow.commit() was called
    

    saved_file = fake_uow.files.get_file_by_hash(file_hash)
    
    assert saved_file is not None
    assert saved_file.filename == "new_batch.csv"
    assert saved_file.status == FileStatus.PENDING

    assert saved_file.potential_types == ["sales"]
    