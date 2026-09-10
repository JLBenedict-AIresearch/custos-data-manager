# src.shared.interfaces.repository_interface


import abc
from typing import Any, Tuple, Union

EntityID = Union[str, int, Tuple[Any, ...]]


class AbstractBaseRepository(abc.ABC):
    """Base interface for domains that only support creation."""
    
    @abc.abstractmethod
    def add(self, entity, *args, **kwargs):
        """Adds a single entity to the repository."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def check_exists(self, identifier: EntityID) -> bool:
        """Checks if an entity exists in the database or not."""
        raise NotImplementedError
        
    @abc.abstractmethod
    def get(self, identifier: EntityID): 
        """Gets an entity or multiple entities from the database; this is NOT linked to config.identifier but could be."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def delete(self, identifier: EntityID): 
        """Deletes an entity or multiple entities from the database by its registry identifier."""
        raise NotImplementedError

class AbstractDomainRepository(AbstractBaseRepository):
    """Supports domains dependent on the aggregate root 'File' with particular methods."""
    
    @abc.abstractmethod
    def delete_by_source_file(self, file_id: int):
        """Deletes an entity or multiple entities from the database by source file id."""
        raise NotImplementedError
    
    @abc.abstractmethod
    def get_by_source_file(self, file_id: int):
        """Gets entities by source file ID."""
        raise NotImplementedError
    
    # Note: For an expansion of this program, you would want more methods; these are sufficient for Custos v. 1.0 features.

class AbstractUpdatableRepository(AbstractBaseRepository):
    """Extended interface for aggregate root updates"""

    @abc.abstractmethod
    def update(self, entity, *args, **kwargs):
        """Updates an existing entity."""
        raise NotImplementedError

class AbstractUpdatableDomainRepository(AbstractDomainRepository):
    """Extended interface for domains that support modification."""
    
    @abc.abstractmethod
    def update(self, entity, *args, **kwargs):
        """Updates an existing entity."""
        raise NotImplementedError