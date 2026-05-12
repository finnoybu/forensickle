"""Artifact: WMI Persistence — event consumers, filters, and bindings via PowerShell."""
import json as _json, logging, os, subprocess, sys
from ..core.collector import SourceCollector
from ..core.output import ResultBuilder

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
log = logging.getLogger(__name__)
NAME = "wmi_persistence"
_OBJECTS_DATA = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "wbem", "Repository", "OBJECTS.DATA")

_PS_CMD = r"""
$consumers = Get-WmiObject -Namespace root\subscription -Class __EventConsumer -EA SilentlyContinue
$filters   = Get-WmiObject -Namespace root\subscription -Class __EventFilter   -EA SilentlyContinue
$bindings  = Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding -EA SilentlyContinue
$fmap = @{}; if ($filters) { foreach ($f in $filters) { $fmap[$f.__PATH] = $f } }
foreach ($c in $consumers) {
    $b = $bindings | Where-Object { $_.Consumer -eq $c.__PATH } | Select-Object -First 1
    $fRef = if ($b) { $b.Filter } else { $null }
    $f = if ($fRef -and $fmap.ContainsKey($fRef)) { $fmap[$fRef] } else { $null }
    [ordered]@{
        type=$c.__CLASS; name=$c.Name; creator_sid=($c.CreatorSID -join '-')
        event_filter=if($f){$f.Name}else{''}; filter_query=if($f){$f.QueryLanguage+': '+$f.Query}else{''}
        executable_path=if($c.ExecutablePath){$c.ExecutablePath}else{''}
        command_line_template=if($c.CommandLineTemplate){$c.CommandLineTemplate}else{''}
        script_file=if($c.ScriptFileName){$c.ScriptFileName}else{''}
        scripting_engine=if($c.ScriptingEngine){$c.ScriptingEngine}else{''}
        script_text=if($c.ScriptText){$c.ScriptText}else{''}
    } | ConvertTo-Json -Compress
}
"""


def _obj_timestamps() -> dict:
    out = {"object_file_path": _OBJECTS_DATA, "object_file_created": None,
           "object_file_accessed": None, "object_file_modified": None, "object_file_entry_modified": None}
    try:
        st = os.stat(_OBJECTS_DATA)
        out["object_file_created"] = int(getattr(st, "st_birthtime", st.st_ctime) * 1000)
        out["object_file_modified"] = int(st.st_mtime * 1000)
        out["object_file_accessed"] = int(st.st_atime * 1000)
        out["object_file_entry_modified"] = int(st.st_ctime * 1000)
    except OSError:
        pass
    return out


def _resolve_sid_bytes(sid_str: str) -> str | None:
    try:
        p = [int(x) for x in sid_str.split("-") if x]
        if len(p) < 8:
            return None
        auth = int.from_bytes(bytes(p[2:8]), "big")
        subs = [int.from_bytes(bytes(p[8+i*4:12+i*4]), "little") for i in range(p[1])]
        sid = f"S-{p[0]}-{auth}" + "".join(f"-{s}" for s in subs)
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"(New-Object System.Security.Principal.SecurityIdentifier('{sid}')).Translate([System.Security.Principal.NTAccount]).Value"],
            capture_output=True, text=True, timeout=10, creationflags=_NO_WINDOW)
        return r.stdout.strip() or None
    except Exception:
        return None


def _query_ps() -> list[dict]:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", _PS_CMD],
                           capture_output=True, text=True, timeout=60, creationflags=_NO_WINDOW)
        entries = []
        for line in r.stdout.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(_json.loads(line))
                except _json.JSONDecodeError:
                    pass
        return entries
    except (subprocess.SubprocessError, FileNotFoundError):
        return []


def _query_wmi_mod() -> list[dict]:
    try:
        import wmi as _wmi
        c = _wmi.WMI(namespace=r"root\subscription")
        return [{
            "type": (con.derivation() or [con.__class__.__name__])[0], "name": getattr(con, "Name", ""),
            "creator_sid": "", "event_filter": "", "filter_query": "",
            "executable_path": getattr(con, "ExecutablePath", ""),
            "command_line_template": getattr(con, "CommandLineTemplate", ""),
            "script_file": getattr(con, "ScriptFileName", ""),
            "scripting_engine": getattr(con, "ScriptingEngine", ""),
            "script_text": getattr(con, "ScriptText", ""),
        } for con in c.__getattr__("__EventConsumer")()]
    except Exception:
        return []


def collect(collector: SourceCollector) -> list[dict]:
    if os.path.isfile(_OBJECTS_DATA):
        e = collector.collect_file(_OBJECTS_DATA)
        return [e] if e else []
    return []


def parse(collector: SourceCollector) -> ResultBuilder:
    result = ResultBuilder(NAME)
    result.add_sources(collect(collector))
    obj_ts = _obj_timestamps()
    for entry in (_query_ps() or _query_wmi_mod()):
        entry["creator_name"] = _resolve_sid_bytes(entry.get("creator_sid", "")) if entry.get("creator_sid") else None
        entry.update(obj_ts)
        result.add_entry(entry)
    return result
