import hashlib
import logging
from functools import lru_cache

log = logging.getLogger(__name__)

CHUNK_SIZE = 65536


def path_hash(path: str) -> str:
    """SHA256 of normalized path string (lowercase, forward slashes)."""
    normalized = path.lower().replace("\\", "/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@lru_cache(maxsize=512)
def file_hashes(path: str) -> dict | None:
    """Returns {"md5": ..., "sha1": ..., "sha256": ...} via chunked reads, or None on failure."""
    try:
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
        return {"md5": md5.hexdigest(), "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}
    except (OSError, IOError) as e:
        log.warning("Failed to hash %s: %s", path, e)
        return None
