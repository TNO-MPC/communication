"""
Pytest fixtures for tno.mpc.communication.
"""

from typing import Iterator

import pytest

from tno.mpc.communication import serialization


@pytest.fixture(autouse=True)
def mock_serialization_funcs(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """
    Mocks tno.mpc.communication.serialization dictionary of (de)serialization functions.

    This ensures that the effects of e.g. Serialization.clear_serialization_logic() are
    scoped to the current test.

    :param monkeypatch: pytest fixture monkeypatch.
    :return: yield control.
    """
    mock_serializer_funcs = serialization.SERIALIZER_FUNCS.copy()
    mock_deserializer_funcs = serialization.DESERIALIZER_FUNCS.copy()
    monkeypatch.setattr(serialization, "SERIALIZER_FUNCS", mock_serializer_funcs)
    monkeypatch.setattr(serialization, "DESERIALIZER_FUNCS", mock_deserializer_funcs)
    yield
