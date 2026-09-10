# src.infrasrtucture.system_check_wrapper

import os
from functools import wraps

from src.infrastructure.logging import logger


def system_halt_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.path.exists("/incoming/SYSTEM_HALTED.lock"):
            logger.warning(f"System halted. Skipping scheduled job: {func.__name__}")
            return  # Database is down; do not pass 'GO'; do not collect $200.
        
        return func(*args, **kwargs)
    return wrapper