"""Artifact: Docker Containers — list all containers via docker CLI."""
import json
import logging

from ..core.collector import SourceCollector
from ..core.output import ResultBuilder
from ..core.system_utils import run_command

log = logging.getLogger(__name__)
NAME = "docker_containers"


def collect(collector: SourceCollector) -> list[dict]:
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    output = run_command(
        ["docker", "ps", "-a", "--no-trunc", "--format", "json"], timeout=30
    )
    if not output.strip():
        return result
    for line in output.strip().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        result.add_entry({
            "id": entry.get("ID", ""),
            "name": entry.get("Names", ""),
            "image": entry.get("Image", ""),
            "status": entry.get("Status", ""),
            "created": entry.get("CreatedAt", ""),
            "ports": entry.get("Ports", ""),
        })
    return result
