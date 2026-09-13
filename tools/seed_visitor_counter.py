"""Create the initial visitor-counter entity when it does not already exist."""

import logging
import os

from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableClient
from azure.identity import DefaultAzureCredential


COUNTER_ENTITY = {
    'PartitionKey': 'resume',
    'RowKey': 'counter',
    'Count': 0,
}


def read_required_setting(name: str) -> str:
    """Return a required deployment setting or raise a clear configuration error."""
    value = os.environ.get(name)
    if not value:
        message = f'{name} must be set.'
        raise RuntimeError(message)
    return value


def seed_counter() -> bool:
    """Create the counter entity and return whether this invocation created it."""
    endpoint = read_required_setting('COSMOS_TABLE_ENDPOINT')
    table_name = read_required_setting('COSMOS_TABLE_NAME')

    credential = DefaultAzureCredential()
    client = TableClient(
        endpoint=endpoint,
        table_name=table_name,
        credential=credential,
        audience='https://cosmos.azure.com',
    )

    try:
        client.create_entity(entity=COUNTER_ENTITY)
    except ResourceExistsError:
        return False
    finally:
        client.close()

    return True


def main() -> None:
    """Initialize the resume visitor counter without overwriting an existing count."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if seed_counter():
        logging.info('Created visitor counter entity with Count 0.')
        return

    logging.info('Visitor counter entity already exists; existing count was preserved.')


if __name__ == '__main__':
    main()
