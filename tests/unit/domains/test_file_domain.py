# tests.unit.domains.test_file_domain

# run command: poetry run python -m pytest tests/unit/domains/test_file_domain.py

from datetime import datetime, timezone
from src.files.domain import File, FileStatus
from src.pipeline.events import DomainEvent


def test_file_equivalency_by_hash():
    
    
    file1 = File(
        filename="super.csv",
        hashed_file="1234",
        assumed_type="sales", 
        is_ambiguous=True,
        potential_types=["sales", "leads"],
        status=FileStatus.PENDING,
        processing_begun=None
        )
    
    file2 = File(
        filename="blah.csv",
        hashed_file="1234",
        assumed_type="leads",
        is_ambiguous=True,
        potential_types=["leads", "sales"],
        status=FileStatus.FINISHING,
        processing_begun=datetime.now(timezone.utc)
    )
    
    assert file1 == file2