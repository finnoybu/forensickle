"""Central file collection engine with type-aware copy routing and dedup."""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from .hash_utils import file_hashes, path_hash as _path_hash

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

log = logging.getLogger(__name__)

try:
    import pytsk3
except ImportError:
    pytsk3 = None


class SourceCollector:
    """Collects forensic source files with dedup by path hash.

    Routes to the appropriate copy method based on source_type:
      - file:            shutil.copy2 → pytsk3 fallback
      - registry_hive:   pytsk3 raw copy (always locked on live), + .LOG* files
      - ese_database:    esentutl.exe → pytsk3 fallback
      - sqlite_database: shutil.copy2 + copy WAL/SHM companions
      - ntfs_artifact:   pytsk3 only ($MFT, $UsnJrnl, $LogFile)
      - live_data:       no file copy (parsed from live system)
    """

    def __init__(self, working_dir: str, identity: dict | None = None):
        self.working_dir = working_dir
        self.sources_dir = os.path.join(working_dir, "sources")
        self.results_dir = os.path.join(working_dir, "results")
        self._manifest_path = os.path.join(working_dir, "source_manifest.json")
        self.identity = identity or {}
        os.makedirs(self.sources_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        self._manifest: dict = self._load_manifest()

    def _load_manifest(self) -> dict:
        if os.path.isfile(self._manifest_path):
            try:
                with open(self._manifest_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Failed to load manifest: %s", e)
        return {**self.identity, "sources": {}}

    @staticmethod
    def path_hash(path: str) -> str:
        return _path_hash(path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect_file(self, source_path: str, source_type: str = "file") -> dict | None:
        """Copy a file using the appropriate method for its type. Returns source entry or None."""
        ph = _path_hash(source_path)

        # Already collected — verify the file still exists in sources
        if ph in self._manifest["sources"]:
            ext_check = os.path.splitext(source_path)[1] or ""
            cached = os.path.join(self.sources_dir, f"{ph}{ext_check}")
            if os.path.isfile(cached):
                return self._manifest["sources"][ph]
            else:
                # File was deleted — remove from manifest and re-collect
                del self._manifest["sources"][ph]

        ext = os.path.splitext(source_path)[1] or ""
        dest = os.path.join(self.sources_dir, f"{ph}{ext}")

        try:
            ok = self._copy_by_type(source_path, dest, source_type)
            if not ok:
                return None
        except (OSError, IOError) as e:
            log.error("Failed to collect %s: %s", source_path, e)
            return None

        hashes = file_hashes(dest)
        entry = {
            "path": source_path,
            "path_hash": ph,
            "content_hash": hashes["sha256"] if hashes else None,
            "source_type": source_type,
        }
        self._manifest["sources"][ph] = entry
        self.save_manifest()
        return entry

    def collected_path(self, source_entry: dict) -> str | None:
        """Resolve a source entry to its copied file path in the sources directory."""
        if not source_entry:
            return None
        ext = os.path.splitext(source_entry["path"])[1]
        path = os.path.join(self.sources_dir, source_entry["path_hash"] + ext)
        return path if os.path.isfile(path) else None

    def collect_files(self, paths: list[str], source_type: str = "file") -> list[dict]:
        """Batch collect. Returns list of source entries (skips failures)."""
        entries = []
        for p in paths:
            entry = self.collect_file(p, source_type)
            if entry:
                entries.append(entry)
        return entries

    def collect_artifact(self, source_paths: list[str], source_type: str) -> list[dict]:
        """
        Collect all files for an artifact, applying type-specific logic.
        Handles companion files (WAL/SHM, LOG1/LOG2) automatically.
        """
        if source_type == "live_data":
            return []

        entries = []
        for path in source_paths:
            entry = self.collect_file(path, source_type)
            if entry:
                entries.append(entry)

            # Companion files by type
            if source_type == "sqlite_database":
                for suffix in ["-wal", "-shm"]:
                    companion = path + suffix
                    if os.path.isfile(companion):
                        ce = self.collect_file(companion, "file")
                        if ce:
                            entries.append(ce)

            elif source_type == "registry_hive":
                for suffix in [".LOG1", ".LOG2", ".LOG"]:
                    companion = path + suffix
                    if os.path.isfile(companion):
                        ce = self.collect_file(companion, "file")
                        if ce:
                            entries.append(ce)

        return entries

    # ------------------------------------------------------------------
    # Copy routing
    # ------------------------------------------------------------------

    def _copy_by_type(self, source: str, dest: str, source_type: str) -> bool:
        """Route to the appropriate copy method. Returns True on success."""
        if source_type == "ntfs_artifact":
            # $MFT, $UsnJrnl, etc. — must use raw methods
            return self._copy_locked(source, dest)

        if source_type == "ese_database":
            # ESE: esentutl with /vssrec for transactional consistency, then fallbacks
            if self._copy_esentutl_vssrec(source, dest):
                return True
            return self._copy_locked(source, dest)

        # For everything else: try standard copy first
        if not self._is_locked(source):
            try:
                shutil.copy2(source, dest)
                return True
            except OSError as e:
                log.debug("Standard copy failed for %s: %s", source, e)

        # File is locked (or standard copy failed) — use locked-file chain
        return self._copy_locked(source, dest)

    # ------------------------------------------------------------------
    # Copy methods
    # ------------------------------------------------------------------

    def _is_locked(self, path: str) -> bool:
        """Check if a file is locked/inaccessible."""
        try:
            with open(path, "rb") as f:
                f.read(1)
            return False
        except PermissionError:
            return True
        except FileNotFoundError:
            return False  # doesn't exist, not locked
        except OSError:
            return True

    def _copy_locked(self, source: str, dest: str) -> bool:
        """Copy a locked file. Tries methods in order until one succeeds.

        Chain: esentutl /y /vss → pytsk3 → Win32 backup semantics
        """
        # Method 1: esentutl /y /vss — works for any file, uses VSS internally
        if self._copy_esentutl_vss(source, dest):
            return True

        # Method 2: pytsk3 raw disk read
        if pytsk3 is not None:
            try:
                if self._tsk_copy_raw(source, dest):
                    return True
            except Exception as e:
                log.debug("pytsk3 failed for %s: %s", source, e)

        # Method 3: Win32 backup semantics (last resort)
        if self._backup_copy(source, dest):
            return True

        log.warning("All copy methods failed for %s", source)
        return False

    def _copy_esentutl_vss(self, source: str, dest: str) -> bool:
        """Copy any locked file using esentutl.exe /y /vss."""
        try:
            result = subprocess.run(
                ["esentutl.exe", "/y", source, "/vss", "/d", dest],
                capture_output=True, text=True, timeout=120, creationflags=_NO_WINDOW,
            )
            if result.returncode == 0 and os.path.isfile(dest):
                log.debug("esentutl /vss copy success: %s (%d bytes)", source, os.path.getsize(dest))
                return True
            else:
                if os.path.isfile(dest):
                    os.remove(dest)
                log.debug("esentutl /vss failed for %s: rc=%d", source, result.returncode)
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            log.debug("esentutl /vss error for %s: %s", source, e)
            return False

    def _backup_copy(self, source: str, dest: str) -> bool:
        """Copy via Win32 CreateFile with FILE_FLAG_BACKUP_SEMANTICS + SeBackupPrivilege."""
        try:
            import ctypes
            import ctypes.wintypes as wt

            advapi32 = ctypes.windll.advapi32
            kernel32 = ctypes.windll.kernel32

            # Enable SeBackupPrivilege
            token = wt.HANDLE()
            kernel32.GetCurrentProcess.restype = ctypes.c_void_p
            proc = kernel32.GetCurrentProcess()
            advapi32.OpenProcessToken.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.HANDLE)]
            advapi32.OpenProcessToken(proc, 0x0028, ctypes.byref(token))

            class LUID(ctypes.Structure):
                _fields_ = [('Low', wt.DWORD), ('High', wt.LONG)]
            class LUID_AND_ATTR(ctypes.Structure):
                _fields_ = [('Luid', LUID), ('Attr', wt.DWORD)]
            class TOKEN_PRIVS(ctypes.Structure):
                _fields_ = [('Count', wt.DWORD), ('Privs', LUID_AND_ATTR * 1)]

            luid = LUID()
            advapi32.LookupPrivilegeValueW(None, 'SeBackupPrivilege', ctypes.byref(luid))
            tp = TOKEN_PRIVS()
            tp.Count = 1
            tp.Privs[0].Luid = luid
            tp.Privs[0].Attr = 2  # SE_PRIVILEGE_ENABLED
            advapi32.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)

            # Open file with backup semantics
            kernel32.CreateFileW.restype = ctypes.c_void_p
            h = kernel32.CreateFileW(
                source,
                0x80000000,   # GENERIC_READ
                0x07,         # FILE_SHARE_READ | WRITE | DELETE
                None,
                3,            # OPEN_EXISTING
                0x02000000,   # FILE_FLAG_BACKUP_SEMANTICS
                None,
            )

            if not h or h == 0xFFFFFFFFFFFFFFFF:
                err = ctypes.GetLastError()
                kernel32.CloseHandle(token)
                log.debug("Backup semantics open failed for %s: error %d", source, err)
                return False

            # Read file in chunks
            total = 0
            buf_size = 1024 * 1024
            with open(dest, 'wb') as out:
                buf = ctypes.create_string_buffer(buf_size)
                br = wt.DWORD()
                while True:
                    ok = kernel32.ReadFile(ctypes.c_void_p(h), buf, buf_size, ctypes.byref(br), None)
                    if not ok or br.value == 0:
                        break
                    out.write(buf.raw[:br.value])
                    total += br.value

            kernel32.CloseHandle(ctypes.c_void_p(h))
            kernel32.CloseHandle(token)

            if total > 0:
                log.debug("Backup semantics copy success: %s (%d bytes)", source, total)
                return True
            else:
                os.remove(dest)
                return False

        except Exception as e:
            log.debug("Backup semantics copy failed for %s: %s", source, e)
            return False

    def _tsk_copy_raw(self, source: str, dest: str) -> bool:
        """Copy via pytsk3 raw disk access. Bypasses Windows file locks."""
        try:
            abs_path = os.path.abspath(source)
            drive, local_path = os.path.splitdrive(abs_path)
            dos_drive = f"\\\\.\\{drive}"
            local_path = local_path.replace("\\", "/")

            img = pytsk3.Img_Info(dos_drive)
            try:
                fs = pytsk3.FS_Info(img)
                f = fs.open(local_path)
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

            log.debug("pytsk3 copy success: %s → %s", source, dest)
            return True

        except Exception as e:
            log.error("pytsk3 copy failed for %s: %s", source, e)
            return False

    def _copy_esentutl_vssrec(self, source: str, dest: str) -> bool:
        """Use esentutl.exe /y /vssrec for transactionally consistent ESE database copy."""
        try:
            # esentutl needs a temp path (can't write to some protected dirs)
            temp_dest = dest + ".tmp"
            log_dir = os.path.dirname(os.path.abspath(source))
            base_name = os.path.splitext(os.path.basename(source))[0]

            result = subprocess.run(
                [
                    "esentutl.exe", "/y", source,
                    "/vssrec", base_name, log_dir,
                    "/d", temp_dest,
                ],
                capture_output=True, text=True, timeout=120, creationflags=_NO_WINDOW,
            )

            if result.returncode == 0 and os.path.isfile(temp_dest):
                os.replace(temp_dest, dest)
                log.debug("esentutl copy success: %s", source)
                return True
            else:
                log.debug("esentutl returned %d: %s", result.returncode, result.stderr[:200])
                if os.path.isfile(temp_dest):
                    os.remove(temp_dest)
                return False

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            log.debug("esentutl failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Manifest and packaging
    # ------------------------------------------------------------------

    def save_manifest(self) -> None:
        with open(self._manifest_path, "w", encoding="utf-8") as f:
            json.dump(self._manifest, f, indent=2)

    def get_manifest(self) -> dict:
        return self._manifest

    def cleanup_sources(self) -> None:
        if os.path.isdir(self.sources_dir):
            shutil.rmtree(self.sources_dir)
            log.info("Cleaned up sources directory")

    def package_sources(self) -> str:
        """Zip the sources/ folder. Returns zip file path."""
        zip_path = os.path.join(self.working_dir, "sources.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.sources_dir):
                for name in files:
                    file_path = os.path.join(root, name)
                    arcname = os.path.relpath(file_path, self.working_dir)
                    zf.write(file_path, arcname)
        log.info("Packaged sources to %s", zip_path)
        return zip_path
