# tests.conftest.fake_storage_manager

from pathlib import Path
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager
from src.shared.errors import ResourceNotFoundError

class FakeFileStorageManager(AbstractFileStorageManager):
    def __init__(self):
        # A set to keep track of what files "exist" in our pretend file system
        self.known_files: set[Path] = set()
        
        # Dictionaries to let tests override specific behaviors if needed
        self.mock_hashes: dict[Path, str] = {}
        self.mock_mimes: dict[str, bool] = {}
        self.mock_headers: dict[str, list[str]] = {}

    def move(self, source: Path, destination: Path) -> None:
        if source not in self.known_files:
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"Source file {source} cannot be found")
        
        # Simulate moving by removing the old path and adding the new one
        self.known_files.remove(source)
        self.known_files.add(destination)

    def validate_csv_mime(self, filepath: str) -> bool:
        path_obj = Path(filepath)
        if path_obj not in self.known_files:
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"File {filepath} cannot be found")
        
        # Default to True, but allow tests to simulate a bad MIME type
        return self.mock_mimes.get(filepath, True)


    def check_headers_for_type(self, filepath: str | Path) -> list[str]:
        """Returns mock headers or raises StopIteration if the list is empty."""

        path_str = str(filepath)
        
        # Fail loudly if the test forgot to configure this file
        if path_str not in self.mock_headers:
            raise ValueError(
                f"Test Configuration Error: No mock headers provided for '{path_str}'. "
                "Did you forget to add it to fake_storage.mock_headers?"
            )
            
        headers = self.mock_headers[path_str]

        if not headers:
            raise StopIteration()
            
        return headers
    
    def get_file_hash(self, filepath: Path) -> str:
        if filepath not in self.known_files:
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"{filepath} cannot be found")
        
        # Default to a dummy hash, but allow tests to inject a specific one
        return self.mock_hashes.get(filepath, "fake_hash_1234567890")
    
    def archive_files(self, file_paths: list[Path], archive_destination: Path) -> None:
        for path in file_paths: 
            if path not in self.known_files: 
                raise ResourceNotFoundError(error_code="NOT_FOUN_ERR", message=f"{path} cannot be found.")
        
            self.known_files.add(archive_destination)