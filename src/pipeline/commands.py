# src.shared.commands

from dataclasses import dataclass
from pathlib import Path

from src.shared.messages import Command


@dataclass(frozen=True, kw_only=True)
class AbortFileProcessingCommand(Command):
    file_id: int
    filpath: str
    filename: str
    reason: str
    assumed_type: str
    
@dataclass(frozen=True, kw_only=True)
class AuditCSVCommand(Command):
    file_id: int
    filepath: str
    filename: str
    original_assumed_type: str
    assumed_type: str
    potential_types: list | None
    is_ambiguous: bool
    attempted_types: list
    
    
@dataclass(frozen=True, kw_only=True)
class SaveValidatedDataCommand(Command):
    file_id: int
    filepath: str
    filename: str
    assumed_type: str
    payload: list[object]
    batch_number: int    
    
    
@dataclass(frozen=True, kw_only=True)
class StageFileCommand(Command):
    """Command to physically move a file out of the incoming directory."""
    original_filepath: str
        
    
@dataclass(frozen=True, kw_only=True)
class ValidateDataCommand(Command): 
    file_id: int
    filepath: str
    filename: str
    assumed_type: str
    payload: list[dict]
    batch_number: int
    


