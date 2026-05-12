"""Artifact: Windows Services — registry enumeration, SCM state, binary and ServiceDll hashing."""
import logging
import os
import re
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

NAME = "services"
SERVICES_KEY = r"SYSTEM\CurrentControlSet\Services"
SERVICE_TYPES = {16, 32, 48, 256}
TYPE_MAP = {16: "Own Process", 32: "Share Process", 48: "Own/Share", 256: "Interactive"}
START_MAP = {0: "Boot", 1: "System", 2: "Auto", 3: "Manual", 4: "Disabled"}
SYSROOT = os.environ.get("SystemRoot", r"C:\Windows")


def collect(collector):
    return []  # Live registry read


def parse(collector) -> dict:
    result = ResultBuilder(NAME)
    if winreg is None:
        log.error("winreg not available (non-Windows)")
        return result

    live = _query_live_states()

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
                    _process_service(root, svc_name, live, result)
                except OSError:
                    continue
    except OSError as exc:
        log.error("Cannot open Services key: %s", exc)
    return result


def _process_service(root, svc_name, live, result):
    with winreg.OpenKey(root, svc_name) as sk:
        svc_type = _val(sk, "Type")
        if svc_type not in SERVICE_TYPES:
            return

        image_path = _val(sk, "ImagePath") or ""
        start = _val(sk, "Start")
        key_path = f"HKLM\\{SERVICES_KEY}\\{svc_name}"
        key_lm = filetime_to_epoch_ms(winreg.QueryInfoKey(sk)[2])

        # Resolve actual binary from ImagePath
        bin_path = _resolve_binary(image_path)
        h = file_hashes(bin_path) if bin_path else None
        ts = _timestamps(bin_path)

        # ServiceDll (svchost services)
        dll_path = _read_service_dll(sk)
        dh = file_hashes(dll_path) if dll_path else None
        dts = _timestamps(dll_path)

        # RequiredPrivileges (REG_MULTI_SZ)
        privs = _val(sk, "RequiredPrivileges")
        if isinstance(privs, list):
            privs = privs
        elif isinstance(privs, str):
            privs = [privs]
        else:
            privs = None

        result.add_entry({
            "service_name": svc_name,
            "display_name": _val(sk, "DisplayName"),
            "service_type": TYPE_MAP.get(svc_type, str(svc_type)),
            "service_state": live.get(svc_name.lower()),
            "service_description": _val(sk, "Description"),
            "image_path": image_path,
            "start_mode": START_MAP.get(start, str(start) if start is not None else None),
            "start_user": _val(sk, "ObjectName"),
            "key_path": key_path,
            "key_last_modified": key_lm,
            "required_privileges": privs,
            "image_path_md5": h["md5"] if h else None,
            "image_path_sha1": h["sha1"] if h else None,
            "image_path_sha256": h["sha256"] if h else None,
            "image_path_created": ts[0],
            "image_path_accessed": ts[1],
            "image_path_modified": ts[2],
            "image_path_entry_modified": ts[3],
            "service_dll": dll_path,
            "service_dll_md5": dh["md5"] if dh else None,
            "service_dll_sha1": dh["sha1"] if dh else None,
            "service_dll_sha256": dh["sha256"] if dh else None,
            "service_dll_created": dts[0],
            "service_dll_accessed": dts[1],
            "service_dll_modified": dts[2],
            "service_dll_entry_modified": dts[3],
        })


def _read_service_dll(parent_key):
    try:
        with winreg.OpenKey(parent_key, "Parameters") as pk:
            dll, _ = winreg.QueryValueEx(pk, "ServiceDll")
            dll = os.path.expandvars(dll)
            return dll if os.path.isfile(dll) else None
    except OSError:
        return None


def _resolve_binary(image_path):
    """Extract actual binary path from ImagePath (handles svchost -k, rundll32, quotes)."""
    if not image_path:
        return None
    p = image_path.strip()
    # Strip quotes
    if p.startswith('"'):
        m = re.match(r'"([^"]+)"', p)
        if m:
            p = m.group(1)
    else:
        # Take first token unless it's a path with spaces that exists
        parts = p.split()
        # Try progressively longer prefixes
        for end in range(1, len(parts) + 1):
            candidate = " ".join(parts[:end])
            candidate = os.path.expandvars(candidate)
            if os.path.isfile(candidate):
                p = candidate
                break
        else:
            p = parts[0] if parts else p
    p = os.path.expandvars(p)
    if not os.path.isabs(p):
        p = os.path.join(SYSROOT, "System32", p)
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


def _timestamps(path):
    if not path or not os.path.isfile(path):
        return (None, None, None, None)
    try:
        s = os.stat(path)
        return (int(s.st_ctime * 1000), int(s.st_atime * 1000),
                int(s.st_mtime * 1000), int(s.st_ctime * 1000))
    except OSError:
        return (None, None, None, None)
