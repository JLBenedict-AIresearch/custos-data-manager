# src.shared.interfaces.file_storage_interface

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractFileStorageManager(ABC):
    
    @abstractmethod
    def move(self, source, destination):
        raise NotImplementedError
    
    @abstractmethod
    def validate_csv_mime(self, filepath: str) -> bool:
        raise NotImplementedError
    
    @abstractmethod
    def check_headers_for_type(self, filepath) -> list:
        raise NotImplementedError
    
    @abstractmethod
    def get_file_hash(self, filepath) -> str: 
        raise NotImplementedError
    
    @abstractmethod
    def archive_files(self, file_paths: list[Path], archive_destination: Path) -> None:
        raise NotImplementedError