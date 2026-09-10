# src.shared.uow_interface

import abc
from typing import Callable

from src.files.repo_interface import AbstractFileRepository
from src.leads.repo_interface import AbstractLeadRepository
from src.quarantine.repo_interface import AbstractQuarantineRepository
from src.sales.repo_interface import AbstractSalesRepository


class AbstractUnitOfWork(abc.ABC):
    leads: "AbstractLeadRepository"
    sales: "AbstractSalesRepository"
    files: "AbstractFileRepository"
    quarantine: "AbstractQuarantineRepository"
    
    def __init__(self, session_factory: Callable):
        self.session_factory = session_factory
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type:
            self.rollback()


    @abc.abstractmethod
    def commit(self):
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError