"""
Logging configuration for MCP Tools Server.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler


def setup_logging():
    """Configure and set up logging for the application."""

    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"mcp_tools_{timestamp}.log"

    # Set up handlers
    handlers = [
        # Console handler with Rich formatting
        RichHandler(rich_tracebacks=True, console=Console(stderr=True)),
        # File handler with rotation (10MB max, keep 5 backups)
        logging.handlers.RotatingFileHandler(
            filename=log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        ),
    ]

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format="| %(levelname)-8s | %(name)s | %(message)s",
        datefmt="[%Y-%m-%d %H:%M:%S]",
        handlers=handlers,
        force=True,
    )

    # Set file handler to use more detailed format
    file_format = (
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(filename)s:%(lineno)d | %(message)s"
    )
    file_formatter = logging.Formatter(file_format, datefmt="%Y-%m-%d %H:%M:%S")
    handlers[1].setFormatter(file_formatter)

    # Configure third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)

    # Create main logger
    logger = logging.getLogger("mcp_tools")
    logger.info(f"Logging to file: {log_file}")

    return logger


# Create the logger instance for import by other modules
logger = setup_logging()
