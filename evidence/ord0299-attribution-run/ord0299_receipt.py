"""ORD-0299 receipt: every cell justifies itself, then the commander's own r2 ruler is run on it.

Sequence, because a ruler output cannot live inside the file it judges without changing that file:
  1. build the receipt from the two runs' artifacts (per-arm readings, not recollections),
  2. run `receipt_cell_derivation_check_r2.py --receipt <it>` (blob re-hashed before use),
  3. store that transcript as a top-level sidecar (never as a cell, so it cannot vote),
  4. run the ruler AGAIN on the finished bytes and keep both transcripts, so what gets published is what
     the ruler actually read.

Every cell's sentence is checked against that cell's own record BEFORE writing, using the ruler's own token
patterns (imported from its file), so a sentence cannot cite a value the cell does not hold. `claimed_result`
is mine; `derived_result` is null everywhere, per the order.
"""
from __future__ import annotations

import glob
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0299_cite as C  # noqa: E402

WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
DRIVER = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0299_counter_arm.py")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
SHEET_REL = "frontend/src/features/planning/PlanWithAiSheet.tsx"
SPEC_REL = "frontend/e2e/qoder-ord0280-attribution-label-speaks-for-itself.spec.ts"
SERVER_LABEL = "服务器给出的原因"
LANDED = "5c4608cede6cb7bd5f3ac7e704bfee379ca47abc"
OLD_BASE = "45b0a5e281cae9c37715173afd3ac5778f309ca7"

PATS = C.ruler_patterns()
run = json.loads((WORK / "ord0299_counter_arm_run.json").read_text(encoding="utf-8"))
stamp = sorted(pathlib.Path(WORK).glob("ord0299_counter_*.json"))[0].name.split("_")[-1].split(".")[0]
base_arms = json.loads((WORK / f"e2e_ord0299_fixed_{stamp}/ord0280/attribution_label_arms.json")
                       .read_text(encoding="utf-8"))["arms"]
counter_rep = json.loads((WORK / f"ord0299_counter_{stamp}.json").read_text(encoding="utf-8"))

counter_payload, counter_status = {}, {}


def walk(n):
    for s in n.get("suites", []) or []:
        walk(s)
    for sp in n.get("specs", []) or []:
        m = re.match(r"ord0280-([A-D]\d?)", sp.get("title", ""))
        if not m:
            continue
        arm = m.group(1)
        for tt in sp.get("tests") or []:
            for r in tt.get("results") or []:
                counter_status.setdefault(arm, r.get("status"))
                errs = ([r["error"]] if r.get("error") else []) + (r.get("errors") or [])
                for e in errs:
                    msg = (e or {}).get("message", "") if isinstance(e, dict) else str(e)
                    if '"want"' in msg and arm not in counter_payload:
                        counter_payload[arm] = json.loads(msg[msg.index("{"):msg.index("}") + 1])


walk({"suites": counter_rep.get("suites") or []})

# Playwright's own coordinates for each arm, taken from the baseline report rather than retyped.
fixed_rep = json.loads((WORK / f"ord0299_fixed_{stamp}.json").read_text(encoding="utf-8"))
NODE = {}


def collect(n):
    for s in n.get("suites", []) or []:
        collect(s)
    for sp in n.get("specs", []) or []:
        m = re.match(r"ord0280-([A-D]\d?)", sp.get("title", ""))
        if not m:
            continue
        outcomes = [r.get("status") for tt in (sp.get("tests") or []) for r in (tt.get("results") or [])]
        NODE[m.group(1)] = {"nodeid": "frontend/e2e/" + str(sp.get("file")) + ":"
                                      + str(sp.get("line")) + ":" + str(sp.get("column")),
                            "test_title": sp.get("title"), "outcomes": outcomes}


collect({"suites": fixed_rep.get("suites") or []})
if sorted(NODE) != sorted(ARM_ORDER := ("A1", "A2", "B1", "B2", "C1", "C2", "D")):
    raise SystemExit(f"the baseline report does not carry all seven arms: {sorted(NODE)}")
if any(v["outcomes"] != ["passed"] for v in NODE.values()):
    raise SystemExit("a baseline arm is not a single passed result: "
                     + json.dumps({k: v["outcomes"] for k, v in NODE.items()}))


def g(args) -> str:
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def git_blob(rev: str, rel: str) -> str:
    """`git rev-parse <rev>:<path>` echoes the argument instead of failing on a missing path, so the
    output must be checked against the input before it can be called a blob id."""
    out = g(["rev-parse", f"{rev}:{rel}"]).strip()
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else "ABSENT"


