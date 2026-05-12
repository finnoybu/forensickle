"""Artifact: XDG Autostart — .desktop files from autostart directories."""
import glob
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import expand_user_paths

log = logging.getLogger(__name__)
NAME = "xdg_autostart"
SYSTEM_PATH = "/etc/xdg/autostart/*.desktop"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(SYSTEM_PATH):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    for path in expand_user_paths("~/.config/autostart/*.desktop"):
        entry = collector.collect_file(path)
        if entry:
            sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        try:
            entry = {"source_file": sf["path"], "name": "", "exec": "", "hidden": False}
            with open(sf["path"], "r", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Exec="):
                        entry["exec"] = line[5:]
                    elif line.startswith("Name="):
                        entry["name"] = line[5:]
                    elif line.startswith("Hidden="):
                        entry["hidden"] = line[7:].lower() == "true"
            result.add_entry(entry)
        except OSError:
            continue
    return result
