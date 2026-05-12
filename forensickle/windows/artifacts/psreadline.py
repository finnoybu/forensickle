"""Artifact: PSReadLine — PowerShell console command history."""
import glob
import logging
import os
import re

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.timestamp_utils import epoch_ms_now
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "psreadline"
SOURCE_PATHS = [r"%APPDATA%\Microsoft\Windows\PowerShell\PSReadLine\ConsoleHost_history.txt"]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in SOURCE_PATHS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                entry = collector.collect_file(path)
                if entry:
                    sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        path = sf["path"]
        # Extract username and SID from path
        username, user_sid = _extract_user_info(path)

        # File timestamps
        try:
            stat = os.stat(path)
            file_created = int(stat.st_ctime * 1000)
            file_modified = int(stat.st_mtime * 1000)
        except OSError:
            file_created = None
            file_modified = None

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    stripped = line.rstrip("\n\r")
                    if stripped:
                        result.add_entry({
                            "line": line_num,
                            "command": stripped,
                            "path": path,
                            "username": username,
                            "user_sid": user_sid,
                            "file_created": file_created,
                            "file_modified": file_modified,
                        })
        except OSError as e:
            log.error("Failed to read PSReadLine history %s: %s", path, e)
    return result


def _extract_user_info(path: str) -> tuple[str, str]:
    """Extract username from path like C:\\Users\\jsmith\\AppData\\..."""
    m = re.search(r"[/\\]Users[/\\]([^/\\]+)[/\\]", path, re.IGNORECASE)
    username = m.group(1) if m else ""
    # SID lookup would require registry/WMI — return empty for now
    return username, ""
