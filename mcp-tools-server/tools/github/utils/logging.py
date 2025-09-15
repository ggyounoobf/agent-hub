"""
Logging utilities for GitHub tools.
"""

import logging

from rich.logging import RichHandler

# Create logger
logger = logging.getLogger("github_tools")
logger.setLevel(logging.INFO)

# Add rich handler if not already present
if not logger.handlers:
    handler = RichHandler(rich_tracebacks=True)
    handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))
    logger.addHandler(handler)
