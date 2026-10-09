#!/usr/bin/env python3
"""ORD-0553 / 长瓦工 -- roll the lane's own readings into committed text.

Nothing here writes a number by hand: every line is read out of an artefact this lane produced (e2e
evidence JSON, the Playwright run logs, the arm's own output files) and every value carries the path
it came from.  `review/evidence/` is gitignored, so without this rollup the readings would exist only
on this machine.

The two screen runs are told apart by what the row actually painted, not by a hard-coded run id:
the arm that still prints an ISO date fragment is the control (parent bytes), the other is the cut.
"""

import glob
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # the lane tree
OUT = os.path.join(ROOT, "review", "changwagong")
EV = os.path.join(ROOT, "review", "evidence", "ord0553")
ISO = re.compile(r"\d{4}-\d{2}-\d{2}")
SPEC_LINES = "frontend/e2e/qoder-ord0553-changwagong-batch-row-r1.spec.ts"


def read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def rel(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def summary(log_text):
    p = re.search(r"(\d+) passed", log_text)
    f = re.search(r"(\d+) failed", log_text)
    return "passed=%s failed=%s" % (p.group(1) if p else "0", f.group(1) if f else "0")


def log_for(run_id):
    path = os.path.join(ROOT, "review", "run-%s.log" % run_id)
    return path if os.path.exists(path) else None


def write(name, lines):
    text = "\n".join(lines) + "\n"
    with io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    sys.stdout.buffer.write(("wrote %s lines=%d\n" % (name, len(lines))).encode("utf-8"))


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(EV, "*__R1*.json"))):
        d = json.loads(read(path))
        d["_run"] = os.path.basename(path).split("__")[0]
        d["_file"] = rel(path)
        d["_mtime"] = os.path.getmtime(path)
        rows.append(d)
    if not rows:
        sys.stdout.buffer.write(b"NO_SCREEN_EVIDENCE: review/evidence/ord0553 has no R1 json\n")
        return 2
    # tell the runs apart by what the row painted: a run whose row still shows an ISO date fragment
    # is the control (parent bytes), any other run is the cut.  Latest of each wins.
    runs = {}
    for d in rows:
        runs.setdefault(d["_run"], []).append(d)
    ordered = sorted(runs.items(), key=lambda kv: max(x["_mtime"] for x in kv[1]))
    after = [d for r, ds in ordered if not any(ISO.search(d["painted"]) for d in ds) for d in ds]
    before = [d for r, ds in ordered if any(ISO.search(d["painted"]) for d in ds) for d in ds]
    after = [d for d in after if d["_run"] == max(r for r, ds in ordered
                                                  if not any(ISO.search(x["painted"]) for x in ds))]
    before = [d for d in before if d["_run"] == max(r for r, ds in ordered
                                                    if any(ISO.search(x["painted"]) for x in ds))]

    lines = ["# ORD-0553 长瓦工 -- discovery batch read-back row: painted screen text AFTER the cut",
             "# locale | painted | this device's own reading of the same instant | old shape | artefact"]
    for d in sorted(after, key=lambda x: x["locale"]):
        lines.append("%s | painted=%s | device=%s | old_shape_would_be=%s | zone=%s | %s" % (
            d["locale"], d["painted"], d["device_reading"], d["old_painting_would_have_been"],
            d["device_zone"], d["_file"]))
        log = log_for(d["_run"])
        if log:
            lines.append("run_id=%s %s | %s | base_tip=%s" % (d["_run"], summary(read(log)), rel(log), d["base_tip"]))
    lines.append("spec=%s" % SPEC_LINES)
    write("ord0553_screen_after_r1.txt", lines)

    lines = ["# ORD-0553 长瓦工 -- the SAME spec against the parent bytes (BEFORE the cut)",
             "# control shape: in this same tree the one product file was restored with",
             "#   git checkout HEAD^ -- frontend/src/features/discovery/RealCityDiscoveryPanel.tsx",
             "# so HEAD is this lane's commit while the bytes are the authoritative tip's.",
             "# locale | painted | what the device reading demanded | artefact"]
    for d in sorted(before, key=lambda x: x["locale"]):
        lines.append("%s | painted=%s | device=%s | %s" % (
            d["locale"], d["painted"], d["device_reading"], d["_file"]))
        log = log_for(d["_run"])
        if log:
            for ln in [l for l in read(log).splitlines() if "ISO fragment" in l][:2]:
                lines.append("  log> %s" % ln.strip())
    write("ord0553_screen_before_control_r1.txt", lines)

    lines = ["# ORD-0435 Q4 (the real compose WRITE route) on this lane's stack -- both sides red",
             "# after = candidate bytes, control = parent bytes; same line, same sentence, so the red is a",
             "# precondition of this store, not a regression from this cut. The refusal this screen can hit is",
             "# named in the product file's own ORD-0435 comment (V13_FULL_GROUNDING_MISSING_MOBILITY_PAIR)."]
    for log in sorted(glob.glob(os.path.join(ROOT, "review", "run-run*.log")), key=os.path.getmtime):
        text = read(log)
        if "poi-batch-multiselect" not in text:
            continue
        run_id = os.path.basename(log)[4:-4]
        lines.append("run_id=%s %s | %s" % (run_id, summary(text), rel(log)))
        for ln in [l for l in text.splitlines() if "produced no read-back block" in l][:1]:
            lines.append("  log> %s" % ln.strip())
    write("ord0553_ord0435_preexisting_red_r1.txt", lines)

    arms = {"after": os.path.join(OUT, "ord0553_arm_after.txt"),
            "control": os.path.join(OUT, "ord0553_arm_before_control.txt")}
    lines = ["# ORD-0553 长瓦工 -- the static arm on both sides (arm: review/changwagong/ord0553_discovery_batch_row_arm_r1.py)"]
    for label, path in arms.items():
        text = read(path)
        lines.append("%s: %s | PASS=%d FAIL=%d | %s" % (
            label, text.splitlines()[0], len(re.findall(r"^PASS", text, re.M)),
            len(re.findall(r"^FAIL", text, re.M)), rel(path)))
    for ln in [l for l in read(arms["control"]).splitlines() if l.startswith("FAIL")]:
        lines.append("  control> %s" % ln)
    write("ord0553_arm_both_sides_r1.txt", lines)

    lines = ["# ORD-0553 长瓦工 -- anti-collision reading, frozen when this lane took the file",
             "# ruler: _qoder_cmdr_ref_20260921/live_checks/patrol/_live_orders_reader_r1.py",
             "# plus the local ref scan, because ls-remote cannot see a lane branch that never left this box."]
    lines.extend(read(os.path.join(OUT, "_claims_capture.txt")).splitlines())
    write("ord0553_claim_scan_r1.txt", lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
