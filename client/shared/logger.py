import logging
import sys
import os
from typing import Optional
from pathlib import Path


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Setup application-wide logging configuration."""

    if not log_level:
        log_level = os.getenv("LOG_LEVEL", "INFO")

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_path = Path(log_file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(file_path)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    logging.getLogger("mcp").setLevel(logging.INFO)
    logging.getLogger("google.genai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name."""
    return logging.getLogger(name)
