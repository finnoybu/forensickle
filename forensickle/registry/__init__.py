"""Artifact registry — single source of truth for all artifact definitions."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

_REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


@dataclass
class PlatformConfig:
    source_paths: list[str] = field(default_factory=list)
    module: str = ""  # Python module name (e.g., "chrome_history")
    source_type: str = "file"  # file, registry_hive, ese_database, sqlite_database, ntfs_artifact, live_data


@dataclass
class ArtifactDefinition:
    artifact_id: str
    display_name: str
    category: str
    description: str = ""
    can_parse: bool = False
    can_retain: bool = True
    parse_location: str = "client"  # "client" or "server"
    timeout: int = 300
    platforms: dict[str, PlatformConfig] = field(default_factory=dict)
    investigative_tags: list[str] = field(default_factory=list)

    def supports_platform(self, platform: str) -> bool:
        return platform in self.platforms

    def get_platform(self, platform: str) -> PlatformConfig | None:
        return self.platforms.get(platform)


class ArtifactRegistry:
    """Loads and provides access to all artifact definitions."""

    def __init__(self, registry_dir: str | None = None):
        self._dir = registry_dir or _REGISTRY_DIR
        self._artifacts: dict[str, ArtifactDefinition] = {}
        self._load_all()

    def _load_all(self):
        if not os.path.isdir(self._dir):
            log.warning("Registry directory not found: %s", self._dir)
            return
        for fname in sorted(os.listdir(self._dir)):
            if fname.endswith(".json"):
                path = os.path.join(self._dir, fname)
                try:
                    defn = self._load_file(path)
                    self._artifacts[defn.artifact_id] = defn
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    log.error("Failed to load artifact definition %s: %s", fname, e)

    def _load_file(self, path: str) -> ArtifactDefinition:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        platforms = {}
        for plat_name, plat_data in data.get("platforms", {}).items():
            platforms[plat_name] = PlatformConfig(
                source_paths=plat_data.get("source_paths", []),
                module=plat_data.get("module", data["artifact_id"]),
                source_type=plat_data.get("source_type", "file"),
            )

        return ArtifactDefinition(
            artifact_id=data["artifact_id"],
            display_name=data["display_name"],
            category=data["category"],
            description=data.get("description", ""),
            can_parse=data.get("can_parse", False),
            can_retain=data.get("can_retain", True),
            parse_location=data.get("parse_location", "client"),
            timeout=data.get("timeout", 300),
            platforms=platforms,
            investigative_tags=data.get("investigative_tags", []),
        )

    def get(self, artifact_id: str) -> ArtifactDefinition | None:
        return self._artifacts.get(artifact_id)

    def all(self) -> list[ArtifactDefinition]:
        return list(self._artifacts.values())

    def for_platform(self, platform: str) -> list[ArtifactDefinition]:
        return [a for a in self._artifacts.values() if a.supports_platform(platform)]

    def by_category(self, platform: str | None = None) -> dict[str, list[ArtifactDefinition]]:
        cats: dict[str, list[ArtifactDefinition]] = {}
        for a in self._artifacts.values():
            if platform and not a.supports_platform(platform):
                continue
            cats.setdefault(a.category, []).append(a)
        return cats

    def by_tag(self, tag: str, platform: str | None = None) -> list[ArtifactDefinition]:
        results = []
        for a in self._artifacts.values():
            if tag in a.investigative_tags:
                if platform is None or a.supports_platform(platform):
                    results.append(a)
        return results

    @property
    def categories(self) -> list[str]:
        return sorted(set(a.category for a in self._artifacts.values()))

    @property
    def investigative_tags_all(self) -> list[str]:
        tags = set()
        for a in self._artifacts.values():
            tags.update(a.investigative_tags)
        return sorted(tags)


# Singleton for convenience
_registry: ArtifactRegistry | None = None


def get_registry() -> ArtifactRegistry:
    global _registry
    if _registry is None:
        _registry = ArtifactRegistry()
    return _registry
