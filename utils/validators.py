"""
Input validation utilities.
"""
import re
from typing import Tuple, Optional
from datetime import datetime

# Email regex pattern
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.

    Args:
        email: Email string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"

    email = email.strip()

    if len(email) > 255:
        return False, "Email is too long (max 255 characters)"

    if not EMAIL_PATTERN.match(email):
        return False, "Invalid email format"

    return True, ""


def validate_name(name: str, min_length: int = 2, max_length: int = 30) -> Tuple[bool, str]:
    """
    Validate user name.

    Args:
        name: Name string to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name is required"

    name = name.strip()

    if len(name) < min_length:
        return False, f"Name is too short (min {min_length} characters)"

    if len(name) > max_length:
        return False, f"Name is too long (max {max_length} characters)"

    # Check for valid characters (letters, spaces, hyphens, apostrophes)
    if not re.match(r"^[a-zA-Z\s\-']+$", name):
        return False, "Name can only contain letters, spaces, hyphens, and apostrophes"

    return True, ""


def validate_text_length(
    text: str,
    field_name: str = "Text",
    min_length: int = 1,
    max_length: int = 500
) -> Tuple[bool, str]:
    """
    Validate text field length.

    Args:
        text: Text to validate
        field_name: Name of field for error messages
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text:
        if min_length > 0:
            return False, f"{field_name} is required"
        return True, ""

    text = text.strip()

    if len(text) < min_length:
        return False, f"{field_name} is too short (min {min_length} characters)"

    if len(text) > max_length:
        return False, f"{field_name} is too long (max {max_length} characters)"

    return True, ""


def validate_positive_integer(
    value: str,
    field_name: str = "Value",
    min_val: int = 1,
    max_val: int = 1000
) -> Tuple[bool, Optional[int], str]:
    """
    Validate and parse positive integer.

    Args:
        value: String value to validate
        field_name: Name of field for error messages
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        Tuple of (is_valid, parsed_value, error_message)
    """
    if not value:
        return False, None, f"{field_name} is required"

    try:
        num = int(value.strip())
    except ValueError:
        return False, None, f"{field_name} must be a number"

    if num < min_val:
        return False, None, f"{field_name} must be at least {min_val}"

    if num > max_val:
        return False, None, f"{field_name} must be at most {max_val}"

    return True, num, ""


def validate_datetime_order(
    start: datetime,
    end: datetime,
    start_name: str = "Start time",
    end_name: str = "End time"
) -> Tuple[bool, str]:
    """
    Validate that end datetime is after start datetime.

    Args:
        start: Start datetime
        end: End datetime
        start_name: Name of start field for error messages
        end_name: Name of end field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if start is None or end is None:
        return False, "Both times are required"

    if end <= start:
        return False, f"{end_name} must be after {start_name}"

    return True, ""


def validate_not_future(
    dt: datetime,
    field_name: str = "Time"
) -> Tuple[bool, str]:
    """
    Validate that datetime is not in the future.

    Args:
        dt: Datetime to validate
        field_name: Name of field for error messages

    Returns:
        Tuple of (is_valid, error_message)
    """
    if dt is None:
        return False, f"{field_name} is required"

    if dt > datetime.now():
        return False, f"{field_name} cannot be in the future"

    return True, ""


def sanitize_text(text: str) -> str:
    """
    Sanitize user input text.

    Args:
        text: Raw user input

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Strip whitespace
    text = text.strip()

    # Remove null bytes
    text = text.replace("\x00", "")

    # Normalize whitespace (multiple spaces to single)
    text = re.sub(r"\s+", " ", text)

    return text


def validate_file_extension(
    filename: str,
    allowed_extensions: list = None
) -> Tuple[bool, str]:
    """
    Validate file extension.

    Args:
        filename: Name of file
        allowed_extensions: List of allowed extensions (without dot)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if allowed_extensions is None:
        allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]

    if not filename:
        return False, "Filename is required"

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in allowed_extensions:
        return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"

    return True, ""
