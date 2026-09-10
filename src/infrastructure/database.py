# src.infrastructure.database

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import settings


class Base(DeclarativeBase):
    pass

engine = create_engine(settings.DATABASE_URL)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

