import hashlib
import logging
from functools import lru_cache

log = logging.getLogger(__name__)


def path_hash(path: str) -> str:
    """SHA256 of normalized path string (lowercase, forward slashes)."""
    normalized = path.lower().replace("\\", "/")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@lru_cache(maxsize=1024)
def file_hashes(path: str) -> dict | None:
    """Returns {"md5": ..., "sha1": ..., "sha256": ...} using 64KB chunked reads."""
    try:
        md5 = hashlib.md5()
        sha1 = hashlib.sha1()
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
        return {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest(),
        }
    except (OSError, IOError) as e:
        log.warning("Cannot hash %s: %s", path, e)
        return None
