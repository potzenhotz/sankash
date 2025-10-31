"""Centralized logging utility for Sankash."""

import logging
import sys
from pathlib import Path

# Create logger
logger = logging.getLogger("sankash")
logger.setLevel(logging.DEBUG)

# Create console handler with formatting
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)

# Add handler to logger
logger.addHandler(console_handler)


def log_state_change(state_name: str, method_name: str, **kwargs) -> None:
    """Log state changes with context."""
    logger.info(f"STATE [{state_name}] {method_name} called with: {kwargs}")


def log_error(context: str, error: Exception) -> None:
    """Log errors with context."""
    logger.error(f"ERROR in {context}: {type(error).__name__}: {str(error)}", exc_info=True)


def log_db_operation(operation: str, **kwargs) -> None:
    """Log database operations."""
    logger.debug(f"DB [{operation}] {kwargs}")