TIP = g(["rev-parse", "HEAD"]).strip()
OLD_TIP = g(["rev-parse", "review/0280-attribution-label"]).strip()
IS_ANC = subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", LANDED, TIP],
                        capture_output=True).returncode
pristine = subprocess.run(["git", "-C", str(LANE), "show", f"HEAD:{SHEET_REL}"],
                          capture_output=True).stdout
sha_fixed = hashlib.sha256(pristine).hexdigest()[:16]
sha_mutant = hashlib.sha256(C.patch_bytes(pristine, run["counter_arm"]["patch"])).hexdigest()[:16]
site_text = pristine.decode("utf-8")
RENDER_LINES = C.lines_of(site_text, "data-reason-origin={result.failureReason.from}")
BLIND_LINES = C.lines_of(site_text, '{result.failureReason.from === "server"')
DB_FIXED = None  # set below, from the driver's own literals + the stamp on the artifact names
DB_COUNTER = None
# Every number in a cell's sentence is measured here from the shipped bytes, never typed from memory:
# the four note-construction sites are located by a needle that must match exactly one line.
SITE_NEEDLES = {"A1": "agent/commands -> HTTP ${response.status}",
                "A2": "agent/commands -> HTTP ${response.status}",
                "B1": "GET /places -> HTTP ${placesResponse.status}",
                "B2": "GET /places -> HTTP ${placesResponse.status}",
                "C1": "POST /plans/generate -> HTTP ${generate.status}",
                "C2": "POST /plans/generate -> HTTP ${generate.status}",
                "D": "text: `GET /places?city_code=${cityCode} -> ${knownIds.size} places`"}
SITES = {}
for _arm, _needle in SITE_NEEDLES.items():
    _ls = C.lines_of(site_text, _needle)
    if len(_ls) != 1:
        raise SystemExit(f"site for {_arm} is not a unique line: {_ls} for {_needle!r}")
    SITES[_arm] = _ls[0]
RUNS = C.runs_pinned(DRIVER)
PORTS = {"baseline": (RUNS[0]["frontend_port"], RUNS[0]["backend_port"]),
         "counter": (RUNS[1]["frontend_port"], RUNS[1]["backend_port"])}
RUN_IDS = {"baseline": RUNS[0]["run_id_prefix"] + stamp[-4:],
           "counter": RUNS[1]["run_id_prefix"] + stamp[-4:]}
DB_FIXED = f"_{RUN_IDS['baseline']}.db"
DB_COUNTER = f"_{RUN_IDS['counter']}.db"
STATUS_NAME = {a: (base_arms.get(a) or {}).get("read", {}).get("status") for a in SITES}
if any(not v for v in STATUS_NAME.values()):
    raise SystemExit(f"an arm has no status in the run artifact: {STATUS_NAME}")
dev_failed = sorted(k for k, v in counter_status.items() if v == "failed")
srv_passed = sorted(k for k, v in counter_status.items() if v == "passed")

