"""Artifact configuration page — grouped list with Parse/Retain checkboxes."""
import customtkinter as ctk

from ..theme import FONT_HEADING, FONT_BODY, FONT_SMALL, PAD_OUTER, PAD_INNER
from ..widgets.category_group import CategoryGroup

from forensickle.windows.profiles import (
    get_categories, display_name, artifact_capabilities, save_config,
)


class ArtifactPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._vars: dict[str, dict] = {}
        self._checkboxes: dict[str, dict] = {}  # artifact -> {"parse_cb", "retain_cb"}
        self._built = False

    def _build(self):
        """Build the UI on first entry."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=PAD_OUTER, pady=(PAD_OUTER, PAD_INNER))
        header.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Configure Artifacts", font=FONT_HEADING,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="Save Config...", font=FONT_SMALL,
            width=120, height=28, fg_color="transparent", border_width=1,
            command=self._save_config,
        ).grid(row=0, column=1, sticky="e")

        # Scrollable artifact list
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=PAD_OUTER, pady=(0, PAD_INNER))

        categories = get_categories()
        for cat_name, defns in categories.items():
            artifacts = []
            for defn in defns:
                aid = defn.artifact_id
                caps = artifact_capabilities(aid)
                parse_var = ctk.BooleanVar(value=False)
                retain_var = ctk.BooleanVar(value=False)
                self._vars[aid] = {"parse": parse_var, "retain": retain_var}
                artifacts.append({
                    "name": aid,
                    "display_name": display_name(aid),
                    "parse_var": parse_var,
                    "retain_var": retain_var,
                    "can_parse": caps["can_parse"],
                    "can_retain": caps["can_retain"],
                })
            group = CategoryGroup(scroll, cat_name, artifacts)
            group.pack(fill="x", pady=(0, PAD_INNER))

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(side="bottom", fill="x", padx=PAD_OUTER, pady=(0, PAD_OUTER))

        ctk.CTkButton(
            nav, text="← Back", width=100, fg_color="transparent", border_width=1,
            command=lambda: self.app.show_page("ProfilePage"),
        ).pack(side="left")

        ctk.CTkButton(
            nav, text="Run Collection", width=160, font=FONT_BODY,
            command=self._on_run,
        ).pack(side="right")

        self._built = True

    def on_enter(self):
        if not self._built:
            self._build()
        config = self.app.shared.get("artifact_config", {})
        for aid, vars_ in self._vars.items():
            flags = config.get(aid, {})
            vars_["parse"].set(flags.get("parse", False))
            vars_["retain"].set(flags.get("retain", False))

    def _read_config(self) -> dict[str, dict]:
        config = {}
        for aid, vars_ in self._vars.items():
            p = vars_["parse"].get()
            r = vars_["retain"].get()
            if p or r:
                config[aid] = {"parse": p, "retain": r}
        return config

    def _save_config(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            title="Save Forensickle Config",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if path:
            config = self._read_config()
            profile = self.app.shared.get("profile", "custom")
            save_config(path, profile, config)

    def _on_run(self):
        from tkinter import messagebox
        config = self._read_config()
        if not config:
            messagebox.showwarning("No Artifacts", "Select at least one artifact to collect or parse.")
            return
        self.app.shared["artifact_config"] = config
        self.app.show_page("ProgressPage")
