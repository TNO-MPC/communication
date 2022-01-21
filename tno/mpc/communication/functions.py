"""
This module contains helper functions
"""

import logging
import signal
from typing import Any


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
