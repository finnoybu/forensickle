"""Artifact: Prefetch — binary .pf parser for versions 17/23/26/30."""
import glob, logging, os, struct
from ..core.collector import SourceCollector
from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder
from ..core.timestamp_utils import filetime_to_epoch_ms

log = logging.getLogger(__name__)
NAME = "prefetch"
_PATTERN = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Prefetch", "*.pf")
_SCCA = 0x53434341
# (ts_offset, ts_count, fn_off_pos, fn_len_pos, run_count_offset)
_LAYOUTS = {17: (0x78,1,0x64,0x68,0x90), 23: (0xA0,1,0x64,0x68,0x98), 26: (0xA0,8,0x64,0x68,0xD0)}


def _decompress_mam(data: bytes) -> bytes | None:
    if data[:4] != b"MAM\x04" or len(data) < 8:
        return None
    size = struct.unpack_from("<I", data, 4)[0]
    try:
        import ctypes
        ntdll = ctypes.windll.ntdll
        buf = ctypes.create_string_buffer(size)
        final = ctypes.c_ulong(0); ws = ctypes.c_ulong(0); fs = ctypes.c_ulong(0)
        ntdll.RtlGetCompressionWorkSpaceSize(4, ctypes.byref(ws), ctypes.byref(fs))
        work = ctypes.create_string_buffer(ws.value)
        if ntdll.RtlDecompressBufferEx(4, buf, size, data[8:], len(data)-8, ctypes.byref(final), work):
            return None
        return buf.raw[:final.value]
    except Exception as e:
        log.debug("MAM decompression error: %s", e)
        return None


def _u(d, off, fmt="<I"):
    return struct.unpack_from(fmt, d, off)[0] if off + struct.calcsize(fmt) <= len(d) else None


def _parse_pf(data: bytes, src: str) -> dict | None:
    if len(data) < 84:
        return None
    ver, sig = struct.unpack_from("<II", data, 0)
    if sig != _SCCA:
        return None
    exe = data[16:76].decode("utf-16-le", errors="replace").rstrip("\x00")
    if ver == 30:
        m = _u(data, 0xC8) or 304
        layout = (0xA0 if m == 304 else 0x80, 8, 0x64, 0x68, 0xD0)
    elif ver in _LAYOUTS:
        layout = _LAYOUTS[ver]
    else:
        return None
    ts_off, ts_n, fn_op, fn_lp, rc_off = layout
    ts = {}
    for i in range(ts_n):
        ft = _u(data, ts_off + i*8, "<Q")
        ts[f"run_time_{i}"] = filetime_to_epoch_ms(ft) if ft else None
    # Fill remaining slots with None so schema is consistent
    for i in range(ts_n, 8):
        ts[f"run_time_{i}"] = None
    fn_off = _u(data, fn_op) or 0; fn_len = _u(data, fn_lp) or 0
    fnames = []
    if fn_off + fn_len <= len(data) and fn_len >= 2:
        fnames = [s for s in data[fn_off:fn_off+fn_len].decode("utf-16-le", errors="replace").split("\x00") if s]
    # Resolve target path
    target, eu = None, exe.upper()
    for fn in fnames:
        if fn.upper().endswith(eu):
            target = fn.replace("\\VOLUME{", "").replace("}", "")
            if target.startswith("\\DEVICE\\"):
                parts = target.split("\\", 4)
                if len(parts) >= 5:
                    target = os.path.join(os.environ.get("SystemDrive", "C:") + os.sep, parts[4])
            break
    h = file_hashes(target) if target and os.path.isfile(target) else {}
    return {"path": src, "name": exe, "run_count": _u(data, rc_off), "file_names": fnames,
            **ts, "target_path": target,
            "md5": h.get("md5"), "sha1": h.get("sha1"), "sha256": h.get("sha256")}


def collect(collector: SourceCollector) -> list[dict]:
    return [e for p in glob.glob(_PATTERN) if (e := collector.collect_file(p))]


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    for sf in sources:
        cp = collector.collected_path(sf)
        if not cp:
            continue
        try:
            raw = open(cp, "rb").read()
        except OSError:
            continue
        if raw[:4] == b"MAM\x04":
            data = _decompress_mam(raw)
            if data is None:
                log.warning("Failed to decompress Win10 prefetch: %s", sf["path"])
                continue
        else:
            data = raw
        entry = _parse_pf(data, sf["path"])
        if entry:
            result.add_entry(entry)
        else:
            log.debug("Failed to parse prefetch: %s (ver=%s, len=%d)", sf["path"],
                      struct.unpack_from("<I", data, 0)[0] if len(data) >= 4 else "?", len(data))
    return result
