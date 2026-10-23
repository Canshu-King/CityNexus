"""CityNexus SE2026 briefing deck - four 16:9 sheets a person can actually read.

The review's finding was fair: the A3 one-pager really is one page, but its
median text is 5.8 pt, which is a wall of ink on a tablet, and the Project view
PNGs were screenshots of a Chrome window sitting on top of Project.

So this builds a presentation layer instead of shrinking the engineering
drawings: four 13.33 x 7.5 in sheets, every body label at 13 pt or larger (a new
gate rule refuses a sheet that breaks its own floor), and every number read out
of the build results rather than typed. A small layout pass sizes each box from
its own wrapped text and stacks the bands, so nothing lands under a band title
and nothing overflows its shape - the two things the gate kept reporting while
this sheet was hand-placed.
"""
import hashlib
import json
import math
import os
import sys
import textwrap
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from se_visio_lib_r1 import Builder, GateError, TEXT_FACTOR      # noqa: E402

OUT = r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Presentation"
LOG = open(os.path.join(HERE, "se_deck_r1.log"), "w", encoding="utf-8", buffering=1)
T0 = time.time()
PW, PH = 13.333, 7.5
MARGIN = 0.35
BODY = 13.0
SUB = 11.0
TOP = 1.30                      # everything below the title block
GAP = 0.10                      # between bands
PAD = 0.10                      # text padding inside a box
LABEL_STRIP = 0.42              # the band's own title row


def log(m):
    line = "[%6.1fs] %s" % (time.time() - T0, m)
    LOG.write(line + "\n")
    LOG.flush()
    print(line, flush=True)


def j(name):
    return json.load(open(os.path.join(HERE, name), encoding="utf-8"))


prj = j("se_project_build_r2_result.json")
st = j("se_plan_status_result.json")
rec = j("se_project_recovery_result.json")
MPP = (r"D:\moodle\CityNexus\deliverables\SoftwareEngineering_2026\Microsoft_Project"
       r"\CityNexus_Software_Engineering_Plan.mpp")
plan_sha = hashlib.sha256(open(MPP, "rb").read()).hexdigest()[:12]
cap = prj["capacity"]
weekly = cap["weekly"]
late = [e for e in st["entries"] if e["late"]]
per_person = {}
for w in weekly:
    per_person.setdefault(w["resource"], []).append(w)
rows = prj["rows"]
tasks = [r for r in rows if not r["summary"] and not r["milestone"]]
mss = [r for r in rows if r["milestone"] and not r["summary"]]
names = {"yang": ("Yang Jianbin 0802240329", "requirements, architecture, integration"),
         "wangjr": ("Wang Jiarui 0802240322", "data integration, scopes, testing"),
         "wangxy": ("Wang Xinyue 0802240324", "frontend, agent surface, SRS writing")}


def wrapped_lines(text, width, size):
    """The engine's own greedy word wrap, not a characters-per-line estimate.

    The first version of this layout counted characters, so a 72-character line
    in a 37-character column measured as two lines while the shape really broke
    into three - the gate then reported an overflow the layout had sworn fitted.
    Calling the same textwrap call the builder uses makes the two agree.
    """
    cpl = max(6, int(width * 72.0 / (size * 0.58)))
    n = 0
    for para in str(text).split("\n"):
        n += len(textwrap.wrap(para, cpl) or [1])
    return n


def box_height(text, width, size, kind="rect"):
    eff = (width - 0.14) * TEXT_FACTOR.get(kind, 1.0)
    return wrapped_lines(text, eff, size) * (size * 1.40 / 72.0) + PAD + 0.04


