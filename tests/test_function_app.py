"""Tests for the Azure Functions v2 application entry point."""

from pathlib import Path
import sys
import unittest

import azure.functions as func


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIRECTORY))

from function_app import app


class FunctionAppTests(unittest.TestCase):
    """Verify that Azure Functions can discover the v2 application object."""

    def test_application_uses_the_v2_function_app_type(self) -> None:
        """Expose a FunctionApp instance for decorator-based function registration."""
        self.assertIsInstance(app, func.FunctionApp)
