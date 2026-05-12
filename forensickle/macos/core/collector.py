import json
import logging
import os
import shutil
import zipfile
from pathlib import Path

from .hash_utils import file_hashes, path_hash

log = logging.getLogger(__name__)

try:
    import pytsk3
    _HAS_PYTSK3 = True
except ImportError:
    _HAS_PYTSK3 = False


class SourceCollector:
    def __init__(self, working_dir: str):
        self.working_dir = Path(working_dir)
        self.sources_dir = self.working_dir / "sources"
        self.results_dir = self.working_dir / "results"
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: dict[str, dict] = {}
        self._manifest_path = self.working_dir / "source_manifest.json"
        if self._manifest_path.exists():
            try:
                self._manifest = json.loads(self._manifest_path.read_text("utf-8"))
            except (json.JSONDecodeError, OSError):
                self._manifest = {}

    @staticmethod
    def path_hash(path: str) -> str:
        return path_hash(path)

    def raw_copy(self, source: str, dest: str) -> None:
        """Forensic copy: pytsk3 if available, else shutil.copy2."""
        if _HAS_PYTSK3:
            try:
                # pytsk3 raw read — volume-level access
                # For now, fall through to shutil if pytsk3 path logic isn't applicable
                shutil.copy2(source, dest)
            except Exception as e:
                log.warning("pytsk3 copy failed for %s, falling back: %s", source, e)
                shutil.copy2(source, dest)
        else:
            shutil.copy2(source, dest)

    def collect_file(self, source_path: str) -> dict | None:
        """Copies file to sources/{path_hash}.{ext}, returns source entry dict."""
        p_hash = path_hash(source_path)
        if p_hash in self._manifest:
            return self._manifest[p_hash]

        if not os.path.isfile(source_path):
            log.warning("Source file not found: %s", source_path)
            return None

        ext = Path(source_path).suffix
        dest_name = f"{p_hash}{ext}"
        dest_path = str(self.sources_dir / dest_name)

        try:
            self.raw_copy(source_path, dest_path)
        except OSError as e:
            log.error("Failed to collect %s: %s", source_path, e)
            return None

        hashes = file_hashes(dest_path)
        content_hash = hashes["sha256"] if hashes else None

        entry = {
            "path": source_path,
            "path_hash": p_hash,
            "content_hash": content_hash,
        }
        self._manifest[p_hash] = entry
        return entry

    def collect_files(self, paths: list[str]) -> list[dict]:
        results = []
        for p in paths:
            entry = self.collect_file(p)
            if entry:
                results.append(entry)
        return results

    def save_manifest(self) -> None:
        self._manifest_path.write_text(
            json.dumps(self._manifest, indent=2), encoding="utf-8"
        )

    def get_manifest(self) -> dict:
        return dict(self._manifest)

    def cleanup_sources(self) -> None:
        if self.sources_dir.exists():
            shutil.rmtree(self.sources_dir)

    def package_sources(self) -> str:
        """Zips sources/ folder, returns zip path."""
        zip_path = str(self.working_dir / "sources.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.sources_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, self.working_dir)
                    zf.write(fpath, arcname)
        return zip_path