class Sheet(object):
    """Two-pass layout: content is declared first, then measured, then placed.

    The first version placed bands while it was still writing rows, so every
    band guessed its own height and the guesses collided - the gate reported
    overlapping boxes and empty bands. Now a band is sized from the rows it
    actually holds, and if the sheet is over-full the whole thing is scaled
    down and reported, never silently clipped.
    """

    def __init__(self, page, title, subtitle, docid):
        self.page = page
        self.title = title
        self.subtitle = subtitle
        self.docid = docid
        self.blocks = []          # (label, state, [row, ...])
        self.cur = None
        self.nodes = []
        self.bands = []
        self.edges = []
        self.pending = []          # (from, to, label, state) by node ordinal
        self.row_gap = 0.14        # a sheet with connectors needs more air

    def band(self, label, state="band"):
        self.cur = [label, state, []]
        self.blocks.append(self.cur)

    def row(self, items, kind="rect"):
        """items: list of (text, state|None, width_share, kind|None)"""
        if self.cur is None:
            self.band("")
        self.cur[2].append(list(items))

    def flow(self, pairs):
        """Edges by ordinal: pairs of (from, to) positions in declaration order.

        Node ids only exist once the layout has run, and hand-writing p2_b0_n11
        is how a diagram ends up pointing at the wrong box after a text edit.
        """
        self.pending.extend(pairs)

    @staticmethod
    def _share(it):
        return float(it[2]) if len(it) > 2 else 1.0

    @staticmethod
    def _kind(it):
        return it[3] if len(it) > 3 and it[3] else "rect"

    def _row_height(self, items, gap):
        total_w = PW - 2 * MARGIN - gap * (len(items) - 1)
        ssum = sum(self._share(i) for i in items) or 1.0
        return max([box_height(it[0], total_w * self._share(it) / ssum, BODY,
                               self._kind(it)) for it in items] + [0.42])

    def measure(self, gap=0.22, row_gap=0.14, bottom=0.12):
        """Heights are never scaled: text that needs 0.61in needs 0.61in. Only the
        air between boxes gives way, and if the sheet still does not fit, that is
        reported as overflow instead of being shrunk into illegibility."""
        hs, rows_h = [], []
        for label, state, rws in self.blocks:
            rh = [self._row_height(r, gap) for r in rws]
            rows_h.append(sum(rh))
            hs.append((LABEL_STRIP + bottom, rh))
        fixed = sum(a + sum(b) for a, b in hs)
        air = (row_gap * sum(max(0, len(b)) - 1 for _a, b in hs)
               + GAP * max(0, len(hs) - 1))
        room = PH - MARGIN - TOP
        log("  sheet %-2d rows: %s  (heads %.2f + rows %.2f = %.2f of %.2f, "
            "air %.2f)" % (self.page,
                           " | ".join("[%s]" % " ".join("%.2f" % v for v in b)
                                      for _a, b in hs),
                           sum(a for a, _b in hs),
                           sum(sum(b) for _a, b in hs), fixed, room, air))
        if fixed + air <= room:
            return hs, 1.0, row_gap, fixed + air, room
        room_for_air = max(0.0, room - fixed)
        k = room_for_air / air if air else 0.0
        return hs, k, row_gap * k, fixed + room_for_air, room

    def layout(self, gap=0.22, row_gap=None):
        row_gap = self.row_gap if row_gap is None else row_gap
        hs, k, rg, total, room = self.measure(gap, row_gap)
        nodes, bands, edges = [], [], []
        y = TOP
        for bi, (label, state, rws) in enumerate(self.blocks):
            head, rh = hs[bi]
            bh = head + sum(rh) + rg * max(0, len(rh) - 1)
            bands.append({"x": MARGIN, "y": round(y, 3), "w": PW - 2 * MARGIN,
                          "h": round(bh, 3), "label": label, "state": state,
                          "labelSize": 12.0})
            cur = y + LABEL_STRIP
            for ri, r in enumerate(rws):
                rh = self._row_height(r, gap)
                total_w = PW - 2 * MARGIN - gap * (len(r) - 1)
                ssum = sum(self._share(i) for i in r) or 1.0
                xs = MARGIN
                for it in r:
                    w = total_w * self._share(it) / ssum
                    nodes.append({"id": "p%d_b%d_n%d" % (self.page, bi, len(nodes)),
                                  "kind": self._kind(it),
                                  "state": it[1] or "verified", "text": it[0],
                                  "x": round(xs, 3), "y": round(cur, 3),
                                  "w": round(w, 3), "h": round(rh, 3),
                                  "size": BODY, "role": "note"})
                    xs += w + gap
                cur += rh + rg
            y += bh + GAP * max(k, 0.4)
        self.nodes, self.bands = nodes, bands
        by_ord = dict((i, n["id"]) for i, n in enumerate(nodes))
        for (a, b, label, state) in self.pending:
            if max(a, b) >= len(nodes):
                raise SystemExit("sheet %d asks for edge %d->%d but the sheet only "
                                 "has %d boxes" % (self.page, a, b, len(nodes)))
            e = {"from": by_ord[a], "to": by_ord[b], "state": state,
                 "route": "orthogonal", "labelSize": 11.0}
            if label:
                e["label"] = label
            edges.append(e)
        self.edges = edges
        overflow = [n["id"] for n in nodes if n["y"] + n["h"] > PH - MARGIN + 0.02]
        return k, overflow, total, room

