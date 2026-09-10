# src.infrastructure.adapters.file_storage_manager

import csv
import hashlib
import magic
import os
from pathlib import Path
import shutil
import zipfile
from src.shared.errors import ResourceNotFoundError
from src.shared.interfaces.file_storage_interface import AbstractFileStorageManager



class CustosFileStorageManager(AbstractFileStorageManager):
    
    def move(self, source: Path, destination: Path):
        try:
            shutil.move(source, destination)
        except FileNotFoundError:
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"Source file {source} cannot be found")
    
    def validate_csv_mime(self, filepath: str) -> bool:
        VALID_CSV_MIMES = {"text/csv", "text/plain"}
        try:
            mime = magic.from_file(filepath, mime=True)
            return mime in VALID_CSV_MIMES    
        except FileNotFoundError:
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"File {filepath} cannot be found")
        
    def check_headers_for_type(self, filepath) -> list:
        with open(filepath, 'r') as f:
            reader = csv.reader(f)
            headers: list[str] = next(reader)
            return headers 

    def get_file_hash(self, filepath: Path) -> str: 
        """Calculates SHA-256 hash in chunks to prevent memory blowouts on huge CSVs."""
        if not filepath.exists(): 
            raise ResourceNotFoundError(error_code="NOT_FOUND_ERR", message=f"{filepath} cannot be found")
        
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            # Read the file in 4KB chunks
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def archive_files(self, file_paths: list[Path], archive_destination: Path) -> None:
        """Compresses a list of files into a zip archive and deletes the originals."""
        if not file_paths:
            return

        with zipfile.ZipFile(archive_destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filepath in file_paths:
                if filepath.exists():
                    zipf.write(filepath, arcname=filepath.name) 


        for filepath in file_paths:
            if filepath.exists():
                os.remove(filepath)
                
