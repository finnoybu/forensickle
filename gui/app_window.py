"""Main application window with page-switching controller."""
import os
import sys

import customtkinter as ctk

from .theme import (
    WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE, VERSION, apply_theme,
)
from .pages.splash_page import SplashPage
from .pages.profile_page import ProfilePage
from .pages.artifact_page import ArtifactPage
from .pages.progress_page import ProgressPage
from .pages.complete_page import CompletePage


class ForensickleApp(ctk.CTk):
    def __init__(self):
        apply_theme()
        super().__init__()

        self.title(f"{WINDOW_TITLE} v{VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(800, 600)
        self.resizable(True, True)

        # Window icon
        ico_path = self._find_asset(os.path.join("images", "icon.ico"))
        if ico_path:
            self.iconbitmap(ico_path)

        # Shared state across all pages
        self.shared = {
            "profile": None,
            "artifact_config": {},
            "working_dir": "",
        }

        # Container for stacked pages
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Create all pages
        self.pages: dict[str, ctk.CTkFrame] = {}
        for PageClass in (SplashPage, ProfilePage, ArtifactPage, ProgressPage, CompletePage):
            page = PageClass(container, self)
            name = PageClass.__name__
            self.pages[name] = page
            page.grid(row=0, column=0, sticky="nsew")

        self.show_page("SplashPage")

    def show_page(self, name: str):
        page = self.pages[name]
        if hasattr(page, "on_enter"):
            page.on_enter()
        page.tkraise()

    @staticmethod
    def _find_asset(relative_path: str) -> str | None:
        """Resolve asset path for source or PyInstaller bundle."""
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
        path = os.path.join(base, relative_path)
        if os.path.isfile(path):
            return path
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, relative_path)
        return path if os.path.isfile(path) else None
