import json
import logging
import os
import shutil
import zipfile

from .hash_utils import file_hashes, path_hash as compute_path_hash

log = logging.getLogger(__name__)

try:
    import pytsk3
except ImportError:
    pytsk3 = None


class SourceCollector:
    """Central file collection engine with dedup by path hash."""

    def __init__(self, working_dir: str):
        self.working_dir = working_dir
        self.sources_dir = os.path.join(working_dir, "sources")
        self.results_dir = os.path.join(working_dir, "results")
        self._manifest: dict[str, dict] = {}
        os.makedirs(self.sources_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)

    @staticmethod
    def path_hash(path: str) -> str:
        return compute_path_hash(path)

    def raw_copy(self, source: str, dest: str) -> None:
        """Forensic copy: pytsk3 raw read if available, else shutil.copy2."""
        if pytsk3 is not None:
            try:
                self._tsk_copy(source, dest)
                return
            except Exception as e:
                log.debug("pytsk3 copy failed for %s, falling back to shutil: %s", source, e)
        shutil.copy2(source, dest)

    def _tsk_copy(self, source: str, dest: str) -> None:
        """Copy via pytsk3 for locked/in-use files."""
        abs_path = os.path.abspath(source)
        # Determine volume — on Linux, find mount point
        # For simplicity, use the device of the file's filesystem
        import subprocess
        result = subprocess.run(
            ["df", "--output=source", abs_path],
            capture_output=True, text=True, timeout=10
        )
        device = result.stdout.strip().split("\n")[-1]
        rel_path = abs_path  # pytsk3 uses absolute path within the volume

        img = pytsk3.Img_Info(device)
        try:
            fs = pytsk3.FS_Info(img)
            f = fs.open(rel_path)
            size = f.info.meta.size
            buf_size = 1024 * 1024
            with open(dest, "wb") as out:
                offset = 0
                while offset < size:
                    chunk = f.read_random(offset, min(buf_size, size - offset))
                    if not chunk:
                        break
                    out.write(chunk)
                    offset += len(chunk)
        finally:
            img.close()

    def collect_file(self, source_path: str) -> dict | None:
        """Copy a file to sources/, dedup by path hash. Returns source entry or None."""
        ph = compute_path_hash(source_path)
        if ph in self._manifest:
            return self._manifest[ph]

        if not os.path.isfile(source_path):
            log.warning("Source file not found: %s", source_path)
            return None

        ext = os.path.splitext(source_path)[1]
        dest = os.path.join(self.sources_dir, f"{ph}{ext}")

        try:
            self.raw_copy(source_path, dest)
        except OSError as e:
            log.error("Failed to collect %s: %s", source_path, e)
            return None

        hashes = file_hashes(dest)
        content_hash = hashes["sha256"] if hashes else ""

        entry = {
            "path": source_path,
            "path_hash": ph,
            "content_hash": content_hash,
        }
        self._manifest[ph] = entry
        return entry

    def collect_files(self, paths: list[str]) -> list[dict]:
        """Batch collect. Returns list of source entries (skips failures)."""
        entries = []
        for p in paths:
            entry = self.collect_file(p)
            if entry:
                entries.append(entry)
        return entries

    def save_manifest(self) -> None:
        path = os.path.join(self.working_dir, "source_manifest.json")
        with open(path, "w") as f:
            json.dump({"sources": list(self._manifest.values())}, f, indent=2)

    def get_manifest(self) -> dict:
        return {"sources": list(self._manifest.values())}

    def cleanup_sources(self) -> None:
        if os.path.isdir(self.sources_dir):
            shutil.rmtree(self.sources_dir)

    def package_sources(self) -> str:
        """Zip the sources/ folder. Returns zip path."""
        zip_path = os.path.join(self.working_dir, "sources.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.sources_dir):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    arcname = os.path.relpath(fpath, self.working_dir)
                    zf.write(fpath, arcname)
        return zip_path
