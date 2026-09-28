"""ORD-0410 lane: assemble the committed evidence pack.

Every number the delivery block quotes has to be retrievable, so the receipts are copied into
`review/ord0410/` on the same branch as the fix and read back as git blobs.  The port-ownership
probe is re-run here rather than transcribed, so the committed artifact is the measurement.
"""
import json
import os
import re
import shutil
import sqlite3
import subprocess
import urllib.parse

RUN = "D:/moodle/_qoder_r_ord0410/run"
LC = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
OUT = "D:/moodle/_qoder_r_ord0410/wt/review/ord0410"
WT = "D:/moodle/_qoder_r_ord0410/wt"
os.makedirs(OUT, exist_ok=True)

# 1. the running backend's identity, measured now (three proofs, with a negative control).
MARK = "CNX-R0410-MARKER"
ns = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True,
                    encoding="utf-8", errors="replace").stdout
pids = [l.split()[-1] for l in ns.splitlines() if "127.0.0.1:8711" in l and "LISTENING" in l]
pid = pids[0] if pids else None
ps = subprocess.run(["powershell", "-NoProfile", "-Command",
                     'Get-CimInstance Win32_Process -Filter "ProcessId=%s" | '
                     "Select-Object ProcessId,ParentProcessId,CommandLine | ConvertTo-Json -Compress" % pid],
                    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
try:
    info = json.loads(ps)
except Exception:
    info = {}


def api(city):
    u = "http://127.0.0.1:8711/api/v1/places?city_code=" + urllib.parse.quote(city)
    body = subprocess.run(["curl", "-s", u], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
    status = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", u],
                            capture_output=True, text=True, encoding="utf-8").stdout
    try:
        parsed = json.loads(body)
        n = len(parsed) if isinstance(parsed, list) else len(parsed.get("items", []))
    except Exception:
        n = -1
    return {"status": status, "rows": n}


con = sqlite3.connect("D:/moodle/_qoder_r_ord0410/run/_r_ord0410.db", timeout=10)
rows_here = con.execute("select count(*) from places where city_code=?", (MARK,)).fetchone()[0]
con.close()
log = open(os.path.join(RUN, "backend_8711.log"), encoding="utf-8", errors="replace").read()
# The user's preview DB is only ever statted here, never opened for writing.  Two reads around a
# request to the lane backend turn "I did not touch it" into something a reader can check.
preview = "D:/moodle/_qoder_preview_20260920/_preview.db"
p_before = (os.path.getmtime(preview), os.path.getsize(preview))
subprocess.run(["curl", "-s", "-o", "/dev/null",
                "http://127.0.0.1:8711/api/v1/journeys/22222222-2222-4222-8222-222222222222/experience"],
               capture_output=True, text=True, timeout=60)
p_after = (os.path.getmtime(preview), os.path.getsize(preview))
ownership = {
    "lane_backend_port": 8711,
    "listening_pid": pid,
    "listening_pid_command_line": (info.get("CommandLine") or "").strip(),
    "launcher_printed_server_pid": re.findall(r"Started server process \[(\d+)\]", log),
    "sqlite_rows_for_marker_city_in_lane_copy": rows_here,
    "api_marker_city": api(MARK),
    "api_absent_city_negative_control": api("CNX-R0410-NOSUCH"),
    "lane_db_copy": RUN + "/_r_ord0410.db",
    "users_preview_db_stat_before": p_before,
    "users_preview_db_stat_after": p_after,
    "users_preview_db_stat_unchanged": p_before == p_after,
}
with open(os.path.join(OUT, "PORT_OWNERSHIP_r1.json"), "w", encoding="utf-8") as fh:
    json.dump(ownership, fh, ensure_ascii=False, indent=1)

# 2. instrument receipts, copied verbatim.
copies = {
    "attribution_base_214ab0ff_r1.json": RUN + "/_attr/attribution.json",
    "attribution_fix_r1.json": RUN + "/_attr_fix/attribution.json",
    "recenter_receipt_214ab0ff_r1.json": RUN + "/_repro_base/receipt.json",
    "recenter_receipt_c24e619b_r1.json": RUN + "/_repro_fix/receipt.json",
    "recenter_receipt_3552c56f_r1.json": RUN + "/_repro_rebased/receipt.json",
    # Discarded reading kept on purpose: 0 markers on the page, yet `cleared_state` reads true.
    # A first instrument run whose stack was not rendering produced it, and it is the reason the
    # gate asserts its own precondition instead of trusting the reading.
    "recenter_receipt_DISCARDED_false_green_r1.json": RUN + "/_repro_basereceipt.json",
    "screen_214ab0ff_RED.png": RUN + "/_repro_base/final.png",
    "screen_3552c56f_GREEN.png": RUN + "/_repro_rebased/final.png",
    "lsremote_r1.txt": RUN + "/lsremote_final.txt",
    "cause_attrib_r1.js": RUN + "/_cause_attrib_r1.js",
    "diag_stack_r1.js": RUN + "/_diag_stack_r1.js",
    "start_backend_r1.py": RUN + "/start_backend_r1.py",
    "copy_db_r1.py": RUN + "/copy_db_r1.py",
    "run_gate_r1.sh": RUN + "/run_gate_r1.sh",
}
for name, src in copies.items():
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(OUT, name))
    else:
        print("MISSING", name, src)

