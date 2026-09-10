from sqlalchemy.types import JSON, TypeDecorator


class JSONSet(TypeDecorator):
    """
    Translates a Python set into a JSON list for database storage, 
    and back into a Python set upon retrieval.
    """

    impl = JSON 
    cache_ok = True 

    def process_bind_param(self, value, dialect):
        """Runs when SAVING to the database (Python -> DB)"""
        if value is not None:
            return list(value)
        return []

    def process_result_value(self, value, dialect):
        """Runs when LOADING from the database (DB -> Python)"""
        if value is not None:
            return set(value)
        return set()