"""Main upload orchestrator — ties chunker, state tracker, and backend together."""
from __future__ import annotations

import logging
import os
import threading
from typing import Callable

from .chunker import plan_chunks, read_chunk, FileManifest, DEFAULT_CHUNK_SIZE
from .state import UploadState, PartState, StateTracker
from .backend import UploadBackend

log = logging.getLogger(__name__)

MAX_RETRIES = 3


class Uploader:
    """
    Uploads files through a pluggable backend with chunking, checksums,
    resume support, and progress reporting.
    """

    def __init__(self, backend: UploadBackend, state_dir: str,
                 chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.backend = backend
        self.tracker = StateTracker(state_dir)
        self.chunk_size = chunk_size

    def upload_file(
        self,
        file_path: str,
        key: str,
        metadata: dict | None = None,
        progress_callback: Callable[[str, int, int, float], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> bool:
        """
        Upload a file with automatic chunking, resume, and retry.

        Args:
            file_path: Local path to the file.
            key: Storage key/destination path.
            metadata: Optional metadata (tenant_id, etc.).
            progress_callback: Called as (file_path, parts_done, total_parts, bytes_fraction).
            cancel_event: Set to cancel the upload.

        Returns:
            True if upload completed successfully.
        """
        if not os.path.isfile(file_path):
            log.error("File not found: %s", file_path)
            return False

        # Plan chunks
        manifest = plan_chunks(file_path, self.chunk_size)
        log.info("Upload plan for %s: %d parts, %s bytes, multipart=%s",
                 file_path, manifest.total_parts, manifest.file_size, manifest.is_multipart)

        # Check for existing state (resume)
        state = self.tracker.load(manifest.file_sha256)
        if state and state.status == "completed":
            log.info("File already uploaded: %s", file_path)
            if progress_callback:
                progress_callback(file_path, state.total_parts, state.total_parts, 1.0)
            return True

        if state and state.upload_id:
            log.info("Resuming upload for %s (upload_id=%s, %d/%d parts done)",
                     file_path, state.upload_id, len(state.completed_parts), state.total_parts)
        else:
            # Initialize new upload
            state = self._init_state(manifest, key, metadata)
            if not state:
                return False

        # Upload pending parts
        success = self._upload_parts(state, manifest, progress_callback, cancel_event)

        if cancel_event and cancel_event.is_set():
            log.info("Upload cancelled for %s", file_path)
            self.tracker.save(state)
            return False

        if success:
            # Complete the upload
            if self._complete(state, key):
                state.status = "completed"
                self.tracker.save(state)
                log.info("Upload completed: %s", file_path)
                return True
            else:
                state.status = "failed"
                self.tracker.save(state)
                return False
        else:
            state.status = "failed"
            self.tracker.save(state)
            return False

    def upload_directory(
        self,
        dir_path: str,
        key_prefix: str,
        metadata: dict | None = None,
        progress_callback: Callable[[str, int, int, float], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> dict:
        """
        Upload all files in a directory.

        Returns:
            {"uploaded": [...], "failed": [...], "skipped": [...]}
        """
        results = {"uploaded": [], "failed": [], "skipped": []}

        files = []
        for root, _, filenames in os.walk(dir_path):
            for fname in filenames:
                files.append(os.path.join(root, fname))

        for fpath in files:
            if cancel_event and cancel_event.is_set():
                break
            rel = os.path.relpath(fpath, dir_path).replace("\\", "/")
            key = f"{key_prefix}/{rel}" if key_prefix else rel

            ok = self.upload_file(fpath, key, metadata, progress_callback, cancel_event)
            if ok:
                results["uploaded"].append(fpath)
            else:
                results["failed"].append(fpath)

        return results

    def resume_incomplete(self, progress_callback=None, cancel_event=None) -> list[str]:
        """Find and resume any incomplete uploads. Returns list of completed file hashes."""
        completed = []
        for sha in self.tracker.list_incomplete():
            state = self.tracker.load(sha)
            if not state or not os.path.isfile(state.file_path):
                continue
            manifest = plan_chunks(state.file_path, self.chunk_size)
            if manifest.file_sha256 != sha:
                log.warning("File changed since upload started: %s", state.file_path)
                self.tracker.clear(sha)
                continue
            success = self._upload_parts(state, manifest, progress_callback, cancel_event)
            if success and self._complete(state, ""):
                state.status = "completed"
                self.tracker.save(state)
                completed.append(sha)
        return completed

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _init_state(self, manifest: FileManifest, key: str,
                    metadata: dict | None) -> UploadState | None:
        """Initialize upload with backend and create state."""
        try:
            result = self.backend.init_upload(
                key, manifest.file_size, manifest.total_parts, metadata,
            )
        except Exception as e:
            log.error("Failed to init upload for %s: %s", manifest.file_path, e)
            return None

        state = UploadState(
            file_path=manifest.file_path,
            file_sha256=manifest.file_sha256,
            file_size=manifest.file_size,
            upload_id=result.upload_id,
            total_parts=manifest.total_parts,
            is_multipart=manifest.is_multipart,
            status="in_progress",
        )

        for chunk in manifest.chunks:
            state.parts[chunk.part_number] = PartState(part_number=chunk.part_number)

        self.tracker.save(state)
        return state

    def _upload_parts(
        self,
        state: UploadState,
        manifest: FileManifest,
        progress_callback: Callable | None,
        cancel_event: threading.Event | None,
    ) -> bool:
        """Upload all pending parts with retry."""
        total = state.total_parts
        done = len(state.completed_parts)

        for chunk in manifest.chunks:
            if cancel_event and cancel_event.is_set():
                return False

            part = state.parts.get(chunk.part_number)
            if part and part.status == "uploaded":
                continue  # Already done (resume)

            # Retry loop
            success = False
            for attempt in range(MAX_RETRIES):
                try:
                    data = read_chunk(manifest.file_path, chunk.offset, chunk.size)
                    result = self.backend.upload_part(
                        state.upload_id, chunk.part_number, data, chunk.checksum_md5,
                    )
                    if result.success:
                        state.mark_uploaded(chunk.part_number, result.etag)
                        self.tracker.save(state)
                        success = True
                        break
                    else:
                        state.mark_failed(chunk.part_number, result.error)
                        log.warning("Part %d failed (attempt %d): %s",
                                    chunk.part_number, attempt + 1, result.error)
                except Exception as e:
                    state.mark_failed(chunk.part_number, str(e))
                    log.warning("Part %d exception (attempt %d): %s",
                                chunk.part_number, attempt + 1, e)

            if not success:
                log.error("Part %d failed after %d attempts", chunk.part_number, MAX_RETRIES)
                return False

            done += 1
            if progress_callback:
                frac = done / total if total > 0 else 1.0
                progress_callback(manifest.file_path, done, total, frac)

        return True

    def _complete(self, state: UploadState, key: str) -> bool:
        """Finalize the upload."""
        parts = [
            {"part_number": p.part_number, "etag": p.etag}
            for p in sorted(state.parts.values(), key=lambda p: p.part_number)
            if p.status == "uploaded"
        ]
        try:
            return self.backend.complete_upload(state.upload_id, key, parts)
        except Exception as e:
            log.error("Failed to complete upload %s: %s", state.upload_id, e)
            return False
