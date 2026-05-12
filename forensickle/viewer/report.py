"""Generate a self-contained HTML report from collection results."""
from __future__ import annotations

import glob
import json
import logging
import os
import sys
from datetime import datetime, timezone

log = logging.getLogger(__name__)


def generate_report(working_dir: str, output_path: str | None = None) -> str:
    """
    Build an HTML report from all result JSONs and the source manifest.
    Returns the path to the generated HTML file.
    """
    results_dir = os.path.join(working_dir, "results")
    manifest_path = os.path.join(working_dir, "source_manifest.json")

    # Collect all artifact results
    artifacts = {}
    for fpath in sorted(glob.glob(os.path.join(results_dir, "*.json"))):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, content in data.items():
                artifacts[name] = {
                    "entries": content.get("data", {}).get("entries", []),
                    "source_files": content.get("source_files", []),
                    "parse_time": content.get("parse_time", ""),
                    "tenant_id": content.get("tenant_id", ""),
                    "endpoint_id": content.get("endpoint_id", ""),
                    "hostname": content.get("hostname", ""),
                }
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Failed to read %s: %s", fpath, e)

    # Collect manifest
    all_sources = []
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            sources_dict = manifest.get("sources", {})
            if isinstance(sources_dict, dict):
                all_sources = list(sources_dict.values())
            elif isinstance(sources_dict, list):
                all_sources = sources_dict
        except (json.JSONDecodeError, OSError):
            pass

    # Identity from first artifact
    identity = {}
    for a in artifacts.values():
        if a.get("endpoint_id"):
            identity = {
                "tenant_id": a.get("tenant_id", ""),
                "endpoint_id": a.get("endpoint_id", ""),
                "hostname": a.get("hostname", ""),
            }
            break

    # Build the data blob
    report_data = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "identity": identity,
        "artifacts": {
            name: {"entries": info["entries"], "source_files": info["source_files"]}
            for name, info in artifacts.items()
        },
        "source_files": all_sources,
    }

    if not output_path:
        output_path = os.path.join(working_dir, "report.html")

    html = _build_html(report_data)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    log.info("Report generated: %s", output_path)
    return output_path


def open_report(path: str):
    """Open the HTML report in the default browser."""
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        import subprocess
        subprocess.run(["open", path])
    else:
        import subprocess
        subprocess.run(["xdg-open", path])


