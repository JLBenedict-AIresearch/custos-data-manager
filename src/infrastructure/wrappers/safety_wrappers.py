# src.infrastructure.middleware.wrappers


import errno
from functools import wraps
from typing import Any, Callable
import time

from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from structlog.contextvars import bind_contextvars, unbind_contextvars

from src.infrastructure.logging import log_domain_error
from src.pipeline.events import FileProcessingAborted, SystemFaultEvent
from src.shared.errors import (
    CustosSystemError,
    DatabaseSchemaError,
    DataIntegrityError,
    DiskFullError,
    FileSystemError,
    PermissionDeniedError,
    UnknownTypeError,
)


def _get_message_from_args(*args, **kwargs):
    """Helper to safely extract the command or event from args/kwargs."""
    if args:
        return args[0]
    return kwargs.get('command', kwargs.get('event'))

def with_infrastructure_safety(max_retries: int = 3) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 1
            
            # Extract the message dynamically without forcing parameter names
            msg = _get_message_from_args(*args, **kwargs)
            
            file_id = getattr(msg, 'file_id', None)
            filepath = getattr(msg, 'filepath', 'UNKNOWN')
            filename = getattr(msg, 'filename', 'UNKNOWN')
            
            while attempt <= max_retries:
                try:
                    return func(*args, **kwargs)
                
                except UnknownTypeError as e:
                    return [FileProcessingAborted(
                        file_id=file_id if file_id else None,
                        filepath=filepath,
                        reason=str(e)
                    )]
                
                except OperationalError as e:
                    if attempt == max_retries:
                        return [SystemFaultEvent(
                            file_id = file_id if file_id else None,
                            filename=filename,
                            filepath=filepath, 
                            error_type="DatabaseConnectionError",
                            message=f"DB failed after {max_retries} attempts. {str(e)}"
                        )]
                        
                    time.sleep(2 ** attempt)
                    attempt += 1

                except OSError as e:

                    
                    error_msg = e.strerror or str(e)
                    if e.errno == errno.ENOSPC:
                        raise DiskFullError(error_msg, original_error=e) from e
                    
                    elif e.errno in (errno.EACCES, errno.EPERM):
                        raise PermissionDeniedError(error_msg, original_error=e) from e
                    else:
                        raise FileSystemError(error_msg, original_error=e) from e

                except ProgrammingError as e:
                    raise DatabaseSchemaError(
                        "Database structure mismatch or invalid SQL.", 
                        None,
                        original_error=e) from e                    
                
                except IntegrityError as e: 
                    raise DataIntegrityError(
                        "Data failed database integrity constraints.", 
                        None,
                        original_error=e) from e
                
                except Exception as e:
                    log_domain_error(e, handler_name=func.__name__)
                    raise CustosSystemError(f"Unhandled system error: {str(e)}", original_error=e) from e
                    
        return wrapper
    return decorator

def with_logging_context(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        msg = _get_message_from_args(*args, **kwargs)
        
        file_id = getattr(msg, 'file_id', None)
        assumed_type = getattr(
            msg, 
            'assumed_type', 
            getattr(msg, 'file_type', None)
        )
        
        keys_to_bind = {}
        if file_id is not None:
            keys_to_bind['file_id'] = file_id
        if assumed_type is not None:
            keys_to_bind['file_type'] = assumed_type
            
        if keys_to_bind:
            bind_contextvars(**keys_to_bind)
            
        try:
            return func(*args, **kwargs)
        finally:
            # Unbind only the keys added by this wrapper
            if keys_to_bind:
                unbind_contextvars(*keys_to_bind.keys())
                
    return wrapper