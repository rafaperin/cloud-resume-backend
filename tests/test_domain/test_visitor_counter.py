"""Unit tests for visitor-counter domain rules."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from domain.visitor_counter import VisitorCount


class VisitorCountTests(unittest.TestCase):
    """Verify that the domain model preserves valid counter states."""

    def test_increment_returns_the_next_non_negative_value(self) -> None:
        """Create a new value without mutating the original domain object."""
        current_count = VisitorCount(41)

        next_count = current_count.increment()

        self.assertEqual(current_count, VisitorCount(41))
        self.assertEqual(next_count, VisitorCount(42))

    def test_visitor_count_rejects_negative_values(self) -> None:
        """Prevent invalid counts from reaching application or infrastructure layers."""
        with self.assertRaises(ValueError):
            VisitorCount(-1)
