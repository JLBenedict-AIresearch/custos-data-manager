# src.files.domain

from datetime import datetime, timezone
from enum import Enum

from src.pipeline.events import DomainEvent


class FileStatus(str, Enum):
    
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    AUDITING = "AUDITING"
    RETRYING = "RETRYING"
    VALIDATING = "VALIDATING"
    PERSISTING = "PERSISTING"
    FINISHING = "FINISHING"
    
    PROCESSED_CLEAN = "PROCESSED_CLEAN"
    PROCESSED_W_QUARANTINE = "PROCESSED_WITH_QUARANTINE"
    FAILURE_SCHEMA = "FAILURE_SCHEMA"
    REJECTED = "REJECTED"
    SYSTEM_FAULT = "SYSTEM_FAULT"
    

class File: 
    def __init__(
        self, 
        filename: str, 
        hashed_file: str, 
        assumed_type: str, 
        is_ambiguous: bool,
        potential_types: list[str],
        status: FileStatus,
        created_at: datetime | None = None,
        processing_begun: datetime | None = None
        ):
        
        self.filename = filename   
        self.hashed_file = hashed_file
        self.assumed_type = assumed_type     
        self.is_ambiguous = is_ambiguous      
        self.potential_types = potential_types
        self.status = status
        self.status_reason: str | None = None
        
        self.id: int | None = None
        
        self.created_at = created_at if created_at else None
        self.processing_begun = processing_begun if processing_begun else None
        self.processing_finished: datetime | None = None    
        self.total_rows = 0
        self.total_processed_rows: int = 0 
        self.quarantined_rows: int = 0
        self.expected_batches: set[int] = set()
        self.validated_batches: set[int] = set()
        self.completed_batches: set[int] = set()
        
        self.events: list[DomainEvent] = []
        
    def __eq__(self ,other: object) -> bool: 
        if not isinstance(other, type(self)):
            return False
        if not self.hashed_file or not other.hashed_file:
            return False
        return self.hashed_file == other.hashed_file
    
    def __hash__(self): 
        return hash(self.hashed_file)
    
    
    def start_processing(self): 
        self.status = FileStatus.PROCESSING
        self.processing_begun = datetime.now(timezone.utc)
    
    def start_auditing(self):
        self.status = FileStatus.AUDITING
        
    def validate(self): 
        self.status = FileStatus.VALIDATING
    
    def retry(self): 
        self.status = FileStatus.RETRYING
        
    def persist(self):
        self.status = FileStatus.PERSISTING
        
    def finish(self): 
        self.status = FileStatus.FINISHING        
    
    def reject(self, reason: str | None):
        self.status = FileStatus.REJECTED
        self.status_reason = reason if reason else "Unknown"
        self.processing_finished = datetime.now(timezone.utc)
    
    def failure_schema(self, reason: str | None = None):
        self.status = FileStatus.FAILURE_SCHEMA
        self.status_reason = reason if reason else "Schema drift detected"
        self.processing_finished = datetime.now(timezone.utc)
        
    def quarantine_processed(self): 
        self.status = FileStatus.PROCESSED_W_QUARANTINE
        self.status_reason = f"Completed with {self.quarantined_rows} of {self.total_rows} rows quarantined"
        self.processing_finished = datetime.now(timezone.utc)
    
    def clean_processed(self):
        self.status = FileStatus.PROCESSED_CLEAN
        self.status_reason = f"""Success! {self.total_rows} rows persisted.""" 
        self.processing_finished = datetime.now(timezone.utc)
    
    def system_fault(self, reason: str | None):
        self.status = FileStatus.SYSTEM_FAULT
        self.status_reason = reason 
        
    
    def update_total_rows(self, total_rows: int):
        self.total_rows = total_rows
    
    def process_row_success(self, num_rows: int | None = None):
        """
        Log a count of rows that resulted in the creation and commission of a domain object to the database.
        
        This method is used only when a row is successfully added to the database
        as a normal entity/object but NOT as a QuarantinedRow object"""
        
        self.total_processed_rows += num_rows if num_rows else 1
           
    
    def add_quarantined_row(self, num_rows: int | None = None): 
        
        self.quarantined_rows += num_rows if num_rows else 1
        self.total_processed_rows += num_rows if num_rows else 1
        if self.quarantined_rows > self.total_rows / 5: 
            self.failure_schema()
            
            
    def reset(self): 
        """
        Reset row counts for the File entity following schema drift detection and database purge of associated records.
        
        This is used to undo a specific count of quarantined rows and all total processed rows 
        for a file if the schema drift threshold is reached.
        The file is marked as a schema failure, the particular quarantined row objects 
        and entity objects from this particular file are all deleted from the database, 
        to ensure atomicity and because data provenance and integrity are questionable."""
        
        self.quarantined_rows = 0
        self.total_processed_rows = 0

        
