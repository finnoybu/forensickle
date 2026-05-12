import glob
import logging
import os
import subprocess

from .timestamp_utils import stat_time_to_epoch_ms

log = logging.getLogger(__name__)

try:
    import pwd
except ImportError:
    pwd = None


def get_users() -> list[dict]:
    """Enumerate system users from /etc/passwd."""
    users = []
    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) >= 7:
                    users.append({
                        "username": parts[0],
                        "uid": int(parts[2]),
                        "home": parts[5],
                        "shell": parts[6],
                    })
    except OSError as e:
        log.error("Failed to read /etc/passwd: %s", e)
    return users


def expand_user_paths(pattern: str) -> list[str]:
    """Expand paths with ~ or /home/* to all user home directories."""
    if "~" in pattern:
        users = get_users()
        paths = []
        for user in users:
            expanded = pattern.replace("~", user["home"])
            paths.extend(glob.glob(expanded))
        return paths
    return glob.glob(pattern)


def get_file_owner(path: str) -> str:
    """Return file owner username."""
    try:
        st = os.stat(path)
        if pwd:
            return pwd.getpwuid(st.st_uid).pw_name
        return str(st.st_uid)
    except (OSError, KeyError) as e:
        log.debug("Cannot get owner for %s: %s", path, e)
        return ""


def get_file_metadata(path: str) -> dict:
    """Return file metadata with timestamps as epoch ms."""
    try:
        st = os.stat(path)
        return {
            "path": path,
            "created_ms": stat_time_to_epoch_ms(st.st_ctime),
            "modified_ms": stat_time_to_epoch_ms(st.st_mtime),
            "changed_ms": stat_time_to_epoch_ms(st.st_ctime),
            "size": st.st_size,
        }
    except OSError as e:
        log.error("Cannot stat %s: %s", path, e)
        return {"path": path, "created_ms": None, "modified_ms": None, "changed_ms": None, "size": None}


def run_command(cmd: list[str], timeout: int = 30) -> str:
    """Run a command and return stdout. Returns empty string on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        log.debug("Command %s failed: %s", cmd, e)
        return ""
