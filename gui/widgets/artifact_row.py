"""Single artifact row: display name + Parse checkbox + Retain checkbox."""
import customtkinter as ctk

from ..theme import FONT_BODY, PAD_SMALL


class ArtifactRow(ctk.CTkFrame):
    def __init__(self, parent, artifact_name: str, display_name: str,
                 parse_var: ctk.BooleanVar, retain_var: ctk.BooleanVar,
                 can_parse: bool = True, can_retain: bool = True):
        super().__init__(parent, fg_color="transparent")
        self.artifact_name = artifact_name

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=0)

        ctk.CTkLabel(
            self, text=display_name, font=FONT_BODY, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=(PAD_SMALL, 0))

        self.parse_cb = ctk.CTkCheckBox(
            self, text="", variable=parse_var, width=24,
            checkbox_width=20, checkbox_height=20,
            state="normal" if can_parse else "disabled",
        )
        self.parse_cb.grid(row=0, column=1, padx=(PAD_SMALL, PAD_SMALL))

        self.retain_cb = ctk.CTkCheckBox(
            self, text="", variable=retain_var, width=24,
            checkbox_width=20, checkbox_height=20,
            state="normal" if can_retain else "disabled",
        )
        self.retain_cb.grid(row=0, column=2, padx=(PAD_SMALL, PAD_SMALL))
