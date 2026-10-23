"""Re-derive every claim in the independent review from the shipped artefacts.

Nothing here trusts the review or my own earlier summary: counts come from the
JSON specs, the proof result, the gate reports, the build result and the
source code itself.
"""
import glob
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
DEL = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = r"D:\moodle\CityNexus"
from se_project_plan_r1 import PLAN  # noqa: E402


def key_of(name):
    m = re.match(r"^(M\d+|\d+(?:\.\d+)?)\s", name)
    return m.group(1) if m else None


print("=" * 72)
print("1. VISIO SPEC TOTALS (shipped JSON)")
tn = te = tb = 0
for f in sorted(glob.glob(os.path.join(DEL, "Visio", "specs", "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    tn += len(d["nodes"])
    te += len(d["edges"])
    tb += len(d.get("bands", []))
    print("   %-46s nodes=%3d edges=%3d bands=%d"
          % (os.path.basename(f), len(d["nodes"]), len(d["edges"]), len(d.get("bands", []))))
print("   TOTAL nodes=%d edges=%d bands=%d  (2*edges=%d connection ends)"
      % (tn, te, tb, 2 * te))

print("=" * 72)
print("2. PER-SHAPE PROPERTY READBACK in se_visio_proof_result.json")
vp = json.load(open(os.path.join(HERE, "se_visio_proof_result.json"), encoding="utf-8"))
for r in vp:
    steps = r.get("steps", {})
    print("   %-46s ok=%s glue=%s/%s" % (r["file"], r.get("ok"),
                                         (r.get("glue") or {}).get("proven"),
                                         (r.get("glue") or {}).get("expected")))
    idx = steps.get("index", {})
    print("        index step ok=%s value-type=%s" % (idx.get("ok"), type(idx.get("value")).__name__))
print("   -> the proof never counted NodeId/State/SourceRef; it only used them to")
print("      select shapes. Review claim 'no per-shape property assertion exists'")
print("      is checked next against the gate reports.")

print("=" * 72)
print("3. GATE REPORTS: custom-property failures")
for f in sorted(glob.glob(os.path.join(DEL, "Visio", "previews", "*.gate.json"))):
    d = json.load(open(f, encoding="utf-8"))
    notes = d.get("notes", []) or []
    prop = [n for n in notes if "custom property" in n]
    print("   %-46s notes=%d custom-property-skipped=%d shapeIds=%d edgeIds=%d"
          % (os.path.basename(f), len(notes), len(prop),
             len(d.get("shapeIds", {})), len(d.get("edgeIds", {}))))
    if prop:
        print("        sample: %s" % prop[0])

print("=" * 72)
print("4. PROJECT: declared links vs the dates Project actually produced")
prj = json.load(open(os.path.join(HERE, "se_project_build_result.json"), encoding="utf-8"))
wbs = prj["first_pass"]["wbs"]
by_key = {}
for row in wbs:
    k = key_of(row[1] or "")
    if k:
        by_key[k] = {"wbs": row[0], "name": row[1], "start": row[2], "finish": row[3],
                     "pct": row[4], "cost": row[5], "mode": row[6]}
declared = []
for r in PLAN:
    k = key_of(r["name"])
    for lk in r.get("links", []):
        m = re.match(r"^(.+?)(FS|SS|FF|SF)$", lk)
        declared.append((k, m.group(1), m.group(2)))
ms_rows = [key_of(r["name"]) for r in PLAN if r["kind"] == "ms" and r.get("ms_date")]
print("   declared links = %d ; milestones with pinned ms_date = %d" % (len(declared), len(ms_rows)))
print("   build log said 'links applied on 38 rows'")


def dt(s):
    try:
        y, mo, d = s.split("-")
        return (int(y), int(mo), int(d))
    except Exception:
        return None


viol, unapp, okc = [], [], 0
for src, typ in [(a, b) for _t, a, b in declared]:
    pass
for tgt, src, typ in declared:
    t = by_key.get(tgt)
    s = by_key.get(src)
    if not t or not s:
        unapp.append("%s->%s%s (row missing)" % (src, tgt, typ))
        continue
    if src in ms_rows and tgt in ms_rows:
        pass
    sf, ss, ts, tf = dt(s["finish"]), dt(s["start"]), dt(t["start"]), dt(t["finish"])
    if None in (sf, ss, ts, tf):
        unapp.append("%s->%s%s (unreadable date)" % (src, tgt, typ))
        continue
    good = {"FS": ts >= sf, "SS": ts >= ss, "FF": tf >= sf, "SF": ts >= sf}[typ]
    rec = "%-6s -> %-6s %s : pred %s..%s  succ %s..%s   [%s %s / %s %s]" % (
        src, tgt, typ, s["start"], s["finish"], t["start"], t["finish"],
        s["name"][:22], s["wbs"], t["name"][:22], t["wbs"])
    if good:
        okc += 1
    else:
        viol.append(rec)
print("   satisfied = %d ; VIOLATED = %d ; unusable = %d" % (okc, len(viol), len(unapp)))
for v in viol:
    print("     VIOLATION  %s" % v)
for v in unapp[:6]:
    print("     UNUSABLE   %s" % v)

print("=" * 72)
print("5. GATEWAY CONTROL FLOW (source truth for BLOCKER 3)")
gw = os.path.join(REPO, "backend", "app", "agent", "gateway.py")
lines = open(gw, encoding="utf-8", errors="replace").read().split("\n")
start = next(i for i, l in enumerate(lines) if "def dispatch(" in l)
for i in range(start, min(start + 45, len(lines))):
    l = lines[i]
    if re.search(r"def dispatch|not in RUNTIME_MCP_ALLOWLIST|raise HTTPException|record_audit|handlers = |return handlers|self\.session\.commit", l):
        print("   %5d  %s" % (i + 1, l.strip()[:110]))
rr = [i for i, l in enumerate(lines) if "def request_replan(" in l]
if rr:
    i0 = rr[0]
    print("   --- request_replan ordering ---")
    for i in range(i0, min(i0 + 60, len(lines))):
        l = lines[i]
        if re.search(r"evaluate_action|_read_idempotent|_write_idempotent|record_audit|def request_replan", l):
            print("   %5d  %s" % (i + 1, l.strip()[:110]))
print("=" * 72)
print("6. ZIP INVENTORY vs what the brief claims")
zp = json.load(open(os.path.join(HERE, "se_review_package_result.json"), encoding="utf-8"))
print("   zip members = %d ; manifest entries = %d" % (zp.get("members"), zp.get("manifest_entries")))
brief = open(os.path.join(DEL, "Evidence", "REVIEW_BRIEF.md"), encoding="utf-8").read()
m = re.search(r"包内文件数 \*\*(\d+)\*\*", brief)
print("   brief claims payload = %s" % (m.group(1) if m else "?"))
m2 = re.search(r"(\d+) 形状 / (\d+) 连线", brief)
print("   brief claims nodes/edges = %s" % (m2.groups() if m2 else "?"))
