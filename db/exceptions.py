"""Custom exceptions for database operations."""


class DatabaseError(Exception):
    """Base exception for database operations."""
    pass


class ContainerError(DatabaseError):
    """Exception for container-related operations."""
    pass


class QueryError(DatabaseError):
    """Exception for query-related operations."""
    pass


class ConnectionError(DatabaseError):
    """Exception for connection-related operations."""
    pass