# tests.fakes.fake_messages

from dataclasses import dataclass
from src.shared.messages import Command, DomainEvent

# --- Fake Messages ---

class FakeCommand(Command):
    file_id: int = 1
    filename: str = "test.csv"
    filepath: str = "test.csv"

class FakeEvent(DomainEvent):
    file_id: int = 1
    
# =-- Particular Fake Messages --- #

class FaultingCommand(FakeCommand) :
    """Makes a system fault"""
    file_id=1

class SurvivingCommand(FakeCommand):
    file_id=2