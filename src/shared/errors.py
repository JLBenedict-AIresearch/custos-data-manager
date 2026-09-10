# src.shared.errors


from pydantic import ValidationError


class DomainError(Exception):
    def __init__(self,  error_code: str, message: str | None = None):
        self.error_code = error_code
        self.message = message or self.__class__.__doc__ or self.error_code
        Exception.__init__(self, self.message)
        
# Logic and Validation errors

class CustomerIdentifierError(ValueError, DomainError):
    """Customer Identifier does not have correct 'CUST-' format."""
    def __init__(self, error_code: str, message: str | None = None):
        
        error_code = "CUST_ID_ERR"        
        DomainError.__init__(self, error_code=error_code, message=message)
        ValueError.__init__(self, self.message)
        
class DataValidationError(DomainError):
    """Wraps Pydantic ValidationErrors into a structured domain error."""
    def __init__(self, original_error: ValidationError, raw_data: dict | None = None):
        self.validation_details = {
            ".".join(str(loc) for loc in err["loc"]): err["msg"]
            for err in original_error.errors()
        }
        
        super().__init__(
            message=f"Validation failed for {len(self.validation_details)} field(s).",
            error_code="ERR_DATA_VALIDATION"
        )
        self.original_error = original_error
        self.raw_data = raw_data
        
class PhoneNumberError(ValueError, DomainError):
    """Phone number has other than 10 digits or contains non-digits"""
    def __init__(self, error_code: str, message: str | None = None):

        error_code = "PHONE_ERR"
        DomainError.__init__(self, error_code=error_code, message=message)
        ValueError.__init__(self, self.message)
        

class RequiresAdditionalArgsError(ValueError, DomainError):
    """We need more arguments and didn't get them."""
    def __init__(self, message: str | None = None):
        
        error_code = "NEED_MORE_ARGS_ERR"
        DomainError.__init__(self, error_code=error_code, message=message)
        ValueError.__init__(self, self.message)
  

class SchemaCorruptionError(DomainError):
    """The validation schema registered for the data type does not match the DTO schema."""
    
    def __init__(self, message: str | None = None):
        error_code = "SCHEMA_CORRUPTION"
        
        DomainError.__init__(self, error_code=error_code, message=message)
        

class UnknownTypeError(DomainError):
    """Error: Unknown file/domain type."""
    def __init__(self, error_code: str, message: str | None = None):
        self.error_code = "UNKNOWN_TYPE"
        self.message = message
        DomainError.__init__(self, error_code=error_code, message=message)
        
        
class WrongTypeError(ValueError, DomainError):
    """Wrong type of data input as argument or returned from function"""
    def __init__(self, message: str | None = None):
        
        error_code = "WRONG_TYPE_ERR"
        DomainError.__init__(self, error_code=error_code, message=message)
        ValueError.__init__(self, self.message)

        
# File Error Types

class EmptyFileError(DomainError):
    """There is no data in this file."""
    def __init__(self, error_code: str, message: str | None = None):
        self.error_code = error_code
        self.message = message    
        super().__init__(
            error_code="Empty_File",
            message="This file is empty."
        )
        
class ResourceNotFoundError(DomainError):
    """We don't have the file or object you're looking for."""
    def __init__(self, error_code: str, message: str | None = None):
        self.error_code = "NOT_FOUND"
        self.message = message if message else "Cannot find the file or object you're seeking."
        DomainError.__init__(self, error_code=error_code, message=message)



# Critical System and Infrastructure Errors
    
class CustosSystemError(DomainError):
    """Wraps unrecoverable infrastructure/database errors."""
    def __init__(self, message: str, error_code: str = "ERR_ETL_SYSTEM_FAILURE", original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code=error_code
        )
        self.original_error = original_error

class DataIntegrityError(CustosSystemError):
    """Raised when incoming data violates SQL unique, foreign key, or non-null constraints."""
    def __init__(self, message: str, error_code: str | None, original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code="ERR_DONT_BREAK_DATABASE"
        )
        self.original_error = original_error
        
class DatabaseSchemaError(CustosSystemError):
    """Raised when the ORM code does not match the SQL database schema or tables are missing."""
    def __init__(self, message: str, error_code: str | None, original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code="ERR_DATABASE_SCHEMA"
        )
        self.original_error = original_error
        
class FileSystemError(CustosSystemError):
    """Base for OS-level file failures."""
    pass        

class DiskFullError(FileSystemError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code="ERR_DISK_FULL",
            original_error=original_error
        )

class PermissionDeniedError(FileSystemError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code="ERR_PERMISSION_DENIED",
            original_error=original_error
        )

       
# Transient/Non-fatal System Errors

class TransientSystemError(DomainError):
    """Base class for system-level errors that can be retried (e.g., network drops)."""
    pass

class DatabaseConnectionError(TransientSystemError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(
            message=message,
            error_code="ERR_DB_CONNECTION",
        )
        self.original_error = original_error
        
        
# Message Bus Specific Errors

class MessageBusConfigurationError(DomainError):
    """Base error for all message bus routing issues."""
    def __init__(self, error_code: str, message: str):
        super().__init__(error_code=error_code, message=message)

class MissingCommandHandlerError(MessageBusConfigurationError):
    """Raised when a Command is dispatched but no handler is mapped to it."""
    def __init__(self, command_type: type):
        super().__init__(
            error_code="BUS_MISSING_COMMAND_HANDLER",
            message=f"CRITICAL: No handler registered for command '{command_type}'."
        )
        
class UnknownMessageTypeError(MessageBusConfigurationError):
    """Raised when the bus receives an object it doesn't know how to route."""
    def __init__(self, message_type: type):
        super().__init__(
            error_code="BUS_UNKNOWN_MESSAGE",
            message=f"Received unknown message type, {message_type}. Expected Command or DomainEvent."
        )

