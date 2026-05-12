"""Artifact: Open Handles — file descriptors per process via psutil."""
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None

NAME = "handles"


def collect(collector: SourceCollector) -> list[dict]:
    return []  # Live data


def parse(collector: SourceCollector) -> dict:
    result = ResultBuilder(NAME)
    if psutil is None:
        log.error("psutil not available")
        return result
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            info = proc.info
            for f in proc.open_files() or []:
                result.add_entry({
                    "pid": info["pid"],
                    "process_name": info["name"],
                    "handle_type": "file",
                    "name": f.path,
                })
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            continue
        except OSError:
            continue
    return result
