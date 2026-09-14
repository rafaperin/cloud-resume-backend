"""Azure Functions v2 HTTP delivery layer for the Cloud Resume API."""

import json
import logging
from collections.abc import Callable

import azure.functions as func

from application.errors import VisitorCounterError
from application.visitor_counter import GetVisitorCount, IncrementVisitorCount
from domain.visitor_counter import VisitorCount
from infrastructure.table_visitor_counter import (
    TableVisitorCounterRepository,
    create_visitor_counter_repository,
)


logger = logging.getLogger(__name__)
app = func.FunctionApp()


@app.function_name(name='GetVisitorCount')
@app.route(route='visitor', methods=['GET'], auth_level=func.AuthLevel.ANONYMOUS)
def get_visitor(req: func.HttpRequest) -> func.HttpResponse:
    """Return the current resume visitor count."""
    del req
    return _execute_counter_request(GetVisitorCount)


@app.function_name(name='IncrementVisitorCount')
@app.route(route='visitor', methods=['POST'], auth_level=func.AuthLevel.ANONYMOUS)
def increment_visitor(req: func.HttpRequest) -> func.HttpResponse:
    """Increment and return the resume visitor count."""
    del req
    return _execute_counter_request(IncrementVisitorCount)


def _execute_counter_request(
    use_case_type: Callable[[TableVisitorCounterRepository], GetVisitorCount | IncrementVisitorCount],
) -> func.HttpResponse:
    """Compose the use case at the delivery boundary and map errors to HTTP."""
    repository: TableVisitorCounterRepository | None = None
    try:
        repository = create_visitor_counter_repository()
        count = use_case_type(repository).execute()
    except VisitorCounterError:
        logger.warning('visitor_counter_unavailable')
        return _json_response({'error': 'Visitor counter is temporarily unavailable.'}, status_code=503)
    finally:
        if repository is not None:
            repository.close()

    return _json_response({'count': count.value})


def _json_response(body: dict[str, int | str], status_code: int = 200) -> func.HttpResponse:
    """Create a consistent JSON HTTP response."""
    return func.HttpResponse(
        body=json.dumps(body),
        status_code=status_code,
        mimetype='application/json',
    )
