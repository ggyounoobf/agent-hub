"""
PDF utility functions.
"""

import os
import tempfile
from typing import Any, Dict

from shared.utils.logging import logger


def create_temp_pdf_file(file_bytes: bytes) -> str:
    """Create a temporary PDF file from bytes."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    temp_file.write(file_bytes)
    temp_file.close()
    return temp_file.name


def cleanup_temp_file(file_path: str) -> None:
    """Safely cleanup a temporary file."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {file_path}: {e}")


def validate_pdf_file(file_path: str) -> Dict[str, Any]:
    """Validate if file exists and is a PDF."""
    if not os.path.exists(file_path):
        return {"valid": False, "error": f"File not found: {file_path}"}

    if not file_path.lower().endswith(".pdf"):
        return {"valid": False, "error": "File must be a PDF"}

    return {"valid": True}


def get_pdf_summary(content: str, max_length: int = 200) -> str:
    """Generate a summary of PDF content."""
    if not content:
        return "Empty document"

    # Clean up the content
    cleaned = " ".join(content.split())

    if len(cleaned) <= max_length:
        return cleaned

    # Find a good breaking point
    summary = cleaned[:max_length]
    last_period = summary.rfind(".")
    last_space = summary.rfind(" ")

    if last_period > max_length * 0.7:
        return summary[: last_period + 1]
    elif last_space > max_length * 0.7:
        return summary[:last_space] + "..."
    else:
        return summary + "..."
