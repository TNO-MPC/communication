"""
This module contains helper functions
"""

import logging
import signal
from typing import Any


def handle_sigterm(*_args: Any) -> None:
    """
    Sigterm handler: raise KeyboardInterrupt.

    :param _args: unused arguments, accept any arguments
    :raise KeyboardInterrupt: raises a keyboard interrupt
    """
    raise KeyboardInterrupt()


def trim_string(string: str, max_length: int = 155) -> str:
    """
    Trim string for debug purposes.

    :param string: the strim to trim
    :param max_length: the maximal output length of the trimmed string
    :return: the trimmed string as '<first half> ... <second half>'
    """
    half_length = int((max_length - 5) / 2)
    return (
        (string[:half_length] + " ... " + string[-half_length:])
        if len(string) > max_length
        else string
    )


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
