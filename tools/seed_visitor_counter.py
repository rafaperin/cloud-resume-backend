"""Create the initial visitor-counter document when it does not already exist."""

import logging
import os

from azure.cosmos import CosmosClient, exceptions
from azure.identity import DefaultAzureCredential


COUNTER_DOCUMENT = {
    'id': 'resume',
    'count': 0,
}


def read_required_setting(name: str) -> str:
    """Return a required deployment setting or raise a clear configuration error."""
    value = os.environ.get(name)
    if not value:
        message = f'{name} must be set.'
        raise RuntimeError(message)
    return value


def seed_counter() -> bool:
    """Create the counter document and return whether this invocation created it."""
    endpoint = read_required_setting('COSMOS_ENDPOINT')
    database_name = read_required_setting('COSMOS_DATABASE_NAME')
    container_name = read_required_setting('COSMOS_CONTAINER_NAME')

    credential = DefaultAzureCredential()
    client = CosmosClient(endpoint, credential=credential)
    container = client.get_database_client(database_name).get_container_client(container_name)

    try:
        container.create_item(body=COUNTER_DOCUMENT)
    except exceptions.CosmosHttpResponseError as error:
        if error.status_code != 409:
            raise
        return False
    finally:
        client.close()

    return True


def main() -> None:
    """Initialize the resume visitor counter without overwriting an existing count."""
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if seed_counter():
        logging.info('Created visitor counter document with count 0.')
        return

    logging.info('Visitor counter document already exists; existing count was preserved.')


if __name__ == '__main__':
    main()
