"""Artifact: Scheduled Tasks — XML parsing with file hashing and live metadata."""
import logging
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from ..core.hash_utils import file_hashes
from ..core.output import ResultBuilder

log = logging.getLogger(__name__)

_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

NAME = "scheduled_tasks"
TASKS_DIR = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "Tasks")
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
_MAX_XML = 7196


def collect(collector):
    sources = []

    def _on_walk_error(exc):
        log.warning("Failed to enumerate %s: %s", getattr(exc, "filename", "?"), exc)

    for dirpath, _, filenames in os.walk(TASKS_DIR, onerror=_on_walk_error):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            entry = collector.collect_file(full)
            if entry:
                sources.append(entry)
    return sources


def parse(collector) -> dict:
    result = ResultBuilder(NAME)
    sources = collect(collector)
    result.add_sources(sources)
    live = _query_live_tasks()

    for sf in sources:
        path = collector.collected_path(sf) or sf["path"]
        try:
            _parse_task(path, sf["path"], live, result)
        except (ET.ParseError, OSError) as exc:
            log.debug("Failed to parse task %s: %s", sf["path"], exc)
    return result


def _parse_task(path, orig_path, live, result):
    tree = ET.parse(path)
    root = tree.getroot()

    def _f(tag):
        el = root.find(f".//{{{NS}}}{tag}")
        if el is None:
            el = root.find(f".//{tag}")
        return el.text.strip() if el is not None and el.text else None

    # Actions — collect all Exec commands
    actions = []
    command = None
    for ex in root.findall(f".//{{{NS}}}Exec") or root.findall(".//Exec"):
        cmd = (ex.findtext(f"{{{NS}}}Command") or ex.findtext("Command") or "").strip()
        args = (ex.findtext(f"{{{NS}}}Arguments") or ex.findtext("Arguments") or "").strip()
        action_str = f"{cmd} {args}".strip()
        actions.append(action_str)
        if command is None and cmd:
            command = cmd

    # Triggers summary
    triggers = []
    triggers_el = root.find(f"{{{NS}}}Triggers") or root.find("Triggers")
    if triggers_el is not None:
        for child in triggers_el:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            triggers.append(tag)

    # Resolve and hash command binary
    cmd_path = _resolve_command(command)
    ch = file_hashes(cmd_path) if cmd_path else None
    cts = _timestamps(cmd_path)

    # Task file timestamps
    tts = _timestamps(orig_path)

    # Raw XML (truncated)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            task_xml = fh.read(_MAX_XML)
    except OSError:
        task_xml = None

    # Live metadata
    task_name = orig_path.replace(TASKS_DIR, "").lstrip(os.sep).replace(os.sep, "\\")
    info = live.get(task_name.lower(), {})

    result.add_entry({
        "name": task_name,
        "actions": actions,
        "triggers": triggers,
        "command": command,
        "enabled": _f("Enabled"),
        "last_run_time": info.get("last_run_time"),
        "last_task_result": info.get("last_task_result"),
        "hidden": _f("Hidden"),
        "author": _f("Author"),
        "task_file_path": orig_path,
        "task_file_created": tts[0],
        "task_file_accessed": tts[1],
        "task_file_modified": tts[2],
        "task_file_entry_modified": tts[3],
        "command_md5": ch["md5"] if ch else None,
        "command_sha1": ch["sha1"] if ch else None,
        "command_sha256": ch["sha256"] if ch else None,
        "command_file_created": cts[0],
        "command_file_accessed": cts[1],
        "command_file_modified": cts[2],
        "command_file_entry_modified": cts[3],
        "task_xml": task_xml,
    })


def _resolve_command(command):
    if not command:
        return None
    p = os.path.expandvars(command.strip().strip('"'))
    if not os.path.isabs(p):
        p = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", p)
    return p if os.path.isfile(p) else None


def _query_live_tasks():
    """Use schtasks /query to get last run time and result for each task."""
    tasks = {}
    try:
        out = subprocess.check_output(
            ["schtasks", "/query", "/fo", "CSV", "/v"],
            creationflags=_NO_WINDOW, text=True, timeout=30,
            stderr=subprocess.DEVNULL,
        )
        lines = out.strip().splitlines()
        if not lines:
            return tasks
        header = lines[0].replace('"', "").split(",")
        idx_name = _col(header, "TaskName")
        idx_lrt = _col(header, "Last Run Time")
        idx_ltr = _col(header, "Last Result")
        if idx_name is None:
            return tasks
        for line in lines[1:]:
            cols = _csv_split(line)
            if len(cols) <= max(filter(None, [idx_name, idx_lrt, idx_ltr]), default=0):
                continue
            name = cols[idx_name].lstrip("\\")
            tasks[name.lower()] = {
                "last_run_time": cols[idx_lrt] if idx_lrt is not None else None,
                "last_task_result": cols[idx_ltr] if idx_ltr is not None else None,
            }
    except Exception as exc:
        log.debug("schtasks query failed: %s", exc)
    return tasks


def _col(header, name):
    for i, h in enumerate(header):
        if name.lower() in h.lower():
            return i
    return None


def _csv_split(line):
    """Naive CSV split handling double-quoted fields."""
    cols, cur, in_q = [], [], False
    for ch in line:
        if ch == '"':
            in_q = not in_q
        elif ch == ',' and not in_q:
            cols.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    cols.append("".join(cur).strip())
    return cols


def _timestamps(path):
    if not path or not os.path.isfile(path):
        return (None, None, None, None)
    try:
        s = os.stat(path)
        return (int(s.st_ctime * 1000), int(s.st_atime * 1000),
                int(s.st_mtime * 1000), int(s.st_ctime * 1000))
    except OSError:
        return (None, None, None, None)
