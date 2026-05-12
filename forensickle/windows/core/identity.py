"""Deterministic endpoint identity from hardware identifiers."""
from __future__ import annotations

import hashlib
import logging
import subprocess
import sys

log = logging.getLogger(__name__)


def get_endpoint_id() -> str:
    """
    Generate a deterministic endpoint ID from hardware identifiers.
    SHA256(smbios_uuid + boot_disk_serial + primary_mac).

    Survives OS reinstall. Unique across VM clones.
    """
    smbios = _get_smbios_uuid()
    disk = _get_boot_disk_serial()
    mac = _get_primary_mac()

    components = f"{smbios}|{disk}|{mac}"
    endpoint_id = hashlib.sha256(components.encode("utf-8")).hexdigest()

    log.debug("Endpoint ID components: smbios=%s, disk=%s, mac=%s",
              smbios[:8] + "..." if smbios else "NONE",
              disk[:8] + "..." if disk else "NONE",
              mac or "NONE")
    log.debug("Endpoint ID: %s", endpoint_id[:16] + "...")

    return endpoint_id


def get_endpoint_info() -> dict:
    """
    Return full endpoint identity info for embedding in results.
    Includes the deterministic ID plus human-readable context.
    """
    import platform
    import socket

    return {
        "endpoint_id": get_endpoint_id(),
        "hostname": socket.gethostname(),
        "os": platform.platform(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
    }


# ---------------------------------------------------------------------------
# Hardware identifier collection
# ---------------------------------------------------------------------------

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _wmic(alias: str, field: str) -> str:
    """Query a single field via wmic. Returns stripped value or empty string."""
    try:
        result = subprocess.run(
            ["wmic", alias, "get", field, "/value"],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        for line in result.stdout.strip().splitlines():
            if "=" in line:
                return line.split("=", 1)[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log.debug("wmic %s get %s failed: %s", alias, field, e)
    return ""


def _powershell(command: str) -> str:
    """Run a PowerShell command, return stripped stdout."""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        log.debug("PowerShell command failed: %s", e)
    return ""


def _get_smbios_uuid() -> str:
    """
    Get SMBIOS/firmware UUID. Persists across OS reinstalls.
    Primary source: wmic csproduct. Fallback: PowerShell CIM.
    """
    uuid = _wmic("csproduct", "UUID")
    if uuid and uuid.lower() not in ("", "not available", "to be filled by o.e.m."):
        return uuid.lower()

    # Fallback: PowerShell
    uuid = _powershell("(Get-CimInstance Win32_ComputerSystemProduct).UUID")
    if uuid and uuid.lower() not in ("", "not available"):
        return uuid.lower()

    log.warning("Could not retrieve SMBIOS UUID")
    return ""


def _get_boot_disk_serial() -> str:
    """
    Get the serial number of the boot disk. Unique even across VM clones
    (hypervisors assign new virtual disk IDs).
    """
    # Get the physical drive index of the boot volume (usually 0)
    boot_drive_index = _get_boot_drive_index()

    # Try wmic first
    serial = _wmic("diskdrive", "SerialNumber")
    if serial and serial.lower() not in ("", "not available"):
        return serial.strip()

    # Fallback: PowerShell with specific disk index
    serial = _powershell(
        f"(Get-PhysicalDisk -DeviceNumber {boot_drive_index}).SerialNumber"
    )
    if serial:
        return serial.strip()

    # Second fallback: any physical disk serial
    serial = _powershell(
        "(Get-PhysicalDisk | Select-Object -First 1).SerialNumber"
    )
    if serial:
        return serial.strip()

    log.warning("Could not retrieve boot disk serial")
    return ""


def _get_boot_drive_index() -> str:
    """Determine which physical disk holds the boot volume."""
    # Get boot partition's disk number
    index = _powershell(
        "(Get-Partition -DriveLetter $env:SystemDrive[0]).DiskNumber"
    )
    if index and index.isdigit():
        return index
    return "0"


def _get_primary_mac() -> str:
    """
    Get the MAC address of the primary network adapter.
    Uses the adapter with the default route (most stable choice).
    """
    # Get adapter with default gateway via PowerShell
    mac = _powershell(
        "(Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} "
        "| Sort-Object -Property InterfaceMetric "
        "| Select-Object -First 1).MacAddress"
    )
    if mac:
        return mac.lower().replace("-", ":")

    # Fallback: wmic
    mac = _wmic("nic where NetConnectionStatus=2", "MACAddress")
    if mac:
        return mac.lower()

    # Last resort: uuid.getnode() — may not be stable across reboots
    try:
        import uuid
        node = uuid.getnode()
        return ":".join(f"{(node >> (8 * i)) & 0xff:02x}" for i in reversed(range(6)))
    except Exception:
        pass

    log.warning("Could not retrieve primary MAC address")
    return ""
