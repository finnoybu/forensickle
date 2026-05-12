"""Upload state tracking for resume support."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict

log = logging.getLogger(__name__)


@dataclass
class PartState:
    part_number: int
    status: str = "pending"  # pending, uploaded, failed
    etag: str = ""
    attempts: int = 0
    error: str = ""


@dataclass
class UploadState:
    """Tracks the state of a single file upload for resume."""
    file_path: str
    file_sha256: str
    file_size: int
    upload_id: str = ""
    total_parts: int = 0
    is_multipart: bool = False
    parts: dict[int, PartState] = field(default_factory=dict)
    status: str = "initialized"  # initialized, in_progress, completed, failed

    @property
    def completed_parts(self) -> list[PartState]:
        return [p for p in self.parts.values() if p.status == "uploaded"]

    @property
    def pending_parts(self) -> list[PartState]:
        return [p for p in self.parts.values() if p.status != "uploaded"]

    @property
    def progress(self) -> float:
        if not self.parts:
            return 0.0
        return len(self.completed_parts) / len(self.parts)

    def mark_uploaded(self, part_number: int, etag: str = ""):
        if part_number in self.parts:
            self.parts[part_number].status = "uploaded"
            self.parts[part_number].etag = etag

    def mark_failed(self, part_number: int, error: str = ""):
        if part_number in self.parts:
            p = self.parts[part_number]
            p.status = "failed"
            p.error = error
            p.attempts += 1


class StateTracker:
    """Persists upload state to disk for resume across restarts."""

    def __init__(self, state_dir: str):
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def _state_path(self, file_sha256: str) -> str:
        return os.path.join(self.state_dir, f"{file_sha256}.upload.json")

    def save(self, state: UploadState) -> None:
        path = self._state_path(state.file_sha256)
        data = {
            "file_path": state.file_path,
            "file_sha256": state.file_sha256,
            "file_size": state.file_size,
            "upload_id": state.upload_id,
            "total_parts": state.total_parts,
            "is_multipart": state.is_multipart,
            "status": state.status,
            "parts": {
                str(k): asdict(v) for k, v in state.parts.items()
            },
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, file_sha256: str) -> UploadState | None:
        path = self._state_path(file_sha256)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            state = UploadState(
                file_path=data["file_path"],
                file_sha256=data["file_sha256"],
                file_size=data["file_size"],
                upload_id=data.get("upload_id", ""),
                total_parts=data.get("total_parts", 0),
                is_multipart=data.get("is_multipart", False),
                status=data.get("status", "initialized"),
            )
            for k, v in data.get("parts", {}).items():
                state.parts[int(k)] = PartState(**v)
            return state
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log.warning("Corrupt upload state for %s: %s", file_sha256, e)
            return None

    def clear(self, file_sha256: str) -> None:
        path = self._state_path(file_sha256)
        if os.path.isfile(path):
            os.remove(path)

    def list_incomplete(self) -> list[str]:
        """Returns SHA256 hashes of incomplete uploads."""
        results = []
        for fname in os.listdir(self.state_dir):
            if fname.endswith(".upload.json"):
                sha = fname.replace(".upload.json", "")
                state = self.load(sha)
                if state and state.status != "completed":
                    results.append(sha)
        return results