# 3. gate logs, trimmed to the lines that carry a reading or a verdict.
KEEP = re.compile(r"one-press — |^\s+\d+\) \[|^\s+ok \d+ \[|^\s+\d+ (passed|failed)|Error: |Expected:|Received:")
for name in ["gate_fix_run1.log", "gate_mutant_run1.log", "gate_rebased_regression.log",
             "gate_mutant_rebased.log", "gate_0403_fix_only.log", "gate_ord0410_fix_run2.log"]:
    src = os.path.join(RUN, name)
    if not os.path.isfile(src):
        print("MISSING LOG", name)
        continue
    lines = [l for l in open(src, encoding="utf-8", errors="replace").read().splitlines()
             if KEEP.search(l) and "[WebServer]" not in l]
    with open(os.path.join(OUT, name.replace(".log", "_trimmed.txt")), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("trimmed", name, "->", len(lines), "lines")

# 4. the readings file, computed from the artifacts that were just copied.
def load(p):
    return json.load(open(os.path.join(OUT, p), encoding="utf-8")) if os.path.isfile(os.path.join(OUT, p)) else {}


base_attr = load("attribution_base_214ab0ff_r1.json")
fix_attr = load("attribution_fix_r1.json")
r_base = load("recenter_receipt_214ab0ff_r1.json")
r_re = load("recenter_receipt_3552c56f_r1.json")
rows = []
for arm, rec in [("base 214ab0ff", r_base), ("delivered 3552c56f", r_re)]:
    rows.append({"instrument": "_recenter_marker_move_r5.js", "generation": arm,
                 "served_assets": rec.get("served_assets"),
                 "markers_at_rest": rec.get("marker_count_at_rest"),
                 "state_after_recenter_1": (rec.get("state_after_recenter_1") or {}).get("state"),
                 "recenter_1_moved_markers": rec.get("recenter_1_moved_markers"),
                 "recenter_1_cleared_state": rec.get("recenter_1_cleared_state"),
                 "pageerrors": rec.get("pageerrors")})
lines = ["ORD-0410 lane R receipts — every value below is read out of the JSON files in this directory.",
         "",
         "cause attribution on the defective generation (attribution_base_214ab0ff_r1.json):",
         "  data-route-legs at rest                 = %s" % (base_attr.get("atRest") or {}).get("legs"),
         "  fitBounds calls reaching the live map  = %s" % base_attr.get("clickReachedLiveFitBounds"),
         "  moveends during the press              = %s" % base_attr.get("moveendsDeltaDuringClick"),
         "  live instance same object as installed = %s" % (base_attr.get("afterClick") or {}).get("sameInstanceAsInstalled"),
         "  live map removed                       = %s" % (base_attr.get("afterClick") or {}).get("liveMapRemoved"),
         "  hand-made fitBounds moved the markers  = %s" % base_attr.get("manualFitMovedMarkers"),
         "  markers moved by the press             = %s" % base_attr.get("clickMovedMarkers"),
         "  pageerrors                             = %s" % base_attr.get("pageerrors"),
         "",
         "the same instrument on the delivered generation (attribution_fix_r1.json):",
         "  data-route-legs at rest                 = %s" % (fix_attr.get("atRest") or {}).get("legs"),
         "  fitBounds calls reaching the live map  = %s" % fix_attr.get("clickReachedLiveFitBounds"),
         "  moveends during the press              = %s" % fix_attr.get("moveendsDeltaDuringClick"),
         "  markers moved by the press             = %s" % fix_attr.get("clickMovedMarkers"),
         "",
         "bundle receipts:"]
for r in rows:
    lines.append("  %s" % json.dumps(r, ensure_ascii=False))
lines += ["",
          "discarded first run, kept deliberately (recenter_receipt_DISCARDED_false_green_r1.json): "
          "markers_at_rest=%s and yet recenter_1_cleared_state=%s — that stack was not rendering at all "
          "(the lane launcher had built an env dict it never applied), so a 'cleared' reading there "
          "meant nothing. It is why the gate pins its precondition."
          % ((load("recenter_receipt_DISCARDED_false_green_r1.json") or {}).get("marker_count_at_rest"),
             (load("recenter_receipt_DISCARDED_false_green_r1.json") or {}).get("recenter_1_cleared_state")),
          "",
          "port ownership: PORT_OWNERSHIP_r1.json (marker city rows = %s, negative control rows = %s)"
          % (ownership["api_marker_city"]["rows"], ownership["api_absent_city_negative_control"]["rows"]),
          "",
          "gate runs: *_trimmed.txt carry each arm's `one-press` reading line and the pass/fail summary."]
with open(os.path.join(OUT, "READINGS_r1.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("\n".join(lines[:24]))
print("files in pack:", sorted(os.listdir(OUT)))
