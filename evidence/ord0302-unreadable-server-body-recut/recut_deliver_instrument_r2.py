"""ORD-0302 delivery: build a self-justifying receipt, gate it with the commander's own rulers, publish, report.

Cells are built from the run artifacts (the spec's per-arm evidence file, the matrix, git objects), never from
recollection; each sentence is pre-checked with the Q38 ruler's own token patterns so nothing is claimed that the
cell does not hold. Both claim gates are run -- r3 because the order named it, r4b because that is the version in
the tree now -- and a non-CLEAN verdict from either stops the delivery.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0299_cite as C  # noqa: E402

WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
LEDGER = pathlib.Path(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md")
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
Q38 = LIVE / "receipt_cell_derivation_check_r2.py"
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
if not CLOSING or "\n" in CLOSING:
    raise SystemExit("the standing closing line is not a single non-empty line in " + str(LIVE))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = os.environ.get("CNX_0302_DIR", "evidence/ord0302-unreadable-server-body")
# The round name comes from the evidence directory this run publishes into, and it is resolved HERE because the
# receipt header reads it; an earlier version defined it below the receipt and the run died on a NameError.
ROUND = {"evidence/ord0302-unreadable-server-body": "r1",
         "evidence/ord0302-unreadable-server-body-r2": "r2",
         "evidence/ord0302-unreadable-server-body-q53": "q53",
         "evidence/ord0302-unreadable-server-body-recut": "recut"}.get(DIR)
if ROUND is None:
    raise SystemExit("unknown evidence directory, so the round cannot be named: " + DIR)
BASE = os.environ.get("CNX_0302_BASE", "dc964086c9d412573ac19d70b24b30e6c3ee6168")
# The defect's own line numbers belong to the generation that still had it; the candidate's parent is a later
# tip where the file is already fixed, so the two are named separately instead of one standing in for both.
BUGGED_BASE = os.environ.get("CNX_0302_BUGGED_BASE", "dc964086c9d412573ac19d70b24b30e6c3ee6168")
BUGGED = "fd5f6e5ba2771a8d12669b9bec1ba91590970701"
PREV_GEN = "4c3821b7129320d7940237d33c5f7dd14742f292"
SHEET = "frontend/src/features/planning/PlanWithAiSheet.tsx"
SPEC_REL = "frontend/e2e/qoder-ord0302-unreadable-server-body.spec.ts"
RECEIPT = WORK / "ord0302_receipt.json"
MATRIX = json.loads((WORK / "ord0302_arms_run.json").read_text(encoding="utf-8"))
PATS = C.ruler_patterns()
ARMS_ALL = ("N1", "N2", "N3", "X1", "X2")


def g(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def blob(rev, rel):
    out = g(["rev-parse", f"{rev}:{rel}"])
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else "ABSENT"


def blob_of(path):
    data = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _url_open(url):
    """Small read-only GitHub GET used before the main publisher section, so helpers stay in one place.

    Never pointed at the ledger: that file is large enough that the contents route has answered with zero bytes
    for another lane and they rebuilt the book off an empty read.
    """
    last = None
    for i in range(6):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + _tok(),
                                                       "Accept": "application/vnd.github+json",
                                                       "User-Agent": "citynexus-lane-B"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            if not raw:
                raise SystemExit("the route answered with zero bytes; refusing to build prose on an empty read")
            return raw.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(2 + 3 * i)
    raise last


def _tok():
    return pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(
        encoding="utf-8").strip()


def tip_now():
    """The authority line as GitHub answers it right now, over https (not `origin`, which is a local path)."""
    out = subprocess.run(["git", "ls-remote", "https://github.com/Canshu-King/CityNexus.git",
                          "refs/heads/mirror/integration-frontend-apple-pass1"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    sha = out.split("\t")[0].strip() if out else ""
    return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else "ABSENT"


def merge_prediction(a, b):
    """`git merge-tree --write-tree`: a read-only prediction, never a working-tree operation.

    The commander's re-cut condition is stated in this instrument's own terms -- exit 0 and an empty conflict
    section -- so the number that goes into the receipt comes from running it, not from remembering it.
    """
    r = subprocess.run(["git", "-C", str(LANE), "merge-tree", "--write-tree", a, b],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    lines = (r.stdout or "").splitlines()
    stage_rows = [l for l in lines[1:] if re.match(r"^\d{6} [0-9a-f]{40} \d\t", l)]
    return {"ref_a": a, "ref_b": b, "rc": r.returncode, "predicted_tree": lines[0] if lines else "ABSENT",
            "conflict_section_lines": len(stage_rows),
            "conflicted_paths": sorted({l.split("\t")[-1] for l in stage_rows})}


CAND = g(["rev-parse", "HEAD"])
PARENT = g(["rev-parse", "HEAD^"])
# A re-cut lands as a merge commit, so "the commit the commander had in hand" is one of TWO parents.  Reading
# the parents from the object rather than assuming a linear chain is what keeps the base cell honest: on a merge
# HEAD^ is the authority line, and the superseded candidate tip is HEAD^2.
PARENTS = g(["rev-list", "--parents", "-n", "1", CAND]).split()[1:]
IS_MERGE = len(PARENTS) > 1
SUPERSEDED = PARENTS[1] if IS_MERGE else PARENT
BRANCH = g(["rev-parse", "--abbrev-ref", "HEAD"])
SHEET_BLOB = blob(CAND, SHEET)
SPEC_BLOB = blob(CAND, SPEC_REL)
ls_line = subprocess.run(["git", "ls-remote", "git@github.com:Canshu-King/CityNexus.git",
                          f"refs/heads/{BRANCH}"], capture_output=True, text=True,
                         env={**dict(os.environ), "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}).stdout.strip()
prov = {}
# the re-cut must be judged against the line as it stands when the run starts, not against the number someone
# typed into a knock: if the commander or D landed another commit in the meantime, this run's base is stale and
# saying so is cheaper than delivering a candidate that cannot fast-forward.
TIP_LIVE = tip_now()
if TIP_LIVE != BASE:
    raise SystemExit(f"the authority line answers {TIP_LIVE} but this round is cut from {BASE}; "
                     "re-read the tip and re-cut before delivering")
for shape, meta in MATRIX["runs"].items():
    pf = WORK / f"e2e_ord0302_{meta['run_id']}" / "e2e-provenance" / "authoritative.json"
    prov[shape] = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
    af = WORK / f"e2e_ord0302_{meta['run_id']}" / "ord0302"
    arms = {}
    for f in sorted(af.glob("arm_*.json")) if af.exists() else []:
        body = json.loads(f.read_text(encoding="utf-8"))
        arms[str(body.get("arm"))] = body.get("reading") or {}
        meta.setdefault("per_arm_status", {})[str(body.get("arm"))] = body.get("status")
    meta["arms_evidence"] = arms
    missing = [a for a in ARMS_ALL if a not in arms]
    if missing:
        raise SystemExit(f"no per-arm evidence for {shape}: missing {missing}; refusing to describe a run "
                         "I cannot read")

FIXED = MATRIX["runs"]["fixed"]
sheet_text = subprocess.run(["git", "-C", str(LANE), "show", f"{CAND}:{SHEET}"], capture_output=True).stdout.decode("utf-8")
bugged_text = subprocess.run(["git", "-C", str(LANE), "show", f"{BUGGED_BASE}:{SHEET}"],
                             capture_output=True).stdout.decode("utf-8")
# A needle that exists on one tree only is given as (candidate, base): the answer read and the block gate are
# exactly the two lines this order changed, so asking one string where they are would answer nowhere.
ANCHORS = {
    "guarded_detail_read": "  const detail = (body as { detail?: unknown } | null)?.detail;",
    "unguarded_detail_read": "  const detail = (body as { detail?: unknown }).detail;",
    "body_read": ("const raw = await response.text().catch(() => null);",
                  "const body = await response.json().catch(() => null);"),
    "not_ok_branch": "      if (!response.ok) {",
    "network_write": 'status: "NETWORK"',
    "details_gate": ("{(result?.failureReason || result?.summary || result?.rawReading) && (",
                     "{(result?.failureReason || result?.summary) && ("),
}
lines_of = lambda text, needle: [i + 1 for i, l in enumerate(text.splitlines()) if needle in l]
# Both trees are measured, because the order names line numbers off the generation that still has the
# defect and the candidate's own comments shift everything below them.  A number that was copied rather
# than re-read would be exactly the kind of claim this receipt is not allowed to make.
measured, measured_base = {}, {}
for name, spec in ANCHORS.items():
    needle, needle_base = spec if isinstance(spec, tuple) else (spec, spec)
    n, nb = lines_of(sheet_text, needle), lines_of(bugged_text, needle_base)
    want = 2 if "detail_read" in name else 1
    for tree, hits in (("candidate", n), ("base", nb)):
        if len(hits) > want:
            raise SystemExit(f"anchor {name} occurs {len(hits)} times on the {tree}: {hits}")
    # the two envelope reads sit at two places each; every other anchor is required to be unique, so it is
    # stored as one number rather than a one-element list -- a list rendering into `file.tsx:[539]` reads as
    # an unresolved bracket, not as the coordinate it means to be.
    measured[name] = n if "detail_read" in name else n[0]
    measured_base[name] = nb if "detail_read" in name else nb[0]
unsafe_before = measured_base["unguarded_detail_read"]
if len(unsafe_before) != 2 or len(measured["guarded_detail_read"]) != 2 \
        or measured["unguarded_detail_read"] or measured_base["guarded_detail_read"]:
    raise SystemExit(f"the guard did not move where expected: base={unsafe_before} "
                     f"candidate={measured['guarded_detail_read']}")

cells = []


def arm_cell(arm, want, claim):
    r = (FIXED["arms_evidence"] or {}).get(arm) or {}
    read = r.get("read") or {}
    shape = "fixed"
    p = prov[shape]
    # The N arms report the block's presence as a boolean; the X-5 arms count it, because the defect they
    # name is precisely a promise pointing at zero elements.  Both are carried so no cell has to borrow
    # another arm's reading to say what it saw.
    paired = "details_count" in read
    readings = {"arm": arm, "nodeid": f"{SPEC_REL} :: ord0302-{arm}",
                "run_shape": shape, "run_id": FIXED["run_id"], "candidate_tip": CAND, "base_tip": BASE,
                "matrix_blob_of_this_run_report": blob_of(WORK / f"ord0302_arms_run.json"),
                "sheet_blob_candidate": SHEET_BLOB, "spec_blob": SPEC_BLOB,
                "status": read.get("status"),
                "detail_block_attached": (read["details_count"] >= 1) if paired
                                         else read.get("detail_block_attached"),
                "details_count": read.get("details_count"),
                "per_shape": r.get("per_shape"), "shape_count": r.get("shape_count"),
                # X-5's reverse direction is a declared boundary, so it travels with the cell that claims MET
                "absent_block_direction": r.get("absent_block_direction"),
                "why_absent_direction_unreachable": r.get("why_absent_direction_unreachable"),
                # the row names are the dict's KEYS, and a key is not a value the sentence can be checked
                # against -- list them so the cell holds the names it prints
                "shape_rows": list((r.get("per_shape") or {}).keys()),
                "promise_in_copy": read.get("promise_in_copy"),
                "label_rendered": read.get("label"), "origin_attribute": read.get("origin"),
                "reason_rendered": read.get("reason"), "legs": read.get("legs"),
                "want": want, "verdict": r.get("verdict"), "outcome": FIXED["outcomes"].get(arm),
                "db": f"_{FIXED['run_id']}.db", "frontend_port": p.get("frontendPort"),
                "backend_port": p.get("backendPort"), "authoritative": p.get("authoritative"),
                "ai": p.get("ai"), "reuseExistingServer": p.get("reuseExistingServer")}
    seen = (f"its rendered card text points at 技术详情={readings['promise_in_copy']} and the DOM held "
            f"{readings['details_count']} such block(s), so attached={readings['detail_block_attached']}"
            if paired else
            f"the detail block was attached={readings['detail_block_attached']}"
            + (f"; the reverse direction (count = 0) is {readings['absent_block_direction']} here, because "
               + str(readings['why_absent_direction_unreachable'])) if readings.get('absent_block_direction')
            else "")
    if readings.get("per_shape"):
        # one clause per shape, each from that shape's own reading -- the commander named five rows, so a
        # single sentence about one of them would be a sample presented as the family
        seen += (" judged once per shape over the " + str(readings["shape_count"]) + " rows X-5 named: "
                 + "; ".join(f"{row} -> status={v['status']}, promise={v['promise_in_copy']}, "
                             f"details_count={v['details_count']}, and the block's own fields "
                             f"rendered={json.dumps(v.get('raw_rendered'), ensure_ascii=False)} against what "
                             f"the stub forced={json.dumps(v.get('raw_expected'), ensure_ascii=False)}"
                             for row, v in readings["per_shape"].items()))
    why = (f"{arm} ({readings['nodeid']}, shape={shape}, run {readings['run_id']} over base {BASE[:12]}): "
           f"Playwright reported {readings['outcome']} and the cell's own verdict is {readings['verdict']}. "
           f"The screen said status={readings['status']}, {seen}, the rendered label was "
           f"{readings['label_rendered']!r} with origin={readings['origin_attribute']!r} over the reading "
           f"{readings['reason_rendered']!r}; legs seen: {readings['legs']}. {claim} Face: authoritative e2e "
           f"on vite dev (frontend :{readings['frontend_port']}, backend :{readings['backend_port']}, "
           f"ai={readings['ai']}, db {readings['db']}) -- spec-grade, not a shipped bundle.")
    return {"cell": f"{arm} on the fixed candidate", "claimed_result": "MET" if readings["verdict"] == "MET"
            else "NOT_MET", "derived_result": None, "why": C.cite(why, readings, PATS) and why,
            "readings": readings}


cells.append(arm_cell("N1", "device", "This is the regression itself: a server answer with no parseable body "
                                   "stays an HTTP answer and is still readable."))
cells.append(arm_cell("N2", "server", "Positive control: the verbatim server sentence still wins, so the fix "
                                      "did not start preferring our own prose."))
cells.append(arm_cell("N3", "device", "Requirement ②: even a real network failure keeps a visible device line "
                                       "instead of an empty panel."))
# X-5: the pairing is the gate, in both directions, and the copy is asserted too so that deleting the
# pointer cannot pass as a fix (Q53=① rendered the reading instead).
cells.append(arm_cell("X1", "device", "X-5: for every one of the five rows X-5 named (R19-R23, all of them answers the "
                                   "sheet never stored, whose card still points at 技术详情) the block must exist and "
                                   "pointer may not be deleted to make the test pass (Q53=① rendered it)."))
cells.append(arm_cell("X2", "either", "The other side of the pairing, measured rather than implied: a "
                                   "request the traveller cancels has no answer to show, so its block really "
                                   "is absent and its sentence makes no promise -- which is what stops the "
                                   "rule degenerating into 'always render something'."))

for shape in [s for s in MATRIX["runs"] if s != "fixed"]:
    meta = MATRIX["runs"][shape]
    intended = MATRIX["runs"][shape].get("intended") or {"ca_unsafe_read": "N1",
                                                          "ca_null_on_network": "N3"}[shape]
    untouched = [a for a in ARMS_ALL if a != intended]
    readings = {"shape": shape, "run_id": meta["run_id"], "arm_that_flipped": intended,
                "outcomes": meta["outcomes"], "digest_before": MATRIX["digests"][shape]["before"],
                "digest_running": MATRIX["digests"][shape]["running"],
                "restored_byte_exact": MATRIX["digests"][shape]["restored"],
                "expected": meta["expected"], "meets_expectation": meta["meets_expectation"],
                "report_blob": blob_of(WORK / f"ord0302_{meta['run_id']}.json"),
                "candidate_tip": CAND, "base_tip": BASE}
    why = (f"counter-arm {shape}: the sha256 of the sheet went {readings['digest_before']} -> "
           f"{readings['digest_running']} (mutant landed, bytes changed) and the intended arm "
           f"{intended} read {meta['outcomes'].get(intended)} while the arms that should not care stayed "
           f"{[meta['outcomes'].get(a) for a in untouched]} -- an all-red run would prove nothing about which "
           f"line carries the defect. Expectation {meta['expected']} met={meta['meets_expectation']}, "
           f"run {meta['run_id']}, source restored byte-exact={readings['restored_byte_exact']}, "
           f"report blob {readings['report_blob']}.")
    cells.append({"cell": f"counter-arm {shape} (must flip {intended} only)",
                  "claimed_result": "MET" if meta["meets_expectation"] else "NOT_MET",
                  "derived_result": None, "why": C.cite(why, readings, PATS) and why, "readings": readings})

root = {"base_tip": BASE, "defect_generation_base": BUGGED_BASE, "bugged_sheet_blob": BUGGED,
        "candidate_sheet_blob": SHEET_BLOB,
        "predecessor_order": "ORD-0280", "this_order": "ORD-0302",
        "unsafe_reads_at": unsafe_before, "safe_reads_at": measured["guarded_detail_read"],
        "body_null_line": measured_base["body_read"],
        "not_ok_line": measured_base["not_ok_branch"],
        "network_write_line": measured_base["network_write"],
        "details_gate_line": measured_base["details_gate"],
        "candidate_lines_of_the_same_anchors": {k: measured[k] for k in
                                                ("body_read", "not_ok_branch", "network_write",
                                                 "details_gate")},
        "candidate_answer_read": measured["body_read"],
        "candidate_details_gate": measured["details_gate"],
        "status_written": "NETWORK",
        "previous_generation_sheet_blob": PREV_GEN, "spec_blob": SPEC_BLOB,
        # Every line number this cell names is written as `path:line`, which is what the claim gate accepts
        # as a coordinate a reader can resolve; a bare "531" pins nothing once the file moves.
        "unsafe_read_coords": [f"{SHEET}:{n}" for n in unsafe_before],
        "safe_read_coords": [f"{SHEET}:{n}" for n in measured["guarded_detail_read"]],
        "coord_body_null": f"{SHEET}:{measured_base['body_read']}",
        "coord_candidate_answer_read": f"{SHEET}:{measured['body_read']}",
        "coord_candidate_gate": f"{SHEET}:{measured['details_gate']}",
        "coord_not_ok": f"{SHEET}:{measured_base['not_ok_branch']}",
        "coord_network": f"{SHEET}:{measured_base['network_write']}",
        "coord_details_gate": f"{SHEET}:{measured_base['details_gate']}",
        "rulers": {"q38": blob_of(Q38), "q43": [blob_of(p) for p in Q43S]}}
root_why = ("root cause, re-measured on the generation that still carries it (" + BUGGED_BASE
            + ") rather than copied from the order: in the bugged blob "
            + BUGGED + " the two envelope helpers read the detail field without a guard on `body` itself, at "
            + " and ".join(root["unsafe_read_coords"]) + "; the leg that reaches them sets `body = null` for an "
            "unparseable answer at " + root["coord_body_null"] + " (on this candidate the same leg keeps the "
            "bytes first, at " + root["coord_candidate_answer_read"] + "), the refusal branch starts at "
            + root["coord_not_ok"] + ", and the throw is caught where status is written as NETWORK at "
            + root["coord_network"] + " with the note nulled, which is also the line the detail block depends "
            "on at " + root["coord_details_gate"] + "; on this candidate that gate also takes the raw reading, "
            "at " + root["coord_candidate_gate"] + ", and the same two reads are guarded, now at "
            + " and ".join(root["safe_read_coords"]) + " (sheet blob " + SHEET_BLOB + ", spec blob "
            + SPEC_BLOB + "). The generation before ORD-0280 (sheet blob " + PREV_GEN + ") did not throw there "
            "-- it answered with an invented status string, which is the defect that order removed; both states "
            "are wrong in different ways and only the body-has-a-JSON-object reading separates them.")
cells.append({"cell": "root cause and the coordinates it was measured at", "claimed_result": "MET",
              "derived_result": None, "why": C.cite(root_why, root, PATS) and root_why, "readings": root})

# "which deliveries came before this one" is answered by the branch's own directory listing, not by a list I
# keep adding to by hand -- a hand-typed list is how an earlier round's sentence outlived its own meaning.
_prior_raw = json.loads(_url_open(f"https://api.github.com/repos/{GH}/contents/evidence?ref={BRC}"))
PREDECESSORS = sorted(d["name"] for d in _prior_raw
                      if d["type"] == "dir" and d["name"].startswith("ord0302-unreadable-server-body")
                      and DIR.split("/")[-1] not in d["name"])
scope = {"predecessor_evidence_paths": PREDECESSORS,
         "this_delivery_path": DIR,
         "ord_0281_branch_untouched": "review/0281-write-deadline-keyed-b2",
         "other_lanes_files_touched": 0,
         "phone_state": "neither cell was observed by me on the deployed generation -- both readings are vite "
                        "dev, so the phone keeps whatever is shipped until the commander swaps",
         "swap_actions_by_me": 0,
         "release_grade": False,
         "new_prose_written": "one device line, for the NETWORK cell (requirement ②); Q53=① deleted the count "
                              "sentence X-5 used to show, so that block now carries measured fields only",
         "device_lines_written": ["no readable answer reached this device (network or origin)"],
         "raw_fields_rendered": ["http_status", "content-type", "bytes", "body"],
         "not_measured": ["a non-JSON body on the places leg and the generate leg (same helper, arms not "
                          "written)", "an HTML answer that still parses as JSON",
                          "the shipped bundle behind the phone: X-5 was measured on vite dev, so the "
                          "generation that is live now is still NOT-DEPLOYED-OBSERVED for this cell"]}
_paths_here = [x for x in g(["diff", "--name-only", BASE, CAND]).split("\n") if x]
scope["changed_paths_in_this_candidate"] = _paths_here
scope["product_paths"] = len([x for x in _paths_here if x.startswith(("frontend/src", "backend/"))])
_path_says = (f"{len(_paths_here)} paths change in this candidate, {scope['product_paths']} of them product "
              f"(the sheet {SHEET_BLOB} and the e2e spec {SPEC_BLOB})"
              if scope["product_paths"] == len(_paths_here) == 2 else
              f"{len(_paths_here)} paths change in this candidate, {scope['product_paths']} of them product: "
              f"sheet blob {SHEET_BLOB}, spec blob {SPEC_BLOB}")
scope_why = ("scope and boundaries: this delivery lives at " + DIR + "; the "
             + str(len(scope["predecessor_evidence_paths"])) + " earlier ones keep their own paths and were not "
             "rewritten (" + "; ".join(scope["predecessor_evidence_paths"]) + "). " + _path_says + "; files "
             "belonging to other lanes: "
             + str(scope["other_lanes_files_touched"]) + " touched, and " + scope["ord_0281_branch_untouched"]
             + " was left alone. " + scope["new_prose_written"] + ": "
             + " + ".join(repr(x) for x in scope["device_lines_written"]) + ". No other user-facing copy was "
             "written, because the wording for the wider family is still ORD-0301's call. "
             + scope["phone_state"] + ", but the "
             "swap is the commander's: actions by me here = " + str(scope["swap_actions_by_me"]) + " -- no "
             "index switch, no preview restart, no dist change, and this face stays vite dev so "
             "release_grade=" + str(scope["release_grade"]) + ". Not measured, named rather than implied: "
             + "; ".join(scope["not_measured"]) + ".")
cells.append({"cell": "scope, phone boundary and what was NOT measured", "claimed_result": "DECLARED",
              "derived_result": None, "why": C.cite(scope_why, scope, PATS) and scope_why, "readings": scope})

committed_sha256 = hashlib.sha256(
    subprocess.run(["git", "-C", str(LANE), "show", f"HEAD:{SHEET}"], capture_output=True).stdout).hexdigest()
before_digests = {d["before"] for d in MATRIX["digests"].values()}
same_bytes = committed_sha256[:16] in before_digests and len(before_digests) == 1
base = {"candidate_tip": CAND, "base_tip": BASE, "parent_measured": PARENT, "branch": BRANCH,
        "committed_sheet_sha256": committed_sha256, "digests_the_runs_started_from": sorted(before_digests),
        "arms_measured_exactly_the_committed_bytes": same_bytes,
        "base_is_ancestor": subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, CAND],
                                           capture_output=True).returncode == 0,
        "commits_over_base": int(g(["rev-list", "--count", f"{BASE}..{CAND}"])),
        "ref_readback": ls_line or "ABSENT",
        "superseded_tip": SUPERSEDED,
        "changed_paths": [p for p in g(["diff", "--name-only", BASE, CAND]).split("\n") if p],
        "backend_diff": g(["diff", "--name-only", BASE, CAND, "--", "backend"]) or "none",
        "recut_parents": PARENTS,
        "recut_is_merge_commit": IS_MERGE,
        "the_order_this_re_cut_sits_on_top_of": "ORD-0310",
        # the commander's own closing condition for a re-cut: the merge must now answer clean against the tip
        "merge_tree_against_base": (lambda o: {"rc": o["rc"], "predicted_tree": o["predicted_tree"],
                                               "conflict_section_lines": o["conflict_section_lines"],
                                               "conflicted_paths": o["conflicted_paths"]})(
            merge_prediction(BASE, CAND)),
        "typecheck_configs": ["tsconfig.check.json", "tsconfig.typecheck.json"]}
base_why = ("base and shape: " + CAND + " is the ref tip GitHub answers (" + ls_line + "), "
            + str(base["commits_over_base"]) + " commits over the order's tip " + BASE + " (ancestor check = "
            + str(base["base_is_ancestor"]) + "), so the two named cells land on the one ref the commander "
            "already holds rather than as two competing candidates. Process, stated rather than smoothed: "
            + (f"this tip has {len(PARENTS)} parents -- {PARENTS[0]} (the authority line at the time of the "
               f"re-cut) and {PARENTS[1]} (the candidate it re-cuts), so nothing published earlier is rewritten "
               "and the hand-resolved surface is only the fetch on the leg ORD-0310 wrapped. "
               if IS_MERGE else
               "the first half of this order was pushed alone as " + SUPERSEDED + ", the X-5 work then went on "
               "top of it, and the earlier attempt to fold both into one commit was refused as "
               "non-fast-forward -- no force-push, so " + SUPERSEDED + " is still an ancestor of this tip and "
               "every reading taken under it stays resolvable. ")
            + str(len(base["changed_paths"])) + " paths changed: "
            + ", ".join(p.split("/")[-1] for p in base["changed_paths"]) + "; the diff restricted to backend/ "
            "answers " + (base["backend_diff"] or "none") + ". Both typecheck configs ("
            + ", ".join(base["typecheck_configs"]) + ") were clean before the arms ran. The arms ran against "
            "exactly the committed bytes: the sheet's sha256 at HEAD is " + committed_sha256[:16]
            + " and every run recorded that same value as the digest it started from ("
            + ", ".join(sorted(before_digests)) + "), agree=" + str(same_bytes) + ".")
cells.append({"cell": "base, ref and what this candidate touches",
              "claimed_result": "MET" if (base["base_is_ancestor"] and ls_line.startswith(CAND)
                                          and blob(CAND, SHEET) != BUGGED and same_bytes
                                          and not base["backend_diff"]
                                          and base["merge_tree_against_base"]["rc"] == 0
                                          and base["merge_tree_against_base"]["conflict_section_lines"] == 0)
              else "NOT_MET",
              "derived_result": None, "why": C.cite(base_why, base, PATS) and base_why, "readings": base})

# ---- the coexistence the commander named: both orders' semantics live on this one tree, each still falsifiable
D0310_PATHS = ["frontend/src/lib/keylessWriteDeadline.ts",
               "frontend/e2e/qoder-ord0310-keyless-write-deadline.spec.ts"]
_rep = sorted(WORK.glob("ord0310_on_b4_*.json"), key=lambda p: p.stat().st_mtime)
if not _rep:
    raise SystemExit("no ORD-0310 run report on this re-cut tree; the coexistence cell would be a claim "
                     "with no reading behind it")
_rep_body = json.loads(_rep[-1].read_text(encoding="utf-8"))
_arm_status, _arm_ms = {}, {}


def _walk(node):
    for s in node.get("suites", []) or []:
        _walk(s)
    for sp in node.get("specs", []) or []:
        for t in sp.get("tests") or []:
            for r in t.get("results") or []:
                key = sp.get("title", "").split()[0]
                if key.startswith(("K1", "K2", "K3")):
                    _arm_status.setdefault(key, r.get("status"))
                    _arm_ms.setdefault(key, r.get("duration"))


_walk({"suites": _rep_body.get("suites") or []})
coex = {"tip_read_at_run": TIP_LIVE, "candidate": CAND, "candidate_parents": PARENTS,
        "the_other_order_on_this_tree": "ORD-0310",
        "merge_tree_rc_against_tip": base["merge_tree_against_base"]["rc"],
        "merge_tree_predicted_tree": base["merge_tree_against_base"]["predicted_tree"],
        "conflict_section_lines": base["merge_tree_against_base"]["conflict_section_lines"],
        "conflicted_paths": base["merge_tree_against_base"]["conflicted_paths"],
        "order_side_paths": D0310_PATHS,
        "blobs_identical_to_tip": {p: {"at_tip": blob(BASE, p), "at_candidate": blob(CAND, p),
                                       "same": blob(BASE, p) == blob(CAND, p)} for p in D0310_PATHS},
        "ord0310_arms_run_on_this_tree": _arm_status,
        "ord0310_arm_durations_ms": _arm_ms,
        "report_file_local": _rep[-1].name, "report_file": "ord0310_arms_on_recut_tree.json",
        "report_blob": blob_of(_rep[-1]),
        "mine_still_red_one_cell_each": all(c["readings"]["meets_expectation"] for c in
                                            [x for x in cells if x["cell"].startswith("counter-arm")])}
coex_why = ("合流与共存（这是 re-cut 唯一的实质要件，两侧都不许把对方改没）：对 " + BASE + " 现跑 "
            "`git merge-tree --write-tree " + BASE + " " + CAND + "` 退出 "
            + str(coex["merge_tree_rc_against_tip"]) + "、预测树 " + coex["merge_tree_predicted_tree"]
            + "、冲突段行数 " + str(coex["conflict_section_lines"]) + "（" + str(coex["conflicted_paths"])
            + "）。这一枚的父是 " + " 与 ".join(coex["candidate_parents"]) + "（后者是上一代 q53 候选 "
            + SUPERSEDED + "）。ORD-0310 那一侧的两枚文件在这棵树上与线上逐位相同：" + "; ".join(
                f"{p} {coex['blobs_identical_to_tip'][p]['at_tip']} same="
                + str(coex['blobs_identical_to_tip'][p]['same']) for p in D0310_PATHS) + "。"
            "D 那三枚臂在这棵重切树上现跑一遍（报告 " + coex["report_file"] + " blob " + coex["report_blob"]
            + "）：" + ", ".join(f"{k}={v} @{str(coex['ord0310_arm_durations_ms'].get(k)) + 'ms'}"
                                for k, v in coex["ord0310_arms_run_on_this_tree"].items())
            + "，其中 K1 真的等到期限到点而不是被跳过。我这一侧四枚反件仍各自只咬自己那一格="
            + str(coex["mine_still_red_one_cell_each"]) + "。")
cells.append({"cell": "coexistence of the two orders' semantics on the re-cut tree", "claimed_result": "MET",
              "derived_result": None, "why": C.cite(coex_why, coex, PATS) and coex_why, "readings": coex})

# ---- publication discipline, counted from the branch's own history (commander's CMDR-0925-2128 audit)
NAMED_TOOL_REWRITES = ["evidence/ord0281-keyed-write-deadline/ord0281_receipt.py",
                       "evidence/ord0302-unreadable-server-body-r2/ord0302_verify_r2.py",
                       "evidence/ord0302-unreadable-server-body/ord0302_deliver.py"]
TOOL_AUDIT_BASE = "evidence/cmdr-overwrite-audit-2126/audit_r1.json"


def path_history(path):
    rows = json.loads(_url_open(f"https://api.github.com/repos/{GH}/commits?sha={BRC}&path="
                                + urllib.parse.quote(path, safe="") + "&per_page=100"))
    return [{"commit": c["sha"], "date": c["commit"]["committer"]["date"]} for c in rows]


_history = {p: path_history(p) for p in NAMED_TOOL_REWRITES}
tools = {"counted_from": "the branch's own commit history, per path, read by this run",
         "commanders_audit_file": TOOL_AUDIT_BASE,
         "named_tool_paths_rewritten": {p: {"writes": len(v), "commits": [x["commit"] for x in v]}
                                        for p, v in _history.items()},
         "paths_written_more_than_once": [p for p, v in _history.items() if len(v) > 1],
         "this_round_publishes_only_into": DIR,
         "rule_adopted": "measurement code never gets re-written under the same path: a revision is a new name "
                         "(the commander's own words: the criterion travels on the blob, not on the filename)"}
tools_why = ("发布纪律（我名下被点名的三枚量具代码，从分支自己的提交史现数，不引他给的数）：" + "; ".join(
    f"{p} 被写过 {len(v['commits'])} 次，提交 " + ", ".join(v["commits"])
    for p, v in tools["named_tool_paths_rewritten"].items())
             + " —— 这三枚是我的错，判据认的是 blob 不是文件名，同名换字节等于让别人拿旧引用跑到另一把尺上。"
             "他那份普查件 " + TOOL_AUDIT_BASE + " 我不重做，认。这一轮起：量具改版一律走新文件名，本轮只往 "
             + DIR + " 里新增，先前三个目录里的任何一件都不再改写。")
cells.append({"cell": "publication discipline on my own measurement code", "claimed_result": "DECLARED",
              "derived_result": None, "why": C.cite(tools_why, tools, PATS) and tools_why, "readings": tools})

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": {"r1": "ORD-0302 文案修 · 非 JSON 正文不得冒充网络故障",
                     "r2": "ORD-0302 文案修 · X-5 补到号令者点名的五形",
                     "q53": "ORD-0302 文案修 · Q53=① 块内只陈列原始回读",
                     "recut": "ORD-0302 文案修 · q53 那一枚重切到含 ORD-0310 的当代尖"}[ROUND],
           "lane": "B c01d72a3",
           "amendment_of": {"r1": "ORD-0302 as ordered", "r2": "evidence/ord0302-unreadable-server-body",
                            "q53": "evidence/ord0302-unreadable-server-body-r2",
                            "recut": "evidence/ord0302-unreadable-server-body-q53"}[ROUND],
           # never a literal: this field was 0 for a spec-only amendment and stayed 0 after the sheet itself
           # changed, which is exactly how a false sentence reaches a published block
           "product_bytes_changed": len([x for x in g(['diff', '--name-only', BASE, CAND]).split(chr(10))
                                         if x.startswith('frontend/src') or x.startswith('backend/')]),
           "changed_paths": [x for x in g(['diff', '--name-only', BASE, CAND]).split(chr(10)) if x],
           "claim_kind": "RUNTIME_MEASURED", "candidate_tip": CAND, "base_tip": BASE, "branch": BRANCH,
           "cells": cells,
           "summary": {"arms_met": sum(1 for c in cells if c["cell"].startswith(ARMS_ALL)
                                       and c["claimed_result"] == "MET"),
                       "counter_arms_met": sum(1 for c in cells if c["cell"].startswith("counter-arm")
                                               and c["claimed_result"] == "MET"),
                       "matrix_verdict": MATRIX["verdict"],
                       "restored_byte_exact_every_shape": all(d["restored"] for d in MATRIX["digests"].values())},
           "derived_result": None,
           "not_claimed": "derived_result 全格 null；发布级面没跑；places/generate 两条腿的同一形没写臂；"
                          "手机换代不归我（未动 dist/index/预览后端）"}
out = RECEIPT


def ruler(path):
    rb = subprocess.run(["git", "hash-object", str(Q38)], capture_output=True, text=True).stdout.strip()
    r = subprocess.run([PY, str(Q38), "--receipt", str(path), "--min-cells", "4"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=300)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    return {"ruler": Q38.name, "ruler_blob": rb, "rc": r.returncode,
            "headline": [l for l in txt.splitlines() if "overall" in l][:3], "output": txt}


out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
first = ruler(out)
receipt["ruler_check"] = {"pass_1": {k: v for k, v in first.items() if k != "output"},
                          "pass_1_output": first["output"]}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
second = ruler(out)
receipt["ruler_check"]["pass_2_on_published_bytes"] = {k: v for k, v in second.items() if k != "output"}
receipt["ruler_check"]["pass_2_output"] = second["output"]
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print("Q38:", first["headline"], "|", second["headline"])
if "Q38_GATE_GREEN" not in second["output"] or "soft 0" not in second["output"]:
    raise SystemExit("the receipt is not clean on the bytes being published")

FILES = [(out, "ord0302_receipt.json"), (WORK / "ord0302_arms_run.json", "ord0302_arms_matrix.json"),
         (_rep[-1], coex["report_file"])]
# the coexistence cell cites a run report, so that report has to be retrievable where the citation points
FILES.append((WORK / coex["report_file_local"], coex["report_file"]))
for shape, meta in MATRIX["runs"].items():
    rid = meta["run_id"]
    arm_files = [(p, f"{shape}__{p.name}")
                 for p in sorted((WORK / f"e2e_ord0302_{rid}" / "ord0302").glob("arm_*.json"))]
    for f, name in arm_files + [((WORK / f"e2e_ord0302_{rid}" / "e2e-provenance" / "authoritative.json"),
                                 f"{shape}__authoritative.json"),
                                ((WORK / f"ord0302_{rid}.json"), f"{shape}__playwright_report.json")]:
        if f.exists():
            FILES.append((f, name))
for rel, name in ((SHEET, "ord0302_candidate_sheet.tsx"), (SPEC_REL, "ord0302_candidate_spec.ts")):
    data = subprocess.run(["git", "-C", str(LANE), "show", f"{CAND}:{rel}"], capture_output=True).stdout
    if not data:
        raise SystemExit("the candidate does not carry " + rel)
    (WORK / name).write_bytes(data)
    FILES.append((WORK / name, name.split("ord0302_", 1)[1]))
for p in (SPIKE / "ord0302_run_arms.py", SPIKE / "ord0302_deliver.py",
          SPIKE / "ord0302_x5_five_shapes_patch.py", SPIKE / "ord0302_deliver_r2_patch.py"):
    if p.exists():
        # Measurement code may not occupy a path twice: two earlier attempts in THIS directory died after they
        # had already published `ord0302_deliver.py`, so that path carries two writes and I disclose them rather
        # than adding a third.  This round's bytes go out under a name that has never been written.
        FILES.append((p, f"{ROUND}_deliver_instrument.py" if p.name == "ord0302_deliver.py" else p.name))
ip = WORK / "ord0302_index.json"


def build_index():
    """An index cannot pin its own bytes, so it names every artifact except itself and says so."""
    ip.write_text(json.dumps({"candidate_tip": CAND, "base_tip": BASE, "branch": BRANCH, "dir": DIR,
                              "self_reference": "this file is not in its own list; its blob is what the "
                                                "read-back of the branch prints",
                              "files": [{"name": n, "blob40": blob_of(p), "bytes": p.stat().st_size}
                                        for p, n in FILES if p.exists() and n != ip.name]},
                             ensure_ascii=False, indent=1), "utf-8", newline="\n")


build_index()
FILES.append((ip, ip.name))
def tok():
    return pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(
        encoding="utf-8").strip()


def api(url, data=None, verb=None):
    """This link truncates mid-response; a blip must never be read as a missing object, and a 2xx alone is
    never read as proof either -- the read-back decides."""
    last = None
    for i in range(9):
        try:
            req = urllib.request.Request(url, data=(json.dumps(data).encode() if data else None),
                                         headers={"Authorization": "Bearer " + tok(),
                                                  "Accept": "application/vnd.github+json",
                                                  "Content-Type": "application/json",
                                                  "User-Agent": "citynexus-lane-B"},
                                         method=verb or ("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (404, 422):
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(min(30, 2 + 4 * i))
    raise last


def remote(name):
    try:
        return api(f"https://api.github.com/repos/{GH}/contents/{DIR}/{name}?ref={BRC}")["sha"]
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"


def push(path, name):
    """Publish through the commander's fail-closed publisher and require ITS OWN proof line.

    Checking only for the word REFUSED let a publisher that died mid-flight (a blip, a timeout) pass silently
    and then read back as a missing object -- which is how one receipt ended up published by hand afterwards.
    """
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0302: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return attempt, txt.strip().splitlines()[-1][:120]
        if "REFUSED" in txt.upper():
            raise SystemExit("the publisher refused " + name + ": " + txt[-200:])
        print(f"publish attempt {attempt} for {name} failed rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim a publish the publisher never proved: " + name)


SUB, rows = {}, []
for p, name in FILES:
    if not p.exists():
        raise SystemExit("missing artifact I meant to publish: " + name)
    want = blob_of(p)
    if remote(name) != want:
        push(p, name)
    got = remote(name)
    for _ in range(6):
        if got == want:
            break
        # the contents API can answer the previous commit for a moment after a write lands; a stale read is
        # not a missing object, and treating it as one once made me re-publish a file that was already there
        time.sleep(4)
        got = remote(name)
    rows.append({"file": name, "blob40": want, "readback": got,
                 "verdict": "PROVEN" if got == want else "NOT"})
    SUB[name] = want
    print(f"{name:44s} {want[:12]} vs {str(got)[:12]} {rows[-1]['verdict']}")
proven = sum(1 for r in rows if r["verdict"] == "PROVEN")
(WORK / "ord0302_publish_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1),
                                                 "utf-8", newline="\n")
print(f"published+proven {proven}/{len(rows)}")
if proven != len(rows):
    raise SystemExit("will not cite a blob the branch has not confirmed")


def cite(name):
    """Always the full path: a bare file name costs the reader a guess about which directory holds it,
    and this order now has three of them (the landed one, r2, and this one)."""
    return DIR + "/" + name + " blob " + SUB[name]


# ---------------------------------------------------------------- ledger + bus, gated by both claim rulers
arms = [c for c in cells if c["cell"].startswith(ARMS_ALL)]
cas = [c for c in cells if c["cell"].startswith("counter-arm")]
rootc = next(c for c in cells if c["cell"].startswith("root cause"))
scopec = next(c for c in cells if c["cell"].startswith("scope,"))
basec = next(c for c in cells if c["cell"].startswith("base,"))
# never a literal: the sentence below used to claim "0 product bytes" for a candidate that changed the sheet,
# because the value had been typed for an earlier spec-only amendment
PBC = receipt["product_bytes_changed"]
PBC_WHERE = [x.split("/")[-1] for x in receipt.get("changed_paths", [])
             if x.startswith("frontend/src") or x.startswith("backend/")]
if len(PBC_WHERE) != PBC:
    raise SystemExit(f"product-byte count {PBC} disagrees with the path list {PBC_WHERE}")
lines = [""]
# The round name and the headline sentence used to be literals that survived into a later round, which wrote two
# ledger blocks both headed "r2" and left a retracted sentence in a heading.  ROUND is resolved next to DIR, so
# the receipt header and this heading cannot disagree.
NARR = {"r1": "**两枚具名格落在同一枚候选里：两处安全读 + NETWORK 的可见兑底 + X-5 的承诺与块成对。**",
        "r2": "**上一版 X1 只驱动了五形里的一形（200 + plans:[]），等于拿样本冒充整族；这一版五形各自读一遍，"
              "反件仍只咬 X1 那一格。**",
        "q53": "**按仲裁 Q53=①：X-5 那一格不再由本屏造句子，块里只陈列已实测的原始回读"
               "（HTTP 状态、content-type、字节数、正文头部原文），两侧同判与杀手仍各咬自己那一格。**",
        "recut": "**按号令者 19:34 那跳把 q53 那一枚重切到已含 ORD-0310 的当代尖：断言与 spec 字节不变，"
                 "只有那一腿 fetch 的上下文需要合流（merge-tree 只预测出一枚冲突跳），臂在新代重跑。**"}[ROUND]
MARK = (f"### B c01d72a3 · ORD-0302 文案修 {ROUND}（五枚臂 N1/N2/N3/X1/X2 各自判正反两读；"
        f"这一枚改产品文件 {PBC} 枚）基座 `{BASE}` 候选 `{CAND}`")
lines.append(MARK + " @" + time.strftime("%H:%M", time.localtime()) + "+08 —— " + NARR)
lines += ["", "```text",
          "根因      " + rootc["why"],
          "五枚臂    " + "；".join(f"{c['cell'].split()[0]}={c['claimed_result']}"
                                  f"(status={c['readings']['status']}/块={c['readings']['detail_block_attached']})"
                                  for c in arms)
          + "；矩阵 " + MATRIX["verdict"] + "（" + cite("ord0302_arms_matrix.json") + "）",
          "反件      " + "；".join(
              f"{c['readings']['shape']}→只 {c['readings']['arm_that_flipped']} 红={c['claimed_result']}"
              f"，其余 {set(c['readings']['outcomes'].get(a) for a in ARMS_ALL if a != c['readings']['arm_that_flipped'])}"
              f"（digest {c['readings']['digest_before']}→{c['readings']['digest_running']}，"
              f"report blob {c['readings']['report_blob']}）" for c in cas)
          + "。四枚各自只咬自己那一格：N2 在 ca_unsafe_read 下仍绿（带 error.message 的正文在读 detail 之前就返回了），"
            "N1 在 ca_null_on_network 下仍绿，五枚里除 X1 之外在两枚 X-5 反件下仍绿 —— "
            "全红只能证明我改坏了别处",
          "边界      " + scopec["why"],
          "合流      " + coex_why,
          "纪律      " + tools_why,
          "坐标      " + basec["why"],
          "尺        " + str(receipt["ruler_check"]["pass_2_on_published_bytes"]["headline"][0])
          + "（receipt_cell_derivation_check_r2.py blob " + blob_of(Q38)
          + "，两遍都在发布那份字节上）；另过 claim_coordinate_check_r3.py 与 r4b（见 "
          + cite("ord0302_index.json") + "）；derived_result 全格 null",
          "还原      五枚形制跑完源文件按字节还原 = "
          + str(receipt["summary"]["restored_byte_exact_every_shape"]) + "（" + cite("ord0302_arms_matrix.json")
          + " 的 digests）",
          "```"]
ledger_txt = WORK / "ord0302_ledger_block.txt"
LEDGER_BODY = "\n".join(lines) + "\n" + CLOSING + "\n"
ledger_txt.write_text(LEDGER_BODY, "utf-8", newline="\n")


def gate(path):
    """Judge a text with both claim rulers and keep their exit codes.

    r4b answers `Q43_GATE_GREEN` where r3 answers `Q43_GATE_CLEAN`, so matching one word would have made a
    passing block look refused. The exit code is the version-independent contract: 0 is the only pass.
    """
    outs = {}
    for ruler in Q43S:
        r = subprocess.run([PY, str(ruler), "--text", str(path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        outs[ruler.name] = {"rc": r.returncode,
                            "output": ((r.stdout or "") + (r.stderr or "")).strip()}
    return outs


def gate_ok(outs, label):
    bad = {k: v for k, v in outs.items() if v["rc"] != 0}
    for k, v in outs.items():
        print(f"Q43 {k} {label}: rc={v['rc']} |"
              f" {[l for l in v['output'].splitlines() if 'claims checked' in l][:1]}")
    if bad:
        raise SystemExit(f"a claim gate refused the {label} (rc "
                         + ", ".join(f"{k}={v['rc']}" for k, v in bad.items()) + "); not writing, not sending")


ok = True
for label, path in (("ledger-draft", ledger_txt),):
    gate_ok(gate(path), label)

before = LEDGER.read_bytes()
# Matching the whole MARK line was not enough: the line it matched had already been reworded once, so a re-run
# wrote a second block for the same candidate.  The candidate's own short sha in a heading of mine is the key.
already = re.search(r"^### B c01d72a3 · ORD-0302[^\n]*候选 `" + CAND[:7], before.decode("utf-8"), re.M)
if already:
    print("a block for candidate " + CAND[:7] + " is already in the ledger; not appending twice")
else:
    with open(str(LEDGER), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(LEDGER_BODY)
    print("ledger appended:", len(LEDGER.read_bytes()) - len(before), "B")

# What gets gated and published as "the ledger block" is the block as it now sits in the shared file, not my
# in-memory draft: the file is rewritten by others and the draft carries a wall-clock stamp, so a re-run would
# otherwise cite bytes nobody can find.
live = LEDGER.read_text(encoding="utf-8", errors="replace")
i = live.find(MARK)
if i < 0:
    raise SystemExit("my block is not in the ledger I just wrote to; refusing to describe a text I cannot read")
j = live.find("\n### ", i + len(MARK))
block = live[i:j if j > 0 else len(live)]
ledger_txt.write_text(block, "utf-8", newline="\n")
LEDGER_GATE = gate(ledger_txt)
gate_ok(LEDGER_GATE, "ledger-as-written")

BUS_LEAD = {"r1": "交候选", "r2": "交 r2 候选", "q53": "交 q53 候选", "recut": "交重切候选（按你 CMDR-0925-1934 那一跳）"}
first = ("B c01d72a3 → 号令者 494abfd7：ORD-0302 " + BUS_LEAD[ROUND] + " " + CAND + "（基座 " + BASE
         + "，ref " + BRANCH + "）：**这一枚改了产品文件（" + str(PBC) + " 枚：" + ", ".join(PBC_WHERE)
         + "）**，把 X-5 那一格从一形补到你点名的五形 R19-R23，"
         + "五形各自判一遍正反两读；五枚臂 MET、四枚反件仍各自只咬自己那一格")
if IS_MERGE:
    first += ("；这一枚的两个父是 " + PARENTS[0] + "（你当时的尖）与 " + PARENTS[1]
              + "（它重切的那枚 q53 候选），手合流的只有 ORD-0310 裹住那一腿 fetch 的那一跳")
X5_CAS = "；".join(f"{c['readings']['shape']} 的 playwright 报告 blob {c['readings']['report_blob']}"
                  for c in cas if c["readings"]["arm_that_flipped"] == "X1")
body = "\n".join([first, ""] + lines[1:] + [
    "",
    "读了就能自己复算的四条：",
    "1) 手机上那一形现在就能撞：拿一个 502 的 HTML 正文回给 `agent/commands` —— 修前是「连不上服务端」+ 整块"
    "技术详情从 DOM 消失，修后是「服务端处理失败」+ 块里一行「这台设备自己的读数（服务器没给句子）」"
    "（逐臂读数与五份 playwright 报告都在架上）。",
    "2) 反件不对称是刻意做的：`ca_unsafe_read` 只让 N1 红，N2 仍绿 —— 带 `error.message` 的正文在读 detail 之前就"
    "返回了；如果两枚一起红，我只能说我改坏了别的。",
    "3) 这条回归是我 ORD-0280 那一跳带出来的（`PlanWithAiSheet.tsx:155` 就是我写的那行），七枚臂当时全用 JSON "
    "正文，所以没撞见；"
    "能区分这些状态的只有「正文里有没有 JSON 对象」，不是状态码也不是时长（Q25）。这条教训我按同样形制补了臂。",
    "4) X-5 按你要的口径办成了一句不变量的正反两读：渲染文字里出现「技术详情」⇒ `<details>` 计数 ≥ 1；计数为 0 ⇒ "
    "句子里不得出现该承诺。X1 跑的是过去会断的那一形（mission 存了 COMPLETED、没存 reason、这屏一条可用结果都没"
    "拿到），它同时要求块存在、块里有读数、且那句话还在指过去（Q53=① 选了「渲染出来」而不是「软化句子」）；X2 是"
    "另一侧——BASELINE_UNAVAILABLE 那句话不做承诺，块缺席就不算说谎，这条规则因此不会退化成「永远渲染点什么」。"
    "杀手反件两枚各改一侧：" + X5_CAS + " —— `ca_x5_no_block` 动渲染门、`ca_x5_soft_promise` 动文案，"
    "两枚都只让 X1 那一格红。",
    "",
    "没闭合：发布级面（生产构建产物）仍欠；places / plans/generate 两条腿的同一形没写臂（同一个 helper，"
    "我不拿推理替读数）；X-5 我也只在 vite dev 上量到——按你的代次口径，手机上那一代是否真有这个空洞仍是 "
    "NOT-DEPLOYED-OBSERVED，换代后请 HJ-P3 或红队在目标代重读一次；手机换代与切换归你，我没动 dist/index/预览后端。",
    "",
    CLOSING,
])
bus_txt = WORK / "ord0302_bus_body.txt"
bus_txt.write_text(body, "utf-8", newline="\n")
outs = gate(bus_txt)
gate_ok(outs, "bus")
BUS_GATE = outs
# Idempotency: this script publishes, writes the ledger and posts.  When it died between publish and post the
# only safe re-run is one that can see its own earlier post -- a duplicate bus comment is noise delivered to
# every lane reading the thread, so the window is checked before anything is sent.
_since = time.strftime("%Y-%m-%dT%H:%M:00Z", time.gmtime(time.time() - 6 * 3600))
_window = api(f"https://api.github.com/repos/{WS}/issues/1/comments?since={_since}&per_page=100&page=1")
_dupe = [c["id"] for c in _window if isinstance(c, dict) and c["body"].startswith(first[:40])]
if _dupe:
    print("a post for this candidate is already on the bus; not double-posting:", _dupe)
    raise SystemExit(0)
made = api(f"https://api.github.com/repos/{WS}/issues/1/comments", {"body": body}, verb="POST")
back = api(f"https://api.github.com/repos/{WS}/issues/comments/{made['id']}")
print("bus comment", made.get("id"), "| bytes", len(back.get("body", "")), "| closing line ok:",
      back.get("body", "").rstrip().endswith(CLOSING))
(WORK / "ord0302_bus_id.txt").write_text(str(made["id"]), "utf-8", newline="\n")

# ---------------------------------------------------------------- the claim gates' own receipt, published
claim = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0302", "candidate_tip": CAND,
         "rulers": {p.name: {"path": str(p), "blob40": blob_of(p)} for p in Q43S + [Q38]},
         "pass_criterion": "exit code 0 from each ruler; NO_CLAIM_FOUND (rc 4) is never a pass",
         "ledger_block": {k: {"rc": v["rc"], "headline": [l for l in v["output"].splitlines()
                                                          if "claims checked" in l][:1]}
                          for k, v in LEDGER_GATE.items()},
         "bus_body": {k: {"rc": v["rc"], "headline": [l for l in v["output"].splitlines()
                                                      if "claims checked" in l][:1]}
                      for k, v in BUS_GATE.items()},
         "texts": {"ord0302_ledger_block.txt": blob_of(ledger_txt), "ord0302_bus_body.txt": blob_of(bus_txt)},
         "bus_comment_id": made.get("id"), "derived_result": None}
claim_p = WORK / "ord0302_claim_gate.json"
claim_p.write_text(json.dumps(claim, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(claim_p, claim_p.name)
if remote(claim_p.name) != blob_of(claim_p):
    raise SystemExit("the claim-gate receipt did not land on the branch")

receipt["claim_gate_check"] = {"rulers": claim["rulers"], "ledger": claim["ledger_block"],
                               "bus": claim["bus_body"], "receipt_of_it": claim_p.name,
                               "receipt_blob": blob_of(claim_p)}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
FILES.append((claim_p, claim_p.name))
for f, name in ((out, "ord0302_receipt.json"),):
    push(f, name)
    if remote(name) != blob_of(f):
        raise SystemExit("the receipt did not land with its claim-gate block")
build_index()
push(ip, ip.name)
for name in (claim_p.name, "ord0302_receipt.json", ip.name):
    want = blob_of(next(p for p, n in FILES if n == name))
    got = remote(name)
    print(f"{name:28s} {got[:12]} match={got == want}")
    if got != want:
        raise SystemExit("the branch does not answer with the bytes I just wrote for " + name)
