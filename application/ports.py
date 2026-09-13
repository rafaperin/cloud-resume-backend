"""Ports used by visitor-counter application use cases."""

from typing import Protocol

from domain.visitor_counter import VisitorCount


class VisitorCounterRepository(Protocol):
    """Persistence operations needed by the visitor-counter use cases."""

    def get_count(self) -> VisitorCount:
        """Return the current visitor count."""

    def increment_count(self) -> VisitorCount:
        """Atomically increment and return the visitor count."""
