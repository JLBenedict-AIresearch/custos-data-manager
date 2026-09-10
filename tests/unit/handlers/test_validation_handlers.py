# tests.unit.handlers.test_validation_handlers

# run command: poetry run python -m pytest tests/unit/handlers/test_validation_handlers.py

from datetime import datetime, timezone
from pandas import Timestamp

from src.files.domain import FileStatus, File

from src.quarantine.domain import QuarantinedRow

from src.pipeline.handlers.validation import validate_data, handle_pydantic_failure, check_file_validation

from src.shared.messages import Message
from src.pipeline.commands import ValidateDataCommand, SaveValidatedDataCommand
from src.pipeline.events import PydanticAuditFailed, FileProcessingAborted, SchemaDriftDetected, BatchValidated
from src.shared.errors import DataValidationError, UnknownTypeError
from tests.fakes.fake_storage_manager import FakeFileStorageManager
from tests.fakes.fake_uow import FakeUnitOfWork
from tests.fakes import dummies



def test_validate_data_validates_correct_data(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"
    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )

        uow.files.add(file)  
        file.total_rows = 5      
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[1]],
        batch_number=1
    )

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # This should process these two rows into sales DTOS

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    dto_message = messages[0] if isinstance(messages[0], SaveValidatedDataCommand) else messages[1]      
    
    assert len(messages) == 2
    assert isinstance(messages[0], BatchValidated) or isinstance(messages[1], BatchValidated)
    assert dto_message is not None
    assert not quarantined
    assert file_entity.status == FileStatus.VALIDATING
    assert len(dto_message.payload) == 2


def test_validate_data_stops_if_file_finished(tmp_path, configured_registry):
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.FINISHING,

        )
 
        uow.files.add(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[1], sales_row_dicts[2]],
        batch_number=1
    )

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # The main validation block should not run and the script should return an empty list
    
    assert not messages
    

def test_validate_data_stops_if_batch_already_validated(tmp_path, configured_registry):
    
    fake_uow = FakeUnitOfWork()
    
    filepath = tmp_path / "sales.csv"

    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )

        uow.files.add(file)        
        file.expected_batches = {1, 2}
        file.validated_batches = {1}
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[2]],
        batch_number=1
    )

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    # The script should see that this batch has been processed, stop, and return an empty list -- no quarantined rows

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)

    assert not quarantined
    assert not messages
    assert file.status == FileStatus.AUDITING


def test_validate_data_recognizes_threshold(tmp_path, configured_registry):
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"
    
    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )
        
        uow.files.add(file)        
        file.total_rows = 5
        file.total_processed_rows = 2
        file.quarantined_rows = 1     
        file.expected_batches = {1, 2}
        file.validated_batches = {2}
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[1], sales_row_dicts[2]],
        batch_number=1
    )

    # the dict at index 2 should be quarantined, pushing the total number of quarantined rows over the threshold 
    # quarantined rows do not save if over threshold

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    assert file_entity.status == FileStatus.FINISHING
    assert not quarantined
    assert isinstance(messages[0], PydanticAuditFailed)


def test_validate_data_corrects_sku_format(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )
        
        uow.files.add(file)
        file.total_rows = 5
        file.total_processed_rows = 2
        file.quarantined_rows = 1
        uow.files.update(file)
        uow.commit()


    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[1], sales_row_dicts[3]],
        batch_number=1
    )

    # the sku format in index 3 should be fixed; all three should pass validation

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
        
    dto_message = messages[0] if isinstance(messages[0], SaveValidatedDataCommand) else messages[1]
    
    assert not quarantined
    assert file_entity.status == FileStatus.VALIDATING
    assert len(messages) == 2
    assert isinstance(messages[0], BatchValidated) or isinstance(messages[1], BatchValidated)
    assert len(dto_message.payload) == 3
    assert dto_message.payload[2].sku == "SAD_CLOWN_PTG"


def test_validate_data_corrects_phone_format(tmp_path, configured_registry):
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "leads.csv"

    leads_row_dicts = dummies.get_leads_dicts()

    with fake_uow as uow: 
        file = File(
        filename="leads.csv", 
        hashed_file="123", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=["leads"],
        status=FileStatus.AUDITING,

        )
        uow.files.add(file)
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="leads",
        payload=[leads_row_dicts[0], leads_row_dicts[2]],
        batch_number=1
    )

    # the phone number in index 2 should be fixed and both should pass validation

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    dto_message = messages[0] if isinstance(messages[0], SaveValidatedDataCommand) else messages[1]
    
    assert not quarantined
    assert file_entity.status == FileStatus.VALIDATING
    assert len(messages) == 2
    assert isinstance(messages[0], BatchValidated) or isinstance(messages[1], BatchValidated)
    assert dto_message is not None
    assert len(dto_message.payload) == 2
    assert dto_message.payload[1].phone == "8005556601"
    

def test_validate_data_catches_bad_customer_identifier(tmp_path, configured_registry):    
    
    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "sales.csv"

    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.AUDITING,

        )
          
        uow.files.add(file)
        file.total_rows = 5  
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales",
        payload=[sales_row_dicts[0], sales_row_dicts[1], sales_row_dicts[4]],
        batch_number=1
    )
    
    # the dict at index 4 should be quarantined for bad customer ID, leaving 2 DTOs returned
    
    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    dto_message = messages[0] if isinstance(messages[0], SaveValidatedDataCommand) else messages[1]
    
    assert len(quarantined) == 1
    assert quarantined[0].line_number == 6
    assert file_entity.status == FileStatus.VALIDATING
    assert len(messages) == 2
    assert isinstance(messages[0], BatchValidated) or isinstance(messages[1], BatchValidated)
    assert dto_message is not None
    assert len(dto_message.payload) == 2
    assert "Customer identifier must begin wtih 'CUST-' prefix." in quarantined[0].error_reason 
    
    
def test_validate_data_catches_bad_phone_format(tmp_path, configured_registry):

    fake_uow = FakeUnitOfWork()

    filepath = tmp_path / "leads.csv"

    leads_row_dicts = dummies.get_leads_dicts()

    with fake_uow as uow: 
        file = File(
        filename="leads.csv", 
        hashed_file="123", 
        assumed_type="leads", 
        is_ambiguous=False,
        potential_types=["leads"],
        status=FileStatus.AUDITING,

        )
        uow.files.add(file)
        file.total_rows = 5  
        file.expected_batches = {1, 2, 3}
        uow.files.update(file)
        uow.commit()

    command = ValidateDataCommand(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="leads",
        payload=[leads_row_dicts[0], leads_row_dicts[3]],
        batch_number=1
    )

    # the phone number at index 3 cannot be corrected and that row should be quarantined, leaving one DTO in the payload

    messages = validate_data(command=command, uow_factory=lambda: fake_uow, registry=configured_registry)

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    dto_message = messages[0] if isinstance(messages[0], SaveValidatedDataCommand) else messages[1]
    
    
    assert len(quarantined) == 1
    assert len(messages) == 2
    assert isinstance(messages[0], BatchValidated)
    assert file_entity.status == FileStatus.VALIDATING
    assert quarantined[0].line_number == 5
    assert len(dto_message.payload) == 1
    assert "Phone number has incorrect number of digits." in quarantined[0].error_reason
    

def test_handle_pydantic_failure_handles_failure(tmp_path):
    
    fake_uow = FakeUnitOfWork()
    
    filepath = tmp_path / "sales.csv"

    sales_row_dicts = dummies.get_sales_dicts()

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )
 
        uow.files.add(file)
        file.total_rows = 5

        
        quarantined_row = QuarantinedRow(
            file_id=1,
            assumed_type=file.assumed_type,
            raw_payload=sales_row_dicts[4],
            payload_hash="123",
            error_reason="Bad Customer ID",
            line_number=6,
            quarantined_at=datetime.now(timezone.utc)
        )
        file.add_quarantined_row()
        uow.files.update(file)
        uow.commit()
        

    event = PydanticAuditFailed(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        assumed_type="sales"
    )

# quarantined rows should be deleted, status should be FINISHING; schema drift detected event

    messages = handle_pydantic_failure(event=event, uow_factory=lambda: fake_uow)

    with fake_uow as uow: 
        file_entity = uow.files.get(1)
        quarantined = uow.quarantine.get(1)
    
    assert len(messages) == 1
    assert isinstance(messages[0], SchemaDriftDetected)
    assert not quarantined
    assert file_entity.status == FileStatus.FINISHING


def test_check_file_validation_updates_for_batch(tmp_path):
    
    fake_uow = FakeUnitOfWork()
    
    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)
        file.expected_batches = {1, 2}
        uow.files.update(file)
        uow.commit()
    
    event = BatchValidated(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
    )
    
    messages = check_file_validation(event=event, uow_factory=lambda: fake_uow)
    # This should do nothing besides updating the validated_batches; no status changes
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
    
    assert not messages
    assert file_entity.status == FileStatus.VALIDATING
    assert file_entity.validated_batches == {1}
    
        
def test_check_file_validation_updates_status(tmp_path):
    
    fake_uow = FakeUnitOfWork()
    
    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.VALIDATING,

        )

        uow.files.add(file)
        file.expected_batches = {1, 2}
        file.validated_batches = {2}
        uow.files.update(file)
        uow.commit()
        
    event = BatchValidated(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
    )
        
    messages = check_file_validation(event=event, uow_factory=lambda: fake_uow)
    # This should update the status AND the validated_batches
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)
    
    assert not messages
    assert file.status == FileStatus.PERSISTING
    assert file.validated_batches == {1, 2}
    
    
def test_check_file_validation_stops_if_file_finished(tmp_path):

    fake_uow = FakeUnitOfWork()
    
    filepath = tmp_path / "sales.csv"

    with fake_uow as uow: 
        file = File(
        filename="sales.csv", 
        hashed_file="123", 
        assumed_type="sales", 
        is_ambiguous=False,
        potential_types=["sales"],
        status=FileStatus.FINISHING,

        )

        uow.files.add(file)
        file.expected_batches = {1, 2}
        file.validated_batches = {2}
        uow.files.update(file)
        uow.commit()
        
    event = BatchValidated(
        file_id=1,
        filepath=filepath,
        filename=file.filename,
        batch_number=1
    )
    
    messages = check_file_validation(event=event, uow_factory=lambda: fake_uow)
    # This should not update validated_batches, not change the status, not do anything.
    
    with fake_uow as uow: 
        file_entity = uow.files.get(1)        
    
    assert not messages
    assert file.validated_batches == {2}
    assert file.status == FileStatus.FINISHING