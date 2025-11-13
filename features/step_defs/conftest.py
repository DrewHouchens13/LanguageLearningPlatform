"""
pytest-bdd Configuration for BDD Tests
Shared fixtures and configuration for all BDD step definitions
"""

import pytest

# Enable Django database access for all BDD tests
pytest_plugins = ['pytest_django']


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Enable database access for all BDD tests automatically"""
    pass
