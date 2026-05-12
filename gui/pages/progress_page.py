"""Progress page — threaded collection with live progress reporting."""
import logging
import os
import threading

import customtkinter as ctk

from ..theme import (
    FONT_HEADING, FONT_BODY, FONT_MONO, FONT_SMALL,
    PAD_OUTER, PAD_INNER, COLOR_SUCCESS, COLOR_ERROR, COLOR_MUTED,
)

log = logging.getLogger(__name__)


class ProgressPage(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        self._cancel_event = threading.Event()
        self._thread: threading.Thread | None = None

        # Header
        ctk.CTkLabel(
            self, text="Collecting...", font=FONT_HEADING,
        ).pack(pady=(PAD_OUTER, PAD_INNER))

        # Current artifact label
        self.current_label = ctk.CTkLabel(
            self, text="Preparing...", font=FONT_BODY, text_color=COLOR_MUTED,
        )
        self.current_label.pack()

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=500, height=16)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(PAD_INNER, PAD_INNER))

        # Counter label
        self.counter_label = ctk.CTkLabel(
            self, text="0 / 0", font=FONT_SMALL,
        )
        self.counter_label.pack()

        # Log textbox
        self.log_box = ctk.CTkTextbox(
            self, font=FONT_MONO, height=280, state="disabled", wrap="word",
        )
        self.log_box.pack(fill="both", expand=True, padx=PAD_OUTER, pady=PAD_INNER)

        # Cancel button
        self.cancel_btn = ctk.CTkButton(
            self, text="Cancel", width=120,
            fg_color=COLOR_ERROR, hover_color="#b33a3a",
            command=self._on_cancel,
        )
        self.cancel_btn.pack(pady=(0, PAD_OUTER))

    def on_enter(self):
        self._cancel_event.clear()
        self.progress_bar.set(0)
        self.counter_label.configure(text="0 / 0")
        self.current_label.configure(text="Preparing...")
        self.cancel_btn.configure(state="normal")
        self._clear_log()

        # Start collection in background thread
        self._thread = threading.Thread(target=self._run_collection, daemon=True)
        self._thread.start()

    def _run_collection(self):
        from forensickle.windows.orchestrator import run_config

        working_dir = self.app.shared["working_dir"]
        artifact_config = self.app.shared["artifact_config"]
        os.makedirs(working_dir, exist_ok=True)

        try:
            summary = run_config(
                working_dir=working_dir,
                artifact_config=artifact_config,
                progress_callback=self._on_progress,
                cancel_event=self._cancel_event,
            )
        except Exception as e:
            log.error("Collection failed: %s", e, exc_info=True)
            summary = {"artifacts": {}, "errors": [{"artifact": "_fatal", "error": str(e)}]}

        self.after(0, self._on_complete, summary)

    def _on_progress(self, name: str, status: str, current: int, total: int):
        self.after(0, self._update_ui, name, status, current, total)

    def _update_ui(self, name: str, status: str, current: int, total: int):
        if name == "_complete":
            return

        frac = current / total if total > 0 else 0
        self.progress_bar.set(frac)
        self.counter_label.configure(text=f"{current} / {total}")

        if status == "starting":
            from forensickle.windows.profiles import display_name
            self.current_label.configure(text=f"Processing: {display_name(name)}")
        else:
            color = COLOR_SUCCESS if status in ("parsed", "collected") else COLOR_ERROR
            status_icon = "✓" if status != "error" else "✗"
            self._append_log(f"  {status_icon}  {name}: {status}\n", color)

    def _on_complete(self, summary: dict):
        self.app.shared["summary"] = summary
        self.cancel_btn.configure(state="disabled")

        if summary.get("cancelled"):
            self.current_label.configure(text="Collection cancelled")
            self._append_log("\n  Collection was cancelled by user.\n", COLOR_ERROR)
        else:
            self.current_label.configure(text="Collection complete")

        # Auto-advance after brief pause
        self.after(800, lambda: self.app.show_page("CompletePage"))

    def _on_cancel(self):
        self._cancel_event.set()
        self.cancel_btn.configure(state="disabled")
        self.current_label.configure(text="Cancelling...")

    def _append_log(self, text: str, color: str | None = None):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
