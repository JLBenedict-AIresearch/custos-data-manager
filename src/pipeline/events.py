# src.shared.events


from dataclasses import dataclass

from src.shared.messages import DomainEvent

@dataclass(frozen=True, kw_only=True)
class BadFileDetected(DomainEvent):
    filepath: str
    filename: str
    
    
@dataclass(frozen=True, kw_only=True)
class BatchProcessed(DomainEvent):
    file_id: int
    filepath: str
    filename: str
    batch_number: int

    
@dataclass(frozen=True, kw_only=True)
class BatchValidated(DomainEvent):
    file_id: int
    filepath: str
    filename: str
    batch_number: int


@dataclass(frozen=True, kw_only=True)
class DuplicateFileDetected(DomainEvent):
    filepath: str
    filename: str

        
@dataclass(frozen=True, kw_only=True)
class FileProcessingAborted(DomainEvent):
    """Triggers the handler to move the file to data/retry/ or data/failed/"""
    file_id: int | None
    filepath: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class FileStaged(DomainEvent):
    filepath: str
    filename: str
    assumed_type: str
    potential_types: list | None
    is_ambiguous: bool 


@dataclass(frozen=True, kw_only=True)
class FileSuccessfullyProcessed(DomainEvent):
    file_id: int
    filepath: str
    filename: str
  
    
@dataclass(frozen=True, kw_only=True)
class PandasAuditFailed(DomainEvent):
    """More than 20% of the file's CSV lines were missing required fields based on type."""
    file_id: int
    filepath: str
    filename: str
    original_assumed_type: str
    assumed_type: str
    potential_types: list | None
    is_ambiguous: bool
    attempted_types: list


@dataclass(frozen=True, kw_only=True)
class PydanticAuditFailed(DomainEvent):
    """More than 20% of the file's rows failed validation checks."""
    file_id: int 
    filepath: str
    filename: str
    assumed_type: str
    
    
@dataclass(frozen=True, kw_only=True)
class SchemaDriftDetected(DomainEvent):
    """The data departs by over 20% from any known schema for the database."""
    file_id: int
    filepath: str
    filename: str
    assumed_type: str
    reason: str


@dataclass(frozen=True, kw_only=True)
class SystemFaultEvent(DomainEvent):
    file_id: int | None
    filename: str
    filepath: str
    error_type: str
    message: str
            




