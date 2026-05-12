"""Abstract upload backend interface — plug in S3, local disk, etc."""
from __future__ import annotations

import logging
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass
class InitResult:
    """Returned by init_upload — provides upload_id and per-part URLs if applicable."""
    upload_id: str
    part_urls: dict[int, str] = None  # part_number -> presigned URL (optional)


@dataclass
class PartResult:
    """Returned after uploading a part."""
    part_number: int
    etag: str = ""
    success: bool = True
    error: str = ""


class UploadBackend(ABC):
    """
    Interface for upload destinations. Implementations handle the actual
    transport (S3 presigned URLs, direct HTTP, local filesystem, etc.).
    """

    @abstractmethod
    def init_upload(self, key: str, file_size: int, total_parts: int,
                    metadata: dict | None = None) -> InitResult:
        """
        Initialize an upload session.

        Args:
            key: Storage key/path for the file (e.g., "tenant_id/upload_id/file.zip").
            file_size: Total file size in bytes.
            total_parts: Number of parts for multipart, or 1 for single.
            metadata: Optional metadata dict (tenant_id, content_hash, etc.).

        Returns:
            InitResult with upload_id and optional presigned URLs.
        """

    @abstractmethod
    def upload_part(self, upload_id: str, part_number: int,
                    data: bytes, checksum_md5: str = "") -> PartResult:
        """
        Upload a single part/chunk.

        Args:
            upload_id: From init_upload().
            part_number: 1-based part number.
            data: Raw bytes for this part.
            checksum_md5: MD5 hex digest for integrity verification.

        Returns:
            PartResult with etag and success status.
        """

    @abstractmethod
    def complete_upload(self, upload_id: str, key: str,
                        parts: list[dict]) -> bool:
        """
        Finalize a multipart upload.

        Args:
            upload_id: From init_upload().
            key: Storage key (same as init_upload).
            parts: List of {"part_number": int, "etag": str} in order.

        Returns:
            True if successful.
        """

    @abstractmethod
    def abort_upload(self, upload_id: str, key: str) -> bool:
        """Abort/cancel an incomplete multipart upload."""

    def upload_single(self, key: str, data: bytes,
                      metadata: dict | None = None,
                      checksum_md5: str = "") -> bool:
        """
        Convenience: upload a small file in one shot.
        Default implementation uses init → upload_part → complete.
        """
        result = self.init_upload(key, len(data), 1, metadata)
        part = self.upload_part(result.upload_id, 1, data, checksum_md5)
        if not part.success:
            return False
        return self.complete_upload(
            result.upload_id, key,
            [{"part_number": 1, "etag": part.etag}],
        )


# ---------------------------------------------------------------------------
# Local filesystem backend — for testing and offline use
# ---------------------------------------------------------------------------

class LocalBackend(UploadBackend):
    """
    Writes uploads to a local directory. Useful for testing the upload
    pipeline without any network destination.
    """

    def __init__(self, dest_dir: str):
        self.dest_dir = dest_dir
        self._uploads: dict[str, dict] = {}  # upload_id -> {key, parts_dir, ...}
        os.makedirs(dest_dir, exist_ok=True)

    def init_upload(self, key: str, file_size: int, total_parts: int,
                    metadata: dict | None = None) -> InitResult:
        import uuid
        upload_id = str(uuid.uuid4())
        parts_dir = os.path.join(self.dest_dir, ".parts", upload_id)
        os.makedirs(parts_dir, exist_ok=True)

        self._uploads[upload_id] = {
            "key": key,
            "parts_dir": parts_dir,
            "total_parts": total_parts,
            "metadata": metadata or {},
        }

        # Write metadata
        import json
        meta_path = os.path.join(parts_dir, "_meta.json")
        with open(meta_path, "w") as f:
            json.dump({"key": key, "file_size": file_size,
                        "total_parts": total_parts, "metadata": metadata or {}}, f, indent=2)

        log.info("LocalBackend: init upload %s for key '%s' (%d parts)", upload_id, key, total_parts)
        return InitResult(upload_id=upload_id)

    def upload_part(self, upload_id: str, part_number: int,
                    data: bytes, checksum_md5: str = "") -> PartResult:
        info = self._uploads.get(upload_id)
        if not info:
            return PartResult(part_number=part_number, success=False, error="Unknown upload_id")

        part_path = os.path.join(info["parts_dir"], f"part_{part_number:05d}")
        with open(part_path, "wb") as f:
            f.write(data)

        # Verify checksum if provided
        if checksum_md5:
            import hashlib
            actual = hashlib.md5(data, usedforsecurity=False).hexdigest()
            if actual != checksum_md5:
                os.remove(part_path)
                return PartResult(
                    part_number=part_number, success=False,
                    error=f"MD5 mismatch: expected {checksum_md5}, got {actual}",
                )

        log.debug("LocalBackend: uploaded part %d (%d bytes)", part_number, len(data))
        return PartResult(part_number=part_number, etag=checksum_md5 or "local", success=True)

    def complete_upload(self, upload_id: str, key: str,
                        parts: list[dict]) -> bool:
        info = self._uploads.get(upload_id)
        if not info:
            log.error("LocalBackend: unknown upload_id %s", upload_id)
            return False

        # Reassemble parts into final file
        dest_path = os.path.join(self.dest_dir, key.replace("/", os.sep))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        sorted_parts = sorted(parts, key=lambda p: p["part_number"])
        with open(dest_path, "wb") as out:
            for p in sorted_parts:
                part_path = os.path.join(info["parts_dir"], f"part_{p['part_number']:05d}")
                with open(part_path, "rb") as inp:
                    shutil.copyfileobj(inp, out)

        # Cleanup parts
        shutil.rmtree(info["parts_dir"], ignore_errors=True)
        del self._uploads[upload_id]

        log.info("LocalBackend: completed upload for '%s' -> %s", key, dest_path)
        return True

    def abort_upload(self, upload_id: str, key: str) -> bool:
        info = self._uploads.pop(upload_id, None)
        if info:
            shutil.rmtree(info["parts_dir"], ignore_errors=True)
        return True
