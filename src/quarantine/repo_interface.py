# src.quarantine.repo_interface

import abc

from src.shared.interfaces.repository_interface import AbstractDomainRepository

# This is not strictly necessary, but it is here in case you wanted to define distinctive methods for the Quarantined Rows domain.

class AbstractQuarantineRepository(AbstractDomainRepository):
    """Base interface for domains that only support creation."""
    
    @abc.abstractmethod
    def add(self, entity, *args, **kwargs):
        """Adds a single entity to the repository."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def check_exists(self, identifier) -> bool:
        """Checks if an entity exists in the database or not."""
        raise NotImplementedError
        
    @abc.abstractmethod
    def get(self, identifier): 
        """Gets an entity or multiple entities from the database; this is NOT linked to config.identifier but could be."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def delete(self, identifier): 
        """Deletes an entity or multiple entities from the database by its registry identifier."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_by_source_file(self, file_id: int):
        """Deletes an entity or multiple entities from the database by source file id."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_by_source_file(self, file_id: int):
        """Gets entities by source file ID."""
        raise NotImplementedError