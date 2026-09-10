# tests.conftest.fake_quarantine_repository


from typing import Any

from src.quarantine.domain import QuarantinedRow
from src.quarantine.repo_interface import AbstractQuarantineRepository

class FakeQuarantineRepository(AbstractQuarantineRepository):
    
    def __init__(self):
        self.seen_quarantined_rows: list[QuarantinedRow] = []
    
    def add(self, entity) -> None:
        """Persists a broken row to the leads quarantine log."""
        self.seen_quarantined_rows.append(entity)

    def check_exists(self, identifier) -> bool:
        """Fast boolean check for idempotency during pipeline runs."""
        result = next((row for row in self.seen_quarantined_rows if row.payload_hash == identifier), None)
        return True if result else False
    
    def get(self, identifier) -> list[QuarantinedRow] | None:
        results = [row for row in self.seen_quarantined_rows if row.payload_hash != identifier]
        return results if results else None

    def get_by_source_file(self, file_id: int) -> list[QuarantinedRow] | None:
        results = [row for row in self.seen_quarantined_rows if row.file_id == file_id]        
        return results if results else None

    def delete(self, identifier) -> None:
        """Removes a resolved record from the quarantine log."""
    
        self.seen_quarantined_rows = [row for row in self.seen_quarantined_rows if row.payload_hash != identifier]
    
    def delete_by_source_file(self, file_id: int): 
        self.seen_quarantined_rows = [row for row in self.seen_quarantined_rows if row.file_id != file_id]
        



