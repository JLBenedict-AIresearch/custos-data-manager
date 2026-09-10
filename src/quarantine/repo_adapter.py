# src.quarantine.repo_adapter

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from src.quarantine.domain import QuarantinedRow
from src.quarantine.orm import QuarantinedRowORM
from src.quarantine.repo_interface import AbstractQuarantineRepository


class SQLAlchemyQuarantineRepository(AbstractQuarantineRepository):
    def __init__(self, session: Session):
        self.session = session
        self.seen_quarantined: set[QuarantinedRow] = set()
        
# Internal Helper methods

    def _to_orm(self, domain_row: QuarantinedRow) -> QuarantinedRowORM:
        return QuarantinedRowORM(
            file_id=domain_row.file_id,
            assumed_type=domain_row.assumed_type,
            raw_payload=domain_row.raw_payload,
            payload_hash=domain_row.payload_hash,
            error_reason=domain_row.error_reason,
            line_number=domain_row.line_number,
            quarantined_at=domain_row.quarantined_at
        )

    def _to_domain(self, orm_row: QuarantinedRowORM) -> QuarantinedRow:
        return QuarantinedRow(
            file_id=orm_row.file_id,
            assumed_type=orm_row.assumed_type,
            raw_payload=orm_row.raw_payload,
            payload_hash=orm_row.payload_hash,
            error_reason=orm_row.error_reason,
            line_number=orm_row.line_number,
            quarantined_at=orm_row.quarantined_at
        )

# Base class inherited methods

    def add(self, entity: QuarantinedRow) -> None:
        if self.check_exists(entity.payload_hash):
            return 
        else: 
            orm_row = self._to_orm(entity)
            self.session.add(orm_row)
            self.seen_quarantined.add(entity)
    
    def get(self, identifier) -> list[QuarantinedRow] | None:

        stmt = select(QuarantinedRowORM).where(QuarantinedRowORM.file_id == identifier)
        results = self.session.execute(stmt).scalars().all()
        if results: 
            return [self._to_domain(result) for result in results]
        return None
        
    def check_exists(self, identifier) -> bool:
        """The identifier here is the PAYLOAD HASH: str"""

        for row in self.seen_quarantined:
            if row.payload_hash == identifier:
                return True
            
        stmt = select(QuarantinedRowORM.id).where(QuarantinedRowORM.payload_hash == identifier)
        result = self.session.execute(stmt)
        return result.first() is not None

    def delete(self, identifier): 
        pass

    def delete_by_source_file(self, file_id: int) -> None:
        """The identifier is the source file id (int) and this deletes ALL rows."""
        stmt = delete(QuarantinedRowORM).where(QuarantinedRowORM.file_id == file_id)
        deletion = self.session.execute(stmt)


    def get_by_source_file(self, file_id: int) -> list[QuarantinedRow] | None: 
        stmt = select(QuarantinedRowORM).where(QuarantinedRowORM.file_id == file_id)
        orm_rows = self.session.execute(stmt).scalars().all()
        if orm_rows: 
            return [self._to_domain(row) for row in orm_rows]
        return None