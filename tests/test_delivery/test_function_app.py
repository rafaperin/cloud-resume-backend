"""Unit tests for the Azure Functions HTTP delivery boundary."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import azure.functions as func


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from application.errors import VisitorCounterStorageError
from domain.visitor_counter import VisitorCount
from function_app import app, get_visitor, increment_visitor


class FakeVisitorCounterRepository:
    """Stateful repository fake for exercising HTTP contracts."""

    def __init__(self, count: int = 0, should_fail: bool = False) -> None:
        self.count = count
        self.should_fail = should_fail
        self.closed = False

    def get_count(self) -> VisitorCount:
        """Return the current count or emulate an adapter failure."""
        if self.should_fail:
            raise VisitorCounterStorageError('Storage is unavailable.')
        return VisitorCount(self.count)

    def increment_count(self) -> VisitorCount:
        """Return the incremented count or emulate an adapter failure."""
        if self.should_fail:
            raise VisitorCounterStorageError('Storage is unavailable.')
        self.count += 1
        return VisitorCount(self.count)

    def close(self) -> None:
        """Record that the delivery boundary released the repository."""
        self.closed = True


def make_request(method: str) -> func.HttpRequest:
    """Build an empty HTTP request for direct handler tests."""
    return func.HttpRequest(
        method=method,
        url='http://localhost:7071/api/visitor',
        headers={},
        params={},
        route_params={},
        body=b'',
    )


class FunctionAppTests(unittest.TestCase):
    """Verify the Azure Functions v2 application and visitor HTTP contracts."""

    def test_application_uses_the_v2_function_app_type(self) -> None:
        """Expose a FunctionApp instance for decorator-based function registration."""
        self.assertIsInstance(app, func.FunctionApp)

    def test_get_visitor_returns_current_count(self) -> None:
        """Return the JSON count without incrementing it."""
        repository = FakeVisitorCounterRepository(count=41)

        with patch('function_app.create_visitor_counter_repository', return_value=repository):
            response = get_visitor(make_request('GET'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {'count': 41})
        self.assertEqual(repository.count, 41)
        self.assertTrue(repository.closed)

    def test_post_visitor_increments_and_returns_count(self) -> None:
        """Return the incremented JSON count and close the dependency."""
        repository = FakeVisitorCounterRepository(count=41)

        with patch('function_app.create_visitor_counter_repository', return_value=repository):
            response = increment_visitor(make_request('POST'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {'count': 42})
        self.assertEqual(repository.count, 42)
        self.assertTrue(repository.closed)

    def test_get_visitor_returns_service_unavailable_for_storage_failure(self) -> None:
        """Do not expose storage details when the counter cannot be read."""
        repository = FakeVisitorCounterRepository(should_fail=True)

        with patch('function_app.create_visitor_counter_repository', return_value=repository):
            response = get_visitor(make_request('GET'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            json.loads(response.get_body()),
            {'error': 'Visitor counter is temporarily unavailable.'},
        )
        self.assertTrue(repository.closed)
