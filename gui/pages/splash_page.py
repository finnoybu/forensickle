"""Splash page — logo header + tabbed interface (Collector, Install, Config, About)."""
import os
import sys

import customtkinter as ctk
from PIL import Image

from ..theme import (
    FONT_BODY, FONT_SMALL, FONT_HEADING, VERSION,
    PAD_OUTER, PAD_INNER, COLOR_MUTED, COLOR_ACCENT, COLOR_SURFACE_LIGHT,
)
from ..widgets.tab_bar import TabBar
from ..widgets.theme_toggle import ThemeToggle


def _find_image(relative_path: str) -> str:
    """Resolve image path for source or PyInstaller bundle."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    path = os.path.join(base, relative_path)
    if os.path.isfile(path):
        return path
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, relative_path)


class SplashPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        # --- Logo header ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD_OUTER, pady=(PAD_OUTER, 0))

        logo_white_path = _find_image(os.path.join("images", "logo_white.png"))
        logo_black_path = _find_image(os.path.join("images", "logo_black.png"))
        if os.path.isfile(logo_white_path) and os.path.isfile(logo_black_path):
            logo_dark = Image.open(logo_white_path)
            logo_light = Image.open(logo_black_path)
            # Scale to reasonable height based on the dark logo dimensions
            scale = 80 / logo_dark.height
            w, h = int(logo_dark.width * scale), 80
            self._logo = ctk.CTkImage(light_image=logo_light, dark_image=logo_dark, size=(w, h))
            ctk.CTkLabel(header, image=self._logo, text="").pack(side="left")
        else:
            ctk.CTkLabel(header, text="Forensickle",
                         font=("Segoe UI", 28, "bold")).pack(side="left")

        ctk.CTkLabel(
            header, text=f"v{VERSION}", font=FONT_SMALL, text_color=COLOR_MUTED,
        ).pack(side="left", padx=(12, 0), anchor="s", pady=(0, 8))

        # Theme toggle (sun/moon/computer) — right side of header
        self._theme_toggle = ThemeToggle(header)
        self._theme_toggle.pack(side="right", anchor="ne")

        # --- Tabview ---
        self.tabs = ctk.CTkTabview(self, corner_radius=8)
        self.tabs.pack(fill="both", expand=True, padx=PAD_OUTER, pady=(PAD_INNER, PAD_OUTER))

        self._build_collector_tab(self.tabs.add("Collector"))
        self._build_install_tab(self.tabs.add("Install"))
        self._build_config_tab(self.tabs.add("Config"))
        self._build_about_tab(self.tabs.add("About"))

        self.tabs.set("Collector")

    # ------------------------------------------------------------------
    # Collector tab
    # ------------------------------------------------------------------
    def _build_collector_tab(self, tab):
        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(expand=True, fill="both", padx=PAD_INNER, pady=PAD_INNER)

        ctk.CTkLabel(
            content, text="Run a forensic collection on this machine.",
            font=FONT_BODY, text_color=COLOR_MUTED,
        ).pack(anchor="w", pady=(0, PAD_INNER))

        # Output directory
        dir_frame = ctk.CTkFrame(content, fg_color="transparent")
        dir_frame.pack(fill="x", pady=(0, PAD_INNER))

        ctk.CTkLabel(
            dir_frame, text="Output Directory:", font=FONT_BODY, anchor="w",
        ).pack(anchor="w")

        row = ctk.CTkFrame(dir_frame, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))
        row.columnconfigure(0, weight=1)

        default_output = os.path.join(os.path.expanduser("~"), "Documents", "Forensickle")
        self.dir_var = ctk.StringVar(value=default_output)
        self.dir_entry = ctk.CTkEntry(
            row, textvariable=self.dir_var, font=FONT_BODY,
        )
        self.dir_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            row, text="Browse...", width=100, command=self._browse_dir,
        ).grid(row=0, column=1)

        # Run button
        ctk.CTkButton(
            content, text="Run Collector", font=("Segoe UI", 15, "bold"),
            width=240, height=48, corner_radius=8,
            command=self._on_run,
        ).pack(pady=(PAD_OUTER, 0))

    # ------------------------------------------------------------------
    # Install tab (placeholder)
    # ------------------------------------------------------------------
    def _build_install_tab(self, tab):
        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(expand=True)

        ctk.CTkLabel(
            content, text="Install Forensickle Agent",
            font=FONT_HEADING,
        ).pack(pady=(PAD_OUTER, PAD_INNER))

        ctk.CTkLabel(
            content,
            text="Install the Forensickle agent on this machine for scheduled\n"
                 "collection and server-managed operation.",
            font=FONT_BODY, text_color=COLOR_MUTED, justify="center",
        ).pack(pady=(0, PAD_OUTER))

        ctk.CTkButton(
            content, text="Install Agent", width=200, height=40,
            state="disabled",
        ).pack()

        ctk.CTkLabel(
            content, text="Coming soon", font=FONT_SMALL, text_color=COLOR_MUTED,
        ).pack(pady=(8, 0))

    # ------------------------------------------------------------------
    # Config tab (placeholder)
    # ------------------------------------------------------------------
    def _build_config_tab(self, tab):
        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(expand=True)

        ctk.CTkLabel(
            content, text="Configuration",
            font=FONT_HEADING,
        ).pack(pady=(PAD_OUTER, PAD_INNER))

        ctk.CTkLabel(
            content,
            text="Manage collection profiles, tenant settings,\n"
                 "and agent configuration.",
            font=FONT_BODY, text_color=COLOR_MUTED, justify="center",
        ).pack(pady=(0, PAD_OUTER))

        # Tenant ID display (placeholder)
        tenant_frame = ctk.CTkFrame(content, fg_color=COLOR_SURFACE_LIGHT, corner_radius=8)
        tenant_frame.pack(fill="x", padx=PAD_OUTER, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            tenant_frame, text="Tenant ID:", font=FONT_SMALL, anchor="w",
        ).pack(anchor="w", padx=PAD_INNER, pady=(PAD_INNER, 0))

        ctk.CTkLabel(
            tenant_frame, text="Not configured",
            font=("Consolas", 12), text_color=COLOR_MUTED, anchor="w",
        ).pack(anchor="w", padx=PAD_INNER, pady=(2, PAD_INNER))

    # ------------------------------------------------------------------
    # About tab
    # ------------------------------------------------------------------
    def _build_about_tab(self, tab):
        content = ctk.CTkFrame(tab, fg_color="transparent")
        content.pack(expand=True)

        # Icon
        icon_path = _find_image(os.path.join("images", "png", "icon_128.png"))
        if os.path.isfile(icon_path):
            icon_img = Image.open(icon_path)
            self._about_icon = ctk.CTkImage(
                light_image=icon_img, dark_image=icon_img, size=(96, 96),
            )
            ctk.CTkLabel(content, image=self._about_icon, text="").pack(pady=(PAD_OUTER, PAD_INNER))

        ctk.CTkLabel(
            content, text="Forensickle", font=("Segoe UI", 22, "bold"),
        ).pack()

        ctk.CTkLabel(
            content, text=f"Version {VERSION}", font=FONT_BODY, text_color=COLOR_MUTED,
        ).pack(pady=(2, PAD_INNER))

        ctk.CTkLabel(
            content,
            text="Forensic collection and analysis tool.\n"
                 "Streamlined endpoint forensics for incident response.",
            font=FONT_BODY, text_color=COLOR_MUTED, justify="center",
        ).pack(pady=(0, PAD_OUTER))

        # Endpoint info
        try:
            from forensickle.windows.core.identity import get_endpoint_info
            info = get_endpoint_info()
            info_text = (
                f"Endpoint ID:  {info['endpoint_id']}\n"
                f"Hostname:     {info['hostname']}\n"
                f"OS:           {info['os']}\n"
                f"Architecture: {info['architecture']}"
            )
        except Exception:
            info_text = "Endpoint info unavailable"

        info_frame = ctk.CTkFrame(content, fg_color=COLOR_SURFACE_LIGHT, corner_radius=8)
        info_frame.pack(fill="x", padx=PAD_OUTER, pady=(0, PAD_INNER))

        ctk.CTkLabel(
            info_frame, text=info_text, font=("Consolas", 11),
            justify="left", anchor="w",
        ).pack(padx=PAD_INNER, pady=PAD_INNER)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _browse_dir(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.dir_var.set(path)

    def _on_run(self):
        self.app.shared["working_dir"] = self.dir_var.get()
        self.app.show_page("ProfilePage")

    def on_enter(self):
        pass
