"""Artifact: USB Device History — USBSTOR and MountedDevices from registry."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "usb_device_history"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Registry live read


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    try:
        import winreg
        # USBSTOR entries
        try:
            usb_key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Enum\USBSTOR")
            i = 0
            while True:
                try:
                    dev_name = winreg.EnumKey(usb_key, i)
                    i += 1
                    dev_key = winreg.OpenKey(usb_key, dev_name)
                    j = 0
                    while True:
                        try:
                            serial = winreg.EnumKey(dev_key, j)
                            j += 1
                            result.add_entry({
                                "device_name": dev_name,
                                "serial": serial,
                                "vid_pid": dev_name,
                                "first_connected": None,
                                "last_connected": None,
                            })
                        except OSError:
                            break
                except OSError:
                    break
        except OSError as e:
            log.debug("USBSTOR not found: %s", e)
        # MountedDevices
        try:
            md_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\MountedDevices")
            i = 0
            while True:
                try:
                    name, data, _ = winreg.EnumValue(md_key, i)
                    i += 1
                    if isinstance(data, bytes) and b"USBSTOR" in data:
                        result.add_entry({
                            "device_name": name,
                            "serial": data.decode("utf-16-le", errors="replace"),
                            "vid_pid": None,
                            "first_connected": None,
                            "last_connected": None,
                        })
                except OSError:
                    break
        except OSError as e:
            log.debug("MountedDevices not found: %s", e)
    except ImportError:
        log.error("winreg not available (non-Windows platform)")
    return result
