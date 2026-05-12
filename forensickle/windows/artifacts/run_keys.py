"""Artifact: Run Keys — registry persistence (Run/RunOnce) with file hashing."""
import ctypes
import logging
import os
import re

from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder
from ..core.timestamp_utils import filetime_to_epoch_ms

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None

NAME = "run_keys"

_HKLM_SUBKEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce",
]
_HKU_SUBKEYS = [
    r"Software\Microsoft\Windows\CurrentVersion\Run",
    r"Software\Microsoft\Windows\CurrentVersion\RunOnce",
]


def collect(collector):
    return []  # Live registry read


def parse(collector) -> dict:
    result = ResultBuilder(NAME)
    if winreg is None:
        log.error("winreg not available (non-Windows)")
        return result

    # HKLM keys
    for subkey in _HKLM_SUBKEYS:
        _read_key(winreg.HKEY_LOCAL_MACHINE, subkey, f"HKLM\\{subkey}",
                   None, None, result)

    # Per-user keys via HKU
    for sid, username in _enumerate_user_sids():
        for subkey in _HKU_SUBKEYS:
            full = f"{sid}\\{subkey}"
            _read_key(winreg.HKEY_USERS, full, f"HKU\\{full}",
                       sid, username, result)

    return result


def _read_key(hive, subkey, key_path, user_sid, user_name, result):
    try:
        with winreg.OpenKey(hive, subkey) as key:
            key_lm = filetime_to_epoch_ms(winreg.QueryInfoKey(key)[2])
            i = 0
            while True:
                try:
                    name, data, _ = winreg.EnumValue(key, i)
                    i += 1
                except OSError:
                    break
                command = str(data) if data else ""
                file_path = _extract_path(command)
                h = file_hashes(file_path) if file_path else None
                ts = _timestamps(file_path)
                result.add_entry({
                    "name": name,
                    "command": command,
                    "key_path": key_path,
                    "file_path": file_path,
                    "user_sid": user_sid,
                    "user_name": user_name,
                    "file_md5": h["md5"] if h else None,
                    "file_sha1": h["sha1"] if h else None,
                    "file_sha256": h["sha256"] if h else None,
                    "file_created": ts[0],
                    "file_accessed": ts[1],
                    "file_modified": ts[2],
                    "file_entry_modified": ts[3],
                    "key_last_modified": key_lm,
                })
    except OSError:
        pass  # Key may not exist


def _extract_path(command):
    """Parse the executable path from a Run key command string."""
    if not command:
        return None
    cmd = command.strip()
    # Handle rundll32 — extract the DLL
    if cmd.lower().startswith("rundll32") or cmd.lower().startswith("rundll32.exe"):
        parts = cmd.split(None, 1)
        if len(parts) > 1:
            dll = parts[1].split(",")[0].strip().strip('"')
            dll = os.path.expandvars(dll)
            return dll if os.path.isfile(dll) else None
    # Quoted path
    if cmd.startswith('"'):
        m = re.match(r'"([^"]+)"', cmd)
        if m:
            p = os.path.expandvars(m.group(1))
            return p if os.path.isfile(p) else None
    # Unquoted — try progressively longer token runs
    tokens = cmd.split()
    for end in range(1, len(tokens) + 1):
        candidate = os.path.expandvars(" ".join(tokens[:end]))
        if os.path.isfile(candidate):
            return candidate
    return None


def _enumerate_user_sids():
    """Yield (sid, username) for loaded HKU hives."""
    pairs = []
    try:
        with winreg.OpenKey(winreg.HKEY_USERS, "") as root:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(root, i)
                    i += 1
                except OSError:
                    break
                if not sid.startswith("S-1-5-21") or sid.endswith("_Classes"):
                    continue
                username = _sid_to_username(sid)
                pairs.append((sid, username))
    except OSError:
        pass
    return pairs


def _sid_to_username(sid):
    """Resolve SID to DOMAIN\\user via LookupAccountSid, or None."""
    try:
        import ctypes.wintypes
        advapi = ctypes.windll.advapi32
        sid_obj = ctypes.c_void_p()
        if not advapi.ConvertStringSidToSidW(sid, ctypes.byref(sid_obj)):
            return None
        name = ctypes.create_unicode_buffer(256)
        domain = ctypes.create_unicode_buffer(256)
        name_sz = ctypes.wintypes.DWORD(256)
        domain_sz = ctypes.wintypes.DWORD(256)
        use = ctypes.wintypes.DWORD()
        if advapi.LookupAccountSidW(None, sid_obj, name, ctypes.byref(name_sz),
                                      domain, ctypes.byref(domain_sz), ctypes.byref(use)):
            ctypes.windll.kernel32.LocalFree(sid_obj)
            return f"{domain.value}\\{name.value}" if domain.value else name.value
        ctypes.windll.kernel32.LocalFree(sid_obj)
    except Exception:
        pass
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
