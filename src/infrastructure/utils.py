# src.infrastructure.utils

import hashlib
import hmac
import json

from src.core.config import settings

HASH_SECRET = settings.custos_hash_secret.get_secret_value().encode('utf-8')

def calculate_row_hash_from_dict(row_data: dict) -> str:
    """
    Generates a consistent SHA-256 hash of a dictionary.
    Alphabetizes keys to ensure identical dictionaries always yield the same hash.
    """

    serialized_row = json.dumps(row_data, sort_keys=True, separators=(',', ':'), default=str)

    hasher = hashlib.sha256()
    hasher.update(serialized_row.encode('utf-8'))
    
    return hasher.hexdigest()

def calculate_email_row_hash(email: str) -> str:
    """
    Generates a consistent, secure HMAC-SHA-256 of a normalized email address 
    to permit deterministic database searching.
    """
    
    secret_key=HASH_SECRET
    normalized_email = email.strip().lower()
    
    hasher = hmac.new(
        key=secret_key, 
        msg=normalized_email.encode('utf-8'), 
        digestmod=hashlib.sha256
    )
    
    return hasher.hexdigest()