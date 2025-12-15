"""
Shared regex patterns for Telegram callback query handlers.
Centralizes all pattern generation to eliminate duplication.
"""
from typing import List

from utils.keyboards import (
    MINUTE_INTERVALS,
    FOOD_LABELS,
    GYM_TYPES,
    YOGA_TYPES,
    PRANAYAM_TYPES,
)


def generate_number_pattern(start: int, end: int) -> str:
    """
    Generate a regex pattern matching numbers in a range.

    Args:
        start: Starting number (inclusive)
        end: Ending number (inclusive)

    Returns:
        Regex pattern string like "^1|2|3|4|5$"
    """
    numbers = [str(n) for n in range(start, end + 1)]
    return "^" + "|".join(numbers) + "$"


def generate_options_pattern(options: List[str]) -> str:
    """
    Generate a regex pattern matching a list of options.

    Args:
        options: List of option strings

    Returns:
        Regex pattern string
    """
    return "^" + "|".join(options) + "$"


def generate_hour_pattern(start: int = 0, end: int = 24) -> str:
    """
    Generate pattern for hour selection (0-23).

    Args:
        start: Starting hour (inclusive)
        end: Ending hour (exclusive)

    Returns:
        Regex pattern for hours
    """
    hours = [str(h) for h in range(start, end)]
    return "^" + "|".join(hours) + "$"


def generate_minute_pattern(
    hours: range = range(24),
    minutes: List[int] = None
) -> str:
    """
    Generate pattern for minute selection (e.g., "14:30").

    Args:
        hours: Range of hours to include
        minutes: List of minute values (default: MINUTE_INTERVALS)

    Returns:
        Regex pattern for hour:minute combinations
    """
    if minutes is None:
        minutes = MINUTE_INTERVALS

    combinations = []
    for hour in hours:
        for minute in minutes:
            combinations.append(f"{hour}:{minute:02d}")
            # Also match without leading zero for backwards compatibility
            if minute < 10:
                combinations.append(f"{hour}:{minute}")

    return "^" + "|".join(combinations) + "$"


# Pre-built patterns (computed once at import time)

# Date selection pattern
DATE_PATTERN = "^today|yday|daybeforeyday|3daysago|4daysago|other|now$"

# Hour pattern (0-23) - includes "now" for quick selection
HOUR_PATTERN = "^now|" + "|".join([str(h) for h in range(24)]) + "$"

# Minute pattern (all hour:minute combinations)
MINUTE_PATTERN = generate_minute_pattern()

# Number patterns for gym
SETS_PATTERN = generate_number_pattern(1, 10)
REPS_PATTERN = generate_number_pattern(1, 30)
WEIGHT_PATTERN = generate_number_pattern(1, 100)

# Generic number pattern (1-15, commonly used)
NUMBER_PATTERN = generate_number_pattern(1, 15)

# Food labels pattern
FOOD_LABEL_PATTERN = generate_options_pattern([opt[1] for opt in FOOD_LABELS])

# Gym types pattern
GYM_TYPE_PATTERN = generate_options_pattern([opt[1] for opt in GYM_TYPES])

# Yoga types pattern
YOGA_TYPE_PATTERN = generate_options_pattern([opt[1] for opt in YOGA_TYPES])

# Pranayam types pattern
PRANAYAM_TYPE_PATTERN = generate_options_pattern([opt[1] for opt in PRANAYAM_TYPES])

# Confirmation pattern
CONFIRMATION_PATTERN = "^confirm|cancel$"

# Timezone patterns
TIMEZONE_EFFECTIVE_PATTERN = "^sincefirstday|yesterday|today$"

# All timezone names supported
ALL_TIMEZONE_NAMES = [
    "Asia/Kolkata",
    "Europe/London",
    "Pacific/Honolulu",
    "America/Anchorage",
    "America/Los_Angeles",
    "America/Denver",
    "America/Chicago",
    "America/New_York",
]
TIMEZONE_NAME_PATTERN = generate_options_pattern(ALL_TIMEZONE_NAMES)
