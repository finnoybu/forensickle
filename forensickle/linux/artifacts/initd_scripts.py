"""Artifact: Init.d Scripts — scripts from /etc/init.d/."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)
NAME = "initd_scripts"
INITD_DIR = "/etc/init.d"


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for path in glob.glob(f"{INITD_DIR}/*"):
        if os.path.isfile(path):
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
        result.add_entry({
            "name": os.path.basename(path),
            "path": path,
            "executable": os.access(path, os.X_OK),
        })
    return result
