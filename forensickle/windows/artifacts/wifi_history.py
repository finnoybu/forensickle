"""Artifact: Wi-Fi History — saved wireless profiles and connection details."""
import logging
import re
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "wifi_history"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "profiles"],
            capture_output=True, text=True, timeout=15, creationflags=_NO_WINDOW,
        )
        profiles = re.findall(r"All User Profile\s*:\s*(.+)", out.stdout)
        for ssid in profiles:
            ssid = ssid.strip()
            entry = {"ssid": ssid, "auth": None, "encryption": None, "connection_mode": None}
            try:
                detail = subprocess.run(
                    ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
                    capture_output=True, text=True, timeout=10, creationflags=_NO_WINDOW,
                )
                for line in detail.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("Authentication"):
                        entry["auth"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Cipher") or line.startswith("Encryption"):
                        entry["encryption"] = line.split(":", 1)[1].strip()
                    elif line.startswith("Connection mode"):
                        entry["connection_mode"] = line.split(":", 1)[1].strip()
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
            result.add_entry(entry)
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("Failed to query Wi-Fi profiles: %s", e)
    return result
