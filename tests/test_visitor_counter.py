"""Tests for visitor-counter use cases, delivery, and Table API adapter."""

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import azure.functions as func
from azure.data.tables import TableEntity


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from application.errors import VisitorCounterStorageError
from application.visitor_counter import GetVisitorCount, IncrementVisitorCount
from domain.visitor_counter import VisitorCount
from function_app import get_visitor, increment_visitor
from infrastructure.cosmos_table_visitor_counter import CosmosTableVisitorCounterRepository


class FakeVisitorCounterRepository:
    """In-memory visitor-counter port implementation for tests."""

    def __init__(self, count: int = 0) -> None:
        self.count = count
        self.closed = False

    def get_count(self) -> VisitorCount:
        """Return the configured count."""
        return VisitorCount(self.count)

    def increment_count(self) -> VisitorCount:
        """Increment and return the configured count."""
        self.count += 1
        return VisitorCount(self.count)

    def close(self) -> None:
        """Record that the HTTP boundary released the repository."""
        self.closed = True


class FailingVisitorCounterRepository(FakeVisitorCounterRepository):
    """Repository that represents a temporary storage failure."""

    def get_count(self) -> VisitorCount:
        """Raise the application error mapped to HTTP 503."""
        raise VisitorCounterStorageError('Storage is unavailable.')


class FakeTableClient:
    """Minimal TableClient fake that records optimistic-concurrency updates."""

    def __init__(self, count: int = 0) -> None:
        self.entity = TableEntity(
            {
                'PartitionKey': 'resume',
                'RowKey': 'counter',
                'Count': count,
            }
        )
        self.entity.metadata['etag'] = 'etag-1'
        self.update_arguments: dict[str, object] | None = None
        self.closed = False

    def get_entity(self, partition_key: str, row_key: str) -> TableEntity:
        """Return the seeded entity."""
        self.last_partition_key = partition_key
        self.last_row_key = row_key
        return self.entity

    def update_entity(self, **kwargs: object) -> None:
        """Record the update request and persist the merged count for the fake."""
        self.update_arguments = kwargs
        entity = kwargs['entity']
        if not isinstance(entity, dict):
            raise AssertionError('Expected a dictionary entity.')
        self.entity['Count'] = entity['Count']

    def close(self) -> None:
        """Record that the adapter closed the client."""
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


class VisitorCounterUseCaseTests(unittest.TestCase):
    """Verify the use cases depend only on the repository port."""

    def test_get_visitor_count_returns_repository_value(self) -> None:
        """Return the current count without changing it."""
        repository = FakeVisitorCounterRepository(count=41)

        result = GetVisitorCount(repository).execute()

        self.assertEqual(result, VisitorCount(41))
        self.assertEqual(repository.count, 41)

    def test_increment_visitor_count_returns_next_value(self) -> None:
        """Increment the count through the persistence port."""
        repository = FakeVisitorCounterRepository(count=41)

        result = IncrementVisitorCount(repository).execute()

        self.assertEqual(result, VisitorCount(42))
        self.assertEqual(repository.count, 42)


class VisitorCounterHttpTests(unittest.TestCase):
    """Verify the public GET and POST visitor-counter contracts."""

    def test_get_visitor_returns_current_count(self) -> None:
        """Return the JSON count without incrementing it."""
        repository = FakeVisitorCounterRepository(count=41)

        with patch(
            'function_app.CosmosTableVisitorCounterRepository.from_environment',
            return_value=repository,
        ):
            response = get_visitor(make_request('GET'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {'count': 41})
        self.assertTrue(repository.closed)

    def test_post_visitor_increments_and_returns_count(self) -> None:
        """Return the incremented JSON count."""
        repository = FakeVisitorCounterRepository(count=41)

        with patch(
            'function_app.CosmosTableVisitorCounterRepository.from_environment',
            return_value=repository,
        ):
            response = increment_visitor(make_request('POST'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.get_body()), {'count': 42})
        self.assertTrue(repository.closed)

    def test_get_visitor_returns_service_unavailable_for_storage_failure(self) -> None:
        """Avoid exposing storage details when the counter cannot be read."""
        repository = FailingVisitorCounterRepository()

        with patch(
            'function_app.CosmosTableVisitorCounterRepository.from_environment',
            return_value=repository,
        ):
            response = get_visitor(make_request('GET'))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            json.loads(response.get_body()),
            {'error': 'Visitor counter is temporarily unavailable.'},
        )
        self.assertTrue(repository.closed)


class CosmosTableVisitorCounterRepositoryTests(unittest.TestCase):
    """Verify Cosmos Table adapter persistence behavior without Azure access."""

    def test_increment_count_uses_the_seeded_entity_and_its_etag(self) -> None:
        """Issue a conditional update with the next Count value."""
        table_client = FakeTableClient(count=41)
        repository = CosmosTableVisitorCounterRepository(table_client=table_client)

        result = repository.increment_count()

        self.assertEqual(result, VisitorCount(42))
        self.assertEqual(table_client.last_partition_key, 'resume')
        self.assertEqual(table_client.last_row_key, 'counter')
        self.assertIsNotNone(table_client.update_arguments)
        self.assertEqual(
            table_client.update_arguments['entity'],
            {'PartitionKey': 'resume', 'RowKey': 'counter', 'Count': 42},
        )
        self.assertEqual(table_client.update_arguments['etag'], 'etag-1')
