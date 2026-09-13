"""Application-level errors for visitor-counter operations."""


class VisitorCounterError(RuntimeError):
    """Base class for visitor-counter application errors."""


class VisitorCounterNotFoundError(VisitorCounterError):
    """Raised when the seeded visitor-counter entity does not exist."""


class VisitorCounterStorageError(VisitorCounterError):
    """Raised when visitor-counter storage cannot complete an operation."""
