"""Artifact: Drivers — kernel and file-system drivers via registry, SCM state, and file hashing."""
import logging
import os
import subprocess
import sys

from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder
from ..core.timestamp_utils import filetime_to_epoch_ms

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None

try:
    import psutil
except ImportError:
    psutil = None

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

NAME = "drivers"
SERVICES_KEY = r"SYSTEM\CurrentControlSet\Services"
DRIVER_TYPES = {1: "Kernel Driver", 2: "File System Driver"}
START_MAP = {0: "Boot", 1: "System", 2: "Auto", 3: "Manual", 4: "Disabled"}
SYSROOT = os.environ.get("SystemRoot", r"C:\Windows")


def collect(collector):
    return []  # Live registry read — no file collection


def parse(collector) -> dict:
    result = ResultBuilder(NAME)
    if winreg is None:
        log.error("winreg not available (non-Windows)")
        return result

    live_states = _query_live_states()

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, SERVICES_KEY) as root:
            i = 0
            while True:
                try:
                    svc_name = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                try:
                    _process_driver(root, svc_name, live_states, result)
                except OSError:
                    continue
    except OSError as exc:
        log.error("Cannot open Services key: %s", exc)
    return result


def _process_driver(root, svc_name, live_states, result):
    with winreg.OpenKey(root, svc_name) as sk:
        svc_type = _val(sk, "Type")
        if svc_type not in DRIVER_TYPES:
            return
        image_path = _val(sk, "ImagePath") or ""
        start = _val(sk, "Start")
        delayed = bool(_val(sk, "DelayedAutostart"))
        key_path = f"HKLM\\{SERVICES_KEY}\\{svc_name}"

        # Key last modified (FILETIME)
        key_lm = filetime_to_epoch_ms(winreg.QueryInfoKey(sk)[2])

        driver_path = _resolve_path(image_path)
        hashes = file_hashes(driver_path) if driver_path else None
        ts = _file_timestamps(driver_path)

        result.add_entry({
            "driver_name": svc_name,
            "display_name": _val(sk, "DisplayName"),
            "service_type": DRIVER_TYPES.get(svc_type, str(svc_type)),
            "service_state": live_states.get(svc_name.lower()),
            "image_path": image_path,
            "start_mode": START_MAP.get(start, str(start) if start is not None else None),
            "driver_path": driver_path,
            "key_path": key_path,
            "key_last_modified": key_lm,
            "start_name": _val(sk, "ObjectName"),
            "control_accepted": _val(sk, "ControlsAccepted"),
            "delayed": delayed,
            "driver_md5": hashes["md5"] if hashes else None,
            "driver_sha1": hashes["sha1"] if hashes else None,
            "driver_sha256": hashes["sha256"] if hashes else None,
            "driver_created": ts[0],
            "driver_accessed": ts[1],
            "driver_modified": ts[2],
            "driver_entry_modified": ts[3],
        })


def _resolve_path(image_path):
    if not image_path:
        return None
    p = image_path.strip()
    low = p.lower()
    # Strip common NT-style prefixes
    if low.startswith("\\systemroot\\"):
        p = os.path.join(SYSROOT, p[len("\\systemroot\\"):])
    elif low.startswith("\\??\\"):
        p = p[len("\\??\\"):]
    elif low.startswith("system32\\") or low.startswith("system32/"):
        p = os.path.join(SYSROOT, p)
    if not os.path.isabs(p):
        p = os.path.join(SYSROOT, "System32", "drivers", p)
    p = os.path.expandvars(p)
    return p if os.path.isfile(p) else None


def _query_live_states():
    states = {}
    if psutil:
        try:
            for svc in psutil.win_service_iter():
                try:
                    states[svc.name().lower()] = svc.status()
                except Exception:
                    pass
        except Exception:
            pass
    return states


def _val(key, name):
    try:
        v, _ = winreg.QueryValueEx(key, name)
        return v
    except OSError:
        return None


def _file_timestamps(path):
    if not path or not os.path.isfile(path):
        return (None, None, None, None)
    try:
        s = os.stat(path)
        return (
            int(s.st_ctime * 1000),
            int(s.st_atime * 1000),
            int(s.st_mtime * 1000),
            int(s.st_ctime * 1000),  # Windows st_ctime = entry modified
        )
    except OSError:
        return (None, None, None, None)
