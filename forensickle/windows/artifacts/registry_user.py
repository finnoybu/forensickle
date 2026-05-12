"""Artifact: User Registry Hives — NTUSER.DAT and UsrClass.dat for all profiles."""
import glob
import logging
import os

from ..core.collector import SourceCollector
from ..core.registry_utils import expand_user_paths
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

NAME = "registry_user"
PATTERNS = [
    r"%USERPROFILE%\NTUSER.DAT",
    r"%USERPROFILE%\NTUSER.DAT.LOG*",
    r"%USERPROFILE%\AppData\Local\Microsoft\Windows\UsrClass.dat",
    r"%USERPROFILE%\AppData\Local\Microsoft\Windows\UsrClass.dat.LOG*",
]


def collect(collector: SourceCollector) -> list[dict]:
    sources = []
    for pattern in PATTERNS:
        for expanded in expand_user_paths(pattern):
            for path in glob.glob(expanded):
                entry = collector.collect_file(path, source_type="registry_hive")
                if entry:
                    sources.append(entry)
    return sources


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    return result
