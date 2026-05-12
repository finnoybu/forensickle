"""Registry-driven artifact collection — reads artifact JSON and collects files automatically."""
from __future__ import annotations

import glob
import logging
import os

from forensickle.registry import get_registry

log = logging.getLogger(__name__)

PLATFORM = "windows"


def expand_source_paths(patterns: list[str]) -> list[str]:
    """Expand environment variables and globs in source path patterns."""
    paths = []
    for pattern in patterns:
        # Expand environment variables
        expanded = os.path.expandvars(pattern)

        # Expand user home (~) — not typical on Windows but handle it
        expanded = os.path.expanduser(expanded)

        # Glob expansion
        matches = glob.glob(expanded, recursive=True)
        if matches:
            paths.extend(matches)
        else:
            # If no glob match, still include the path (might be a locked file
            # that os.path.isfile returns False for but pytsk3 can read)
            if not any(c in expanded for c in "*?["):
                paths.append(expanded)

    return paths


def collect_artifact_by_id(artifact_id: str, collector) -> list[dict]:
    """
    Collect source files for an artifact using its registry definition.

    Reads source_paths and source_type from the artifact JSON,
    expands paths, and calls collector.collect_artifact().

    Returns list of source file entries.
    """
    reg = get_registry()
    defn = reg.get(artifact_id)
    if not defn:
        log.warning("Unknown artifact: %s", artifact_id)
        return []

    plat = defn.get_platform(PLATFORM)
    if not plat:
        log.warning("Artifact %s not available for %s", artifact_id, PLATFORM)
        return []

    if plat.source_type == "live_data":
        return []  # No files to collect

    if not plat.source_paths:
        log.debug("No source paths defined for %s", artifact_id)
        return []

    # Expand all path patterns
    resolved_paths = expand_source_paths(plat.source_paths)
    if not resolved_paths:
        log.debug("No files found for %s", artifact_id)
        return []

    log.info("Collecting %s: %d paths, source_type=%s", artifact_id, len(resolved_paths), plat.source_type)
    return collector.collect_artifact(resolved_paths, plat.source_type)
