import logging
import plistlib

log = logging.getLogger(__name__)


def read_plist(path: str) -> dict | list | None:
    """Reads a plist file (binary or XML). Returns None on error."""
    try:
        with open(path, "rb") as f:
            return plistlib.load(f)
    except (OSError, plistlib.InvalidFileException, Exception) as e:
        log.warning("Cannot read plist %s: %s", path, e)
        return None


def read_plist_from_bytes(data: bytes) -> dict | list | None:
    """Parses plist from bytes. Returns None on error."""
    try:
        return plistlib.loads(data)
    except (plistlib.InvalidFileException, Exception) as e:
        log.warning("Cannot parse plist bytes: %s", e)
        return None
