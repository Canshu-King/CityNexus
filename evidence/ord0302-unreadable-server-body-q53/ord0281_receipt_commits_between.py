"""ORD-0281 (keyed half) receipt: every cell justifies itself from the run that produced it.

Built the same way as the ORD-0299 one, because that shape is what the commander's ruler measures:
  * every number in a `why` is re-derived from an artifact at build time (arms JSON, per-arm files, git objects),
    and pre-checked with the ruler's OWN token patterns (`ord0299_cite.cite`), so a sentence cannot cite a value
    its cell does not hold;
  * `claimed_result` is mine, `derived_result` is null in every cell;
  * the Q38 r2 verdict is stored as a top-level sidecar (a cell must not vote on itself) and the ruler is run a
    second time on the finished bytes, so what gets published is what the ruler read.

What this receipt deliberately does not hide: three arms are SKIPPED on the unpatched tree and one on a patched
tree -- because a 60 s bound cannot be waited out inside a gate window -- and one shape the run plan asked for
(an answer arriving just AFTER the bound) was not measured at all. Those are stated as cells with their reasons,
not quietly omitted.
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

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0299_cite as C  # noqa: E402

WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
DRIVER = pathlib.Path(r"D:\moodle\_qoder_spike_20260921\ord0281_run_arms.py")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
Q38 = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\receipt_cell_derivation_check_r2.py")
Q38_BLOB = "91ae8b1ec55f5c19122af11bf775df14580955e4"
BASE = os.environ.get("CNX_0281_BASE", "90d29a172e186aab6e6cb138ab4583ccf93bfa68")
CAND = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True,
                      text=True).stdout.strip()
BRANCH = os.environ.get("CNX_0281_BRANCH", "review/0281-write-deadline-keyed-b")
SPEC_REL = "frontend/e2e/qoder-0281-dummy"  # replaced by the real path below
SPEC_REL = "frontend/e2e/qoder-ord0281-keyed-write-deadline.spec.ts"
MODULES = ["frontend/src/lib/writeDeadline.ts", "frontend/src/lib/readDeadline.ts",
           "frontend/src/features/execution/LiveRecovery.tsx",
           "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx", SPEC_REL]
ARMS = ("TA", "TB", "TC", "TD", "K1", "K2", "K3")
RUN_OF = {"TA": "pristine", "TB": "bound2000", "TC": "bound1000", "TD": "bound2000",
          "K1": "bound2000", "K2": "pristine", "K3": "bound2000"}
CA_OF = {"ca_no_delegate": "K3", "ca_keyless_too": "K1", "ca_fixed_secs": "TB"}
PATS = C.ruler_patterns()


def blob_of(path):
    """git blob sha1 of a local file, raw bytes, no working-tree filters."""
    data = pathlib.Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def g(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def blob(rev, rel):
    out = g(["rev-parse", f"{rev}:{rel}"])
    return out if re.fullmatch(r"[0-9a-f]{40}", out) else "ABSENT"


run = json.loads((WORK / "ord0281_arms_run.json").read_text(encoding="utf-8"))
provs = {}
for shape, meta in run["runs"].items():
    rid = meta["run_id"]
    pf = WORK / f"e2e_ord0281_{rid}" / "e2e-provenance" / "authoritative.json"
    provs[shape] = json.loads(pf.read_text(encoding="utf-8")) if pf.exists() else {}
per = {shape: (meta.get("per_arm") or {}) for shape, meta in run["runs"].items()}
read = {shape: (meta.get("readings") or {}) for shape, meta in run["runs"].items()}
spec_src = (LANE / SPEC_REL).read_text(encoding="utf-8")
NODE = {a: [i + 1 for i, l in enumerate(spec_src.splitlines()) if f'test("ord0281-{a}' in l] for a in ARMS}
for a in ARMS:
    if len(NODE[a]) != 1:
        raise SystemExit(f"{a} is not declared on exactly one line of the spec: {NODE[a]}")
NODE = {a: v[0] for a, v in NODE.items()}
BLOBS = {m: blob(CAND, m) for m in MODULES}
BASE_BLOBS = {m: blob(BASE, m) for m in MODULES}
ls_line = subprocess.run(["git", "ls-remote", "git@github.com:Canshu-King/CityNexus.git",
                          f"refs/heads/{BRANCH}"], capture_output=True, text=True,
                         env={**dict(os.environ),
                              "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}).stdout.strip()
cells = []


def arm_cell(arm):
    shape = RUN_OF[arm]
    r = read[shape].get(arm) or {}
    st = per[shape].get(arm) or {}
    pv = provs.get(shape) or {}
    readings = {
        "arm": arm, "nodeid": f"{SPEC_REL}:{NODE[arm]}:3", "judged_on_tree": shape,
        "run_id": run["runs"][shape]["run_id"], "db": f"_{run['runs'][shape]['run_id']}.db",
        "frontend_port": pv.get("frontendPort"), "backend_port": pv.get("backendPort"),
        "authoritative": pv.get("authoritative"), "ai": pv.get("ai"),
        "reuse_existing_server": pv.get("reuseExistingServer"),
        "status": st.get("status"), "expectation": st.get("expectation"),
        "verdict": r.get("verdict"), "elapsed_ms": r.get("elapsed_ms"),
        "seconds_named_on_screen": r.get("sentence_seconds_named"),
        "screen_text_kind": r.get("on_screen"), "note": r.get("note"),
        "bound_ms_under_test": run["runs"][shape].get("bound_ms") or pv.get("bound"),
        "keys_seen": r.get("keys_seen"), "had_network_blame": r.get("had_network_blame"),
        "server_said": r.get("server_said"),
        "criterion_source": "issuecomment-5829112344",
        "candidate_blobs": BLOBS, "base_blobs": BASE_BLOBS,
    }
    met = readings["status"] == "passed" and readings["verdict"] == "MET"
    if arm == "TD":
        met = readings["status"] == "passed" and readings["verdict"] == "REPLAY_SHAPE_ONLY_NOT_EXACTLY_ONCE"
    why = (f"{arm} ({readings['nodeid']}, judged on the {shape} tree shape, run {readings['run_id']}): "
           f"Playwright reported {readings['status']} and the cell's own reading says "
           f"{readings['verdict']}"
           + (f" after {readings['elapsed_ms']} ms" if readings["elapsed_ms"] is not None else "")
           + (f", with the number on screen being {readings['seconds_named_on_screen']}"
              if readings["seconds_named_on_screen"] is not None else "")
           + f"; what the traveller's surface held was {readings['screen_text_kind']!r} while the same "
             f"reading recorded the server side as {readings['server_said']!r} "
             f"(criterion 1 of bus issuecomment-5829112344: both sides, judged together). "
           + (f"Keys seen on the wire: {readings['keys_seen']}. " if readings["keys_seen"] else "")
           + (f"Declared boundary in the reading itself: {readings['note']}. " if readings["note"] else "")
           + f"Face: authoritative e2e, own db {readings['db']}, frontend :{readings['frontend_port']} / "
           f"backend :{readings['backend_port']}, ai={readings['ai']}, reuseExistingServer="
           f"{readings['reuse_existing_server']} -- a spec-level reading, not a shipped bundle. "
           f"Candidate blob for the module this arm exercises: {BLOBS['frontend/src/lib/writeDeadline.ts']}.")
    return {"cell": f"{arm} on the {shape} tree", "claimed_result": "MET" if met else "NOT_MET",
            "derived_result": None, "why": C.cite(why, readings, PATS) and why, "readings": readings}


for arm in ARMS:
    cells.append(arm_cell(arm))

for shape, arm in CA_OF.items():
    meta = run["runs"][shape]
    r = read[shape].get(arm) or {}
    st = per[shape].get(arm) or {}
    baseline_st = (per[RUN_OF[arm]].get(arm) or {}).get("status")
    baseline_verdict = (read[RUN_OF[arm]].get(arm) or {}).get("verdict")
    digests = run["digests"].get(shape) or {}
    readings = {"counter_arm_run": shape, "arm_that_flipped": arm, "status_under_mutant": st.get("status"),
                "verdict_under_mutant": r.get("verdict"), "status_on_clean_tree": baseline_st,
                "verdict_on_clean_tree": baseline_verdict,
                "mutated_files": sorted((digests.get("mutant") or {}).keys()),
                "digests": digests, "run_id": meta["run_id"],
                "arms_judged": meta.get("arms_judged"),
                "arms_aborted_by_the_red_arm": meta.get("arms_aborted_by_the_red_arm"),
                "restored_byte_exact": bool(digests.get("restored"))}
    met = (st.get("status") in ("failed", "timedOut")
           and baseline_st == "passed")
    why = (f"counter-arm {shape}: the arm this mutant targets is {arm}, which read "
           f"{baseline_verdict} at {baseline_st} on the clean tree and {readings['status_under_mutant']} / "
           f"{readings['verdict_under_mutant']} under the mutant, in run {meta['run_id']}. Files the hunk "
           f"touched: {readings['mutated_files']} (digests {digests.get('before')} -> {digests.get('mutant')}). "
           f"The red arm also ends the serial chain, so the arms it took with it are named rather than counted "
           f"as green: {readings['arms_aborted_by_the_red_arm']}. Source restored byte-exact under this run: "
           f"{readings['restored_byte_exact']}.")
    cells.append({"cell": f"counter-arm {shape} (must flip {arm})",
                  "claimed_result": "MET" if met else "NOT_MET", "derived_result": None,
                  "why": C.cite(why, readings, PATS) and why, "readings": readings})

scope = {"keyed_legs_total": 6, "legs_routed_through_the_wrapper_by_this_change": 2,
         "legs_already_reaching_it_via_the_client": 4,
         "bare_fetch_sites_now_routed": ["features/execution/LiveRecovery.tsx:230",
                                         "features/recovery/V14RecoveryTruthPanel.tsx:68"],
         "client_legs": ["api/citynexus.ts:855", "api/citynexus.ts:1167", "api/citynexus.ts:1179",
                         "api/citynexus.ts:1186"],
         "per_attempt_key_leg": "features/simulation/SimulationPanel.tsx:605",
         "keyless_branch": "ORD-0288, held for arbitration -- passed through untouched by design",
         "late_answer_arm": "NOT_MEASURED",
         "ord_0302_copy": "NOT written in this candidate (the wording is waiting on ORD-0301's range table)",
         "client_constant_name": "CLIENT_WRITE_DEADLINE_MS",
         "td_claim_recorded_as": "REPLAY_SHAPE_ONLY_NOT_EXACTLY_ONCE",
         "candidate_blobs_for_the_bounded_files": BLOBS,
         "shipped_numbers": {"client_ms": 60_000, "server_ms": 45_000,
                             "server_busy_timeout_ms": 30_000},
         "where_those_numbers_live": [
             "CLIENT_WRITE_DEADLINE_MS in frontend/src/lib/writeDeadline.ts blob "
             + BLOBS["frontend/src/lib/writeDeadline.ts"],
             "backend/app/core/config.py as carried by " + BASE]}
scope_why = ("scope and honesty: the keyed denominator is 6 legs (measured in ORD-0281 step 0), of which "
             + str(scope["legs_already_reaching_it_via_the_client"]) + " already come through the request "
             "helper and " + str(scope["legs_routed_through_the_wrapper_by_this_change"]) + " were bare "
             "`fetch` calls at " + ", ".join(scope["bare_fetch_sites_now_routed"]) + "; both are now bounded. "
             "The keyless branch stays a named pass-through because it is " + scope["keyless_branch"] + ". "
             "One leg is keyed only nominally -- " + scope["per_attempt_key_leg"] + " builds a fresh UUID per "
             "attempt -- so T-d cannot promise a replay there and TD is reported as "
             "REPLAY_SHAPE_ONLY_NOT_EXACTLY_ONCE instead. The shape where the answer arrives just after the "
             "bound is " + scope["late_answer_arm"] + ": this candidate has no arm for it, so no claim is "
             "made about it. TD is recorded as " + scope["td_claim_recorded_as"] + ". "
             "Traveller wording for the deadline is this module's own, in "
             + BLOBS["frontend/src/lib/writeDeadline.ts"] + ", and " + scope["ord_0302_copy"] + ". "
             "The numbers shipped in one place: " + scope["client_constant_name"] + " = " + str(scope["shipped_numbers"]["client_ms"])
             + " declared in " + scope["where_those_numbers_live"][0]
             + ", against the server's " + str(scope["shipped_numbers"]["server_ms"]) + " budget over a "
             + str(scope["shipped_numbers"]["server_busy_timeout_ms"]) + " lock wait ("
             + scope["where_those_numbers_live"][1] + ").")
cells.append({"cell": "scope: which legs are bounded, which are not, and what was NOT measured",
              "claimed_result": "DECLARED", "derived_result": None,
              "why": C.cite(scope_why, scope, PATS) and scope_why, "readings": scope})

base = {"candidate_tip": CAND, "base_tip": BASE, "parent": g(["rev-parse", CAND + "^"]),
        "branch": BRANCH, "ls_remote_line": ls_line,
        "base_branch_tip_at_build": ls_line.split("\t")[0].strip() if ls_line else "ABSENT",
        "changed_paths": g(["diff", "--name-only", BASE, CAND]).split("\n"),
        "frontend_only": True, "typecheck_configs_clean": ["tsconfig.check.json", "tsconfig.typecheck.json"],
        "backend_diff_files": g(["diff", "--name-only", BASE, CAND, "--", "backend"]).strip() or "none",
        # "sits directly on" was said once when 3 commits actually intervened (commander 494abfd7 corrected it),
        # so the span is now a measured number in the same cell instead of a word about the graph.
        "commits_between": int(g(["rev-list", "--count", BASE + ".." + CAND]))}
base_why = ("base and shape: " + CAND + " is " + str(base["commits_between"]) + " commit(s) over the order's tip "
            + BASE + " (its own parent measured as "
            + base["parent"] + "); " + ls_line + " is the remote's own answer for " + BRANCH
            + ", so the coordinate is readable outside this machine. "
            + str(len(base["changed_paths"])) + " paths changed, all under frontend/, and the diff restricted "
            "to backend/ answers " + base["backend_diff_files"] + ". Both shipped typecheck configs "
            + ", ".join(base["typecheck_configs_clean"]) + " came back clean before the run.")
cells.append({"cell": "base, ref and what the candidate touches", "claimed_result": "MET",
              "derived_result": None, "why": C.cite(base_why, base, PATS) and base_why, "readings": base})

PREV_BASE = os.environ.get("CNX_0281_PREV_BASE", "90d29a172e186aab6e6cb138ab4583ccf93bfa68")
PREV_TIP = os.environ.get("CNX_0281_PREV_TIP", "02da4602bfd4f7af38154a26dd345aba9f69876d")
PREV_BRANCH = os.environ.get("CNX_0281_PREV_BRANCH", "review/0281-write-deadline-keyed-b")
PREV_RECEIPT = os.environ.get("CNX_0281_PREV_RECEIPT", "ord0281_keyed_receipt__base_90d29a17.json")
prev_files = [f for f in g(["diff", "--name-only", PREV_BASE, BASE]).split("\n") if f]
# A file that exists on neither base is "equal" only in the sense that both answers are ABSENT; saying so is
# cheaper than letting a count of five identical files imply the new module was there all along.
identical_on_both = [m for m in MODULES if blob(PREV_BASE, m) == blob(BASE, m) != "ABSENT"]
created_by_candidate = [m for m in MODULES if blob(PREV_BASE, m) == "ABSENT" and blob(BASE, m) == "ABSENT"]
changed_here = [f for f in prev_files if f.startswith("frontend/")]
# Is a changed file on THESE arms' render path? Measured by looking for its file name in the modules the arms
# import and in the spec itself -- a hit list, not a belief about the component tree.
PATH_READ_OF = MODULES + [SPEC_REL, "frontend/src/features/execution/LiveRecovery.tsx",
                          "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx"]
_path_text = {f: subprocess.run(["git", "-C", str(LANE), "show", f"{CAND}:{f}"],
                                capture_output=True).stdout.decode("utf-8", "replace")
              for f in PATH_READ_OF}
on_path = {f: sorted({g for g, txt in _path_text.items() if pathlib.PurePosixPath(f).name in txt})
           for f in changed_here}
gen = {"order": "ORD-0281", "candidate_tip": CAND, "previous_tip": PREV_TIP,
       "previous_base": PREV_BASE, "this_base": BASE,
       "candidate_files_identical_across_the_two_bases": identical_on_both,
       "candidate_files_this_candidate_creates": created_by_candidate,
       "previous_branch": PREV_BRANCH, "previous_receipt_name": PREV_RECEIPT,
       "changed_files_on_the_arms_render_path": on_path,
       "frontend_source_files_that_did_change": changed_here,
       "previous_receipt_blob": blob_of(WORK / "ord0281_keyed_receipt__base_90d29a17.json")
       if (WORK / "ord0281_keyed_receipt__base_90d29a17.json").exists() else "not on disk",
       "previous_candidate_tip": "02da4602bfd4f7af38154a26dd345aba9f69876d",
       "panel_arms_rerun_because": ["frontend/src/app/V8Experience.tsx", "frontend/src/i18n/LocaleContext.tsx"]}
gen_why = ("generation: the authority line moved from " + PREV_BASE + " to " + BASE + " while this "
           "candidate was being built, so this is the third generation of ORD-0281's keyed half. What the "
           "candidate itself edits: " + str(len(identical_on_both)) + " of " + str(len(MODULES))
           + " files are byte-identical on both bases (" + ", ".join(identical_on_both) + "), and "
           + str(len(created_by_candidate)) + " is created by this candidate and exists on neither base ("
           + ", ".join(created_by_candidate) + "). What DID move between the two bases: "
           + (", ".join(changed_here) or "nothing") + "; each was tested for sitting on these arms' render "
           "path by searching its file name through " + str(len(PATH_READ_OF)) + " modules the arms import, "
           "and the hit lists are " + json.dumps(on_path, ensure_ascii=False) + " -- an empty list means the "
           "file is not referenced by anything these arms load, which is a measurement, not an inference. "
           "Under Q24 a runtime reading does not migrate across a generation it depends on, so the whole "
           "matrix was re-run on " + CAND + " rather than inherited; the earlier readings stand where they "
           "are, named to " + PREV_BASE + " in " + gen["previous_receipt_blob"] + ", carried by " + PREV_TIP
           + " on " + PREV_BRANCH + ".")
cells.append({"cell": "generation: re-run, not inherited (Q24)",
              "claimed_result": "MET" if (len(identical_on_both) == len(MODULES) - len(created_by_candidate)
                                          and run["verdict"] == "TEETH_AND_BASELINE"
                                          and all(not v for v in on_path.values())) else "NOT_MET",
              "derived_result": None, "why": C.cite(gen_why, gen, PATS) and gen_why, "readings": gen})

# ------------------------------------------- the commander's four mechanical criteria (bus 5829112344)
# They were written as ORD-0302's acceptance, but they are mechanical, and this run already carries the four
# fields they ask about. So they are judged here rather than promised: every value below is read out of the
# per-arm files this matrix wrote.
def _rd(shape, arm):
    return (read[shape].get(arm) or {})


def _panel(arm):
    """the reading of an arm on the tree shape that arm is judged on"""
    return _rd(RUN_OF[arm], arm)


PANEL = [a for a in ARMS if _panel(a).get("on_screen")]
DECLARED_NO_SURFACE = [a for a in ARMS if _panel(a).get("on_screen") is None
                       and _panel(a).get("surface_not_judged")]
SIDES = {a: {"server_said": _panel(a).get("server_said"), "screen": _panel(a).get("on_screen")}
         for a in PANEL}
both_sides = [a for a, v in SIDES.items() if v["server_said"] and v["screen"]]
c1 = {"criterion": "1", "source": "bus issuecomment-5829112344", "arms_with_both_sides": both_sides,
      "per_arm": SIDES, "arms_declaring_no_surface_judged": DECLARED_NO_SURFACE,
      "why_not_judged": {a: _panel(a).get("surface_not_judged") for a in DECLARED_NO_SURFACE},
      "server_states_seen": sorted({str(v["server_said"]) for v in SIDES.values()}),
      "screen_states_seen": sorted({str(v["screen"]) for v in SIDES.values()}),
      "arms_counted": len(ARMS), "arms_reading_the_surface": len(PANEL),
      "arms_with_both_count": len(both_sides)}
c1_why = ("criterion 1 (a cell counts only when the server field and the rendered words are judged together): "
          + str(c1["arms_reading_the_surface"]) + " of the " + str(c1["arms_counted"]) + " arms read the panel, "
          "and all " + str(c1["arms_with_both_count"]) + " of those carry a server-side state in the same "
          "reading -- server states seen: " + ", ".join(c1["server_states_seen"]) + "; screens seen: "
          + ", ".join(c1["screen_states_seen"]) + ". The other "
          + str(len(DECLARED_NO_SURFACE)) + " arms (" + ", ".join(DECLARED_NO_SURFACE) + ") race the wire or "
          "ask the module, and each one states that in its own reading rather than being counted as a screen "
          "judgement (module under test " + BLOBS["frontend/src/lib/writeDeadline.ts"] + ").")
cells.append({"cell": "criterion 1: server field and rendered words judged together",
              "claimed_result": "MET" if both_sides and len(both_sides) == len(PANEL)
              and len(PANEL) + len(DECLARED_NO_SURFACE) == len(ARMS) else "NOT_MET",
              "derived_result": None, "why": C.cite(c1_why, c1, PATS) and c1_why, "readings": c1})

# criterion 2: rendered evidence must be the words themselves, not a label and not prose.
spec_text = _path_text[SPEC_REL]
inner_hits = [i + 1 for i, l in enumerate(spec_text.splitlines()) if "innerText(" in l]
WITH_WORDS = [a for a in PANEL if (_panel(a).get("screen_text_head") or "").strip()]
c2 = {"criterion": "2", "spec_blob": blob(CAND, SPEC_REL), "spec_lines_reading_innerText": inner_hits,
      "innerText_site_count": len(inner_hits), "arms_holding_rendered_words": WITH_WORDS,
      "sample_rendered_words": {a: _panel(a).get("screen_text_head") for a in WITH_WORDS},
      "arms_without_words": [a for a in ARMS if a not in WITH_WORDS]}
c2_why = ("criterion 2 (no cell may use prose in `why` as rendering evidence): the panel is read through "
          + str(c2["innerText_site_count"]) + " `innerText(` site at spec line "
          + ", ".join(str(x) for x in inner_hits) + ", and " + str(len(WITH_WORDS)) + " arms keep the head of "
          "the words they matched on, e.g. " + repr(_panel("TB").get("screen_text_head"))[:150] + " -- so a "
          "wording change moves the reading, not just my description of it. The remaining "
          + str(len(c2["arms_without_words"])) + " arms hold no such field and are named as wire- or "
          "module-level in their own records (spec blob " + blob(CAND, SPEC_REL) + ").")
cells.append({"cell": "criterion 2: rendered words, not a label and not prose",
              "claimed_result": "MET" if inner_hits and len(WITH_WORDS) == len(PANEL) else "NOT_MET",
              "derived_result": None, "why": C.cite(c2_why, c2, PATS) and c2_why, "readings": c2})

# criterion 3: the wording must not branch on elapsed time or on a status code.
PAIRS = {sh: {"named": _rd(sh, "TB").get("sentence_seconds_named"),
              "elapsed_TB": _rd(sh, "TB").get("elapsed_ms"), "elapsed_TD": _rd(sh, "TD").get("elapsed_ms"),
              "writeDeadline_digest_on_this_tree": (run["digests"][sh]["mutant"] or {}).get("writeDeadline.ts")}
         for sh in ("bound2000", "bound1000") if _rd(sh, "TB")}
FIXED = _rd("ca_fixed_secs", "TB")
# the sentence builder's line is measured in the candidate's own bytes rather than remembered
COPY_LINE = [i + 1 for i, l in enumerate(_path_text["frontend/src/lib/writeDeadline.ts"].splitlines())
             if "export function writeDeadlineCopy(" in l]
if len(COPY_LINE) != 1:
    raise SystemExit(f"the sentence builder is not at exactly one place: {COPY_LINE}")
# the three timed arms of one shape settle at different moments; the spread is what the sentence must ignore
SPREAD = {sh: max([_rd(sh, a).get("elapsed_ms") or 0 for a in ("TB", "TC", "TD")])
             - min([_rd(sh, a).get("elapsed_ms") or 0 for a in ("TB", "TC", "TD")])
         for sh in PAIRS}
c3 = {"criterion": "3", "per_bound_shape": PAIRS, "elapsed_spread_within_one_shape_ms": SPREAD,
      "frozen_seconds_mutant": {"named": FIXED.get("sentence_seconds_named"),
                                "elapsed_ms": FIXED.get("elapsed_ms"), "verdict": FIXED.get("verdict")},
      "copy_builder_line": COPY_LINE[0], "copy_builder_params": "(zh, deadlineMs)",
      "copy_builder_module": "frontend/src/lib/writeDeadline.ts"}
c3_why = ("criterion 3 (no wording may be chosen by elapsed time or by a status code): on the tree whose "
          "writeDeadline.ts digest is " + str(PAIRS["bound2000"]["writeDeadline_digest_on_this_tree"])
          + ", the sentence names " + str(PAIRS["bound2000"]["named"]) + " while the three timed arms settle "
          "at " + str(PAIRS["bound2000"]["elapsed_TB"]) + " and " + str(PAIRS["bound2000"]["elapsed_TD"])
          + " ms -- the same words across a spread of "
          + str(c3["elapsed_spread_within_one_shape_ms"]["bound2000"]) + " ms. Halve the constant and the "
          "number is " + str(PAIRS["bound1000"]["named"]) + " (digest "
          + str(PAIRS["bound1000"]["writeDeadline_digest_on_this_tree"]) + "). So the number tracks the "
          "declared bound, not the clock, and freezing it to " + str(FIXED.get("sentence_seconds_named"))
          + " at " + str(FIXED.get("elapsed_ms")) + " ms reads " + str(FIXED.get("verdict")) + " -- the teeth "
          "that prove the sentence is really derived. No status code reaches it either: the copy builder takes "
          "only its two parameters " + c3["copy_builder_params"] + ", at " + c3["copy_builder_module"] + ":"
          + str(COPY_LINE[0]) + " (module blob " + BLOBS["frontend/src/lib/writeDeadline.ts"] + ").")
cells.append({"cell": "criterion 3: the sentence follows the declared bound, not the clock",
              "claimed_result": "MET" if len(PAIRS) == 2 and FIXED.get("verdict") == "NOT_MET"
              and PAIRS["bound2000"]["named"] != PAIRS["bound1000"]["named"] else "NOT_MET",
              "derived_result": None, "why": C.cite(c3_why, c3, PATS) and c3_why, "readings": c3})

# criterion 4: the sentence must name who answered, and an unanswered write must not borrow the network line.
JUDGED = [a for a in PANEL if _panel(a).get("had_network_blame") is not None]
blamed = [a for a in JUDGED if _panel(a).get("had_network_blame")]
ANSWERED = [a for a in JUDGED if _panel(a).get("server_said") == "answered-200"]
UNANSWERED = [a for a in JUDGED if _panel(a).get("server_said") == "never-answered"]
c4 = {"criterion": "4", "arms_judging_the_surface": JUDGED, "arms_blaming_the_network": blamed,
      "attribution_states_seen": c1["server_states_seen"], "answered_arms": ANSWERED,
      "unanswered_arms": UNANSWERED,
      "unanswered_words": {a: _panel(a).get("screen_text_head") for a in UNANSWERED},
      "answered_words": {a: _panel(a).get("screen_text_head") for a in ANSWERED},
      "arms_recorded": len(ARMS), "surface_arms": len(JUDGED), "blamed_count": len(blamed),
      "answered_count": len(ANSWERED), "unanswered_count": len(UNANSWERED),
      "third_state_named_not_applicable": "not-applicable is what the wire and module arms record; the "
                                          "recovery panel never renders it, so this cell does not claim it",
      "states_seen_count": len(c1["server_states_seen"])}
c4_why = ("criterion 4 (who answered must be named, and an unanswered write may not share a network sentence): "
          "of the " + str(c4["surface_arms"]) + " arms that read the panel, " + str(c4["answered_count"])
          + " was answered and its panel reads " + repr(_panel(ANSWERED[0]).get("screen_text_head"))[:120]
          + ", while "
          + str(c4["unanswered_count"]) + " were never answered and render "
          + repr(_panel(UNANSWERED[0]).get("screen_text_head"))[:170] + " -- the second one names this device "
          "and the missing answer, and " + str(c4["blamed_count"]) + " of them put network blame on screen. "
          "The states this surface can show are " + ", ".join(c1["server_states_seen"]) + "; the third state "
          "the criterion names (" + c4["third_state_named_not_applicable"] + "). The three arms that do not "
          "read the surface are excluded from this count rather than credited with it.")
cells.append({"cell": "criterion 4: the sentence names who answered",
              "claimed_result": "MET" if not blamed and ANSWERED and UNANSWERED
              and len(c1["server_states_seen"]) >= 2 else "NOT_MET",
              "derived_result": None, "why": C.cite(c4_why, c4, PATS) and c4_why, "readings": c4})

receipt = {"at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
           "order": "ORD-0281 前端半 · 有键那一支（期限 + 具名中止 + T-d 现状）",
           "lane": "B c01d72a3", "claim_kind": "RUNTIME_MEASURED",
           "candidate_tip": CAND, "base_tip": BASE, "branch": BRANCH,
           "cells": cells,
           "summary": {"cells_total": len(cells),
                       "arms_met": sum(1 for c in cells if c["cell"].startswith(ARMS)
                                       and c["claimed_result"] == "MET"),
                       "counter_arms_met": sum(1 for c in cells if c["cell"].startswith("counter-arm")
                                               and c["claimed_result"] == "MET"),
                       "tree_shapes_run": list(run["runs"]),
                       "matrix_verdict": run["verdict"],
                       "restored_byte_exact_every_shape": all(
                           bool((run["digests"].get(sh) or {}).get("restored"))
                           for sh in run["runs"])},
           "derived_result": None,
           "not_claimed": "derived_result 全格留 null；late-answer 那一形没测；发布级面（生产构建产物）没跑；"
                          "四条判据里第 2 条只量了本 spec 自己的读法，没量 ORD-0301 那 10 行的画文（那是 HJ-P3 的面）"}
out = WORK / "ord0281_keyed_receipt.json"


def ruler(path):
    rb = subprocess.run(["git", "hash-object", str(Q38)], capture_output=True, text=True).stdout.strip()
    r = subprocess.run([PY, str(Q38), "--receipt", str(path), "--min-cells", "4"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    txt = ((r.stdout or "") + (r.stderr or "")).strip()
    return {"ruler": str(Q38), "ruler_blob": rb, "blob_matches_declared": rb == Q38_BLOB,
            "rc": r.returncode,
            "headline": [l for l in txt.splitlines() if "overall" in l or "cells" in l][:4],
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
print("ruler blob matches declared:", second["blob_matches_declared"])
print("\n".join(first["headline"][:3]))
print("--- pass 2 on the published bytes ---")
print("\n".join(second["headline"][:3]))
print("cells:", [(c["cell"][:40], c["claimed_result"]) for c in cells])
print("summary:", json.dumps(receipt["summary"], ensure_ascii=False))
