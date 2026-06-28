import logging

logger = logging.getLogger(__name__)


def get_logger(filename: str):
    return logging.getLogger(filename)
