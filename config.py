"""Configuration for the webbooks static site generator."""

from pathlib import Path

# Directories
ROOT_DIR = Path(__file__).parent
BOOKS_DIR = ROOT_DIR / "books"
OUTPUT_DIR = ROOT_DIR / "docs"
TEMPLATES_DIR = ROOT_DIR / "templates"
STATIC_DIR = ROOT_DIR / "static"

# Screen configurations for Cloud Phone
SCREENS = {
    "qvga": {  # 240x320 - Nokia 215/225 4G
        "width": 240,
        "height": 320,
        "content_height": 280,  # Leave space for nav bar
        "padding": 8,
    },
    "qqvga": {  # 128x160
        "width": 128,
        "height": 160,
        "content_height": 120,
        "padding": 4,
    },
}

# Font size presets
FONT_SIZES = {
    "small": {
        "size_px": 14,
        "line_height": 1.3,
        "chars_per_line": 32,
        "lines_per_page": 12,
    },
    "medium": {
        "size_px": 16,
        "line_height": 1.4,
        "chars_per_line": 25,
        "lines_per_page": 9,
    },
    "large": {
        "size_px": 20,
        "line_height": 1.5,
        "chars_per_line": 22,
        "lines_per_page": 7,
    },
}

# Default font size for pagination
DEFAULT_FONT_SIZE = "medium"

# Navigation keys (Cloud Phone accesskey mapping)
NAV_KEYS = {
    "prev_page": "4",      # D-pad left
    "next_page": "6",      # D-pad right
    "toc": "5",            # Center key
    "home": "8",           # D-pad down
    "goto": "0",           # Key 0 - go to page
}