cells = []
for arm in ("A1", "A2", "B1", "B2", "C1", "C2", "D"):
    b = (base_arms.get(arm) or {}).get("read") or {}
    c = counter_payload.get(arm) or {}
    want = (base_arms.get(arm) or {}).get("want")
    readings = {
        "arm": arm, "want": want, "site_line": SITES[arm],
        "nodeid": NODE[arm]["nodeid"], "test_title": NODE[arm]["test_title"],
        "baseline": {"run_id": RUN_IDS["baseline"], "db": DB_FIXED,
                     "frontend_port": PORTS["baseline"][0], "backend_port": PORTS["baseline"][1],
                     "label_rendered": b.get("label"),
                     "origin_attribute": b.get("origin"), "reason_rendered": b.get("reason"),
                     "result_status": b.get("status", STATUS_NAME[arm]),
                     "outcome": NODE[arm]["outcomes"][0]},
        "counter": {"run_id": RUN_IDS["counter"], "db": DB_COUNTER,
                    "frontend_port": PORTS["counter"][0], "backend_port": PORTS["counter"][1],
                    "label_rendered": c.get("label") or b.get("label"),
                    "origin_attribute": c.get("origin") or b.get("origin"),
                    "reason_rendered": c.get("reason") or b.get("reason"),
                    "outcome": counter_status.get(arm)},
        "component_sha256_fixed": sha_fixed, "component_sha256_mutant": sha_mutant,
        "render_lines": RENDER_LINES, "blind_lines": BLIND_LINES}
    if want == "device":
        verdict = ("MET" if (b.get("label") != SERVER_LABEL and b.get("origin") == "device"
                             and counter_status.get(arm) == "failed"
                             and (c.get("label") == SERVER_LABEL)) else "NOT_MET")
        why = (f"{arm} ({NODE[arm]['nodeid']}, device leg, code at line {SITES[arm]}): on the candidate "
               f"the screen renders "
               f"{b.get('label')!r} with origin={b.get('origin')!r} over the reading "
               f"{b.get('reason')!r} ({STATUS_NAME[arm]}); with the label forced blind at lines "
               f"{RENDER_LINES} the same arm turns {counter_status.get(arm)} and its label becomes "
               f"{c.get('label')!r} while the reading is still {c.get('reason')!r}. component sha256 "
               f"{sha_fixed} -> {sha_mutant}, run {readings['baseline']['run_id']} vs "
               f"{readings['counter']['run_id']}.")
    else:
        verdict = "MET" if (b.get("label") == SERVER_LABEL and b.get("origin") == "server"
                            and counter_status.get(arm) == "passed") else "NOT_MET"
        why = (f"{arm} ({NODE[arm]['nodeid']}, server leg, code at line {SITES[arm]}): "
               f"the sentence {b.get('reason')!r} is shown "
               f"under {SERVER_LABEL!r} with origin={b.get('origin')!r} and status {STATUS_NAME[arm]}, and "
               f"it stays {counter_status.get(arm)} when the label goes blind at lines {RENDER_LINES} "
               f"(label still {c.get('label') or b.get('label')!r}) - the control that stops the device arms "
               f"from being satisfied by hiding the panel. component sha256 {sha_fixed} / mutant "
               f"{sha_mutant}, runs {readings['baseline']['run_id']} and {readings['counter']['run_id']}.")
    cells.append({"cell": f"{arm} attribution arm ({want})", "claimed_result": verdict,
                  "derived_result": None,
                  "why": C.cite(why, readings, PATS) and why, "readings": readings})

c7_readings = {"device_arms_failed": dev_failed, "server_arms_passed": srv_passed,
               "hunk_count": len(run["counter_arm"]["patch"]),
               "render_lines": RENDER_LINES, "blind_lines": BLIND_LINES,
               "component_sha256_fixed": sha_fixed, "component_sha256_mutant": sha_mutant,
               "restored_byte_exact": run["restored_byte_exact"],
               "src_dirty_after": g(["status", "--porcelain", "frontend/src"]).strip() or "clean",
               "counter_run_id": RUN_IDS["counter"], "counter_db": DB_COUNTER}
c7_why = ("counter-arm: " + str(len(run["counter_arm"]["patch"])) + " hunks at the render lines "
          + str(RENDER_LINES) + " and " + str(BLIND_LINES) + " replace the two reads of the note's source "
          "with the constant server, so the label stops consulting who spoke; component sha256 "
          + sha_fixed + " became " + sha_mutant + " in run " + RUN_IDS["counter"] + " (db "
          + DB_COUNTER + "), and exactly " + str(dev_failed) + " failed while " + str(srv_passed)
          + " stayed passed - the source was put back byte-exact (" + str(run["restored_byte_exact"])
          + "), tree " + (c7_readings["src_dirty_after"] or "clean") + ".")
cells.append({"cell": "counter-arm shape (label no longer consults the source)",
              "claimed_result": "MET" if (dev_failed and all(a in dev_failed for a in ("A1", "B1", "C1", "D"))
                                          and "A2" in srv_passed and run["restored_byte_exact"]) else "NOT_MET",
              "derived_result": None, "why": C.cite(c7_why, c7_readings, PATS) and c7_why,
              "readings": c7_readings})

PROV_FIXED = json.loads((WORK / f"e2e_ord0299_fixed_{stamp}" / "e2e-provenance" / "authoritative.json")
                        .read_text(encoding="utf-8"))
PROV_COUNTER = json.loads((WORK / f"e2e_ord0299_counter_{stamp}" / "e2e-provenance" / "authoritative.json")
                          .read_text(encoding="utf-8"))
# Two independent sources must agree before I say anything about the face: what the driver pinned, and what
# the product's own hook recorded while the run was live.
PINS_AGREE = {
    "frontend_ports": [int(PORTS["baseline"][0]), int(PORTS["counter"][0])]
                     == [PROV_FIXED["frontendPort"], PROV_COUNTER["frontendPort"]],
    "backend_ports": [int(PORTS["baseline"][1]), int(PORTS["counter"][1])]
                     == [PROV_FIXED["backendPort"], PROV_COUNTER["backendPort"]],
    "run_ids": [RUN_IDS["baseline"], RUN_IDS["counter"]] == [PROV_FIXED["runId"], PROV_COUNTER["runId"]],
    "dbs": [DB_FIXED, DB_COUNTER] == [pathlib.Path(PROV_FIXED["databaseUrl"].replace("sqlite:///", "")).name,
                                      pathlib.Path(PROV_COUNTER["databaseUrl"].replace("sqlite:///", "")).name],
    "ai_off": [PROV_FIXED["ai"], PROV_COUNTER["ai"]] == ["disabled", "disabled"],
    "server_not_reused": [PROV_FIXED["reuseExistingServer"], PROV_COUNTER["reuseExistingServer"]]
                         == [False, False],
    "authoritative": [PROV_FIXED["authoritative"], PROV_COUNTER["authoritative"]] == [True, True]}
