"""Azure Functions v2 application entry point for the Cloud Resume API."""

import azure.functions as func


app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
