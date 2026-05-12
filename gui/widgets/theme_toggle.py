"""Theme toggle button — cycles through light (sun), dark (moon), system (monitor)."""
from __future__ import annotations

import json
import logging
import os
import sys

import customtkinter as ctk
from PIL import Image

log = logging.getLogger(__name__)

MODES = ["light", "dark", "system"]

_PREFS_FILENAME = "forensickle_prefs.json"
_ICON_SIZE = 22


def _find_image(relative_path: str) -> str | None:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    path = os.path.join(base, relative_path)
    if os.path.isfile(path):
        return path
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, relative_path)
    return path if os.path.isfile(path) else None


def _load_icon(name: str) -> ctk.CTkImage | None:
    """Load a toggle icon with light/dark variants."""
    dark_path = _find_image(os.path.join("images", "png", f"{name}_dark.png"))
    light_path = _find_image(os.path.join("images", "png", f"{name}_light.png"))
    if dark_path and light_path:
        return ctk.CTkImage(
            light_image=Image.open(dark_path),
            dark_image=Image.open(light_path),
            size=(_ICON_SIZE, _ICON_SIZE),
        )
    return None


def _prefs_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".forensickle", _PREFS_FILENAME)


def load_theme_pref() -> str:
    path = _prefs_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                mode = data.get("theme_mode", "dark")
                if mode in MODES:
                    return mode
    except (json.JSONDecodeError, OSError):
        pass
    return "dark"


def save_theme_pref(mode: str) -> None:
    path = _prefs_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {}
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
    except (json.JSONDecodeError, OSError):
        pass
    data["theme_mode"] = mode
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        log.warning("Failed to save theme preference: %s", e)


# Icon name mapping: current mode -> icon to show
_ICON_NAMES = {
    "light": "toggle-light",
    "dark": "toggle-dark",
    "system": "toggle-auto",
}

# Fallback unicode if PNGs not found
_FALLBACK_TEXT = {
    "light": "☀",
    "dark": "☽",
    "system": "⚙",
}


class ThemeToggle(ctk.CTkButton):
    def __init__(self, parent, initial_mode: str | None = None, **kwargs):
        self._mode = initial_mode or load_theme_pref()

        # Pre-load all icons
        self._icons = {}
        for mode, name in _ICON_NAMES.items():
            self._icons[mode] = _load_icon(name)

        kwargs.setdefault("width", 36)
        kwargs.setdefault("height", 36)
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("fg_color", "transparent")
        kwargs.setdefault("hover_color", ("gray80", "#3a3a3a"))
        kwargs.setdefault("text_color", ("gray10", "#e0e0e0"))

        icon = self._icons.get(self._mode)
        if icon:
            kwargs["image"] = icon
            kwargs["text"] = ""
        else:
            kwargs["text"] = _FALLBACK_TEXT[self._mode]
            kwargs.setdefault("font", ("Segoe UI", 18))

        super().__init__(parent, command=self._cycle, **kwargs)
        self._apply()

    def _cycle(self):
        idx = MODES.index(self._mode)
        self._mode = MODES[(idx + 1) % len(MODES)]
        self._apply()
        save_theme_pref(self._mode)

    def _apply(self):
        ctk.set_appearance_mode(self._mode)
        icon = self._icons.get(self._mode)
        if icon:
            self.configure(image=icon, text="")
        else:
            self.configure(text=_FALLBACK_TEXT[self._mode])

    @property
    def mode(self) -> str:
        return self._mode
