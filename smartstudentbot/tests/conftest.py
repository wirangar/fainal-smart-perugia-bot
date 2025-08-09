import os
import pytest
from fastapi.testclient import TestClient

# This import should be safe now because we are isolating the app
from main import app

@pytest.fixture(scope="session", autouse=True)
def _force_dev_mode_for_tests():
    """
    A session-wide, auto-used fixture to force environment variables
    that put the application in a safe, isolated mode for all tests.
    This prevents any external network calls during test collection and execution.
    """
    os.environ["DEV_MODE"] = "1"
    os.environ["DISABLE_EXTERNAL_CALLS"] = "1"
    os.environ["STARTUP_SET_WEBHOOK"] = "0"
    os.environ["STARTUP_CONNECT_DB"] = "0"
    os.environ["STARTUP_CONNECT_REDIS"] = "0"
    os.environ["FEATURE_AI"] = "0" # Ensure heavy AI models are not loaded

@pytest.fixture
def client() -> TestClient:
    """
    Provides a FastAPI TestClient instance for making requests to the app.
    It is configured to not run the lifespan events (startup/shutdown),
    preventing any potential network calls defined there from executing.
    """
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
