"""Completion page — summary of results with action buttons."""
import os
import sys

import customtkinter as ctk

from ..theme import (
    FONT_HEADING, FONT_BODY, FONT_MONO, FONT_SMALL,
    PAD_OUTER, PAD_INNER, COLOR_SUCCESS, COLOR_ERROR, COLOR_MUTED,
)


class CompletePage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app

        # Header
        self.header_label = ctk.CTkLabel(
            self, text="Collection Complete", font=FONT_HEADING,
        )
        self.header_label.pack(pady=(PAD_OUTER, PAD_INNER))

        # Summary stats
        self.stats_label = ctk.CTkLabel(
            self, text="", font=FONT_BODY, justify="left",
        )
        self.stats_label.pack(pady=(0, PAD_INNER))

        # Detail log
        self.detail_box = ctk.CTkTextbox(
            self, font=FONT_MONO, height=320, state="disabled", wrap="word",
        )
        self.detail_box.pack(fill="both", expand=True, padx=PAD_OUTER, pady=(0, PAD_INNER))

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(0, PAD_OUTER))

        ctk.CTkButton(
            btn_frame, text="View Report", width=140,
            command=self._view_report,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Open Output Folder", width=180,
            command=self._open_folder,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="New Collection", width=140,
            fg_color="transparent", border_width=1,
            command=self._new_collection,
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Exit", width=80,
            fg_color="transparent", border_width=1,
            command=self._exit,
        ).pack(side="left", padx=8)

    def on_enter(self):
        summary = self.app.shared.get("summary", {})
        artifacts = summary.get("artifacts", {})
        errors = summary.get("errors", [])
        cancelled = summary.get("cancelled", False)

        # Counts
        total = len(artifacts)
        parsed = sum(1 for a in artifacts.values() if a.get("status") == "parsed")
        collected = sum(1 for a in artifacts.values() if a.get("status") == "collected")
        errored = sum(1 for a in artifacts.values() if a.get("status") == "error")
        total_entries = sum(a.get("entries", 0) for a in artifacts.values())

        if cancelled:
            self.header_label.configure(text="Collection Cancelled", text_color=COLOR_ERROR)
        else:
            self.header_label.configure(text="Collection Complete", text_color=COLOR_SUCCESS)

        stats = (
            f"Artifacts: {total}  |  Parsed: {parsed}  |  Collected: {collected}  |  "
            f"Errors: {errored}\n"
            f"Total entries: {total_entries:,}"
        )
        if summary.get("source_package"):
            stats += f"\nSource package: {summary['source_package']}"
        self.stats_label.configure(text=stats)

        # Detail log
        self.detail_box.configure(state="normal")
        self.detail_box.delete("1.0", "end")

        for name, info in artifacts.items():
            status = info.get("status", "unknown")
            icon = "✓" if status in ("parsed", "collected") else "✗"
            line = f"  {icon}  {name}: {status}"
            if "entries" in info:
                line += f" ({info['entries']} entries)"
            if "duration_ms" in info:
                line += f" [{info['duration_ms']}ms]"
            if "error" in info:
                line += f" — {info['error']}"
            self.detail_box.insert("end", line + "\n")

        if errors:
            self.detail_box.insert("end", "\nGlobal Errors:\n")
            for err in errors:
                self.detail_box.insert("end", f"  {err['artifact']}: {err['error']}\n")

        self.detail_box.configure(state="disabled")

    def _view_report(self):
        working_dir = self.app.shared.get("working_dir", "")
        if not working_dir:
            return
        try:
            from forensickle.viewer.report import generate_report, open_report
            path = generate_report(working_dir)
            open_report(path)
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Report Error", f"Failed to generate report: {e}")

    def _open_folder(self):
        path = self.app.shared.get("working_dir", "")
        if path and os.path.isdir(path):
            if sys.platform == "win32":
                os.startfile(path)

    def _new_collection(self):
        self.app.shared["profile"] = None
        self.app.shared["artifact_config"] = {}
        self.app.shared.pop("summary", None)
        self.app.show_page("SplashPage")

    def _exit(self):
        self.app.quit()
