"""
Pytest fixtures for tno.mpc.communication.

This module is not exported as pytest plugin.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from tno.mpc.communication import Serializer


@pytest.fixture(autouse=True)
def mock_serialization_funcs(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """
    Mocks tno.mpc.communication.serialization dictionary of (de)serialization functions.

    This ensures that the effects of e.g. Serialization.clear_serialization_logic() are
    scoped to the current test.

    :param monkeypatch: pytest fixture monkeypatch.
    :return: yield control.
    """
    mock_serializer_funcs = Serializer._serializer_funcs.copy()
    mock_deserializer_funcs = Serializer._deserializer_funcs.copy()
    monkeypatch.setattr(Serializer, "_serializer_funcs", mock_serializer_funcs)
    monkeypatch.setattr(Serializer, "_deserializer_funcs", mock_deserializer_funcs)
    yield