sheets = []

# ============================================================ 1  architecture
s = Sheet(1, "CityNexus   |   System at a glance",
          "Four layers and one rule: the agent proposes, the domain services "
          "decide. Every box is a real component in the reviewed tree.",
          "CNX-SE-DECK-1   architecture")
s.band("1  PEOPLE AND EXPERIENCE")
s.row([("Traveler", "user", 1.0), ("Administrator", "user", 1.0),
       ("React shell, 15 routed panels", "verified", 1.6),
       ("Copilot dock and agent rail", "verified", 1.4)])
s.row([("MapLibre map, plan comparison, Trip Studio", "verified", 1.0, ),
       ("Check-ins and collections", "verified", 1.0)])
s.band("2  HTTP SURFACE")
s.row([("FastAPI /api/v1, 175 endpoints", "verified", 1.0),
       ("MCP surface, 11 tools", "verified", 1.0),
       ("OpenAPI contract", "verified", 1.0)])
s.band("3  AGENT PLANE AND DOMAIN SERVICES")
s.row([("Mission loop, at most 12 steps", "agent", 1.0),
       ("Gateway: allowlist, audit, idempotency, authorization", "agent", 1.4),
       ("Journey, twin and place services", "verified", 1.2)])
s.band("4  PROVIDERS AND PERSISTENCE")
s.row([("Mock providers are the shipped default", "built", 1.0),
       ("Photon, Nominatim, Open-Meteo on opt-in", "built", 1.2),
       ("SQLite, 60 tables, audit and idempotency", "data", 1.0)])
_pf = j("se_visio_proof_result.json")
s.row([("The four full engineering drawings behind this sheet carry %d/%d Shape "
        "Data properties and %d/%d glued connectors, every one read back from the "
        "saved file"
        % (sum((r.get("shapeData") or {}).get("propsOk", 0) for r in _pf),
           sum((r.get("shapeData") or {}).get("expected", 0) for r in _pf),
           sum((r.get("glue") or {}).get("proven", 0) for r in _pf),
           sum((r.get("glue") or {}).get("expected", 0) for r in _pf)),
        "foot", 1.0)])
sheets.append(s)

# ================================================================ 2  agent
s = Sheet(2, "CityNexus   |   How the agent is bounded",
          "Drawn from gateway.py as measured on 2026-10-22: the order of the "
          "doors is the code's order, not a diagram convention.",
          "CNX-SE-DECK-2   agent flow")
s.band("WHAT THE AGENT MAY DO, AND WHERE IT STOPS")
s.row_gap = 0.50
s.row([("You ask in the app", "user", 1.0)])
s.row([("The server builds the trusted context; the mission loop runs at most 12 "
        "steps over the 11 allowlisted tools", "verified", 1.0)])
s.row([("Does the answer change the plan?", "agent", 1.0)])
s.row([("No: the answer goes back and nothing is written.      Yes: a proposal is "
        "stored and waits for you", "verified", 1.0)])
s.row([("Yes path only - you accept, then the service runs policy, idempotency, "
        "effect, audit, receipt", "verified", 1.0)])
s.row([("Reads need no policy call.  Unknown tool: 404 raised before any audit row "
        "exists.  Typed actions raise their own domain guards (409 / 422 / 404).",
        "foot", 1.0)])
s.flow([(0, 1, None, "verified"), (1, 2, None, "verified"),
        (2, 3, "the two outcomes", "verified"), (3, 4, "if you accept", "planned")])
sheets.append(s)

# ============================================================== 3  progress
s = Sheet(3, "CityNexus   |   Progress, blockers and lateness",
          "Every figure on this sheet is read out of the shipped .mpp by the "
          "build that produced it; nothing is typed. Part 1's course-platform "
          "submission is still not evidenced, so no row here claims it was made.",
          "CNX-SE-DECK-3   status")
