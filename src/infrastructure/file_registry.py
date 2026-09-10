# src.infrastructure.file_registry

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence, Set, Tuple, Type, Union

from src.shared.errors import UnknownTypeError


@dataclass
class FileTypeConfig:
    key_fields: Set[str]
    id_fields: str | tuple[str, ...]
    schema: Type[Any] 
    data: Type[Any]    
    entity: Type[Any]  
    associated_entities: list[Type[Any]] | None
    repo_name: str
    allows_updates: bool
    update_model: Type[Any] | None
    helper: Callable
    requires_timestamp: bool
    required_fields: Set[str]
    batch_size: int | None

class FileTypeRegistry:
    def __init__(self):
        self._registry: dict[str, FileTypeConfig] = {}

    def register(
        self, 
        file_type: str, 
        key_fields: Set[str], 
        id_fields: str | tuple[str, ...],
        schema: Type, 
        data: Type, 
        entity: Type,
        associated_entities: list[Type] | None,
        repo_name: str,
        allows_updates: bool, 
        update_model: Type | None, 
        helper: Callable,
        requires_timestamp: bool, 
        required_fields: Set[str],
        batch_size: int | None
    ):
        self._registry[file_type] = FileTypeConfig(
            key_fields=key_fields,
            id_fields=id_fields,
            schema=schema,
            data=data,
            entity=entity, 
            associated_entities=associated_entities if associated_entities else None,
            repo_name=repo_name,
            allows_updates=allows_updates,
            update_model=update_model if update_model else None,
            helper=helper,
            requires_timestamp=requires_timestamp,
            required_fields=required_fields,
            batch_size=batch_size
        )

    def get(self, file_type: str) -> FileTypeConfig:
        if file_type not in self._registry:
            raise UnknownTypeError(f"Unregistered file type: {file_type}")
        return self._registry[file_type]

    def identify_from_headers(self, assumed_type: str, file_headers: Sequence[str]) -> str | tuple[str, list]:
        header_set = set(file_headers)
        matches = []
        
        for file_type, config in self._registry.items():
            if not config.key_fields.isdisjoint(header_set):
                matches.append(file_type)
                
        if len(matches) == 0:
            raise UnknownTypeError("Headers do not match any known file type.")
        
        if len(matches) > 1:
            # This would be very weird, but it's technically possible -- viz. file has a "transaction_id" column AND a "lead_score" column.
            if assumed_type in matches:
                return (assumed_type, matches)
            else:
                raise UnknownTypeError(f"Unregistered file type: {assumed_type}.")
        
        return matches[0]

    