"""Custom tab bar with independent text colors per tab state."""
import customtkinter as ctk

# (light_mode, dark_mode) tuples
ACTIVE_BG = "#008844"
ACTIVE_HOVER = "#006e37"
ACTIVE_TEXT = "#1a1a1a"  # dark on green — passes 4.61:1 (light), 3.82:1 (dark)

INACTIVE_BG = ("gray78", "#2e2e2e")
INACTIVE_HOVER = ("gray70", "#3a3a3a")
INACTIVE_TEXT = ("gray20", "#e0e0e0")  # dark on light bg, light on dark bg

BAR_BG = ("gray85", "#2e2e2e")

TAB_FONT = ("Segoe UI", 13, "bold")
TAB_HEIGHT = 32
TAB_WIDTH = 100
TAB_CORNER = 6


class TabBar(ctk.CTkFrame):
    """Horizontal tab bar with custom buttons and a stacked content area."""

    def __init__(self, parent, tab_names: list[str], **kwargs):
        super().__init__(parent, **kwargs)
        self._tabs: dict[str, dict] = {}
        self._active: str | None = None

        # Tab button strip
        self._bar = ctk.CTkFrame(self, fg_color=BAR_BG, corner_radius=TAB_CORNER)
        self._bar.pack(fill="x")

        btn_container = ctk.CTkFrame(self._bar, fg_color="transparent")
        btn_container.pack(padx=6, pady=5)

        for name in tab_names:
            btn = ctk.CTkButton(
                btn_container, text=name, font=TAB_FONT,
                width=TAB_WIDTH, height=TAB_HEIGHT, corner_radius=TAB_CORNER,
                fg_color=INACTIVE_BG, hover_color=INACTIVE_HOVER,
                text_color=INACTIVE_TEXT, border_width=0,
                command=lambda n=name: self.select(n),
            )
            btn.pack(side="left", padx=2)

            frame = ctk.CTkFrame(self, fg_color="transparent")
            self._tabs[name] = {"button": btn, "frame": frame}

        # Content container — fixed size, frames stack inside it
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="both", expand=True)
        self._content.grid_rowconfigure(0, weight=1)
        self._content.grid_columnconfigure(0, weight=1)

    def add(self, name: str) -> ctk.CTkFrame:
        """Return the content frame for a tab."""
        frame = self._tabs[name]["frame"]
        # Place all frames in the grid — only the active one will be raised
        frame.grid(in_=self._content, row=0, column=0, sticky="nsew")
        return frame

    def select(self, name: str):
        """Activate a tab."""
        if name == self._active:
            return

        # Deactivate previous
        if self._active and self._active in self._tabs:
            prev = self._tabs[self._active]
            prev["button"].configure(
                fg_color=INACTIVE_BG, hover_color=INACTIVE_HOVER,
                text_color=INACTIVE_TEXT,
            )

        # Activate new
        tab = self._tabs[name]
        tab["button"].configure(
            fg_color=ACTIVE_BG, hover_color=ACTIVE_HOVER,
            text_color=ACTIVE_TEXT,
        )
        tab["frame"].tkraise()
        self._active = name
