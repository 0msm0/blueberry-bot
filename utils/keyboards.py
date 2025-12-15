"""
Shared inline keyboard generators for Telegram bot.
Consolidates all keyboard generation to eliminate duplication.
"""
from typing import List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# Standard minute intervals for time selection
MINUTE_INTERVALS = [0, 10, 20, 30, 40, 50]


def generate_date_keyboard(
    include_other: bool = True,
    extra_options: Optional[List[Tuple[str, str]]] = None
) -> List[List[InlineKeyboardButton]]:
    """
    Generate a date selection keyboard.

    Args:
        include_other: Whether to include "other" option
        extra_options: Additional options as list of (label, callback_data) tuples

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    # First row: Today, Yesterday, Day Before
    row1 = [
        InlineKeyboardButton("Today", callback_data="today"),
        InlineKeyboardButton("Yesterday", callback_data="yday"),
        InlineKeyboardButton("2 Days Ago", callback_data="daybeforeyday"),
    ]

    keyboard = [row1]

    # Second row: More days back + Other
    row2 = [
        InlineKeyboardButton("3 Days Ago", callback_data="3daysago"),
        InlineKeyboardButton("4 Days Ago", callback_data="4daysago"),
    ]
    if include_other:
        row2.append(InlineKeyboardButton("Other...", callback_data="other"))
    keyboard.append(row2)

    if extra_options:
        extra_row = [
            InlineKeyboardButton(label, callback_data=data)
            for label, data in extra_options
        ]
        keyboard.append(extra_row)

    return keyboard


def generate_hour_keyboard(
    start_hour: int = 0,
    end_hour: int = 24,
    columns: int = 4
) -> List[List[InlineKeyboardButton]]:
    """
    Generate an hour selection keyboard.

    Args:
        start_hour: Starting hour (inclusive)
        end_hour: Ending hour (exclusive)
        columns: Number of buttons per row

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    keyboard = []
    row = []

    for hour in range(start_hour, end_hour):
        label = f"{hour:02d}:00"
        button = InlineKeyboardButton(label, callback_data=str(hour))
        row.append(button)

        if len(row) == columns:
            keyboard.append(row)
            row = []

    if row:  # Add remaining buttons
        keyboard.append(row)

    return keyboard


def generate_minute_keyboard(
    hour: int,
    intervals: Optional[List[int]] = None
) -> List[List[InlineKeyboardButton]]:
    """
    Generate a minute selection keyboard for a specific hour.

    Args:
        hour: The hour to prefix the minutes with
        intervals: List of minute values (default: [0, 10, 20, 30, 40, 50])

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    if intervals is None:
        intervals = MINUTE_INTERVALS

    buttons = []
    for minute in intervals:
        label = f"{hour}:{minute:02d}"
        button = InlineKeyboardButton(label, callback_data=label)
        buttons.append(button)

    return [buttons]


def generate_number_keyboard(
    start: int,
    end: int,
    columns: int = 5,
    suffix: str = ""
) -> List[List[InlineKeyboardButton]]:
    """
    Generate a number selection keyboard.

    Useful for sets, reps, weights, etc.

    Args:
        start: Starting number (inclusive)
        end: Ending number (inclusive)
        columns: Number of buttons per row
        suffix: Optional suffix for display (e.g., " kg", " reps")

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    keyboard = []
    row = []

    for num in range(start, end + 1):
        label = f"{num}{suffix}"
        button = InlineKeyboardButton(label, callback_data=str(num))
        row.append(button)

        if len(row) == columns:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return keyboard


def generate_options_keyboard(
    options: List[Tuple[str, str]],
    columns: int = 3
) -> List[List[InlineKeyboardButton]]:
    """
    Generate a keyboard from a list of options.

    Args:
        options: List of (label, callback_data) tuples
        columns: Number of buttons per row

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    keyboard = []
    row = []

    for label, callback_data in options:
        button = InlineKeyboardButton(label, callback_data=callback_data)
        row.append(button)

        if len(row) == columns:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return keyboard


def generate_confirmation_keyboard(
    confirm_text: str = "Confirm",
    cancel_text: str = "Cancel",
    confirm_data: str = "confirm",
    cancel_data: str = "cancel"
) -> List[List[InlineKeyboardButton]]:
    """
    Generate a simple confirm/cancel keyboard.

    Returns:
        Keyboard layout for InlineKeyboardMarkup
    """
    return [[
        InlineKeyboardButton(confirm_text, callback_data=confirm_data),
        InlineKeyboardButton(cancel_text, callback_data=cancel_data),
    ]]


def make_markup(keyboard: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
    """
    Convenience function to wrap keyboard in InlineKeyboardMarkup.

    Args:
        keyboard: Keyboard layout from any generate_* function

    Returns:
        InlineKeyboardMarkup ready to use in reply_text
    """
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Pre-built common keyboards
DATE_KEYBOARD = generate_date_keyboard()
DATE_KEYBOARD_WITH_NOW = generate_date_keyboard(
    include_other=False,
    extra_options=[("Just Now", "now")]
)
HOUR_KEYBOARD = generate_hour_keyboard()
HOUR_KEYBOARD_WITH_NOW = generate_hour_keyboard()
# Add "Now" as first option in hour keyboard
HOUR_KEYBOARD_WITH_NOW.insert(0, [InlineKeyboardButton("Just Now", callback_data="now")])
SETS_KEYBOARD = generate_number_keyboard(1, 5, columns=5)
REPS_KEYBOARD = generate_number_keyboard(1, 15, columns=5)
WEIGHT_KEYBOARD = generate_number_keyboard(1, 50, columns=5, suffix=" kg")


# Food label options
FOOD_LABELS = [
    ("Breakfast", "breakfast"),
    ("Lunch", "lunch"),
    ("Evening Snacks", "evening_snacks"),
    ("Dinner", "dinner"),
    ("Night Snacks", "night_snacks"),
    ("Other", "other"),
]
FOOD_LABEL_KEYBOARD = generate_options_keyboard(FOOD_LABELS, columns=3)


# Gym exercise types
GYM_TYPES = [
    ("Biceps", "biceps"),
    ("Triceps", "triceps"),
    ("Chest", "chest"),
    ("Shoulder", "shoulder"),
    ("Back", "back"),
    ("Squats", "squats"),
    ("Deadlift", "deadlift"),
    ("Leg Press", "leg_press"),
    ("Calf Raise", "calf_raise"),
    ("Planks", "planks"),
    ("Pushups", "pushups"),
    ("Pullups", "pullups"),
    ("Other", "other"),
]
GYM_TYPE_KEYBOARD = generate_options_keyboard(GYM_TYPES, columns=4)


# Yoga types
YOGA_TYPES = [
    ("Surya Namaskar", "surya_namaskar"),
    ("Pranayama", "pranayama"),
    ("Meditation", "meditation"),
    ("Asanas", "asanas"),
    ("Stretching", "stretching"),
    ("Other", "other"),
]
YOGA_TYPE_KEYBOARD = generate_options_keyboard(YOGA_TYPES, columns=3)


# Pranayam types
PRANAYAM_TYPES = [
    ("Anulom Vilom", "anulom_vilom"),
    ("Kapalbhati", "kapalbhati"),
    ("Bhastrika", "bhastrika"),
    ("Bhramari", "bhramari"),
    ("Ujjayi", "ujjayi"),
    ("Other", "other"),
]
PRANAYAM_TYPE_KEYBOARD = generate_options_keyboard(PRANAYAM_TYPES, columns=3)
