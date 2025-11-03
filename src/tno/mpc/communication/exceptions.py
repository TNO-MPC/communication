"""
Collection of custom exceptions.
"""


class AnnotationError(Exception):
    """
    Raised when a function is incorrectly annotated.
    """


class RepetitionError(Exception):
    """
    Raised when the action has already been performed and should not be repeated.
    """


class OptionalImportError(ImportError):
    """
    Raised when an optional import is missing.
    """


class CommunicationError(Exception):
    """
    Raised when a communication operation failed.
    """


class NumpySerializationWarning(Warning):
    """
    Raised when the user tries to serialize a numpy array to warn the user about the limitations.
    """
