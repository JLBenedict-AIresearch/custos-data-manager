# src.infrastructure.directory

from pathlib import Path


class CustosDirectoryManager:
    def __init__(self, base_dir: str | Path = "data"):
        self.base_dir = Path(base_dir)
        
        # Add any other "zones" you want in your pipeline here.
        self.incoming = self.base_dir / "incoming"
        self.processing = self.base_dir / "processing"
        self.bad_files = self.base_dir / "bad_files"
        self.duplicate_files = self.base_dir / "duplicate_files"
        self.schema_failure = self.base_dir / "schema_failure"
        self.completed_quarantine = self.base_dir / "quarantine"
        self.completed_clean = self.base_dir / "archive"
        self.system_failure = self.base_dir / "system_failure"
        self.rejected = self.base_dir / "rejected"
        self.cold_storage = self.base_dir / "cold_storage"
        self.outgoing_alerts = self.base_dir / "outgoing_alerts"
        

    def setup_directories(self) -> None:
        """Creates all necessary directories if they don't exist."""
        self.incoming.mkdir(parents=True, exist_ok=True)
        self.processing.mkdir(parents=True, exist_ok=True)
        self.bad_files.mkdir(parents=True, exist_ok=True)
        self.duplicate_files.mkdir(parents=True, exist_ok=True)
        self.schema_failure.mkdir(parents=True, exist_ok=True)        
        self.completed_quarantine.mkdir(parents=True, exist_ok=True)
        self.completed_clean.mkdir(parents=True, exist_ok=True)
        self.system_failure.mkdir(parents=True, exist_ok=True)
        self.rejected.mkdir(parents=True, exist_ok=True)
        self.cold_storage.mkdir(parents=True, exist_ok=True)
        self.outgoing_alerts.mkdir(parents=True, exist_ok=True)

    # Helper methods
    
    def get_incoming_path(self, type: str, filename: str) -> Path: 
        return self.incoming / type / filename
    
    def get_processing_path(self, filename: str) -> Path:
        return self.processing / filename

    def get_bad_file_path(self, filename: str) -> Path:
        return self.bad_files / filename
    
    def get_duplicate_file_path(self, filename: str) -> Path: 
        return self.duplicate_files / filename
    
    def get_schema_failure_path(self, filename: str) -> Path:
        return self.schema_failure / filename
    
    def get_quarantine_completed_path(self, filename: str) -> Path: 
        return self.completed_quarantine / filename
    
    def get_clean_completed_path(self, filename: str) -> Path:
        return self.completed_clean / filename
    
    def get_rejected_path(self, filename: str) -> Path: 
        return self.rejected / filename
    
    def get_system_failure_path(self, filename: str) -> Path: 
        return self.system_failure / filename
    
    def get_cold_storage_path(self, filename: str) -> Path: 
        return self.cold_storage / filename
    
    def get_outgoing_alerts_path(self, filename: str) -> Path:
        return self.outgoing_alerts / filename
