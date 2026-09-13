"""Domain model for the resume visitor counter."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VisitorCount:
    """A non-negative visitor count."""

    value: int

    def __post_init__(self) -> None:
        """Reject values that cannot represent a visitor count."""
        if self.value < 0:
            message = 'Visitor count cannot be negative.'
            raise ValueError(message)

    def increment(self) -> 'VisitorCount':
        """Return the next visitor count."""
        return VisitorCount(self.value + 1)
