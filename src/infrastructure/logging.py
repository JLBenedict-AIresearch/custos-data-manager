# src.infrastructure.logging

import logging
from pathlib import Path
import sys

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from structlog.dev import ConsoleRenderer, RichTracebackFormatter

from src.shared.errors import DataValidationError, DomainError

logger = structlog.get_logger()

def configure_structlog(is_dev_mode: bool = True):
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if is_dev_mode:
        rich_formatter = RichTracebackFormatter(
            show_locals=False, 
            max_frames=10,     
        )
        
        formatter = ConsoleRenderer(
            colors=True,
            exception_formatter=rich_formatter
        )
    else:
        # For production: use standard dict tracebacks within the JSON output
        shared_processors.append(structlog.processors.dict_tracebacks)
        formatter = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [formatter],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    
def on_file_drop(file_path: Path):
    # 1. Clear previous context (important for long-running Watchdog processes)
    clear_contextvars()
    
    # 2. Bind the file name globally for this execution thread
    bind_contextvars(file_name=file_path.name)
    
    
def log_domain_error(error: Exception, **kwargs):
    """
    Logs an error, extracting structured data if it is a DomainError.
    Falls back to a standard error log for unexpected exceptions.
    """
    if isinstance(error, DomainError):
        log_kwargs = {
            "error_code": error.error_code,
            "exc_info": error,
            **kwargs
        }
        
        if isinstance(error, DataValidationError):
            log_kwargs["validation_details"] = error.validation_details
            
        logger.error(error.message, **log_kwargs)
        
    else:
        # Catch-all for built-in or third-party errors not yet wrapped
        logger.error(
            "Unhandled system exception occurred.",
            error_type=type(error).__name__,
            exc_info=error,
            **kwargs
        )