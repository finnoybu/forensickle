from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:
    winreg = None

try:
    from Registry import Registry
except ImportError:
    Registry = None


def read_registry_key(hive: int, subkey: str, values: list[str] | None = None) -> dict:
    """Read live registry values. Returns {value_name: value_data}."""
    if winreg is None:
        log.warning("winreg not available (non-Windows platform)")
        return {}
    result = {}
    try:
        with winreg.OpenKey(hive, subkey) as key:
            if values:
                for name in values:
                    try:
                        data, _ = winreg.QueryValueEx(key, name)
                        result[name] = data
                    except FileNotFoundError:
                        pass
            else:
                i = 0
                while True:
                    try:
                        name, data, _ = winreg.EnumValue(key, i)
                        result[name] = data
                        i += 1
                    except OSError:
                        break
    except OSError as e:
        log.error("Failed to read registry %s: %s", subkey, e)
    return result


def read_offline_hive(hive_path: str, subkey: str) -> list[dict]:
    """Read offline registry hive using python-registry. Returns list of {name, value, type}."""
    if Registry is None:
        log.warning("python-registry not available")
        return []
    try:
        reg = Registry.Registry(hive_path)
        key = reg.open(subkey)
        return [
            {"name": v.name(), "value": v.value(), "type": v.value_type_str()}
            for v in key.values()
        ]
    except Exception as e:
        log.error("Failed to read offline hive %s\\%s: %s", hive_path, subkey, e)
        return []


def expand_user_paths(pattern: str) -> list[str]:
    """Expand pattern for all user profiles. Replaces %USERPROFILE%, %LOCALAPPDATA%, etc."""
    profiles = _enumerate_profiles()
    results = []
    for profile_path in profiles:
        local_appdata = os.path.join(profile_path, "AppData", "Local")
        roaming_appdata = os.path.join(profile_path, "AppData", "Roaming")
        expanded = pattern.replace("%USERPROFILE%", profile_path)
        expanded = expanded.replace("%LOCALAPPDATA%", local_appdata)
        expanded = expanded.replace("%APPDATA%", roaming_appdata)
        if os.path.exists(os.path.dirname(expanded)) or "*" in expanded:
            results.append(expanded)
    return results


def _enumerate_profiles() -> list[str]:
    """Get all user profile paths from the registry."""
    profile_list_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"
    profiles = []
    if winreg is None:
        # Fallback: use Users directory
        users_dir = os.path.join(os.environ.get("SystemDrive", "C:"), os.sep, "Users")
        if os.path.isdir(users_dir):
            for name in os.listdir(users_dir):
                p = os.path.join(users_dir, name)
                if os.path.isdir(p) and name not in ("Public", "Default", "Default User", "All Users"):
                    profiles.append(p)
        return profiles

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, profile_list_key) as key:
            i = 0
            while True:
                try:
                    sid = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, sid) as subkey:
                        path, _ = winreg.QueryValueEx(subkey, "ProfileImagePath")
                        path = os.path.expandvars(path)
                        if os.path.isdir(path):
                            profiles.append(path)
                    i += 1
                except OSError:
                    break
    except OSError as e:
        log.error("Failed to enumerate profiles: %s", e)
    return profiles
