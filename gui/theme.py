"""Centralized theme configuration for Forensickle GUI."""
import ctypes
import os
import sys

import customtkinter as ctk

# Appearance
APPEARANCE_MODE = "dark"
COLOR_THEME = os.path.join(os.path.dirname(__file__), "forensickle_theme.json")

# Window
WINDOW_WIDTH = 940
WINDOW_HEIGHT = 680
WINDOW_TITLE = "Forensickle"

# Fonts (name, size, weight)
FONT_TITLE = ("Segoe UI", 28, "bold")
FONT_HEADING = ("Segoe UI", 18, "bold")
FONT_SUBHEADING = ("Segoe UI", 14, "bold")
FONT_BODY = ("Segoe UI", 13)
FONT_SMALL = ("Segoe UI", 11)
FONT_MONO = ("Consolas", 12)

# Padding
PAD_OUTER = 24
PAD_INNER = 12
PAD_SMALL = 6

# Colors (supplement the theme)
COLOR_ACCENT = "#00cc66"
COLOR_ACCENT_HOVER = "#00b359"
COLOR_SUCCESS = "#00cc66"
COLOR_ERROR = "#d94f4f"
COLOR_WARNING = "#d9a24f"
COLOR_MUTED = "#6b7280"  # Used in code; theme.json handles per-mode via widget colors
COLOR_SURFACE = "#2b2b2b"
COLOR_SURFACE_LIGHT = ("gray85", "#2e2e2e")

VERSION = "0.1.0"


def apply_theme():
    """Apply Forensickle theme settings. Call before creating any widgets."""
    # DPI awareness on Windows
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass

    # Load saved preference, fall back to dark
    from .widgets.theme_toggle import load_theme_pref
    mode = load_theme_pref()
    ctk.set_appearance_mode(mode)
    ctk.set_default_color_theme(COLOR_THEME)
