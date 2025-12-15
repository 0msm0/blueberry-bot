"""
Bot command definitions for Telegram bot menu.
Uses consistent naming conventions.
"""

# Command definitions with descriptions
# Format: command_name: description
BOT_COMMANDS = {
    # Registration and Setup
    "register": "Register to start using the bot",
    "set_timezone": "Set your timezone (important for accurate logs)",

    # Logging Commands - Activity
    "sleep": "Log your sleep and wake times",
    "food": "Log your meals",
    "water": "Log your water intake",
    "gym": "Log your workouts",
    "yoga": "Log yoga sessions",
    "pranayam": "Log breathing exercises",

    # Logging Commands - Productivity
    "thought": "Journal your thoughts",
    "task": "Log completed tasks",

    # Daily Prompts
    "gratitude": "Log 3 things you're grateful for",
    "themeoftheday": "Set your theme/intention for today",
    "affirmation": "Set your daily affirmations",
    "selflove": "Log 3 things you love about yourself",

    # Smart Commands
    "rundown": "Daily check-in - shows progress, logs missing items",
    "myday": "View summary of today's activities",
    "settings": "Configure daily prompt times",

    # Goals and Lists
    "goals": "Set your wellness goals (north star)",
    "affirmationlists": "Manage your affirmation lists library",

    # View History Commands
    "mysleep": "View your sleep history",
    "myfood": "View your food history",
    "mywater": "View your water intake history",
    "mygym": "View your workout history",
    "myyoga": "View your yoga history",
    "mypranayam": "View your pranayam history",
    "mythoughts": "View your journal entries",
    "mytasks": "View your completed tasks",
    "myprompts": "View today's daily prompts",
    "myaffirmations": "View your recent affirmations",
    "mygratitude": "View your recent gratitude entries",
    "mytheme": "View your recent themes",
    "myselflove": "View your recent self-love entries",
    "mygoals": "View your wellness goals",
    "myaffirmationlists": "View your affirmation lists",
    "mytimezone": "View your timezone settings",

    # General
    "start": "Welcome message and quick start guide",
    "help": "Show available commands",
    "cancel": "Cancel current operation",
}

# Backwards compatibility mapping (old -> new command names)
COMMAND_ALIASES = {
    "wakesleep": "sleep",
    "mywakesleep": "mysleep",
    "taskcompleted": "task",
    "mytaskcompleted": "mytasks",
    "mythought": "mythoughts",
    "theme": "themeoftheday",
}

# Commands that don't require registration
PUBLIC_COMMANDS = ["start", "register", "help"]

# Commands that require timezone to be set
TIMEZONE_REQUIRED_COMMANDS = ["sleep", "food", "water", "gym", "yoga", "pranayam"]


def get_commands_list():
    """Get commands formatted for BotFather setcommands."""
    return [(cmd, desc) for cmd, desc in BOT_COMMANDS.items()]


def get_help_text():
    """Generate help text message."""
    lines = ["<b>Available Commands:</b>\n"]

    lines.append("\n<b>Setup:</b>")
    lines.append("/register - Register to start")
    lines.append("/set_timezone - Set your timezone")

    lines.append("\n<b>Log Activities:</b>")
    lines.append("/sleep - Log sleep/wake times")
    lines.append("/food - Log meals")
    lines.append("/water - Log water intake")
    lines.append("/gym - Log workouts")
    lines.append("/yoga - Log yoga sessions")
    lines.append("/pranayam - Log breathing exercises")

    lines.append("\n<b>Log Productivity:</b>")
    lines.append("/thought - Journal thoughts")
    lines.append("/task - Log completed tasks")

    lines.append("\n<b>Daily Prompts:</b>")
    lines.append("/gratitude - Log what you're grateful for")
    lines.append("/themeoftheday - Set your daily theme/intention")
    lines.append("/affirmation - Set your daily affirmations")
    lines.append("/selflove - Log things you love about yourself")

    lines.append("\n<b>Smart Commands:</b>")
    lines.append("/rundown - Daily check-in (shows progress, fills gaps)")
    lines.append("/myday - View today's full summary")
    lines.append("/settings - Configure daily prompt times")

    lines.append("\n<b>Goals & Lists:</b>")
    lines.append("/goals - Set your wellness goals (north star)")
    lines.append("/affirmationlists - Manage affirmation lists library")

    lines.append("\n<b>View History:</b>")
    lines.append("/mysleep, /myfood, /mywater, /mygym, /myyoga, /mypranayam")
    lines.append("/mythoughts, /mytasks, /myprompts")
    lines.append("/mygratitude, /mytheme, /myaffirmations, /myselflove")
    lines.append("/mygoals, /myaffirmationlists")

    lines.append("\n<b>Tips:</b>")
    lines.append("- Use /cancel to cancel any operation")
    lines.append("- Use /skip to skip optional fields")
    lines.append("- Use /done to finish multi-item inputs")

    return "\n".join(lines)


# Legacy export for backwards compatibility
suggested_commands = BOT_COMMANDS
