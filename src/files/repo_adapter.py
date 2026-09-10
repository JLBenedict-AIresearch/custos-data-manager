# src.files.repo_adapter

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.files.domain import File as DomainFile
from src.files.domain import FileStatus
from src.files.orm import FileORM
from src.files.repo_interface import AbstractFileRepository


class SQLAlchemyFileRepository(AbstractFileRepository):
    def __init__(self, session: Session):
        self.session = session
        self.seen: set[DomainFile] = set()
        self._identity_map: dict[str, FileORM] = {}

    # Internal Helper methods

    def _to_domain(self, orm_file: FileORM) -> DomainFile:
        """Rebuilds the pure Domain File from the database state."""
        file = DomainFile(
            filename=orm_file.filename,
            assumed_type=orm_file.assumed_type,
            hashed_file=orm_file.hashed_file, 
            status=FileStatus(orm_file.status), 
            is_ambiguous=orm_file.is_ambiguous, 
            potential_types=orm_file.potential_types,
            created_at=orm_file.created_at,
            processing_begun=orm_file.processing_begun
        )
        file.id = orm_file.id
        file.status_reason = orm_file.status_reason
        file.processing_finished = orm_file.processing_finished
        file.total_rows = orm_file.total_rows
        file.total_processed_rows = orm_file.total_processed_rows
        file.quarantined_rows = orm_file.quarantined_rows
        file.expected_batches = orm_file.expected_batches
        file.validated_batches = orm_file.validated_batches
        file.completed_batches = orm_file.completed_batches
        
        return file

    def _to_orm(self, domain_file: DomainFile) -> FileORM:
        """Translates the domain entity back to the SQLAlchemy ORM."""
        orm_file = self._identity_map.get(domain_file.hashed_file)
        
        if not orm_file:
            orm_file = FileORM(hashed_file=domain_file.hashed_file)
            if domain_file.hashed_file:
                self._identity_map[domain_file.hashed_file] = orm_file

        orm_file.filename = domain_file.filename
        orm_file.assumed_type = domain_file.assumed_type
        orm_file.is_ambiguous = domain_file.is_ambiguous
        orm_file.potential_types = domain_file.potential_types
        orm_file.status = domain_file.status
        orm_file.status_reason = domain_file.status_reason
        orm_file.created_at = domain_file.created_at
        orm_file.processing_begun = domain_file.processing_begun
        orm_file.processing_finished = domain_file.processing_finished
        orm_file.total_rows = domain_file.total_rows
        orm_file.total_processed_rows = domain_file.total_processed_rows
        orm_file.quarantined_rows = domain_file.quarantined_rows
        orm_file.expected_batches = domain_file.expected_batches
        orm_file.validated_batches = domain_file.validated_batches
        orm_file.completed_batches = domain_file.completed_batches
        
        return orm_file

# Abstract/Generic class methods

    def add(self, entity: DomainFile) -> int:
        """Saves a new file to the database and tracks it."""
        existing_entity = self.get_file_by_hash(entity.hashed_file)
        
        if not existing_entity: 
            orm_file = self._to_orm(entity)
            self.session.add(orm_file)
            self.session.flush()
            entity.id = orm_file.id
            self.seen.add(entity)
            return orm_file.id
        else:
            
            assert existing_entity.id is not None
            return existing_entity.id
        self.update(entity)

    def check_exists(self, identifier) -> bool: 
        """Idempotency check by HASHED FILE to see if file exists in database; returns True if it does."""
        identifier = str(identifier)
        return self.get_file_by_hash(identifier) is not None
    
    
    def get(self, identifier) -> DomainFile | None: 
        """Gets a file by its FILE ID"""
        stmt = select(FileORM).where(FileORM.id == identifier)
        orm_file = self.session.execute(stmt).scalar_one_or_none()

        if orm_file: 
            domain_file = self._to_domain(orm_file)
            self.seen.add(domain_file)
            return domain_file
        
        return None    
    
    def update(self, entity: DomainFile) -> None:

        stmt = select(FileORM).where(FileORM.hashed_file == entity.hashed_file)
        orm_file = self.session.execute(stmt).scalars().first()
        assert entity.id is not None

        orm_model = self._to_orm(entity)
        orm_model.id = entity.id  # Crucial: gives merge() the primary key it needs
        
        # Merge handles the rest: it looks up the row by ID and updates all fields in full
        self.session.merge(orm_model)
        self.seen.add(entity)
        # if orm_file: 

        #     orm_file.filename = entity.filename 
        #     orm_file.assumed_type = entity.assumed_type
        #     orm_file.is_ambiguous = entity.is_ambiguous
        #     orm_file.potential_types = entity.potential_types
        #     orm_file.status = entity.status
        #     orm_file.status_reason = entity.status_reason
        #     orm_file.created_at = entity.created_at
        #     orm_file.processing_begun = entity.processing_begun
        #     orm_file.processing_finished = entity.processing_finished
        #     orm_file.total_rows = entity.total_rows
        #     orm_file.total_processed_rows = entity.total_processed_rows
        #     orm_file.quarantined_rows = entity.quarantined_rows
        #     orm_file.expected_batches = entity.expected_batches
        #     orm_file.validated_batches = entity.validated_batches
        #     orm_file.completed_batches = entity.completed_batches
        
    def delete(self, identifier) -> None: 
        """It would be unwise ever to call this method but it's here in case of emergency."""
        
        stmt = select(FileORM).where(FileORM.id == identifier)
        file_orm = self.session.execute(stmt).scalar_one_or_none()
        if file_orm: 
            self.session.delete(file_orm) 
            
    
    
    # Distinctive methods
    
    def check_for_busy_files(self) -> bool: 
        busy_statuses = [
            FileStatus.AUDITING, 
            FileStatus.PROCESSING,
            FileStatus.VALIDATING, 
            FileStatus.PERSISTING, 
            FileStatus.RETRYING, 
            FileStatus.FINISHING
        ]
    
        stmt = select(FileORM.id).where(FileORM.status.in_(busy_statuses))
        return self.session.scalar(stmt) is not None
        

    def get_file_by_hash(self, file_hash: str) -> DomainFile | None:
        """Retrieves a file by its hash to prevent duplicate processing."""
        stmt = select(FileORM).where(FileORM.hashed_file == file_hash)
        orm_file = self.session.execute(stmt).scalar_one_or_none()
        
        if orm_file:
            self._identity_map[file_hash] = orm_file
            domain_file = self._to_domain(orm_file)
            self.seen.add(domain_file)
            return domain_file
            
        return None
    
    def compare_files(self, file1_hash: str, file2_hash: str) -> bool:
        return True if file1_hash == file2_hash else False
    
    
    def get_file_by_name(self, filename: str) -> DomainFile | None: 
        stmt = select(FileORM).where(FileORM.filename == filename)
        orm_file = self.session.execute(stmt).scalar_one_or_none()
        
        if orm_file: 
            domain_file = self._to_domain(orm_file)
            self.seen.add(domain_file)
            return domain_file
        
        return None
    
    def get_file_by_id(self, file_id: int) -> DomainFile| None:
        return self.get(file_id)
    
    def get_oldest_pending_file(self) -> DomainFile | None:
        stmt = (
        select(FileORM)
        .where(FileORM.status == FileStatus.PENDING)
        .order_by(FileORM.created_at.asc()).limit(1)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        return self._to_domain(result) if result else None