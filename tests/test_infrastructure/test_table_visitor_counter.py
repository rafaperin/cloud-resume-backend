"""Unit tests for the Azure Tables visitor-counter adapter."""

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from azure.core import MatchConditions
from azure.core.exceptions import ResourceExistsError, ResourceModifiedError, ResourceNotFoundError
from azure.data.tables import UpdateMode


BACKEND_DIRECTORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from application.errors import VisitorCounterNotFoundError, VisitorCounterStorageError
from domain.visitor_counter import VisitorCount
from infrastructure.table_visitor_counter import (
    TableVisitorCounterRepository,
    create_visitor_counter_repository,
)


class FakeTableEntity(dict[str, object]):
    """Mapping-shaped Table API entity with server metadata for adapter tests."""

    def __init__(self, count: int, etag: str) -> None:
        super().__init__(
            {
                'PartitionKey': 'resume',
                'RowKey': 'counter',
                'Count': count,
            }
        )
        self.metadata = {'etag': etag}


class FakeTableClient:
    """Minimal TableClient fake that records optimistic-concurrency updates."""

    def __init__(self, count: int = 0) -> None:
        self.entity = make_table_entity(count=count, etag='etag-1')
        self.entity_reads: list[FakeTableEntity] = []
        self.update_arguments: dict[str, object] | None = None
        self.update_calls: list[dict[str, object]] = []
        self.created_entity: dict[str, object] | None = None
        self.create_table_called = False
        self.update_errors: list[Exception] = []
        self.create_entity_error: Exception | None = None
        self.closed = False

    def get_entity(self, partition_key: str, row_key: str) -> FakeTableEntity:
        """Return the next configured entity read."""
        self.last_partition_key = partition_key
        self.last_row_key = row_key
        if self.entity_reads:
            return self.entity_reads.pop(0)
        return self.entity

    def update_entity(self, **kwargs: object) -> None:
        """Record the update request and persist the merged count for the fake."""
        recorded_arguments = dict(kwargs)
        requested_entity = kwargs['entity']
        if isinstance(requested_entity, dict):
            recorded_arguments['entity'] = requested_entity.copy()
        self.update_calls.append(recorded_arguments)
        if self.update_errors:
            raise self.update_errors.pop(0)
        self.update_arguments = kwargs
        entity = kwargs['entity']
        if not isinstance(entity, dict):
            raise AssertionError('Expected a dictionary entity.')
        self.entity['Count'] = entity['Count']

    def create_table(self) -> None:
        """Record initialization of the local table."""
        self.create_table_called = True

    def create_entity(self, entity: dict[str, object]) -> None:
        """Record initialization of the local counter entity."""
        if self.create_entity_error is not None:
            raise self.create_entity_error
        self.created_entity = entity

    def close(self) -> None:
        """Record that the adapter closed the client."""
        self.closed = True


def make_table_entity(count: int, etag: str) -> FakeTableEntity:
    """Build a Table API entity with its server-issued concurrency token."""
    return FakeTableEntity(count=count, etag=etag)


