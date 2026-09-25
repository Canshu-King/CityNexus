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
DIR = "evidence/ord0302-unreadable-server-body"
BASE = "dc964086c9d412573ac19d70b24b30e6c3ee6168"
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


CAND = g(["rev-parse", "HEAD"])
PARENT = g(["rev-parse", "HEAD^"])
BRANCH = g(["rev-parse", "--abbrev-ref", "HEAD"])
# The first half of this order was already published on this ref before X-5 arrived, so the commit the
# commander had in hand is this ref's own parent -- stated as a coordinate, not as a deleted detail.
SUPERSEDED = PARENT
SHEET_BLOB = blob(CAND, SHEET)
SPEC_BLOB = blob(CAND, SPEC_REL)
ls_line = subprocess.run(["git", "ls-remote", "git@github.com:Canshu-King/CityNexus.git",
                          f"refs/heads/{BRANCH}"], capture_output=True, text=True,
                         env={**dict(os.environ), "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}).stdout.strip()
prov = {}
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
bugged_text = subprocess.run(["git", "-C", str(LANE), "show", f"{BASE}:{SHEET}"], capture_output=True).stdout.decode("utf-8")
ANCHORS = {
    "guarded_detail_read": "  const detail = (body as { detail?: unknown } | null)?.detail;",
    "unguarded_detail_read": "  const detail = (body as { detail?: unknown }).detail;",
    "body_null_for_unparseable": "const body = await response.json().catch(() => null);",
    "not_ok_branch": "      if (!response.ok) {",
    "network_write": 'status: "NETWORK"',
    "details_gate": "{(result?.failureReason || result?.summary) && (",
}
lines_of = lambda text, needle: [i + 1 for i, l in enumerate(text.splitlines()) if needle in l]
# Both trees are measured, because the order names line numbers off the generation that still has the
# defect and the candidate's own comments shift everything below them.  A number that was copied rather
# than re-read would be exactly the kind of claim this receipt is not allowed to make.
measured, measured_base = {}, {}
for name, needle in ANCHORS.items():
    n, nb = lines_of(sheet_text, needle), lines_of(bugged_text, needle)
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
            f"the detail block was attached={readings['detail_block_attached']}")
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
cells.append(arm_cell("X1", "device", "X-5: this status's own card text points at 技术详情, so the block must "
                                   "exist and must carry the reading; the arm also requires the pointer to "
                                   "still be worded."))
cells.append(arm_cell("X2", "either", "The other side of the pairing: a status whose copy promises nothing may "
                                   "keep the block absent -- which is what stops the rule degenerating into "
                                   "'always render something'."))

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

root = {"base_tip": BASE, "bugged_sheet_blob": BUGGED, "candidate_sheet_blob": SHEET_BLOB,
        "predecessor_order": "ORD-0280", "this_order": "ORD-0302",
        "unsafe_reads_at": unsafe_before, "safe_reads_at": measured["guarded_detail_read"],
        "body_null_line": measured_base["body_null_for_unparseable"],
        "not_ok_line": measured_base["not_ok_branch"],
        "network_write_line": measured_base["network_write"],
        "details_gate_line": measured_base["details_gate"],
        "candidate_lines_of_the_same_anchors": {k: measured[k] for k in
                                                ("body_null_for_unparseable", "not_ok_branch",
                                                 "network_write", "details_gate")},
        "status_written": "NETWORK",
        "previous_generation_sheet_blob": PREV_GEN, "spec_blob": SPEC_BLOB,
        # Every line number this cell names is written as `path:line`, which is what the claim gate accepts
        # as a coordinate a reader can resolve; a bare "531" pins nothing once the file moves.
        "unsafe_read_coords": [f"{SHEET}:{n}" for n in unsafe_before],
        "safe_read_coords": [f"{SHEET}:{n}" for n in measured["guarded_detail_read"]],
        "coord_body_null": f"{SHEET}:{measured_base['body_null_for_unparseable']}",
        "coord_not_ok": f"{SHEET}:{measured_base['not_ok_branch']}",
        "coord_network": f"{SHEET}:{measured_base['network_write']}",
        "coord_details_gate": f"{SHEET}:{measured_base['details_gate']}",
        "rulers": {"q38": blob_of(Q38), "q43": [blob_of(p) for p in Q43S]}}
root_why = ("root cause, re-measured on this tree rather than copied from the order: in the bugged blob "
            + BUGGED + " the two envelope helpers read the detail field without a guard on `body` itself, at "
            + " and ".join(root["unsafe_read_coords"]) + "; the leg that reaches them sets `body = null` for an "
            "unparseable answer at " + root["coord_body_null"] + ", the refusal branch starts at "
            + root["coord_not_ok"] + ", and the throw is caught where status is written as NETWORK at "
            + root["coord_network"] + " with the note nulled, which is also the line the detail block depends "
            "on at " + root["coord_details_gate"] + ". On the candidate the same two reads are guarded, now at "
            + " and ".join(root["safe_read_coords"]) + " (sheet blob " + SHEET_BLOB + ", spec blob "
            + SPEC_BLOB + "). The generation before ORD-0280 (sheet blob " + PREV_GEN + ") did not throw there "
            "-- it answered with an invented status string, which is the defect that order removed; both states "
            "are wrong in different ways and only the body-has-a-JSON-object reading separates them.")
cells.append({"cell": "root cause and the coordinates it was measured at", "claimed_result": "MET",
              "derived_result": None, "why": C.cite(root_why, root, PATS) and root_why, "readings": root})

scope = {"ord_0281_branch_untouched": "review/0281-write-deadline-keyed-b2",
         "other_lanes_files_touched": 0,
         "phone_state": "neither cell was observed by me on the deployed generation -- both readings are vite "
                        "dev, so the phone keeps whatever is shipped until the commander swaps",
         "swap_actions_by_me": 0,
         "release_grade": False,
         "new_prose_written": "two device lines, one per named cell (requirement ② names the first, X-5 the "
                              "second); no server-facing wording was touched",
         "device_lines_written": ["no readable answer reached this device (network or origin)",
                                  "plans compiled; 0 usable result(s) reached this screen"],
         "not_measured": ["a non-JSON body on the places leg and the generate leg (same helper, arms not "
                          "written)", "an HTML answer that still parses as JSON",
                          "the shipped bundle behind the phone: X-5 was measured on vite dev, so the "
                          "generation that is live now is still NOT-DEPLOYED-OBSERVED for this cell"]}
scope_why = ("scope and boundaries: only two product paths changed in this candidate -- the sheet ("
             + SHEET_BLOB + ") and its new spec (" + SPEC_BLOB + "); files belonging to other lanes: "
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
        "typecheck_configs": ["tsconfig.check.json", "tsconfig.typecheck.json"]}
base_why = ("base and shape: " + CAND + " is the ref tip GitHub answers (" + ls_line + "), "
            + str(base["commits_over_base"]) + " commits over the order's tip " + BASE + " (ancestor check = "
            + str(base["base_is_ancestor"]) + "), so the two named cells land on the one ref the commander "
            "already holds rather than as two competing candidates. Process, stated rather than smoothed: the "
            "first half of this order was pushed alone as " + SUPERSEDED + ", the X-5 work then went on top of "
            "it, and the earlier attempt to fold both into one commit was refused as non-fast-forward -- no "
            "force-push, so " + SUPERSEDED + " is still an ancestor of this tip and every reading taken under "
            "it stays resolvable. " + str(len(base["changed_paths"])) + " paths changed: "
            + ", ".join(p.split("/")[-1] for p in base["changed_paths"]) + "; the diff restricted to backend/ "
            "answers " + (base["backend_diff"] or "none") + ". Both typecheck configs ("
            + ", ".join(base["typecheck_configs"]) + ") were clean before the arms ran. The arms ran against "
            "exactly the committed bytes: the sheet's sha256 at HEAD is " + committed_sha256[:16]
            + " and every run recorded that same value as the digest it started from ("
            + ", ".join(sorted(before_digests)) + "), agree=" + str(same_bytes) + ".")
cells.append({"cell": "base, ref and what this candidate touches",
              "claimed_result": "MET" if (base["base_is_ancestor"] and ls_line.startswith(CAND)
                                          and blob(CAND, SHEET) != BUGGED and same_bytes
                                          and not base["backend_diff"]) else "NOT_MET",
              "derived_result": None, "why": C.cite(base_why, base, PATS) and base_why, "readings": base})

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0302 文案修 · 非 JSON 正文不得冒充网络故障", "lane": "B c01d72a3",
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

FILES = [(out, "ord0302_receipt.json"), (WORK / "ord0302_arms_run.json", "ord0302_arms_matrix.json")]
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
for p in (SPIKE / "ord0302_run_arms.py", SPIKE / "ord0302_deliver.py"):
    if p.exists():
        FILES.append((p, p.name))
ip = WORK / "ord0302_index.json"
ip.write_text(json.dumps({"candidate_tip": CAND, "base_tip": BASE, "branch": BRANCH, "dir": DIR,
                          "files": [{"name": n, "blob40": blob_of(p), "bytes": p.stat().st_size}
                                    for p, n in FILES if p.exists()]}, ensure_ascii=False, indent=1),
              "utf-8", newline="\n")
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
    return name + " blob " + SUB[name]


# ---------------------------------------------------------------- ledger + bus, gated by both claim rulers
arms = [c for c in cells if c["cell"].startswith(ARMS_ALL)]
cas = [c for c in cells if c["cell"].startswith("counter-arm")]
rootc = next(c for c in cells if c["cell"].startswith("root cause"))
scopec = next(c for c in cells if c["cell"].startswith("scope,"))
basec = next(c for c in cells if c["cell"].startswith("base,"))
lines = [""]
MARK = ("### B c01d72a3 · ORD-0302 文案修（一枚候选装下两枚具名格：非 JSON 正文冒充网络故障 ＋ X-5 的承诺指向空块）"
        f"基座 `{BASE[:7]}` 候选 `{CAND[:7]}`")
lines.append(MARK + " @" + time.strftime("%H:%M", time.localtime()) + "+08 —— "
             "**号令者自己读出来的那两行我核过了，是真的；X-5 与 null-body 那一格同行域，所以一次候选、一次落地，"
             "没有第二张单。**")
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
    outs = {}
    for ruler in Q43S:
        r = subprocess.run([PY, str(ruler), "--text", str(path)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        outs[ruler.name] = ((r.stdout or "") + (r.stderr or "")).strip()
    return outs


ok = True
for label, path in (("ledger", ledger_txt),):
    outs = gate(path)
    for k, v in outs.items():
        print(f"Q43 {k} {label}:", [l for l in v.splitlines() if "claims checked" in l][:1])
        if "Q43_GATE_CLEAN" not in v:
            print(v[:1200])
            ok = False
if not ok:
    raise SystemExit("a claim gate refused the ledger block; not writing, not sending")

before = LEDGER.read_bytes()
if MARK.encode("utf-8") in before:
    print("ledger anchor already present; not appending twice")
else:
    with open(str(LEDGER), "a", encoding="utf-8", newline="\n") as fh:
        fh.write(LEDGER_BODY)
    print("ledger appended:", len(LEDGER.read_bytes()) - len(before), "B")

first = ("B c01d72a3 → 号令者 494abfd7：ORD-0302 交候选 " + CAND + "（基座 " + BASE
         + "，两枚具名格落在同一枚 ref " + BRANCH + " 上，快进自你手上那一枚 " + SUPERSEDED
         + "，没有 force-push）：两处安全读 + NETWORK 的可见兑底 + X-5 的承诺与块成对；"
         + "五枚臂 MET、四枚反件各自只咬自己那一格")
body = "\n".join([first, ""] + lines[1:] + [
    "",
    "读了就能自己复算的四条：",
    "1) 手机上那一形现在就能撞：拿一个 502 的 HTML 正文回给 `agent/commands` —— 修前是「连不上服务端」+ 整块"
    "技术详情从 DOM 消失，修后是「服务端处理失败」+ 块里一行「这台设备自己的读数（服务器没给句子）」"
    "（逐臂读数与五份 playwright 报告都在架上）。",
    "2) 反件不对称是刻意做的：`ca_unsafe_read` 只让 N1 红，N2 仍绿 —— 带 `error.message` 的正文在读 detail 之前就"
    "返回了；如果两枚一起红，我只能说我改坏了别的。",
    "3) 这条回归是我 0280 那一跳带出来的（`:155` 就是我写的那行），七枚臂当时全用 JSON 正文，所以没撞见；"
    "能区分这些状态的只有「正文里有没有 JSON 对象」，不是状态码也不是时长（Q25）。这条教训我按同样形制补了臂。",
    "4) X-5 按你要的口径办成了一句不变量的正反两读：渲染文字里出现「技术详情」⇒ `<details>` 计数 ≥ 1；计数为 0 ⇒ "
    "句子里不得出现该承诺。X1 跑的是过去会断的那一形（mission 存了 COMPLETED、没存 reason、这屏一条可用结果都没"
    "拿到），它同时要求块存在、块里有读数、且那句话还在指过去（Q53=① 选了「渲染出来」而不是「软化句子」）；X2 是"
    "另一侧——BASELINE_UNAVAILABLE 那句话不做承诺，块缺席就不算说谎，这条规则因此不会退化成「永远渲染点什么」。"
    "杀手反件两枚各改一侧：`ca_x5_no_block` 动渲染门、`ca_x5_soft_promise` 动文案，两枚都只让 X1 那一格红。",
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
for k, v in outs.items():
    print(f"Q43 {k} bus:", [l for l in v.splitlines() if "claims checked" in l][:1])
    if "Q43_GATE_CLEAN" not in v:
        print(v[:1200])
        raise SystemExit("bus body refused by a claim gate; not posting")
made = api(f"https://api.github.com/repos/{WS}/issues/1/comments", {"body": body}, verb="POST")
back = api(f"https://api.github.com/repos/{WS}/issues/comments/{made['id']}")
print("bus comment", made.get("id"), "| bytes", len(back.get("body", "")), "| closing line ok:",
      back.get("body", "").rstrip().endswith(CLOSING))
(WORK / "ord0302_bus_id.txt").write_text(str(made["id"]), "utf-8", newline="\n")
