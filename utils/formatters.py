"""
Shared formatting utilities for dates, times, and messages.
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Any, Dict

# Separator used for storing multiple items in a single field
ITEM_SEPARATOR = ",,,"


def readable_datetime(dt: datetime, include_year: bool = False) -> str:
    """
    Format datetime for display to user.

    Args:
        dt: Datetime object to format
        include_year: Whether to include year in output

    Returns:
        Formatted string like "14 Dec, 09:30" or "14 Dec 2024, 09:30"
    """
    if dt is None:
        return "-"

    if include_year:
        return dt.strftime("%d %b %Y, %H:%M")
    return dt.strftime("%d %b, %H:%M")


def readable_date(d: date, include_year: bool = False) -> str:
    """
    Format date for display to user.

    Args:
        d: Date object to format
        include_year: Whether to include year in output

    Returns:
        Formatted string like "14 Dec" or "14 Dec 2024"
    """
    if d is None:
        return "-"

    if include_year:
        return d.strftime("%d %b %Y")
    return d.strftime("%d %b")


def readable_time(dt: datetime) -> str:
    """
    Format time portion of datetime for display.

    Args:
        dt: Datetime object

    Returns:
        Formatted string like "09:30"
    """
    if dt is None:
        return "-"
    return dt.strftime("%H:%M")


def parse_date_selection(selection: str, reference_date: Optional[date] = None) -> date:
    """
    Parse date selection callback data to actual date.

    Args:
        selection: One of "today", "yday", "daybeforeyday", "3daysago", "4daysago"
        reference_date: Reference date (default: today)

    Returns:
        Corresponding date object
    """
    if reference_date is None:
        reference_date = date.today()

    date_offsets = {
        "today": 0,
        "yday": 1,
        "daybeforeyday": 2,
        "3daysago": 3,
        "4daysago": 4,
    }

    offset = date_offsets.get(selection, 0)
    return reference_date - timedelta(days=offset)


def parse_custom_date(text: str, reference_date: Optional[date] = None) -> Optional[date]:
    """
    Parse custom date input from user.

    Accepts formats:
    - "DD/MM" or "DD-MM" (assumes current year)
    - "DD/MM/YYYY" or "DD-MM-YYYY"
    - "DD/MM/YY" or "DD-MM-YY"

    Args:
        text: User input text
        reference_date: Reference date for year (default: today)

    Returns:
        Parsed date or None if invalid
    """
    if reference_date is None:
        reference_date = date.today()

    text = text.strip()

    # Try different separators
    for sep in ["/", "-", "."]:
        if sep in text:
            parts = text.split(sep)
            break
    else:
        return None

    try:
        if len(parts) == 2:
            # DD/MM format - assume current year
            day = int(parts[0])
            month = int(parts[1])
            year = reference_date.year
        elif len(parts) == 3:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            # Handle 2-digit year
            if year < 100:
                year += 2000
        else:
            return None

        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def parse_time_selection(time_str: str) -> tuple:
    """
    Parse time selection callback data to hour and minute.

    Args:
        time_str: String like "14:30" or "9:0"

    Returns:
        Tuple of (hour, minute) as integers
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    return hour, minute


def combine_date_time(d: date, time_str: str) -> datetime:
    """
    Combine a date and time string into a datetime.

    Args:
        d: Date object
        time_str: Time string like "14:30"

    Returns:
        Combined datetime object
    """
    hour, minute = parse_time_selection(time_str)
    return datetime(d.year, d.month, d.day, hour, minute)


def join_items(items: List[str]) -> str:
    """
    Join multiple items into a single string for storage.

    Args:
        items: List of strings

    Returns:
        Joined string using ITEM_SEPARATOR
    """
    if not items:
        return ""
    return ITEM_SEPARATOR.join(items)


def split_items(stored: str) -> List[str]:
    """
    Split stored string back into items.

    Args:
        stored: String from database

    Returns:
        List of individual items
    """
    if not stored:
        return []
    return stored.split(ITEM_SEPARATOR)


def display_items(stored: str, separator: str = ", ") -> str:
    """
    Convert stored items string to display format.

    Args:
        stored: String from database with ITEM_SEPARATOR
        separator: Separator for display

    Returns:
        Human-readable string
    """
    items = split_items(stored)
    return separator.join(items) if items else "-"


def format_record_saved(
    title: str,
    fields: Dict[str, Any],
    success_message: str = "Record added"
) -> str:
    """
    Format a record saved confirmation message.

    Args:
        title: Title of the record type (e.g., "Food Log")
        fields: Dictionary of field names to values
        success_message: Custom success message

    Returns:
        HTML formatted message
    """
    lines = [f"{success_message} - \n"]

    for label, value in fields.items():
        if value is None or value == "":
            display_value = "-"
        elif isinstance(value, datetime):
            display_value = readable_datetime(value)
        elif isinstance(value, date):
            display_value = readable_date(value)
        elif isinstance(value, list):
            display_value = ", ".join(str(v) for v in value)
        else:
            display_value = str(value)

        lines.append(f"<b>{label}:</b> {display_value}")

    return "\n".join(lines)


def format_duration(start: datetime, end: datetime) -> str:
    """
    Format duration between two datetimes.

    Args:
        start: Start datetime
        end: End datetime

    Returns:
        Human readable duration like "7h 30m"
    """
    if start is None or end is None:
        return "-"

    diff = end - start
    total_minutes = int(diff.total_seconds() / 60)
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0 and minutes > 0:
        return f"{hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h"
    else:
        return f"{minutes}m"


def format_gym_sets(reps: str, weights: str) -> str:
    """
    Format gym reps and weights for display.

    Args:
        reps: Comma-separated reps string
        weights: Comma-separated weights string

    Returns:
        Formatted string showing each set
    """
    reps_list = [r.strip() for r in reps.split(",")]
    weights_list = [w.strip() for w in weights.split(",")]

    lines = []
    for i, (rep, weight) in enumerate(zip(reps_list, weights_list), 1):
        lines.append(f"Set {i}: {weight}kg x {rep} reps")

    return "\n".join(lines)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text or ""

    return text[:max_length - len(suffix)] + suffix


def escape_html(text: str) -> str:
    """
    Escape HTML special characters for Telegram HTML parse mode.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for HTML parse mode
    """
    if not text:
        return ""

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def mask_email(email: str) -> str:
    """
    Mask email address for logging purposes.

    Args:
        email: Email address to mask

    Returns:
        Masked email like "j***@e***"
    """
    if not email or "@" not in email:
        return "***"

    local, domain = email.split("@", 1)
    domain_parts = domain.split(".", 1)

    # Mask local part: show first char + ***
    masked_local = local[0] + "***" if local else "***"

    # Mask domain: show first char + ***
    masked_domain = domain_parts[0][0] + "***" if domain_parts[0] else "***"

    return f"{masked_local}@{masked_domain}"
