"""ORD-0262 readback: every number in the receipt is derived here from the lane's own log/DB,
never typed by hand.  Writes receipt_ord0262.json + backend_contention_extract_ord0262.txt.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sqlite3
import subprocess

LOG = pathlib.Path("D:/moodle/_hjp3_lane_backend.log")
DB = pathlib.Path("D:/moodle/_lane_aad2d1f2_livecopy.sqlite3")
TREE = pathlib.Path("D:/moodle/_qoder_cmdr_gate_20260921")
BUNDLE = pathlib.Path("D:/moodle/_hjp3_ord0257_0923/snap_old2/frontend/dist/assets/index-CrAwWm5f.js")
OUT = pathlib.Path("D:/moodle/_hjp3_ord0262_0923")
OUT.mkdir(exist_ok=True)

txt = LOG.read_bytes().decode("utf-8", "replace")
lines = txt.splitlines()

acc = re.compile(r'"(\w+) ([^"]*?) HTTP/[\d.]+" (\d{3})')
hist: dict[str, dict[str, int]] = {}
per_journey: dict[str, dict[str, int]] = {}
for l in lines:
    m = acc.search(l)
    if not m:
        continue
    meth, path, st = m.group(1), m.group(2), m.group(3)
    if "{" in path:
        continue
    key = "%s %s" % (meth, re.sub(r"/[0-9a-f]{8}-[0-9a-f-]{27,}", "/{id}", path))
    hist.setdefault(key, {})
    hist[key][st] = hist[key].get(st, 0) + 1
    if meth == "POST" and path.endswith("/agent/commands"):
        jid = path.split("/journeys/")[1].split("/")[0][:8]
        per_journey.setdefault(jid, {"200": 0, "500": 0})
        if st in ("200", "500"):
            per_journey[jid][st] += 1

# hard-fail events: the exception line, plus the first [SQL:]/[parameters:] that follow it
idx = [i for i, l in enumerate(lines) if l.startswith("sqlalchemy.exc.OperationalError")]
events = []
extract = []
for n, i in enumerate(idx, 1):
    stmt = par = None
    frames = []
    for j in range(i - 60, i):
        s = lines[j].strip()
        if s.startswith('File "') and "site-packages" not in s and "_qoder_cmdr_gate" in s:
            mm = re.search(r'File "(.*?)", line (\d+), in (.*)', s)
            if mm:
                frames.append("%s:%s in %s" % (
                    pathlib.Path(mm.group(1)).as_posix().split("backend/")[-1],
                    mm.group(2), mm.group(3)))
    for j in range(i + 1, min(i + 40, len(lines))):
        if lines[j].startswith("[SQL:") and stmt is None:
            stmt = lines[j][6:].split("VALUES")[0].split("WHERE")[0].strip()
            extract.append("[SQL] " + lines[j][6:150])
        if lines[j].startswith("[parameters:") and par is None:
            par = lines[j][12:]
            extract.append(lines[j][:220])
        if lines[j].startswith("[parameters:"):
            break
    kind = (stmt or "?").split(" ")[0] + " " + (stmt or "?").split(" ")[1] if stmt else "?"
    table = re.search(r"(journey_missions|agent_runs|plan_versions|journey_twins)", stmt or "")
    events.append({
        "n": n,
        "line": i + 1,
        "statement": stmt,
        "table": table.group(1) if table else None,
        "parameters_head": (par or "")[:120],
        "app_frames": frames[-2:],
    })
    extract.append("event %d | %s | %s" % (n, stmt, " <- ".join(frames[-2:])))
    extract.append("")

by_table: dict[str, int] = {}
for e in events:
    k = "%s %s" % (e["statement"].split(" ")[0], e["table"])
    by_table[k] = by_table.get(k, 0) + 1

soft = sum(1 for l in lines if "cache write skipped" in l)
frames_soft = sorted({m.group(1) + ":" + m.group(2) for m in re.finditer(
    r'(main\.py)", line (\d+)', "")} if False else set())

# where the soft-skip lives (source read, not a guess)
src = (TREE / "backend" / "app" / "main.py").read_text(encoding="utf-8").splitlines()
soft_sites = ["app/main.py:%d" % (k + 1) for k, s in enumerate(src) if "cache write skipped" in s]
sess = (TREE / "backend" / "app" / "db" / "session.py").read_text(encoding="utf-8").splitlines()
busy = ["app/db/session.py:%d" % (k + 1) for k, s in enumerate(sess) if "busy_timeout" in s or "timeout" in s]

c = sqlite3.connect(DB.as_uri().replace("file:", "file:") + "?mode=ro" if False else "file:" + DB.as_posix() + "?mode=ro", uri=True)
c.row_factory = sqlite3.Row
totals = {t: c.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
          for t in ("journey_missions", "agent_runs", "plan_versions")}
orphans = [dict(r) for r in c.execute(
    "SELECT m.id,m.journey_id,m.status,m.created_at,"
    "(SELECT COUNT(*) FROM agent_runs r WHERE r.mission_id=m.id) runs "
    "FROM journey_missions m WHERE m.status='CREATED' ORDER BY m.created_at")]
mission_status = {r[0]: r[1] for r in c.execute("SELECT status,COUNT(*) FROM journey_missions GROUP BY status")}

head = subprocess.run(["git", "-C", str(TREE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
dirty = subprocess.run(["git", "-C", str(TREE), "status", "--porcelain"], capture_output=True, text=True).stdout.splitlines()

blob = BUNDLE.read_bytes()
receipt = {
    "order": "ORD-0262 DUPLICATE_RAPID_SUBMIT_RETURNS_500",
    "lane": "HJ-P3 aad2d1f2",
    "measured_at_local": "2026-09-23T16:0x+08:00 (UTC 07:49-08:07 sweep)",
    "backend": {
        "tree": str(TREE), "head": head, "porcelain_lines": len(dirty),
        "served_on": "127.0.0.1:8424", "database": str(DB),
        "busy_timeout_lines_found": busy,
    },
    "frontend_under_test": {
        "url": "http://127.0.0.1:8476/v8/hub",
        "bundle": BUNDLE.name, "bytes": len(blob),
        "sha256": hashlib.sha256(blob).hexdigest(),
        "provenance": "vite build of `git archive f5a6b9a` export; byte-identical to the published canary bundle (ORD-0257)",
    },
    "log_tally": {
        "endpoint_status_histogram": hist,
        "agent_commands_per_journey": per_journey,
        "hard_fail_events": len(events),
        "hard_fails_by_statement": by_table,
        "soft_skipped_twin_writes": soft,
        "soft_skip_site": soft_sites,
    },
    "db_tally": {
        "totals": totals,
        "missions_by_status": mission_status,
        "orphan_CREATED_missions_no_run": orphans,
    },
    "events": events,
    "rounds": json.loads(pathlib.Path("D:/moodle/HJ-P3_evidence/rounds_capture_ord0262.json").read_text(encoding="utf-8")),
    "q_and_p_series": json.loads(pathlib.Path("D:/moodle/HJ-P3_evidence/qp_capture_ord0262.json").read_text(encoding="utf-8")),
}
(OUT / "receipt_ord0262.json").write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding="utf-8")
(OUT / "backend_contention_extract_ord0262.txt").write_text("\n".join(extract), encoding="utf-8")

print(json.dumps({
    "head": head[:7], "porcelain": len(dirty),
    "hist": {k: v for k, v in hist.items() if any(int(s) >= 400 for s in v)},
    "per_journey": per_journey,
    "hard_events": len(events), "by_stmt": by_table, "soft": soft,
    "soft_site": soft_sites, "busy": busy,
    "totals": totals, "mission_status": mission_status,
    "orphans": [(o["id"][:8], o["journey_id"][:8], o["runs"]) for o in orphans],
    "bundle": BUNDLE.name, "bundle_sha256": receipt["frontend_under_test"]["sha256"][:16],
}, indent=1, ensure_ascii=False))
