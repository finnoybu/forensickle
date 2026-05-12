"""Collapsible category frame containing artifact rows."""
import customtkinter as ctk

from ..theme import FONT_SUBHEADING, PAD_SMALL, PAD_INNER, COLOR_SURFACE_LIGHT
from .artifact_row import ArtifactRow


class CategoryGroup(ctk.CTkFrame):
    def __init__(self, parent, category_name: str, artifacts: list[dict]):
        """
        Args:
            parent: Parent widget.
            category_name: Display name for the category header.
            artifacts: List of {"name", "display_name", "parse_var", "retain_var",
                                "can_parse", "can_retain"}.
        """
        super().__init__(parent, fg_color=COLOR_SURFACE_LIGHT, corner_radius=8)
        self.artifacts = artifacts
        self.rows: list[ArtifactRow] = []

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD_INNER, pady=(PAD_INNER, PAD_SMALL))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text=category_name, font=FONT_SUBHEADING, anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text="Parse", font=("Segoe UI", 10), width=50, anchor="center",
        ).grid(row=0, column=1, padx=(PAD_SMALL, 0))

        ctk.CTkLabel(
            header, text="Retain", font=("Segoe UI", 10), width=50, anchor="center",
        ).grid(row=0, column=2, padx=(PAD_SMALL, 0))

        # Artifact rows
        for art in artifacts:
            row = ArtifactRow(
                self, art["name"], art["display_name"],
                art["parse_var"], art["retain_var"],
                can_parse=art.get("can_parse", True),
                can_retain=art.get("can_retain", True),
            )
            row.pack(fill="x", padx=PAD_INNER, pady=1)
            self.rows.append(row)

        # Bottom padding
        ctk.CTkFrame(self, height=PAD_SMALL, fg_color="transparent").pack()
