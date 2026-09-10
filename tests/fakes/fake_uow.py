# tests.conftest.fake_uow

from src.shared.interfaces.uow_interface import AbstractUnitOfWork
from tests.fakes.fake_file_repository import FakeFileRepository
from tests.fakes.fake_lead_repository import FakeLeadRepository
from tests.fakes.fake_sales_repository import FakeSalesRepository
from tests.fakes.fake_quarantine_repository import FakeQuarantineRepository

class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self, *args):
        self.committed = False
        self.rolled_back = False
        self.file_routed_to = None
        self.leads = FakeLeadRepository()
        self.sales = FakeSalesRepository()
        self.quarantine = FakeQuarantineRepository()
        self.files = FakeFileRepository()

    def __enter__(self):
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)

    def commit(self):
        self.committed = True
        self.file_routed_to = "archive"

    def rollback(self):
        self.rolled_back = True
        self.file_routed_to = "error"
        
        

    