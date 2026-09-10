# src.infrastructure.dependencies

from src.infrastructure.database import session_factory

from src.infrastructure.adapters.message_bus import MessageBus
from src.infrastructure.adapters.uow_adapter import SQLAlchemyUnitOfWork
from src.shared.interfaces.uow_interface import AbstractUnitOfWork


def get_uow() -> AbstractUnitOfWork:
    """Typed as Abstract UoW and returns SQLAlchemy UoW; yields a fresh UoW per request."""

    return SQLAlchemyUnitOfWork(session_factory)