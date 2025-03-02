import logging
from logging.handlers import RotatingFileHandler
import os

from .request_id_filter import RequestIdFilter

from langchain.globals import set_debug

LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s] %(request_id)s - %(message)s"
LANG_CHAIN_LOG_FORMAT = "%(asctime)s %(name)s [%(levelname)s] - %(message)s"

LOGGING_DIR = "logs"
MAX_LOG_SIZE_BYTES = 1024 * 1024 * 1024  # 1GB


def setup_langchain_logging():
    # Enable Langchain debug mode
    set_debug(True)

    # Set up Langchain specific logging
    langchain_logger = logging.getLogger("langchain")
    langchain_logger.setLevel(logging.DEBUG)

    # File handler for Langchain logs
    file_handler = RotatingFileHandler(
        f"{LOGGING_DIR}/langchain.log", maxBytes=MAX_LOG_SIZE_BYTES, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LANG_CHAIN_LOG_FORMAT))
    langchain_logger.addHandler(file_handler)

    # Console handler for immediate feedback
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LANG_CHAIN_LOG_FORMAT))
    langchain_logger.addHandler(console_handler)


def setup_application_logging(is_verbose: bool, request_id_filter: RequestIdFilter):
    logger = logging.getLogger("hangoutsscheduler")

    if is_verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # File handler for application logs
    file_handler = RotatingFileHandler(
        f"{LOGGING_DIR}/application.log", maxBytes=MAX_LOG_SIZE_BYTES, backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    file_handler.addFilter(request_id_filter)
    logger.addHandler(file_handler)

    # Console handler for immediate feedback
    if is_verbose:
        ch = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        ch.setFormatter(formatter)
        ch.addFilter(request_id_filter)
        logger.addHandler(ch)


def setup_logging(is_verbose: bool, request_id_filter: RequestIdFilter):
    """Configure logging for both application and Langchain"""
    if not os.path.exists(LOGGING_DIR):
        os.makedirs(LOGGING_DIR)

    setup_application_logging(is_verbose, request_id_filter)

    if is_verbose:
        setup_langchain_logging()
