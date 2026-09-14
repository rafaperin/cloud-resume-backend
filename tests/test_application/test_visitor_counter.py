"""Unit tests for visitor-counter application use cases."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from application.visitor_counter import GetVisitorCount, IncrementVisitorCount
from domain.visitor_counter import VisitorCount


class FakeVisitorCounterRepository:
    """Stateful application-port fake for use-case tests."""

    def __init__(self, count: int) -> None:
        self.count = count
        self.get_count_calls = 0
        self.increment_count_calls = 0

    def get_count(self) -> VisitorCount:
        """Return the current stored count."""
        self.get_count_calls += 1
        return VisitorCount(self.count)

    def increment_count(self) -> VisitorCount:
        """Persist and return the next count."""
        self.increment_count_calls += 1
        self.count += 1
        return VisitorCount(self.count)


class VisitorCounterUseCaseTests(unittest.TestCase):
    """Verify use cases depend on the visitor-counter port only."""

    def test_get_visitor_count_returns_repository_value_without_incrementing(self) -> None:
        """Read the current value through the application port."""
        repository = FakeVisitorCounterRepository(count=41)

        result = GetVisitorCount(repository).execute()

        self.assertEqual(result, VisitorCount(41))
        self.assertEqual(repository.get_count_calls, 1)
        self.assertEqual(repository.increment_count_calls, 0)

    def test_increment_visitor_count_returns_the_persisted_next_value(self) -> None:
        """Delegate the state transition to the persistence port exactly once."""
        repository = FakeVisitorCounterRepository(count=41)

        result = IncrementVisitorCount(repository).execute()

        self.assertEqual(result, VisitorCount(42))
        self.assertEqual(repository.increment_count_calls, 1)
        self.assertEqual(repository.count, 42)
