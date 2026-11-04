"""Opt-in PostgreSQL fixture harness for integration tests.

Integration tests require DATABASE_URL to explicitly point at rpm_test. Each test gets a database
transaction that is rolled back, preserving both rpm_test's schema and the seeded rpm database.
"""

from collections.abc import Generator
from os import getenv

import pytest
from sqlalchemy import Connection, create_engine


@pytest.fixture
def integration_connection() -> Generator[Connection, None, None]:
    url = getenv("DATABASE_URL", "")
    if "/rpm_test" not in url:
        pytest.skip("integration tests require DATABASE_URL ending in /rpm_test")
    engine = create_engine(url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()
    engine.dispose()
