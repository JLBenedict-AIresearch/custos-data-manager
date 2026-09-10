# src.infrastructure.adapters.uow_adapter

from pathlib import Path
from typing import Callable

from src.files.repo_adapter import SQLAlchemyFileRepository
from src.infrastructure.adapters.message_bus import MessageBus
from src.leads.repo_adapter import SQLAlchemyLeadsRepository
from src.quarantine.repo_adapter import SQLAlchemyQuarantineRepository
from src.sales.repo_adapter import SQLAlchemySalesRepository
from src.shared.interfaces.uow_interface import AbstractUnitOfWork


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):

    def __init__(self, session_factory: Callable):
        self.session_factory = session_factory

        
    def __enter__(self):
        
        self.session = self.session_factory()
        self.leads = SQLAlchemyLeadsRepository(self.session)
        self.sales = SQLAlchemySalesRepository(self.session)
        self.files = SQLAlchemyFileRepository(self.session)        
        self.quarantine = SQLAlchemyQuarantineRepository(self.session)
        return super().__enter__()

    def __exit__(self, exc_type, exc_val, traceback):
        if exc_type:
            self.rollback()
        self.session.close()

    def commit(self):
        """Commits the database transaction and dispatches all events."""
        self.session.commit()
        #self._publish_events()

    def rollback(self):
        self.session.rollback()


# This is for use in a later version in case events were to save their own events; at present, all events are handled within pipeline
# or by background runners.
    # def _publish_events(self):
    #     """Pulls events from seen entities and hands them to the bus."""
        
    #     while True:
    #         all_seen_entities = set().union(
    #             self.leads.seen,
    #             self.sales.seen, 
    #             self.files.seen,
    #             self.quarantine.seen_quarantined_rows
    #         )
            
    #         batch = []
    #         for entity in all_seen_entities:
    #             events = getattr(entity, "events", [])
    #             while events:
    #                 batch.append(events.pop(0))
            
    #         if not batch:
    #             break
                
    #         for event in batch:
    #             self.bus.handle(event, self)