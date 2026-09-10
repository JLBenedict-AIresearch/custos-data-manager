# tests.unit.adapters.test_background_runners

# run command: poetry run python -m pytest tests/unit/adapters/test_background_runners.py

from apscheduler.triggers.cron import CronTrigger
from pathlib import Path
from unittest.mock import MagicMock, patch
from watchdog.events import FileCreatedEvent, DirCreatedEvent

from src.infrastructure.adapters.apscheduler_runner import APSchedulerAdapter
from src.infrastructure.adapters.watchdog_runner import CSVFileHandler, WatchdogAdapter
from src.infrastructure.handlers.maintenance import handle_file_archiving, handle_quarantine_alerts
from src.pipeline.commands import AuditCSVCommand, StageFileCommand
from src.pipeline.events import BadFileDetected


def test_handler_ignores_directories():
    bus = MagicMock()
    handler = CSVFileHandler(bus)
    event = DirCreatedEvent(src_path="/fake/path/new_folder")
    
    handler.on_created(event)
    
    bus.handle.assert_not_called()

def test_handler_ignores_already_seen_files():
    bus = MagicMock()
    handler = CSVFileHandler(bus)
    event = FileCreatedEvent(src_path="/fake/path/data.csv")
    
    handler.seen_files.add(Path("/fake/path/data.csv"))
    
    handler.on_created(event)
    
    bus.handle.assert_not_called()

def test_handler_dispatches_bad_file_detected_for_non_csv():
    bus = MagicMock()
    handler = CSVFileHandler(bus)
    event = FileCreatedEvent(src_path="/fake/path/image.png")
    
    handler.on_created(event)
    
    bus.handle.assert_called_once()
    message = bus.handle.call_args[0][0]
    assert isinstance(message, BadFileDetected)
    assert message.filename == "image.png"

@patch("src.infrastructure.adapters.watchdog_runner.wait_for_file_ready", return_value=True)
def test_handler_dispatches_stage_command_when_file_ready(mock_wait, tmp_path):
    bus = MagicMock()
    handler = CSVFileHandler(bus)
    

    target_file = tmp_path / "leads_batch.csv"
    event = FileCreatedEvent(src_path=str(target_file))
    
    handler.on_created(event)
    
    mock_wait.assert_called_once_with(target_file)
    
    bus.handle.assert_called_once()
    command = bus.handle.call_args[0][0]
    assert isinstance(command, StageFileCommand)
    assert command.original_filepath == str(target_file)
    
    assert target_file in handler.seen_files

@patch("src.infrastructure.adapters.watchdog_runner.wait_for_file_ready", return_value=False)
def test_handler_aborts_if_file_lock_times_out(mock_wait, tmp_path):
    bus = MagicMock()
    handler = CSVFileHandler(bus)
    target_file = tmp_path / "locked_batch.csv"
    event = FileCreatedEvent(src_path=str(target_file))
    
    handler.on_created(event)
    
    bus.handle.assert_not_called()
    
@patch("src.infrastructure.adapters.watchdog_runner.Observer")
def test_watchdog_adapter_lifecycle(mock_observer_class):

    mock_observer_instance = MagicMock()
    mock_observer_class.return_value = mock_observer_instance
    
    bus = MagicMock()
    adapter = WatchdogAdapter(incoming_directory="/fake/incoming", message_bus=bus)
    
    # Test Start
    adapter.start()
    
    mock_observer_instance.schedule.assert_called_once()
    args, kwargs = mock_observer_instance.schedule.call_args
    assert isinstance(args[0], CSVFileHandler)
    assert args[1] == "/fake/incoming"
    assert kwargs.get("recursive") is False
    
    mock_observer_instance.start.assert_called_once()
    
    # Test Stop
    adapter.stop()
    
    mock_observer_instance.stop.assert_called_once()
    mock_observer_instance.join.assert_called_once()
    
