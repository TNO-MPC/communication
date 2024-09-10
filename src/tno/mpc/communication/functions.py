"""
This module contains helper functions.
"""

import warnings
from contextlib import contextmanager
from typing import Iterator

from tno.mpc.communication.exceptions import OptionalImportError


@contextmanager
def redirect_importerror_oserror_to_optionalimporterror() -> Iterator[None]:
    """
    Redirect ImportError to OptionalImportError.

    :raise OptionalImportError: Managed context raised ImportError
    :return: Pass control from within a try block
    """
    try:
        yield
    except ImportError as exc:
        raise OptionalImportError from exc
    except OSError as exc:
        warnings.warn(f"OSError raised when loading optional serializer: {exc}")
        raise OptionalImportError from exc