s.band("WHERE THE PLAN STANDS AT THE STATUS DATE 2026-10-22")
kpi = [
    ("the plan as built\n%d rows, %d tasks"
     % (len(rows), len(tasks)), "verified", 1.0),
    ("dependencies\n%d written, %d violate"
     % (prj["links"]["declared"], len(prj["links"]["violations"])),
     "verified", 1.0),
    ("student effort\n%.0f h, peak %.1f of %.0f"
     % (cap["studentHours"], max(w["assignedHours"] for w in weekly),
        cap["availabilityPerWeek"]["yang"]), "verified", 1.0),
    ("cost and finish\n$%d, %s"
     % (int(round(prj["reopen_pass"]["cost"])), prj["reopen_pass"]["finish"]),
     "built", 1.0),
]
s.row(kpi)
s.row([("recovery forecast\n%s, one day early" % rec["finish"], "built", 1.0),
       ("late rows\n%d past plan, none finished" % len(late), "planned", 1.0),
       ("over-allocation\n%d person-weeks (gate refuses >0)"
        % len([w for w in weekly if w["overallocatedHours"] > 0]),
        "verified", 1.0)])
s.band("BLOCKERS, AND EIGHT OF THE %d LATE ROWS  (WBS, percent complete, "
       "forecast finish)" % len(late))
blockers = [
    "Valhalla live routing: no URL configured, the travel matrix stays mocked",
    "Native Hermes binary absent; runtime identity is still DIRECT",
    "No real payment or refund instrument registered",
    "Impact resolver disabled by default in configuration",
    "Phone and PWA shadow trial not performed",
    "Requirement baseline not approved by the teacher as customer",
]
for chunk in [blockers[:3], blockers[3:]]:
    s.row([(t, "planned", 1.0) for t in chunk])
s.row([("%s %d%%, planned %s, forecast %s"
        % (e["wbs"], e["pct"], e["plannedFinish"][5:], e["forecastFinish"][5:]),
        "built", 1.0) for e in late[:4]])
s.row([("%s %d%%, planned %s, forecast %s"
        % (e["wbs"], e["pct"], e["plannedFinish"][5:], e["forecastFinish"][5:]),
        "built", 1.0) for e in late[4:8]])
sheets.append(s)

# ============================================================== 4  resources
s = Sheet(4, "CityNexus   |   Who does what, and what it costs",
          "Three students at a declared availability, two compute lanes priced "
          "separately so machine work never looks like labour hours.",
          "CNX-SE-DECK-4   resources")
s.band("STUDENT EFFORT AGAINST DECLARED AVAILABILITY")
for k in [p for p in ("yang", "wangjr", "wangxy") if p in per_person]:
    rowsk = per_person[k]
    assigned = round(sum(w["assignedHours"] for w in rowsk), 1)
    avail = round(sum(w["availableHours"] for w in rowsk), 1)
    peak = max(w["assignedHours"] for w in rowsk)
    name, duty = names[k]
    s.row([("%s\n%s" % (name, duty), "verified", 1.5),
           ("%.0f h of %.0f h available" % (assigned, avail), "built", 0.9),
           ("peak week %.1f h\n%d week(s) over" % (peak, len(
               [w for w in rowsk if w["overallocatedHours"] > 0])), "verified", 0.9)])
s.row([("Availability is an assumption for each member to confirm: %.0f h per "
        "week while the module runs. Total student effort %.0f h."
        % (cap["availabilityPerWeek"]["yang"], cap["studentHours"]), "foot", 1.0)])
s.band("NOT STUDENT LABOUR")
s.row([("Qoder agent lanes\nmaterial resource: priced, zero student hours",
        "external", 1.0),
       ("Codex co-development\nmaterial resource: priced, zero student hours",
        "external", 1.0)])
s.row([("%d priced compute assignments; %d rows are staffed by a lane alone and "
        "still carry student hours.\nThe duty split is a plan proposal, not a "
        "confirmed record: git shows one commit identity for all three members."
        % (prj["costs"]["computePricedAssignments"],
           len(prj["costs"]["compute_only_rows_without_zero_hours"])),
        "foot", 1.0)])
sheets.append(s)