def _build_html(data: dict) -> str:
    data_json = json.dumps(data, default=str, ensure_ascii=False)
    data_json = (data_json
        .replace("</", "<\\/")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029"))
    identity = data.get("identity", {})
    hostname = identity.get("hostname", "Unknown")
    generated = data.get("generated", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Forensickle Report — {hostname}</title>
<style>
{_CSS}
</style>
</head>
<body>
<div id="app">
  <nav id="sidebar">
    <div class="logo">
      <h2>Forensickle</h2>
      <div class="meta">
        <div>{hostname}</div>
        <div class="muted">{generated[:19]}Z</div>
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-label">Artifacts</div>
      <div id="artifact-nav"></div>
    </div>
    <div class="nav-section">
      <div class="nav-item" onclick="showSourceFiles()">
        <span class="nav-icon">📁</span> Source Files
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-item" onclick="showSummary()">
        <span class="nav-icon">📊</span> Summary
      </div>
    </div>
  </nav>
  <main id="content">
    <div id="summary-view"></div>
    <div id="table-view" style="display:none">
      <div class="table-header">
        <h3 id="table-title"></h3>
        <div class="table-controls">
          <input type="text" id="search-input" placeholder="Filter..." oninput="filterTable()">
          <span id="row-count" class="muted"></span>
        </div>
      </div>
      <div class="table-container">
        <table id="data-table">
          <thead id="table-head"></thead>
          <tbody id="table-body"></tbody>
        </table>
      </div>
      <div class="pagination" id="pagination"></div>
    </div>
  </main>
</div>
<script>
const REPORT_DATA = {data_json};
{_JS}
</script>
</body>
</html>"""


_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #1e1e1e; --bg-surface: #262626; --bg-hover: #2e2e2e;
  --text: #e0e0e0; --text-muted: #9ca3af; --text-heading: #ffffff;
  --accent: #008844; --accent-hover: #006e37;
  --border: #3a3a3a; --row-alt: #222222;
  --sidebar-w: 260px;
}
body { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--bg); color: var(--text); height: 100vh; overflow: hidden; }
#app { display: flex; height: 100vh; }

/* Sidebar */
#sidebar {
  width: var(--sidebar-w); min-width: var(--sidebar-w); background: var(--bg-surface);
  border-right: 1px solid var(--border); display: flex; flex-direction: column;
  overflow-y: auto; padding: 0;
}
.logo { padding: 20px 16px; border-bottom: 1px solid var(--border); }
.logo h2 { color: var(--accent); font-size: 20px; margin-bottom: 8px; }
.meta { font-size: 12px; color: var(--text-muted); }
.nav-section { padding: 8px 0; }
.nav-label { padding: 8px 16px 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-muted); }
.nav-item {
  padding: 7px 16px; cursor: pointer; font-size: 13px; display: flex; align-items: center;
  gap: 8px; transition: background 0.15s;
}
.nav-item:hover { background: var(--bg-hover); }
.nav-item.active { background: var(--accent); color: #fff; border-radius: 4px; margin: 0 8px; }
.nav-icon { font-size: 14px; width: 20px; text-align: center; }
.nav-badge { margin-left: auto; font-size: 11px; color: var(--text-muted); background: var(--bg); padding: 1px 6px; border-radius: 8px; }
.nav-item.active .nav-badge { background: rgba(0,0,0,0.2); color: #fff; }

/* Main content */
main { flex: 1; overflow: hidden; display: flex; flex-direction: column; padding: 20px; }

/* Views — both fill remaining space inside `main` (a flex column) and scroll internally */
#summary-view { flex: 1; min-height: 0; overflow-y: auto; }
#table-view { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }
.stat-card { background: var(--bg-surface); padding: 16px; border-radius: 8px; border: 1px solid var(--border); }
.stat-value { font-size: 28px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* Table */
.table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-shrink: 0; }
.table-header h3 { color: var(--text-heading); }
.table-controls { display: flex; align-items: center; gap: 12px; }
#search-input {
  background: var(--bg-surface); border: 1px solid var(--border); color: var(--text);
  padding: 6px 12px; border-radius: 6px; font-size: 13px; width: 250px; outline: none;
}
#search-input:focus { border-color: var(--accent); }
.table-container { flex: 1; overflow: auto; border: 1px solid var(--border); border-radius: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead { position: sticky; top: 0; z-index: 1; }
th {
  background: var(--bg-surface); padding: 10px 12px; text-align: left; font-weight: 600;
  border-bottom: 2px solid var(--border); cursor: pointer; white-space: nowrap; user-select: none;
}
th:hover { background: var(--bg-hover); }
th .sort-arrow { margin-left: 4px; font-size: 10px; color: var(--text-muted); }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
tr:nth-child(even) { background: var(--row-alt); }
tr:hover { background: var(--bg-hover); }

/* Pagination */
.pagination { display: flex; justify-content: center; align-items: center; gap: 8px; padding: 12px 0; flex-shrink: 0; }
.page-btn {
  background: var(--bg-surface); border: 1px solid var(--border); color: var(--text);
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.page-btn:hover { background: var(--bg-hover); }
.page-btn.active { background: var(--accent); color: #fff; border-color: var(--accent); }
.page-info { font-size: 12px; color: var(--text-muted); }

.muted { color: var(--text-muted); }
.empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); }
"""

_JS = """
const PAGE_SIZE = 100;
let currentData = [];
let currentColumns = [];
let currentPage = 0;
let sortCol = -1;
let sortAsc = true;
let filterText = '';

function init() {
  buildNav();
  showSummary();
}

function buildNav() {
  const nav = document.getElementById('artifact-nav');
  const artifacts = REPORT_DATA.artifacts;
  const names = Object.keys(artifacts).sort();
  names.forEach(name => {
    const count = artifacts[name].entries.length;
    const div = document.createElement('div');
    div.className = 'nav-item';
    div.setAttribute('data-artifact', name);
    div.onclick = () => showArtifact(name);
    div.innerHTML = `<span class="nav-icon">📋</span>${formatName(name)}<span class="nav-badge">${count}</span>`;
    nav.appendChild(div);
  });
}

function formatName(name) {
  return name.replace(/_/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase());
}

function setActiveNav(selector) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  if (selector) {
    const el = document.querySelector(selector);
    if (el) el.classList.add('active');
  }
}

function showSummary() {
  setActiveNav(null);
  document.getElementById('summary-view').style.display = '';
  document.getElementById('table-view').style.display = 'none';

  const artifacts = REPORT_DATA.artifacts;
  const names = Object.keys(artifacts);
  const totalEntries = names.reduce((sum, n) => sum + artifacts[n].entries.length, 0);
  const totalSources = REPORT_DATA.source_files.length;
  const identity = REPORT_DATA.identity;

  let html = '<h3 style="margin-bottom:16px;color:var(--text-heading)">Collection Summary</h3>';
  html += '<div class="summary-grid">';
  html += statCard(names.length, 'Artifacts');
  html += statCard(totalEntries.toLocaleString(), 'Total Entries');
  html += statCard(totalSources, 'Source Files');
  html += statCard(identity.hostname || '—', 'Hostname');
  html += '</div>';

  // Per-artifact breakdown
  html += '<h4 style="margin:20px 0 12px;color:var(--text-heading)">Artifact Breakdown</h4>';
  html += '<div class="table-container"><table><thead><tr><th>Artifact</th><th>Entries</th><th>Source Files</th></tr></thead><tbody>';
  names.sort().forEach(name => {
    const a = artifacts[name];
    html += `<tr><td>${formatName(name)}</td><td>${a.entries.length}</td><td>${a.source_files.length}</td></tr>`;
  });
  html += '</tbody></table></div>';

  // Identity
  if (identity.endpoint_id) {
    html += '<h4 style="margin:20px 0 12px;color:var(--text-heading)">Endpoint Identity</h4>';
    html += '<div style="background:var(--bg-surface);padding:16px;border-radius:8px;border:1px solid var(--border);font-family:Consolas,monospace;font-size:13px;line-height:1.8">';
    html += `Endpoint ID: ${identity.endpoint_id}<br>`;
    html += `Hostname: ${identity.hostname}<br>`;
    html += `Tenant ID: ${identity.tenant_id || 'Not configured'}`;
    html += '</div>';
  }

  document.getElementById('summary-view').innerHTML = html;
}

function statCard(value, label) {
  return `<div class="stat-card"><div class="stat-value">${value}</div><div class="stat-label">${label}</div></div>`;
}

function showArtifact(name) {
  setActiveNav(`.nav-item[data-artifact="${name}"]`);
  const artifact = REPORT_DATA.artifacts[name];
  if (!artifact || artifact.entries.length === 0) {
    showEmpty(formatName(name), 'No parsed entries for this artifact.');
    return;
  }
  showTable(formatName(name), artifact.entries);
}

function showSourceFiles() {
  setActiveNav(null);
  // Highlight the source files nav item
  document.querySelectorAll('.nav-item').forEach(el => {
    if (el.textContent.includes('Source Files')) el.classList.add('active');
  });
  const sources = REPORT_DATA.source_files;
  if (!sources.length) {
    showEmpty('Source Files', 'No source files were retained.');
    return;
  }
  // Enrich with filename
  const enriched = sources.map(s => ({
    filename: s.path ? s.path.split(/[\\\\/]/).pop() : '',
    ...s,
  }));
  showTable('Source Files', enriched);
}

function showTable(title, rows) {
  document.getElementById('summary-view').style.display = 'none';
  document.getElementById('table-view').style.display = '';
  document.getElementById('table-title').textContent = title;
  document.getElementById('search-input').value = '';

  // Determine columns from all rows
  const colSet = new Set();
  rows.forEach(row => Object.keys(row).forEach(k => colSet.add(k)));
  currentColumns = Array.from(colSet);
  currentData = rows;
  currentPage = 0;
  sortCol = -1;
  filterText = '';
  renderTable();
}

function showEmpty(title, msg) {
  document.getElementById('summary-view').style.display = 'none';
  document.getElementById('table-view').style.display = '';
  document.getElementById('table-title').textContent = title;
  document.getElementById('table-head').innerHTML = '';
  document.getElementById('table-body').innerHTML = `<tr><td class="empty-state" colspan="99">${msg}</td></tr>`;
  document.getElementById('row-count').textContent = '';
  document.getElementById('pagination').innerHTML = '';
  document.getElementById('search-input').value = '';
}

function getFilteredData() {
  if (!filterText) return currentData;
  const lower = filterText.toLowerCase();
  return currentData.filter(row =>
    currentColumns.some(col => String(row[col] ?? '').toLowerCase().includes(lower))
  );
}

function getSortedData(data) {
  if (sortCol < 0) return data;
  const col = currentColumns[sortCol];
  return [...data].sort((a, b) => {
    let va = a[col] ?? '', vb = b[col] ?? '';
    if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
    va = String(va).toLowerCase(); vb = String(vb).toLowerCase();
    return sortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
  });
}

function renderTable() {
  const filtered = getFilteredData();
  const sorted = getSortedData(filtered);
  const totalPages = Math.ceil(sorted.length / PAGE_SIZE);
  if (currentPage >= totalPages) currentPage = Math.max(0, totalPages - 1);
  const start = currentPage * PAGE_SIZE;
  const pageRows = sorted.slice(start, start + PAGE_SIZE);

  // Header
  let headHtml = '<tr>';
  currentColumns.forEach((col, i) => {
    const arrow = sortCol === i ? (sortAsc ? ' ▲' : ' ▼') : '';
    headHtml += `<th onclick="sortBy(${i})">${col}<span class="sort-arrow">${arrow}</span></th>`;
  });
  headHtml += '</tr>';
  document.getElementById('table-head').innerHTML = headHtml;

  // Body
  let bodyHtml = '';
  pageRows.forEach(row => {
    bodyHtml += '<tr>';
    currentColumns.forEach(col => {
      let val = row[col] ?? '';
      if (typeof val === 'object') val = JSON.stringify(val);
      bodyHtml += `<td title="${String(val).replace(/"/g, '&quot;')}">${escHtml(String(val))}</td>`;
    });
    bodyHtml += '</tr>';
  });
  if (!pageRows.length) bodyHtml = '<tr><td class="empty-state" colspan="99">No matching rows</td></tr>';
  document.getElementById('table-body').innerHTML = bodyHtml;

  // Count
  document.getElementById('row-count').textContent =
    `${filtered.length} row${filtered.length !== 1 ? 's' : ''}` +
    (filtered.length !== currentData.length ? ` (of ${currentData.length})` : '');

  // Pagination
  renderPagination(totalPages);
}

function renderPagination(totalPages) {
  const pg = document.getElementById('pagination');
  if (totalPages <= 1) { pg.innerHTML = ''; return; }
  let html = '';
  html += `<button class="page-btn" onclick="goPage(0)" ${currentPage === 0 ? 'disabled' : ''}>«</button>`;
  html += `<button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 0 ? 'disabled' : ''}>‹</button>`;
  html += `<span class="page-info">Page ${currentPage + 1} of ${totalPages}</span>`;
  html += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>›</button>`;
  html += `<button class="page-btn" onclick="goPage(${totalPages - 1})" ${currentPage >= totalPages - 1 ? 'disabled' : ''}>»</button>`;
  pg.innerHTML = html;
}

function goPage(p) { currentPage = p; renderTable(); }
function sortBy(col) {
  if (sortCol === col) { sortAsc = !sortAsc; } else { sortCol = col; sortAsc = true; }
  renderTable();
}
function filterTable() {
  filterText = document.getElementById('search-input').value;
  currentPage = 0;
  renderTable();
}
function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

init();
"""
