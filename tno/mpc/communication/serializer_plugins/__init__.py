"""
Module that defines and registers (de)serialization logic for objects that the Serializer supports
by default.

_register_plugins defines a list of plugins (modules) that is to be registered. This list is a
subset of the other modules in this directory.
"""

from ._register import register_defaults as register_defaults