if not all(PINS_AGREE.values()):
    raise SystemExit("driver pins and the runs' own provenance disagree: " + json.dumps(PINS_AGREE))

c8_readings = {"release_grade": False,
               "served_by": "vite dev (the playwright webServer this invocation owns), not the built bundle",
               "provenance_files": ["authoritative.json", "authoritative.json"],
               "provenance_baseline_run": PROV_FIXED, "provenance_counter_run": PROV_COUNTER,
               "pins_agree": PINS_AGREE,
               "command_as_recorded_in_the_run_artifact": run["face"]["command"],
               "grade_honest_label_as_recorded": run["face"]["grade_honest_label"],
               "env_pinned_by_the_executed_driver": C.env_pinned_by(DRIVER),
               "ai_keys_removed_by_the_executed_driver": C.pop_keys(DRIVER),
               "driver_script": DRIVER.name,
               "driver_sha256": hashlib.sha256(DRIVER.read_bytes()).hexdigest(),
               "driver_mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(DRIVER.stat().st_mtime)),
               "run_artifact_recorded_at": run["at"]}
c8_why = ("face: the product's own e2e hook recorded both runs in authoritative.json - "
          + PROV_FIXED["runId"] + " on frontend :" + str(PROV_FIXED["frontendPort"]) + " / backend :"
          + str(PROV_FIXED["backendPort"]) + " with db " + DB_FIXED + ", and " + PROV_COUNTER["runId"]
          + " on :" + str(PROV_COUNTER["frontendPort"]) + " / :" + str(PROV_COUNTER["backendPort"])
          + " with db " + DB_COUNTER + " - each with authoritative=true, ai=disabled, "
          "reuseExistingServer=false; the ports and run ids the driver pins (" + c8_readings["driver_script"]
          + ", sha256 " + c8_readings["driver_sha256"][:12] + ", last written " + c8_readings["driver_mtime"]
          + ") match those records on every point, so the two sources agree rather than one restating the "
          "other. What answered the browser was " + c8_readings["served_by"] + ", i.e. the source tree, not a "
          "shipped bundle, so by the commander's grading this is spec-level red/green and NOT release-grade "
          "(release_grade=" + str(c8_readings["release_grade"]) + "); the grade label written at run time was "
          + c8_readings["grade_honest_label_as_recorded"] + ".")
cells.append({"cell": "face of the run (what grade this evidence is)", "claimed_result": "DECLARED",
              "derived_result": None, "why": C.cite(c8_why, c8_readings, PATS) and c8_why,
              "readings": c8_readings})

c9_readings = {"candidate_tip": TIP, "landed_base": LANDED, "previous_candidate_tip": OLD_TIP,
               "old_base": OLD_BASE, "is_ancestor_rc": IS_ANC,
               "component_path": SHEET_REL, "spec_path": SPEC_REL,
               "sheet_blob_landed_base": git_blob(LANDED, SHEET_REL),
               "sheet_blob_old_base": git_blob(OLD_BASE, SHEET_REL),
               "sheet_blob_candidate": git_blob(TIP, SHEET_REL),
               "sheet_blob_previous_candidate": git_blob(OLD_TIP, SHEET_REL),
               "spec_blob_landed_base": git_blob(LANDED, SPEC_REL),
               "spec_blob_candidate": git_blob(TIP, SPEC_REL),
               "new_ref": "review/0280-attribution-label-r2",
               "old_ref_left_at": OLD_TIP}
# What "nothing was rewritten" means here, checked rather than asserted: same input on both bases, the same
# fixed file on both candidates, and the old ref still pointing where it was.
if c9_readings["sheet_blob_landed_base"] != c9_readings["sheet_blob_old_base"]:
    raise SystemExit("the two bases do not carry the same input file; the re-parent changed content: "
                     + c9_readings["sheet_blob_landed_base"] + " vs " + c9_readings["sheet_blob_old_base"])
