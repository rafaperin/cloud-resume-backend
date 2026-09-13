"""Azure Cosmos DB for Table adapter for the visitor counter."""

import os
from collections.abc import Mapping
from typing import Protocol

from azure.core import MatchConditions
from azure.core.exceptions import AzureError, ResourceModifiedError, ResourceNotFoundError
from azure.data.tables import TableClient, UpdateMode
from azure.identity import DefaultAzureCredential

from application.errors import VisitorCounterNotFoundError, VisitorCounterStorageError
from domain.visitor_counter import VisitorCount


COUNTER_PARTITION_KEY = 'resume'
COUNTER_ROW_KEY = 'counter'
COUNT_PROPERTY_NAME = 'Count'
MAX_INCREMENT_ATTEMPTS = 5


class Closable(Protocol):
    """Describe the close operation used by Azure SDK clients and credentials."""

    def close(self) -> None:
        """Release resources held by the object."""


class CosmosTableVisitorCounterRepository:
    """Persist visitor counts in the seeded Cosmos DB for Table entity."""

    def __init__(
        self,
        table_client: TableClient,
        credential: Closable | None = None,
    ) -> None:
        self._table_client = table_client
        self._credential = credential

    @classmethod
    def from_environment(cls) -> 'CosmosTableVisitorCounterRepository':
        """Build a repository using Function App settings and managed identity."""
        endpoint = _read_required_setting('COSMOS_TABLE_ENDPOINT')
        table_name = _read_required_setting('COSMOS_TABLE_NAME')
        credential = DefaultAzureCredential()
        table_client = TableClient(
            endpoint=endpoint,
            table_name=table_name,
            credential=credential,
            audience='https://cosmos.azure.com',
        )
        return cls(table_client=table_client, credential=credential)

    def get_count(self) -> VisitorCount:
        """Return the count stored in the seeded entity."""
        entity = self._get_counter_entity()
        return VisitorCount(_read_count(entity))

    def increment_count(self) -> VisitorCount:
        """Increment the entity using optimistic concurrency and bounded retries."""
        for _ in range(MAX_INCREMENT_ATTEMPTS):
            entity = self._get_counter_entity()
            next_count = VisitorCount(_read_count(entity)).increment()

            try:
                self._table_client.update_entity(
                    entity={
                        'PartitionKey': COUNTER_PARTITION_KEY,
                        'RowKey': COUNTER_ROW_KEY,
                        COUNT_PROPERTY_NAME: next_count.value,
                    },
                    mode=UpdateMode.MERGE,
                    etag=_read_etag(entity),
                    match_condition=MatchConditions.IfNotModified,
                )
            except ResourceModifiedError:
                continue
            except AzureError as error:
                raise VisitorCounterStorageError('Unable to increment the visitor counter.') from error

            return next_count

        message = 'Visitor counter changed too frequently to increment safely.'
        raise VisitorCounterStorageError(message)

    def close(self) -> None:
        """Close the Azure SDK client and managed identity credential."""
        self._table_client.close()
        if self._credential is not None:
            self._credential.close()

    def _get_counter_entity(self) -> Mapping[str, object]:
        try:
            return self._table_client.get_entity(
                partition_key=COUNTER_PARTITION_KEY,
                row_key=COUNTER_ROW_KEY,
            )
        except ResourceNotFoundError as error:
            message = 'Visitor counter entity does not exist.'
            raise VisitorCounterNotFoundError(message) from error
        except AzureError as error:
            message = 'Unable to read the visitor counter.'
            raise VisitorCounterStorageError(message) from error


def _read_required_setting(name: str) -> str:
    """Return a required application setting or raise a storage error."""
    value = os.environ.get(name)
    if value:
        return value

    message = f'{name} must be configured.'
    raise VisitorCounterStorageError(message)


def _read_count(entity: Mapping[str, object]) -> int:
    """Validate and return the persisted Count property."""
    value = entity.get(COUNT_PROPERTY_NAME)
    if isinstance(value, int) and value >= 0:
        return value

    message = 'Visitor counter entity has an invalid Count property.'
    raise VisitorCounterStorageError(message)


def _read_etag(entity: Mapping[str, object]) -> str:
    """Return the entity ETag required for an optimistic-concurrency update."""
    metadata = getattr(entity, 'metadata', None)
    etag = metadata.get('etag') if isinstance(metadata, dict) else None
    if isinstance(etag, str) and etag:
        return etag

    message = 'Visitor counter entity does not include an ETag.'
    raise VisitorCounterStorageError(message)
