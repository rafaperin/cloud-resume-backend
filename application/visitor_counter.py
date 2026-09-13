"""Use cases for reading and incrementing the visitor counter."""

from application.ports import VisitorCounterRepository
from domain.visitor_counter import VisitorCount


class GetVisitorCount:
    """Return the current visitor count."""

    def __init__(self, repository: VisitorCounterRepository) -> None:
        self._repository = repository

    def execute(self) -> VisitorCount:
        """Retrieve the current count through the persistence port."""
        return self._repository.get_count()


class IncrementVisitorCount:
    """Increment and return the visitor count."""

    def __init__(self, repository: VisitorCounterRepository) -> None:
        self._repository = repository

    def execute(self) -> VisitorCount:
        """Increment the count through the persistence port."""
        return self._repository.increment_count()
