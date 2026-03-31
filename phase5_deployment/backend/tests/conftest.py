"""
Conftest — ensure CarbonEngine is initialized before any tests.
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "phase5_deployment", "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture(scope="session", autouse=True)
def init_engine():
    """Force engine initialization before any tests run."""
    from app.services.engine import engine
    engine.initialize()
    yield engine