class TableVisitorCounterRepositoryTests(unittest.TestCase):
    """Verify Table API adapter persistence behavior without Azure access."""

    def test_increment_count_uses_the_seeded_entity_and_its_etag(self) -> None:
        """Issue a conditional update with the next Count value."""
        table_client = FakeTableClient(count=41)
        repository = TableVisitorCounterRepository(table_client=table_client)

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
        self.assertEqual(table_client.update_arguments['mode'], UpdateMode.MERGE)
        self.assertEqual(
            table_client.update_arguments['match_condition'],
            MatchConditions.IfNotModified,
        )

    def test_get_count_returns_the_seeded_entity_value(self) -> None:
        """Read the persisted Count property through the Table adapter."""
        repository = TableVisitorCounterRepository(table_client=FakeTableClient(count=41))

        self.assertEqual(repository.get_count(), VisitorCount(41))

    def test_increment_count_retries_an_optimistic_concurrency_conflict(self) -> None:
        """Reload the latest count and ETag before retrying a conflicted update."""
        table_client = FakeTableClient(count=41)
        table_client.entity_reads = [
            make_table_entity(count=41, etag='etag-1'),
            make_table_entity(count=42, etag='etag-2'),
        ]
        table_client.update_errors.append(ResourceModifiedError(message='Conflict.'))
        repository = TableVisitorCounterRepository(table_client=table_client)

        result = repository.increment_count()

        self.assertEqual(result, VisitorCount(43))
        self.assertEqual(len(table_client.update_calls), 2)
        self.assertEqual(table_client.update_calls[0]['entity']['Count'], 42)
        self.assertEqual(table_client.update_calls[0]['etag'], 'etag-1')
        self.assertEqual(table_client.update_calls[1]['entity']['Count'], 43)
        self.assertEqual(table_client.update_calls[1]['etag'], 'etag-2')
        self.assertTrue(
            all(
                call['match_condition'] is MatchConditions.IfNotModified
                for call in table_client.update_calls
            )
        )

    def test_increment_count_rejects_an_entity_without_an_etag(self) -> None:
        """Prevent unconditional writes when the Table API omits its ETag."""
        table_client = FakeTableClient(count=41)
        table_client.entity.metadata.pop('etag')
        repository = TableVisitorCounterRepository(table_client=table_client)

        with self.assertRaises(VisitorCounterStorageError):
            repository.increment_count()

        self.assertEqual(table_client.update_calls, [])

    def test_azurite_mode_initializes_a_local_seed_entity(self) -> None:
        """Use the local connection string without constructing Azure credentials."""
        table_client = FakeTableClient()

        with (
            patch.dict(
                os.environ,
                {
                    'VISITOR_COUNTER_STORAGE': 'azurite',
                    'AZURE_TABLES_CONNECTION_STRING': 'UseDevelopmentStorage=true',
                    'VISITOR_TABLE_NAME': 'visitorcounter',
                },
                clear=True,
            ),
            patch(
                'infrastructure.table_visitor_counter.TableClient.from_connection_string',
                return_value=table_client,
            ),
        ):
            repository = create_visitor_counter_repository()

        self.assertIsInstance(repository, TableVisitorCounterRepository)
        self.assertTrue(table_client.create_table_called)
        self.assertEqual(
            table_client.created_entity,
            {'PartitionKey': 'resume', 'RowKey': 'counter', 'Count': 0},
        )

    def test_azurite_mode_does_not_reset_an_existing_counter(self) -> None:
        """Preserve the existing local counter when its seed entity already exists."""
        table_client = FakeTableClient(count=9)
        table_client.create_entity_error = ResourceExistsError(message='Already exists.')

        with (
            patch.dict(
                os.environ,
                {
                    'VISITOR_COUNTER_STORAGE': 'azurite',
                    'AZURE_TABLES_CONNECTION_STRING': 'UseDevelopmentStorage=true',
                    'VISITOR_TABLE_NAME': 'visitorcounter',
                },
                clear=True,
            ),
            patch(
                'infrastructure.table_visitor_counter.TableClient.from_connection_string',
                return_value=table_client,
            ),
        ):
            repository = create_visitor_counter_repository()

        self.assertEqual(repository.get_count(), VisitorCount(9))
        self.assertIsNone(table_client.created_entity)

    def test_cosmos_mode_uses_managed_identity_settings(self) -> None:
        """Build the production adapter from app settings without local storage keys."""
        table_client = FakeTableClient()

        with (
            patch.dict(
                os.environ,
                {
                    'COSMOS_TABLE_ENDPOINT': 'https://example.table.cosmos.azure.com:443/',
                    'VISITOR_TABLE_NAME': 'visitorcounter',
                },
                clear=True,
            ),
            patch('infrastructure.table_visitor_counter.DefaultAzureCredential') as credential_type,
            patch('infrastructure.table_visitor_counter.TableClient', return_value=table_client) as client_type,
        ):
            repository = TableVisitorCounterRepository.from_cosmos_environment()

        self.assertIsInstance(repository, TableVisitorCounterRepository)
        client_type.assert_called_once()
        self.assertIs(repository._credential, credential_type.return_value)

    def test_missing_entity_maps_to_an_application_error(self) -> None:
        """Avoid leaking Azure SDK errors beyond the infrastructure boundary."""
        table_client = FakeTableClient()
        table_client.get_entity = lambda **_: (_ for _ in ()).throw(
            ResourceNotFoundError(message='Missing.')
        )
        repository = TableVisitorCounterRepository(table_client=table_client)

        with self.assertRaises(VisitorCounterNotFoundError):
            repository.get_count()

    def test_invalid_storage_mode_is_rejected(self) -> None:
        """Fail fast when local configuration selects an unknown adapter."""
        with patch.dict(os.environ, {'VISITOR_COUNTER_STORAGE': 'unknown'}, clear=True):
            with self.assertRaises(VisitorCounterStorageError):
                create_visitor_counter_repository()
