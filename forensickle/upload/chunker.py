"""File chunking with per-chunk checksums."""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field


DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB — S3 minimum part size
SMALL_FILE_THRESHOLD = 50 * 1024 * 1024  # 50MB — below this, single upload


@dataclass
class ChunkInfo:
    part_number: int
    offset: int
    size: int
    checksum_md5: str = ""
    checksum_sha256: str = ""


@dataclass
class FileManifest:
    """Describes a file split into uploadable chunks."""
    file_path: str
    file_size: int
    file_sha256: str
    total_parts: int
    chunk_size: int
    is_multipart: bool
    chunks: list[ChunkInfo] = field(default_factory=list)


def compute_file_hash(path: str) -> str:
    """SHA256 of entire file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def plan_chunks(file_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE) -> FileManifest:
    """
    Plan how to chunk a file for upload. Returns a FileManifest with
    per-chunk offset, size, and checksums pre-computed.
    """
    file_size = os.path.getsize(file_path)
    file_sha256 = compute_file_hash(file_path)
    is_multipart = file_size > SMALL_FILE_THRESHOLD

    if not is_multipart:
        # Single chunk = whole file
        chunk = ChunkInfo(
            part_number=1,
            offset=0,
            size=file_size,
            checksum_sha256=file_sha256,
        )
        # Compute MD5 for the single part
        chunk.checksum_md5 = _md5_of_range(file_path, 0, file_size)
        return FileManifest(
            file_path=file_path,
            file_size=file_size,
            file_sha256=file_sha256,
            total_parts=1,
            chunk_size=file_size,
            is_multipart=False,
            chunks=[chunk],
        )

    # Multipart: split into chunks
    chunks = []
    offset = 0
    part = 1
    while offset < file_size:
        size = min(chunk_size, file_size - offset)
        md5 = _md5_of_range(file_path, offset, size)
        sha256 = _sha256_of_range(file_path, offset, size)
        chunks.append(ChunkInfo(
            part_number=part,
            offset=offset,
            size=size,
            checksum_md5=md5,
            checksum_sha256=sha256,
        ))
        offset += size
        part += 1

    return FileManifest(
        file_path=file_path,
        file_size=file_size,
        file_sha256=file_sha256,
        total_parts=len(chunks),
        chunk_size=chunk_size,
        is_multipart=True,
        chunks=chunks,
    )


def read_chunk(file_path: str, offset: int, size: int) -> bytes:
    """Read a specific byte range from a file."""
    with open(file_path, "rb") as f:
        f.seek(offset)
        return f.read(size)


def _md5_of_range(path: str, offset: int, size: int) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        f.seek(offset)
        remaining = size
        while remaining > 0:
            block = f.read(min(65536, remaining))
            if not block:
                break
            h.update(block)
            remaining -= len(block)
    return h.hexdigest()


def _sha256_of_range(path: str, offset: int, size: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        f.seek(offset)
        remaining = size
        while remaining > 0:
            block = f.read(min(65536, remaining))
            if not block:
                break
            h.update(block)
            remaining -= len(block)
    return h.hexdigest()
