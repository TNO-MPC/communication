"""
This module contains helper functions.
"""

import logging
import signal
from contextlib import contextmanager
from typing import Any, Iterator

from tno.mpc.communication.exceptions import OptionalImportError


def handle_sigterm(*_args: Any) -> None:
    r"""
    Sigterm handler: raise KeyboardInterrupt.

    :param \*_args: unused arguments, accept any arguments
    :raise KeyboardInterrupt: raises a keyboard interrupt
    """
    raise KeyboardInterrupt()


def init(name: str, logger_level: int = logging.INFO) -> logging.Logger:
    """
    Initialize logger and sigterm handler.

    :param name: name of the logger
    :param logger_level: the logging level to use
    :return: a logger instance
    """
    signal.signal(signal.SIGTERM, handle_sigterm)

    logger = logging.getLogger(name)
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.setLevel(logger_level)
    return logger


@contextmanager
def redirect_importerror_to_optionalimporterror() -> Iterator[None]:
    """
    Redirect ImportError to OptionalImportError.

    :raise OptionalImportError: Managed context raised ImportError
    :return: Pass control from within a try block
    """
    try:
        yield
    except ImportError as e:  # pylint: disable=invalid-name
        raise OptionalImportError from e
