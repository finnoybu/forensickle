import glob
import logging
import os
import subprocess
from pathlib import Path

from .timestamp_utils import stat_time_to_epoch_ms

log = logging.getLogger(__name__)


def run_command(cmd: list[str], timeout: int = 30) -> str:
    """Runs a command, returns stdout."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log.warning("Command %s failed: %s", cmd, e)
        return ""


def get_users() -> list[dict]:
    """Enumerate macOS user accounts via dscl or /Users/ fallback."""
    users = []
    try:
        output = run_command(["dscl", ".", "-list", "/Users"])
        for username in output.splitlines():
            username = username.strip()
            if not username or username.startswith("_"):
                continue
            uid = run_command(["dscl", ".", "-read", f"/Users/{username}", "UniqueID"])
            uid = uid.split(":")[-1].strip() if ":" in uid else ""
            home = run_command(["dscl", ".", "-read", f"/Users/{username}", "NFSHomeDirectory"])
            home = home.split(":")[-1].strip() if ":" in home else f"/Users/{username}"
            if os.path.isdir(home):
                users.append({"username": username, "uid": uid, "home": home})
    except Exception as e:
        log.warning("dscl failed, falling back to /Users/: %s", e)

    if not users:
        try:
            for entry in os.scandir("/Users"):
                if entry.is_dir() and not entry.name.startswith(".") and entry.name != "Shared":
                    users.append({
                        "username": entry.name,
                        "uid": "",
                        "home": entry.path,
                    })
        except OSError as e:
            log.error("Cannot enumerate /Users/: %s", e)

    return users


def expand_user_paths(pattern: str) -> list[str]:
    """Expands ~/ paths across all user home directories."""
    if not pattern.startswith("~/"):
        return glob.glob(pattern)

    suffix = pattern[2:]  # strip ~/
    results = []
    for user in get_users():
        full = os.path.join(user["home"], suffix)
        matched = glob.glob(full)
        results.extend(matched)
    return results


def find_browser_profiles(base_path: str, db_filename: str) -> list[str]:
    """Finds browser DB files across user profiles and browser profile dirs."""
    results = []
    expanded = expand_user_paths(base_path) if base_path.startswith("~/") else [base_path]

    for base in expanded:
        # Direct match
        direct = os.path.join(base, db_filename)
        if os.path.isfile(direct):
            results.append(direct)
        # Profile subdirectories (Default, Profile 1, etc.)
        if os.path.isdir(base):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir():
                        candidate = os.path.join(entry.path, db_filename)
                        if os.path.isfile(candidate):
                            results.append(candidate)
            except OSError:
                pass
    return results


def get_file_metadata(path: str) -> dict:
    """Returns file metadata with timestamps as epoch ms."""
    try:
        st = os.stat(path)
        return {
            "path": path,
            "created_ms": stat_time_to_epoch_ms(st.st_birthtime)
            if hasattr(st, "st_birthtime")
            else stat_time_to_epoch_ms(st.st_ctime),
            "modified_ms": stat_time_to_epoch_ms(st.st_mtime),
            "size": st.st_size,
        }
    except OSError as e:
        log.warning("Cannot stat %s: %s", path, e)
        return {"path": path, "created_ms": None, "modified_ms": None, "size": None}
