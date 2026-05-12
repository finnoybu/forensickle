"""Artifact: ARP Cache — active ARP/NDP table via Windows API (IPv4 + IPv6).

Uses GetIpNetTable2 for complete neighbor table with interface names
and permanent/dynamic state. Falls back to 'arp -a' parsing if API fails.
"""
import ctypes
import ctypes.wintypes as wt
import logging
import re
import socket
import struct
import subprocess
import sys

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

NAME = "arp_cache"

# Win32 constants
AF_UNSPEC = 0
AF_INET = 2
AF_INET6 = 23
LOCALE_NAME_MAX_LENGTH = 85
NlnsPermanent = 6  # MIB_IPNET_ROW2.State value for permanent entries


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data — no files to collect


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)

    entries = _get_via_api()
    if entries is None:
        log.debug("API method failed, falling back to arp -a")
        entries = _get_via_command()

    for e in entries:
        result.add_entry(e)

    return result


# ---------------------------------------------------------------------------
# Method 1: Windows API (GetIpNetTable2)
# ---------------------------------------------------------------------------

# C structures for GetIpNetTable2
class SOCKADDR_IN(ctypes.Structure):
    _fields_ = [("sin_family", ctypes.c_ushort),
                 ("sin_port", ctypes.c_ushort),
                 ("sin_addr", ctypes.c_ubyte * 4),
                 ("sin_zero", ctypes.c_char * 8)]

class SOCKADDR_IN6(ctypes.Structure):
    _fields_ = [("sin6_family", ctypes.c_ushort),
                 ("sin6_port", ctypes.c_ushort),
                 ("sin6_flowinfo", ctypes.c_ulong),
                 ("sin6_addr", ctypes.c_ubyte * 16),
                 ("sin6_scope_id", ctypes.c_ulong)]

class SOCKADDR_INET(ctypes.Union):
    _fields_ = [("Ipv4", SOCKADDR_IN),
                 ("Ipv6", SOCKADDR_IN6),
                 ("si_family", ctypes.c_ushort)]

class NET_LUID(ctypes.Union):
    _fields_ = [("Value", ctypes.c_ulonglong),
                 ("Info", ctypes.c_ulonglong)]

class MIB_IPNET_ROW2(ctypes.Structure):
    _fields_ = [("Address", SOCKADDR_INET),
                 ("InterfaceIndex", ctypes.c_ulong),
                 ("InterfaceLuid", NET_LUID),
                 ("PhysicalAddress", ctypes.c_ubyte * 32),
                 ("PhysicalAddressLength", ctypes.c_ulong),
                 ("State", ctypes.c_int),
                 ("Flags", ctypes.c_ubyte),
                 ("ReachabilityTime", ctypes.c_ulong * 2)]

class MIB_IPNET_TABLE2(ctypes.Structure):
    _fields_ = [("NumEntries", ctypes.c_ulong),
                 ("Table", MIB_IPNET_ROW2 * 1)]


def _get_via_api() -> list[dict] | None:
    """Get ARP/NDP table via GetIpNetTable2 Windows API."""
    try:
        iphlpapi = ctypes.WinDLL("iphlpapi")
    except OSError:
        return None

    try:
        table_ptr = ctypes.POINTER(MIB_IPNET_TABLE2)()
        iphlpapi.GetIpNetTable2.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.POINTER(MIB_IPNET_TABLE2))]
        iphlpapi.GetIpNetTable2.restype = ctypes.c_ulong

        result = iphlpapi.GetIpNetTable2(AF_UNSPEC, ctypes.byref(table_ptr))
        if result != 0:
            log.debug("GetIpNetTable2 returned %d", result)
            return None

        data = table_ptr.contents
        num = data.NumEntries
        rows = ctypes.cast(ctypes.pointer(data.Table),
                           ctypes.POINTER(MIB_IPNET_ROW2 * num)).contents

        entries = []
        for i in range(num):
            row = rows[i]

            # IP address
            family = row.Address.si_family
            if family == AF_INET:
                ip = socket.inet_ntoa(bytes(row.Address.Ipv4.sin_addr))
            elif family == AF_INET6:
                ip = socket.inet_ntop(AF_INET6, bytes(row.Address.Ipv6.sin6_addr))
            else:
                continue

            # MAC address
            mac_bytes = bytes(row.PhysicalAddress)[:row.PhysicalAddressLength]
            mac = "-".join(f"{b:02x}" for b in mac_bytes) if mac_bytes else ""

            # Interface name
            iface_name = _resolve_interface_name(iphlpapi, row.InterfaceLuid)

            entries.append({
                "ip_address": ip,
                "mac_address": mac,
                "interface": iface_name,
                "permanent": row.State == NlnsPermanent,
            })

        # Free the table
        iphlpapi.FreeMibTable(table_ptr)
        return entries

    except Exception as e:
        log.debug("GetIpNetTable2 failed: %s", e)
        return None


def _resolve_interface_name(iphlpapi, luid: NET_LUID) -> str:
    """Convert interface LUID to friendly name."""
    try:
        buf = (ctypes.c_wchar * LOCALE_NAME_MAX_LENGTH)()
        result = iphlpapi.ConvertInterfaceLuidToAlias(
            ctypes.byref(luid), ctypes.byref(buf), LOCALE_NAME_MAX_LENGTH
        )
        if result == 0:
            return buf.value
    except Exception:
        pass
    return ""


# ---------------------------------------------------------------------------
# Method 2: Fallback — parse 'arp -a' output
# ---------------------------------------------------------------------------

def _get_via_command() -> list[dict]:
    """Fallback: parse arp -a output."""
    entries = []
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=15, creationflags=_NO_WINDOW)
        current_iface = None
        for line in out.stdout.splitlines():
            line = line.strip()
            m = re.match(r"Interface:\s+(\S+)", line)
            if m:
                current_iface = m.group(1)
                continue
            m = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)\s+(\S+)", line)
            if m:
                entries.append({
                    "ip_address": m.group(1),
                    "mac_address": m.group(2),
                    "interface": current_iface or "",
                    "permanent": m.group(3).lower() == "static",
                })
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        log.error("arp -a failed: %s", e)
    return entries
