from enum import Enum


class OutputMode(str, Enum):
    """Output mode for live scraping data storage."""

    APPEND = "append"  # Append each poll cycle to existing file
    OVERWRITE = "overwrite"  # Overwrite file on each poll cycle