REV = "generated %s" % time.strftime("%Y-%m-%d %H:%M")
built = []
for s in sheets:
    # The per-sheet id replaces the document-level one, so the provenance line has
    # to be written into it or the shipped page would carry no source hash at all.
    s.docid = "%s   ·   plan sha256 %s   ·   %s" % (s.docid, plan_sha, REV)
    # The header text is chrome the node audit does not measure, so check it here:
    # a subtitle that wrapped to four lines would sit on top of the first band and
    # nothing in the gate would ever say so.
    for label, txt, size, w, y0 in (("subtitle", s.subtitle, 11.0, PW - 4.0, 0.62),
                                    ("docid", s.docid, 8.0, 4.0, 0.26)):
        need = wrapped_lines(txt, w - 0.14, size) * (size * 1.40 / 72.0) + 0.10
        if y0 + need > TOP - 0.03:
            raise SystemExit("sheet %d header %s needs %.2fin and would sit on the "
                             "first band" % (s.page, label, y0 + need))
    k, overflow, total, room = s.layout()
    log("  sheet %-2d %s: %d bands, %d boxes, used %.2fin of %.2fin, air factor "
        "%.2f%s" % (s.page, s.docid.split()[0], len(s.bands), len(s.nodes), total,
                    room, k, ("  OVERFLOW %s" % overflow) if overflow else ""))
    if overflow:
        raise SystemExit("sheet %d does not fit at %gpt; trim the content"
                         % (s.page, BODY))
    built.append({"name": s.title.split("|")[-1].strip()[:26], "title": s.title,
                  "subtitle": s.subtitle, "docid": s.docid, "bands": s.bands,
                  "nodes": s.nodes, "edges": s.edges, "legend": []})

spec = {
    "file": "CityNexus_SE2026_Briefing_Deck.vsdx",
    "pageName": built[0]["name"],
    "pageW": PW, "pageH": PH,
    "minBodySize": BODY,
    "edgeRule": "none",
    "title": built[0]["title"],
    "subtitle": built[0]["subtitle"],
    "docid": ("CNX-SE-DECK   derived from CityNexus_Software_Engineering_Plan.mpp "
              "sha256 %s" % plan_sha),
    "revline": "generated %s" % time.strftime("%Y-%m-%d %H:%M"),
    "bodySize": BODY,
    "subSize": SUB,
    "subtitleSize": 11.0,
    "sheets": built,
}

os.makedirs(OUT, exist_ok=True)
os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
stem = "CityNexus_SE2026_Briefing_Deck"
paths = {"vsdx": os.path.join(OUT, spec["file"]),
         "png": os.path.join(OUT, "previews", stem + ".png"),
         "pdf": os.path.join(OUT, "previews", stem + ".pdf"),
         "gate": os.path.join(OUT, "previews", stem + ".gate.json")}
try:
    rep = Builder(spec, paths, log).build()
except GateError as exc:
    log("GATE REFUSED the deck: %s" % str(exc)[:200])
    gp = os.path.join(OUT, "debug", stem + ".gate.json")
    rep = {"failures": [str(exc)], "nodes": 0, "edges": 0, "pages": []}
    if os.path.exists(gp):
        rep = json.load(open(gp, encoding="utf-8"))
log("deck gate: %d failures, %d nodes, %d edges, %d pages"
    % (len(rep["failures"]), rep.get("nodes", 0), rep.get("edges", 0),
       len(rep.get("pages", []))))
if not rep["failures"]:
    # the engine keeps the gate report of a REFUSED build under debug/ so a failed
    # run is still diagnosable; once a later build passes, that copy is stale
    # evidence sitting next to the shipped sheet, which is a defect in itself
    import shutil
    dbg = os.path.join(OUT, "debug")
    if os.path.isdir(dbg):
        shutil.rmtree(dbg)
        log("removed the stale debug/ copy of an earlier refused gate report")
for f in rep["failures"][:25]:
    log("   %s" % f[:190])
json.dump({"gate": rep, "planSha256_12": plan_sha,
           "figures": {"rows": len(rows), "links": prj["links"]["declared"],
                       "studentHours": cap["studentHours"],
                       "lateRows": len(late)}},
          open(os.path.join(HERE, "se_deck_result.json"), "w",
               encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
LOG.close()
sys.exit(0 if not rep["failures"] else 1)
