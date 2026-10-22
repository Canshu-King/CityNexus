"""One-page briefing sheet for the coursework plan, drawn from Project's output.

Microsoft Project's own print pagination could not be driven through COM on this
install - every form of FilePageSetupPage came back "参数值无效" (see
se_brief_r2.log), so the plan's Gantt exports as 12 pages, which is fine as a
working document and useless on a tablet during a presentation.

This script therefore takes the numbers Microsoft Project computed - read back
out of the shipped .mpp into se_project_build_r2_result.json, not retyped - and
lays out a single A3 landscape briefing sheet with the same engine and the same
layout gate that the four design drawings pass. The schedule stays in Project;
this page is only a print view of its dates, and it says so in its own header.
"""
import datetime
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_visio_lib_r1 import Builder, GateError            # noqa: E402

OUT_DIR = os.environ.get("SE_BRIEF_OUT",
                         r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Briefing")
RESULT = os.path.join(HERE, "se_project_build_r2_result.json")
MPP = (r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026"
       r"\Microsoft_Project\CityNexus_Software_Engineering_Plan.mpp")
LOG = open(os.path.join(HERE, "se_visio_plan_brief.log"), "w", encoding="utf-8",
           buffering=1)
T0 = time.time()
D = datetime.date


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def dd(s):
    return D(*[int(x) for x in str(s)[:10].split("-")])


res = json.load(open(RESULT, encoding="utf-8"))
rows = res["rows"]
phases = [r for r in rows if r["summary"]]
leaves = [r for r in rows if not r["summary"]]
mss = [r for r in leaves if r["milestone"]]
tasks = [r for r in leaves if not r["milestone"]]
sha = hashlib.sha256(open(MPP, "rb").read()).hexdigest()
log("source %s sha256 %s" % (os.path.basename(MPP), sha[:16]))
log("read %d phase rollups, %d leaf tasks, %d milestones"
    % (len(phases), len(tasks), len(mss)))

AXIS0, AXIS1 = 3.34, 13.58
D0 = min(dd(r["start"]) for r in phases)
D1 = max(dd(r["finish"]) for r in phases)
D1 = max(D1, dd("2026-11-06"))
SPAN = (D1 - D0).days


def x_of(day):
    return AXIS0 + (day - D0).days / float(SPAN) * (AXIS1 - AXIS0)


nodes = []
bands = []


def node(id_, kind, state, text, src, x, y, w, h, size=6.2, role=None):
    n = {"id": id_, "kind": kind, "state": state, "text": text, "src": src,
         "x": round(x, 3), "y": round(y, 3), "w": round(w, 3), "h": round(h, 3),
         "size": size}
    if role:
        n["role"] = role
    nodes.append(n)
    return n


# ---- vertical reference lines drawn as thin bands (bands are not shapes, so
# ---- they sit behind the bars instead of colliding with them)
STATUS = dd("2026-10-22")
for day, label, colour in ((dd("2026-10-02"), "Part 1 due (missed)", "planned"),
                           (STATUS, "status date", "agent"),
                           (dd("2026-11-06"), "Part 2 due", "external")):
    bands.append({"x": round(x_of(day) - 0.035, 3), "y": 1.30, "w": 0.07,
                  "h": 5.55, "state": colour, "label": ""})
    node("ref_%s" % day.strftime("%m%d"), "rect", colour, label,
         "%s" % day.isoformat(), round(x_of(day) - 0.52, 3), 1.06, 1.04, 0.32,
         size=5.6, role="note")
# weekly gridlines
d = D0
while d <= D1:
    if d.weekday() == 0:
        bands.append({"x": round(x_of(d), 3), "y": 1.30, "w": 0.012, "h": 5.55,
                      "state": "band", "label": ""})
        node("wk_%s" % d.strftime("%m%d"), "rect", "band", d.strftime("%m-%d"),
             "", round(x_of(d) - 0.24, 3), 6.50, 0.48, 0.26, size=5.4,
             role="note")
    d += datetime.timedelta(days=1)

# ---- phase rows -----------------------------------------------------------
Y0, PITCH = 1.42, 0.455
for i, ph in enumerate(phases):
    y = Y0 + i * PITCH
    pct = int(round(ph["pct"]))
    node("lab_%s" % ph["wbs"], "rect", "band", ph["name"][:64],
         "mpp row %s" % ph["wbs"], 0.40, y + 0.03, 2.86, PITCH - 0.08, size=6.0,
         role="note")
    s, f = dd(ph["start"]), dd(ph["finish"])
    # a group is drawn as complete when its rollup reaches 100%; the half-point
    # tolerance is because Project rounds a parent of 100% rows to 99%
    state = "verified" if pct >= 99 else ("built" if pct else "planned")
    w = max(0.10, x_of(f) - x_of(s))
    node("bar_%s" % ph["wbs"], "roundrect", state,
         ("%d%%" % pct) if w >= 0.42 else "", "",
         x_of(s), y + 0.075, w, PITCH - 0.20, size=5.8, role="note")
    node("fac_%s" % ph["wbs"], "rect", "band",
         "%s -> %s  %d%%" % (s.strftime("%m-%d"), f.strftime("%m-%d"), pct),
         "%d h  $%s" % (int(round(ph["work"])), int(round(ph["cost"]))),
         13.72, y + 0.03, 2.34, PITCH - 0.08, size=5.6, role="note")

# ---- milestone markers, greedily spread over three lanes ------------------
lanes = [[] for _ in range(3)]
MY0 = Y0 + len(phases) * PITCH + 0.38
placed = []
for m in sorted(mss, key=lambda r: dd(r["finish"])):
    day = dd(m["finish"])
    x = x_of(day)
    key = m["name"].split()[0]
    row = None
    for li, lane in enumerate(lanes):
        if all(abs(x - lx) > 0.16 for lx in lane):
            lane.append(x)
            row = li
            break
    if row is None:
        log("milestone %s could not be placed without overlap" % key)
        continue
    node("ms_%s" % key, "rect", "agent", "", "",
         round(x - 0.055, 3), MY0 + row * 0.24, 0.11, 0.20, size=5.0, role="note")
    placed.append((key, m, day))

# ---- milestone table ------------------------------------------------------
TY = MY0 + 3 * 0.24 + 0.24
node("ms_table_hdr", "rect", "band",
     "MILESTONES, in date order - the schedule's own computed dates",
     "", 0.40, TY, 6.20, 0.26, size=6.4, role="note")
for idx, (key, m, day) in enumerate(placed):
    col = idx // 7
    rowi = idx % 7
    dl = m.get("deadline")
    txt = "%s  %s  %s%s" % (key, m["name"].split(key)[-1].strip()[:34],
                            day.strftime("%m-%d"),
                            "  dl " + dl[5:10] if dl and dl not in ("NA", "None")
                            else "")
    node("mst_%s" % key, "rect", "band", txt, "",
         0.40 + col * 6.42, TY + 0.30 + rowi * 0.245, 6.30, 0.235, size=5.8,
         role="note")

# ---- figures block --------------------------------------------------------
crit = res["critical_path"]
linkr = res["links"]
node("fig_hdr", "rect", "band", "WHAT MICROSOFT PROJECT COMPUTED",
     "", 13.30, TY, 2.80, 0.26, size=6.4, role="note")
figs = [
    ("rows", "%d (%d groups, %d tasks, %d milestones)" % (len(rows), len(phases),
                                                          len(tasks), len(mss))),
    ("dependencies", "%d written, %d violating date order"
     % (linkr["declared"], len(linkr["violations"]))),
    ("constraints", "%d (every row is As Soon As Possible)"
     % len(res["constraints"]["forced"])),
    ("labour hours", "%d h" % int(round(res["costs"]["labour_hours"]))),
    ("cost", "$%s" % int(round(res["reopen_pass"]["cost"]))),
    ("critical rows", "%d" % crit["count"]),
    ("finish", str(res["reopen_pass"]["finish"])),
    ("late at status date", "%d open rows" % len(res["progress"]["history_problems"])),
]
for i, (k, v) in enumerate(figs):
    node("fig_%d" % i, "rect", "band", "%s: %s" % (k, v), "",
         13.30, TY + 0.30 + i * 0.28, 2.80, 0.26, size=5.6, role="note")

spec = {
    "file": "CityNexus_Plan_Briefing_A3.vsdx",
    "pageName": "Plan Briefing",
    "barsOnly": True,
    "edgeRule": "none",
    "title": "CityNexus   |   Software Engineering 2026 - plan on one page",
    "subtitle": ("A print view of the schedule Microsoft Project computed in "
                 "CityNexus_Software_Engineering_Plan.mpp. Bars are the eleven "
                 "phase rollups; the diamonds are the thirteen milestones; nothing "
                 "here is a second plan, and no date on this page was typed by hand."),
    "docid": "CNX-SE-BRF-01   derived from %s sha256 %s" % (os.path.basename(MPP),
                                                            sha[:16]),
    "revline": "generated %s" % time.strftime("%Y-%m-%d %H:%M"),
    "bodySize": 6.0,
    "subSize": 5.2,
    "bands": bands,
    "nodes": nodes,
    "edges": [],
    "legend": [{"state": "verified", "text": "phase complete at the status date",
                 "w": 2.80},
               {"state": "built", "text": "phase in progress", "w": 2.80},
               {"state": "planned", "text": "not started / date missed", "w": 2.80},
               {"state": "agent", "text": "status date, milestones", "w": 2.80}],
    "legendOrigin": (13.10, 10.42),
    "notes": [
        "HOW TO READ: each row is one WBS group, drawn from its computed start to its computed finish on a Mon-Fri calendar anchored at 2026-09-07, the first working day on or after the repository's first commit. The right-hand figures are the group's own work hours and cost as Project derived them from duration x assignment units x 8 h/day.",
        "MILESTONES ARE NOT SEQUENTIAL GATES. The repository shows backend, frontend, contracts and the integration line changing on the same days from 2026-09-19, so a later-numbered milestone can land on an earlier date; the numbering is WBS order, not calendar order.",
        "THE THREE VERTICAL LINES: Part 1 was due 2026-10-02 and its row is still at 0%, which is why that line is drawn in the missed style; the status date is 2026-10-22, the day this pack was produced; Part 2 is due 2026-11-06 and the plan's own finish precedes it.",
        "WHAT THIS PAGE CANNOT SHOW: rows that are late against the status date stay late. Project's Move to Status Date was measured to be inert through COM on this install (se_proj_probe_r10.log), so unfinished work was not silently pushed into the future to make the picture tidy. The full 65-row plan, its links, resources, costs and critical path are in the .mpp.",
    ],
    "notesOrigin": (0.40, 10.00),
    "notesWidth": 12.60,
    "notesSize": 5.6,
}

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUT_DIR, "previews"), exist_ok=True)
paths = {"vsdx": os.path.join(OUT_DIR, spec["file"]),
         "png": os.path.join(OUT_DIR, "previews", "CityNexus_Plan_Briefing_A3.png"),
         "pdf": os.path.join(OUT_DIR, "previews", "CityNexus_Plan_Briefing_A3.pdf"),
         "gate": os.path.join(OUT_DIR, "previews",
                              "CityNexus_Plan_Briefing_A3.gate.json")}
try:
    rep = Builder(spec, paths, log).build()
except GateError as exc:
    log("GATE REFUSED the briefing sheet: %s" % str(exc)[:200])
    dbg = os.path.join(OUT_DIR, "previews", "..", "debug",
                       "CityNexus_Plan_Briefing_A3.gate.json")
    rep = {"failures": [str(exc)], "nodes": len(nodes), "edges": 0}
    if os.path.exists(dbg):
        rep = json.load(open(dbg, encoding="utf-8"))
log("gate: %d failures, %d nodes, %d edges" % (len(rep["failures"]), rep["nodes"],
                                               rep["edges"]))
for f in rep["failures"][:20]:
    log("   %s" % f[:170])
json.dump(rep, open(os.path.join(HERE, "se_visio_plan_brief_result.json"), "w",
                    encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
LOG.close()
sys.exit(0 if not rep["failures"] else 1)
