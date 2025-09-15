"""
Logging configuration for MCP OpenAI Client.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(name: str, log_to_file: bool = True, log_level: str = "INFO") -> logging.Logger:
    """Setup logging with both console and file output."""
    
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler (existing)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (new)
    if log_to_file:
        # Create logs directory
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"agent_hub_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Also create a "latest" symlink for easy access
        latest_log = logs_dir / "latest.log"
        if latest_log.exists():
            latest_log.unlink()

        try:
            # Try symlink (works on Linux/Mac, or Windows with Admin/DevMode)
            latest_log.symlink_to(log_file.name)
        except (OSError, NotImplementedError):
            # Fallback: copy the file instead
            import shutil
            shutil.copy2(log_file, latest_log)
    
    return logger