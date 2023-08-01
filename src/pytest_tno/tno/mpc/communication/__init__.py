"""
Pytest fixtures for the tno.mpc.communication module.

Separate directory pytest_tno adheres to the convention: https://docs.pytest.org/en/7.1.x/how-to/writing_plugins.html#writing-plugins.
"""

from pytest_tno.tno.mpc.communication.pytest_pool_fixtures import (
    determine_pool_scope as determine_pool_scope,
)
