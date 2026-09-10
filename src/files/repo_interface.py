# src.files.repo_interface

from abc import abstractmethod

from src.files.domain import File as DomainFile
from src.files.domain import FileStatus
from src.shared.interfaces.repository_interface import AbstractUpdatableRepository


class AbstractFileRepository(AbstractUpdatableRepository):
    
    @abstractmethod
    def check_for_busy_files(self) -> bool: 
        raise NotImplementedError
        
    @abstractmethod
    def get_file_by_hash(self, file_hash: str) -> DomainFile | None:
        """Retrieves a file by its hash to prevent duplicate processing."""
        raise NotImplementedError
    
    @abstractmethod
    def compare_files(self, file1_hash: str, file2_hash: str) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def get_file_by_name(self, filename: str) -> DomainFile | None: 
        raise NotImplementedError
    

    @abstractmethod
    def get_oldest_pending_file(self):
        raise NotImplementedError