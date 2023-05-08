"""
Import serialization logic provided by package (plugins).
"""
import importlib
from typing import Any, List

from tno.mpc.communication.exceptions import OptionalImportError

PLUGINS_STR = [
    "tno.mpc.communication.serializer_plugins.bitarray",
    "tno.mpc.communication.serializer_plugins.gmpy",
    "tno.mpc.communication.serializer_plugins.int",
    "tno.mpc.communication.serializer_plugins.numpy",
    "tno.mpc.communication.serializer_plugins.pandas",
    "tno.mpc.communication.serializer_plugins.tuple",
]
PLUGINS: List[Any] = []


def _import_plugins() -> None:
    """
    Import all plugins.
    """
    for plugin_str in PLUGINS_STR:
        try:
            plugin = importlib.import_module(plugin_str)
        except OptionalImportError:
            continue
        PLUGINS.append(plugin)


def register_defaults() -> None:
    """
    Registers all (de)serializers specified in PLUGINS_STR.
    """
    if not PLUGINS:
        _import_plugins()
    for plugin in PLUGINS:
        plugin.register()
