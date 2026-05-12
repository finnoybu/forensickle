"""Profile selection page — Triage, Standard, Full, Custom, or load JSON."""
import customtkinter as ctk

from ..theme import FONT_HEADING, FONT_BODY, FONT_SMALL, PAD_OUTER, PAD_INNER, COLOR_MUTED

from forensickle.windows.profiles import PROFILES, get_profile, load_config


PROFILE_DESCRIPTIONS = {
    "triage": "Quick snapshot — processes, connections, persistence, hosts file. Parse only.",
    "standard": "General investigation — Triage + browser history, execution artifacts, SRUM.",
    "full": "Complete collection — all artifacts with source file retention.",
    "custom": "Build your own — select individual artifacts on the next screen.",
}


class ProfilePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        # Header
        ctk.CTkLabel(
            self, text="Select Collection Profile", font=FONT_HEADING,
        ).pack(pady=(PAD_OUTER, PAD_INNER))

        # Profile buttons
        self.selected = ctk.StringVar(value="")
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, PAD_INNER))

        for name in ("triage", "standard", "full", "custom"):
            display = name.title() if name != "full" else "Full Collection"
            ctk.CTkRadioButton(
                btn_frame, text=display, variable=self.selected, value=name,
                font=FONT_BODY, command=self._on_select,
            ).pack(anchor="w", pady=4, padx=PAD_OUTER)

        # Description label
        self.desc_label = ctk.CTkLabel(
            self, text="", font=FONT_SMALL, text_color=COLOR_MUTED,
            wraplength=600, justify="left",
        )
        self.desc_label.pack(pady=(0, PAD_INNER))

        # Load config file
        ctk.CTkButton(
            self, text="Load Config File...", font=FONT_SMALL,
            width=180, height=32, fg_color="transparent", border_width=1,
            command=self._load_config,
        ).pack(pady=(0, PAD_OUTER))

        # Navigation
        nav = ctk.CTkFrame(self, fg_color="transparent")
        nav.pack(side="bottom", fill="x", padx=PAD_OUTER, pady=PAD_OUTER)

        ctk.CTkButton(
            nav, text="← Back", width=100, fg_color="transparent", border_width=1,
            command=lambda: self.app.show_page("SplashPage"),
        ).pack(side="left")

        self.next_btn = ctk.CTkButton(
            nav, text="Next →", width=100, state="disabled",
            command=self._on_next,
        )
        self.next_btn.pack(side="right")

    def _on_select(self):
        name = self.selected.get()
        desc = PROFILE_DESCRIPTIONS.get(name, "")
        self.desc_label.configure(text=desc)
        self.next_btn.configure(state="normal")

    def _load_config(self):
        from tkinter import filedialog, messagebox
        path = filedialog.askopenfilename(
            title="Load Forensickle Config",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            config = load_config(path)
            self.app.shared["artifact_config"] = config
            self.app.shared["profile"] = "custom"
            self.app.show_page("ArtifactPage")
        except (ValueError, OSError) as e:
            messagebox.showerror("Invalid Config", str(e))

    def _on_next(self):
        name = self.selected.get()
        if name == "custom":
            self.app.shared["artifact_config"] = {}
        else:
            self.app.shared["artifact_config"] = get_profile(name)
        self.app.shared["profile"] = name
        self.app.show_page("ArtifactPage")

    def on_enter(self):
        pass