@patch("src.infrastructure.adapters.apscheduler_runner.BackgroundScheduler")
def test_apscheduler_adapter_lifecycle_and_configuration(mock_scheduler_class):

    mock_scheduler_instance = MagicMock()
    mock_scheduler_class.return_value = mock_scheduler_instance
    
    bus = MagicMock()
    uow_factory = MagicMock()
    directory = MagicMock()
    storage = MagicMock()
    
    adapter = APSchedulerAdapter(
        incoming_directory="/fake/dir",
        bus=bus,
        uow_factory=uow_factory,
        directory=directory,
        storage=storage,
        interval_seconds=30
    )
    
    adapter.start()
    
    mock_scheduler_instance.start.assert_called_once()
    

    assert mock_scheduler_instance.add_job.call_count == 4
    

    add_job_calls = mock_scheduler_instance.add_job.call_args_list
    

    assert add_job_calls[0].args[0] == adapter._poll_directory
    assert add_job_calls[0].args[1] == 'interval'
    assert add_job_calls[0].kwargs['seconds'] == 30
    
    assert add_job_calls[1].args[0] == adapter.dispatch_pending_files

    archive_call = add_job_calls[2]
    assert archive_call.kwargs['func'] == handle_file_archiving
    assert isinstance(archive_call.kwargs['trigger'], CronTrigger)
    assert archive_call.kwargs['kwargs']['days_old'] == 30
    

    quarantine_call = add_job_calls[3]
    assert quarantine_call.kwargs['func'] == handle_quarantine_alerts
    assert quarantine_call.kwargs['kwargs']['schema_file_threshold'] == 5
    

    adapter.stop()
    mock_scheduler_instance.shutdown.assert_called_once()
    
def test_poll_directory_dispatches_new_files_and_ignores_seen(tmp_path):
    bus = MagicMock()
    adapter = APSchedulerAdapter(
        incoming_directory=str(tmp_path), 
        bus=bus, uow_factory=MagicMock(), directory=MagicMock(), storage=MagicMock()
    )
    
    file_1 = tmp_path / "batch_1.csv"
    file_1.touch()
    
    # First poll should detect it
    adapter._poll_directory()
    
    bus.handle.assert_called_once()
    command = bus.handle.call_args[0][0]
    assert isinstance(command, StageFileCommand)
    assert command.original_filepath == str(file_1)
    
    bus.handle.reset_mock()
    
    file_2 = tmp_path / "batch_2.csv"
    file_2.touch()
    
    adapter._poll_directory()
    
    bus.handle.assert_called_once()
    command = bus.handle.call_args[0][0]
    assert command.original_filepath == str(file_2)

    assert str(file_1) in adapter.seen_files
    assert str(file_2) in adapter.seen_files
    
def test_dispatch_pending_files_bypasses_if_system_is_busy():
    bus = MagicMock()
    uow_mock = MagicMock()
    uow_factory = MagicMock(return_value=uow_mock)
    uow_mock.__enter__.return_value = uow_mock
    
    uow_mock.files.check_for_busy_files.return_value = True
    
    adapter = APSchedulerAdapter(
        incoming_directory="/fake", bus=bus, uow_factory=uow_factory, directory=MagicMock(), storage=MagicMock()
    )
    
    adapter.dispatch_pending_files()
    
    uow_mock.files.get_oldest_pending_file.assert_not_called()
    bus.handle.assert_not_called()

def test_dispatch_pending_files_updates_and_dispatches_next_file():
    bus = MagicMock()
    uow_mock = MagicMock()
    uow_factory = MagicMock(return_value=uow_mock)
    uow_mock.__enter__.return_value = uow_mock
    
    uow_mock.files.check_for_busy_files.return_value = False
    
    mock_file = MagicMock()
    mock_file.id = 99
    mock_file.filepath = "/fake/data.csv"
    mock_file.filename = "data.csv"
    mock_file.assumed_type = "leads"
    mock_file.is_ambiguous = False
    mock_file.potential_types = []
    
    uow_mock.files.get_oldest_pending_file.return_value = mock_file
    
    mock_storage = MagicMock()
    mock_directory = MagicMock()
    mock_directory.incoming = Path("/fake")
    mock_directory.get_processing_path.return_value = "/fake/data.csv"
    
    adapter = APSchedulerAdapter(
        incoming_directory="/fake", bus=bus, uow_factory=uow_factory, directory=mock_directory, storage=mock_storage
    )
    
    adapter.dispatch_pending_files()
    
    mock_file.start_auditing.assert_called_once()
    uow_mock.files.update.assert_called_once_with(mock_file)
    uow_mock.commit.assert_called_once()
    
    bus.handle.assert_called_once()
    command = bus.handle.call_args[0][0]
    assert isinstance(command, AuditCSVCommand)
    assert command.file_id == 99
    assert command.filepath == "/fake/data.csv"