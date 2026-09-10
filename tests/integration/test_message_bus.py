# tests.integration.test_message_bus

# run command: poetry run python -m pytest tests/integration/test_message_bus.py

import pytest
from src.infrastructure.adapters.message_bus import MessageBus 

from src.shared.errors import CustosSystemError, DiskFullError
from src.pipeline.commands import Command
from src.pipeline.events import DomainEvent, SystemFaultEvent
from tests.fakes.fake_messages import FakeCommand, FakeEvent, FaultingCommand, SurvivingCommand
    
def test_command_handler_raising_custos_error_produces_system_fault_event():
    bus = MessageBus()
    
    def failing_handler(command):
        raise DiskFullError("disk is full", original_error=None)
    
    bus.register_command(FakeCommand, failing_handler)
    
    seen_events = []
    bus.subscribe_event(SystemFaultEvent, lambda e: seen_events.append(e) or [])
    
    bus.handle(FakeCommand())
    
    assert len(seen_events) == 1
    assert seen_events[0].file_id == 1


def test_command_handler_raising_unexpected_error_propagates():
    bus = MessageBus()
    
    def buggy_handler(command):
        raise RuntimeError("this is a an actual bug, not a system fault")
    
    bus.register_command(FakeCommand, buggy_handler)
    
    with pytest.raises(RuntimeError):
        bus.handle(FakeCommand())


def test_event_handler_failure_does_not_block_other_handlers():
    bus = MessageBus()
    ran = {"first": False, "second": False}
    
    def failing_handler(event):
        ran["first"] = True
        raise RuntimeError("boom")
    
    def working_handler(event):
        ran["second"] = True
        return []
    
    bus.subscribe_event(FakeEvent, failing_handler)
    bus.subscribe_event(FakeEvent, working_handler)
    
    bus.handle(FakeEvent())
    
    assert ran["first"] is True
    assert ran["second"] is True 



def test_system_fault_purges_pending_messages_for_same_file():
    bus = MessageBus()
    processed = []
    
    def kickoff_handler(command):

            return [
                FaultingCommand(),  # file id 1, same as the initial command
                SurvivingCommand(), # file id 2
            ]

    def faulting_handler(command):

        return [SystemFaultEvent(
            file_id=1, filename="a.csv", filepath="a.csv",
            error_type="Test", message="fault"
        )]

    def surviving_handler(command):
        processed.append(command)
        return []

    bus.register_command(FakeCommand, kickoff_handler)
    bus.register_command(FaultingCommand, faulting_handler)
    bus.register_command(SurvivingCommand, surviving_handler)

    bus.handle(FakeCommand())

    # file 2's command should have run normally, but file 1's commands get purged
    assert len(processed) == 1
    assert processed[0].file_id == 2