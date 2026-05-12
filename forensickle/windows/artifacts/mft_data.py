"""Artifact: MFT (Data Drives) — Master File Table from non-system NTFS drives."""
import logging
import os
import string

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "mft_data"


def _get_data_drives() -> list[str]:
    """Find NTFS data drives (non-system)."""
    system_drive = os.environ.get("SystemDrive", "C:").upper()
    drives = []
    if os.name == "nt":
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bitmask & (1 << i):
                drive = f"{letter}:"
                if drive.upper() != system_drive:
                    drives.append(drive)
    return drives


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for drive in _get_data_drives():
        mft_path = os.path.join(drive + os.sep, "$MFT")
        entry = collector.collect_file(mft_path, source_type="ntfs_artifact")
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    # MFT parsing is server-side
    return result