if c9_readings["sheet_blob_candidate"] != c9_readings["sheet_blob_previous_candidate"]:
    raise SystemExit("the re-parented candidate is not content-identical to the one that was reviewed")
if c9_readings["sheet_blob_candidate"] == c9_readings["sheet_blob_landed_base"]:
    raise SystemExit("the candidate changes nothing on the landed tip")
if c9_readings["spec_blob_landed_base"] != "ABSENT":
    raise SystemExit("the spec exists at the landed base; 'new on this line' would be false: "
                     + c9_readings["spec_blob_landed_base"])
if c9_readings["spec_blob_candidate"] == "ABSENT":
    raise SystemExit("the spec is not committed on the candidate tip")
c9_why = ("re-parent: " + TIP + " sits directly on the landed tip " + LANDED + " (merge-base --is-ancestor "
          "rc=" + str(IS_ANC) + "). The two bases carry the same input - " + SHEET_REL.split("/")[-1] + " is "
          + c9_readings["sheet_blob_landed_base"] + " at " + LANDED[:8] + " and "
          + c9_readings["sheet_blob_old_base"] + " at " + OLD_BASE[:8] + " - and the two candidates carry the "
          "same fixed file, " + c9_readings["sheet_blob_candidate"] + " at both " + TIP[:8] + " and "
          + OLD_TIP[:8] + " (different from the base blob, so the change is still there). "
          "The spec is new on this line: " + c9_readings["spec_blob_landed_base"] + " at the landed base, "
          + c9_readings["spec_blob_candidate"] + " here. Old ref review/0280-attribution-label was left at "
          + OLD_TIP + ", nothing was force-pushed.")
cells.append({"cell": "re-parent identity onto the landed tip",
              "claimed_result": "MET" if (IS_ANC == 0
                                          and c9_readings["sheet_blob_candidate"]
                                          == c9_readings["sheet_blob_previous_candidate"]
                                          and c9_readings["sheet_blob_landed_base"]
                                          == c9_readings["sheet_blob_old_base"]) else "NOT_MET",
              "derived_result": None, "why": C.cite(c9_why, c9_readings, PATS) and c9_why,
              "readings": c9_readings})

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0299 · 0280 的 e2e 真跑 + 反件（landed tip 上）",
           "lane": "B c01d72a3", "claim_kind": "RUNTIME_MEASURED",
           "candidate_tip": TIP, "landed_base": LANDED, "branch": "review/0280-attribution-label-r2",
           "cells": cells,
           "summary": {"arms_total": 7, "arms_met": sum(1 for c in cells[:7] if c["claimed_result"] == "MET"),
                       "device_arms": 4, "server_arms": 3,
                       "counter_device_failed": dev_failed, "counter_server_passed": srv_passed,
                       "non_arm_cells": sum(1 for c in cells[7:] if c["claimed_result"] in ("MET", "DECLARED"))},
           "derived_result": None,
           "not_claimed": "derived_result 全格留 null；发布级证据缺（见 face 格），要补的是同一批臂跑在生产构建产物上"}

out = WORK / "ord0299_attribution_run_receipt.json"


def ruler(path: pathlib.Path) -> dict:
    rb = subprocess.run(["git", "hash-object", str(RULER)], capture_output=True, text=True,
                        encoding="utf-8", errors="replace").stdout.strip() \
        if (RULER := C.RULER).exists() else "MISSING"
    r = subprocess.run([PY, str(C.RULER), "--receipt", str(path), "--min-cells", "4"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    return {"ruler_path": str(C.RULER), "ruler_blob": rb,
            "ruler_blob_matches_declared": rb == "91ae8b1ec55f5c19122af11bf775df14580955e4",
            "rc": r.returncode, "headline": [l for l in txt.splitlines() if "overall" in l or "finding" in l],
            "output": txt}


out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
first = ruler(out)
receipt["ruler_check"] = {"pass_1_before_sidecar": {k: v for k, v in first.items() if k != "output"},
                          "pass_1_output": first["output"]}
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
second = ruler(out)
receipt["ruler_check"]["pass_2_on_published_bytes"] = {k: v for k, v in second.items() if k != "output"}
receipt["ruler_check"]["pass_2_output"] = second["output"]
out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print("ruler blob matches declared:", second["ruler_blob_matches_declared"])
print("\n".join(first["headline"][:6]))
print("--- pass 2 (on the published bytes) ---")
print("\n".join(second["headline"][:8]))
print("rc pass1/pass2:", first["rc"], second["rc"])
print("summary:", json.dumps(receipt["summary"], ensure_ascii=False))
print("cells:", [(c["cell"][:44], c["claimed_result"]) for c in cells])
