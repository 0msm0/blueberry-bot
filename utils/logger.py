"""
Centralized logging configuration for the bot.
All modules should use get_logger(__name__) to get their logger.

Features:
- Rotating file logs (5MB x 5 files)
- Separate error log file
- JSON logging for production (optional)
- Console output for development
- Structured logging helpers
"""
import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, Dict, Any

# Ensure logs directory exists
LOG_DIR = os.environ.get("LOG_DIR", "logs")
if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configuration from environment
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.environ.get(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_JSON = os.environ.get("LOG_JSON", "false").lower() == "true"

# File paths
LOG_FILE = os.path.join(LOG_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOG_DIR, "error.log")

# Create formatters
_standard_formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
_detailed_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s",
    datefmt=LOG_DATE_FORMAT
)


def _create_json_formatter():
    """Create JSON formatter if python-json-logger is available."""
    try:
        from pythonjsonlogger import jsonlogger

        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                log_record['timestamp'] = datetime.utcnow().isoformat()
                log_record['level'] = record.levelname
                log_record['logger'] = record.name
                log_record['module'] = record.module
                log_record['function'] = record.funcName
                log_record['line'] = record.lineno

        return CustomJsonFormatter()
    except ImportError:
        return None


# Create handlers
def _create_file_handler(filepath: str, level: int = logging.DEBUG) -> RotatingFileHandler:
    """Create a rotating file handler."""
    handler = RotatingFileHandler(
        filepath,
        maxBytes=5 * 1024 * 1024,  # 5MB per file
        backupCount=5,
        encoding="utf-8"
    )
    handler.setLevel(level)

    if LOG_JSON:
        json_formatter = _create_json_formatter()
        if json_formatter:
            handler.setFormatter(json_formatter)
        else:
            handler.setFormatter(_standard_formatter)
    else:
        handler.setFormatter(_standard_formatter)

    return handler


def _create_console_handler() -> logging.StreamHandler:
    """Create a console handler for development."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(_standard_formatter)
    return handler


def _create_error_handler() -> RotatingFileHandler:
    """Create a handler for error-level logs only."""
    handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    handler.setLevel(logging.ERROR)
    handler.setFormatter(_detailed_formatter)
    return handler


# Shared handlers (created once)
_file_handler = _create_file_handler(LOG_FILE)
_error_handler = _create_error_handler()
_console_handler = _create_console_handler()

# Cache for loggers
_loggers: Dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with consistent configuration.

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
        logger.info("Message here")

    Args:
        name: Usually __name__ of the calling module

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(_file_handler)
        logger.addHandler(_error_handler)

        # Console output when LOG_LEVEL is DEBUG or explicitly enabled
        if LOG_LEVEL == "DEBUG" or os.environ.get("LOG_CONSOLE", "false").lower() == "true":
            logger.addHandler(_console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    _loggers[name] = logger
    return logger


def log_user_action(
    logger: logging.Logger,
    user_id: int,
    action: str,
    details: str = "",
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a user action with consistent format.

    Args:
        logger: Logger instance
        user_id: User's database ID or chat_id
        action: Action being performed (e.g., "food_log", "registration")
        details: Additional details
        extra: Extra fields for JSON logging
    """
    msg = f"[User:{user_id}] {action}"
    if details:
        msg += f" | {details}"

    if extra and LOG_JSON:
        logger.info(msg, extra=extra)
    else:
        logger.info(msg)


def log_error(
    logger: logging.Logger,
    error: Exception,
    context: str = "",
    user_id: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with consistent format and traceback.

    Args:
        logger: Logger instance
        error: The exception that occurred
        context: Additional context about where the error occurred
        user_id: Optional user ID related to the error
        extra: Extra fields for JSON logging
    """
    parts = []
    if user_id:
        parts.append(f"[User:{user_id}]")
    if context:
        parts.append(f"[{context}]")
    parts.append(f"{type(error).__name__}: {str(error)}")

    msg = " ".join(parts)

    if extra and LOG_JSON:
        logger.error(msg, exc_info=True, extra=extra)
    else:
        logger.error(msg, exc_info=True)


def log_request(
    logger: logging.Logger,
    user_id: int,
    command: str,
    duration_ms: Optional[float] = None
) -> None:
    """
    Log an incoming command/request.

    Args:
        logger: Logger instance
        user_id: User's chat ID
        command: The command or action requested
        duration_ms: Optional processing duration in milliseconds
    """
    msg = f"[User:{user_id}] CMD: {command}"
    if duration_ms is not None:
        msg += f" | {duration_ms:.2f}ms"
    logger.info(msg)


def log_db_operation(
    logger: logging.Logger,
    operation: str,
    model: str,
    user_id: Optional[int] = None,
    record_id: Optional[int] = None,
    success: bool = True
) -> None:
    """
    Log a database operation.

    Args:
        logger: Logger instance
        operation: Type of operation (create, read, update, delete)
        model: Model name
        user_id: Optional user ID
        record_id: Optional record ID
        success: Whether operation succeeded
    """
    status = "OK" if success else "FAILED"
    parts = [f"DB:{operation.upper()}"]
    parts.append(f"model={model}")
    if user_id:
        parts.append(f"user={user_id}")
    if record_id:
        parts.append(f"id={record_id}")
    parts.append(f"status={status}")

    msg = " | ".join(parts)
    if success:
        logger.debug(msg)
    else:
        logger.warning(msg)


# Configure root logger to catch any unconfigured loggers
logging.basicConfig(
    level=logging.WARNING,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)

# Silence noisy third-party loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
