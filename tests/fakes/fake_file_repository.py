# tests.conftest.fake_file_repository

from datetime import datetime, timezone

from src.files.domain import File, FileStatus
from src.files.repo_interface import AbstractFileRepository


class FakeFileRepository(AbstractFileRepository):

    def __init__(self):
        self._files: dict[int, File] = {}
     
    def _get_next_id(self) -> int:
        current_max = max(self._files.keys(), default=0)
        return current_max + 1 
        
    def add(self, file: File) -> int:
        file_id = self._get_next_id()
        file.id = file_id
        self._files[file_id] = file
        return file_id
    
    def check_exists(self, identifier) -> bool:
        identifier = str(identifier)
        return self.get_file_by_hash(identifier) is not None

  
    def get(self, identifier) -> File | None:
        
        # It's slower, but this seems to be the only syntax that satisifies the typechecker.
        for key, obj in self._files.items(): 
            if hasattr(obj, "id") and getattr(obj, "id") == identifier:
                return obj 
        return None
    
    def delete(self, identifier):
        pass
    
    def get_by_source_file(self, file_id: int):
        result = self.get(file_id)
        return [result] if result else None
    
    def delete_by_source_file(self, file_id: int):
        pass
    
    def update(self, entity):
        identifier = entity.id
        entry = self._files.get(identifier)
        if entry: 
            self._files[identifier] = entity


    def check_for_busy_files(self) -> bool:
        busy_statuses = {
            FileStatus.AUDITING, 
            FileStatus.PROCESSING,
            FileStatus.VALIDATING, 
            FileStatus.PERSISTING, 
            FileStatus.RETRYING, 
            FileStatus.FINISHING
        }
        for key, obj in self._files.items():
            if hasattr(obj, "status") and getattr(obj, "status") in busy_statuses:
                return True
        return False     
                 

    def get_file_by_hash(self, file_hash: str) -> File | None:
        """Retrieves a file by its hash for idempotency checks."""
        for key, obj in self._files.items():
            if hasattr(obj, "hashed_file") and getattr(obj, "hashed_file") == file_hash:
                return obj
        return None

    def compare_files(self, file1_hash: str, file2_hash: str) -> bool: 
        """Checks if two files are the same/equal; returns True if so, False if not."""
        raise NotImplementedError
    
    def get_file_by_id(self, file_id: int) -> File | None:
        return self._files.get(file_id)
    
    def get_file_by_name(self, filename) -> File | None: 
        raise NotImplementedError
    
    def get_oldest_pending_file(self) -> File | None: 
        oldest_file: File | None = None
        
        for file in self._files.values():
            if file.status != FileStatus.PENDING or not file.created_at:
                continue
            
            if oldest_file is None or oldest_file.created_at is None:
                oldest_file = file
                
            elif file.created_at < oldest_file.created_at:
                oldest_file = file
                
        return oldest_file