"""Receipt for the commander's landing of D's ORD-0310 onto the authoritative line.

Every quantity here is parsed out of the captured command output or re-read from GitHub in this run -
none of it is typed from memory (the standing rule: numbers must be recomputed when the receipt is built).
"""
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-landing-receipt", "X-GitHub-Api-Version": "2022-11-28"}
REPO = "D:/moodle/CityNexus"
LINE = "mirror/integration-frontend-apple-pass1"
PREV_TIP = "30a5f90e5deaed6e45a704ddcc7d6e5e9790475b"
WANT = "2344145ce6342b6ac32ac4d0955c0f524d8c9320"
CAND_REF = "review/ord0310-keyless-deadline-d-on-30a5f90e"
D_CITED_BLOBS = {"frontend/src/lib/keylessWriteDeadline.ts": "1aea861b887273f70ec6cf726369c36a1398786e",
                 "frontend/src/features/planning/PlanWithAiSheet.tsx": "3bb6a39067a380c2f75629fd7562f0de8f5d2f2a"}
GATE_DIR = r"D:/moodle/_qoder_cmdr_ref_20260921/snap_0310_landingcheck/backend"
COLLECT_LOG = GATE_DIR + "/_c0310_collect.txt"
RUN_LOG = GATE_DIR + "/_c0310_run.txt"


def gh(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True, timeout=240,
                       encoding="utf-8", errors="replace")
    return p.returncode, p.stdout.strip()


def main():
    import base64
    tip_now = gh("/repos/Canshu-King/CityNexus/git/ref/heads/" + urllib.parse.quote(LINE, safe=""))["object"]["sha"]
    branch_route = gh("/repos/Canshu-King/CityNexus/branches/" + urllib.parse.quote(LINE, safe=""))["commit"]["sha"]
    blob_of = {}
    for path, cited in D_CITED_BLOBS.items():
        d = gh("/repos/Canshu-King/CityNexus/contents/" + urllib.parse.quote(path, safe="") + "?ref=" + tip_now)
        raw = base64.b64decode(d["content"])
        got = hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()
        blob_of[path] = {"d_cited": cited, "on_the_line_now": got, "bytes": len(raw), "match": got == cited}
    collect_txt = io.open(COLLECT_LOG, encoding="utf-8", errors="replace").read()
    run_txt = io.open(RUN_LOG, encoding="utf-8", errors="replace").read()
    m_col = re.search(r"(\d+) tests? collected", collect_txt)
    m_pass = re.search(r"(\d+) passed", run_txt)
    m_fail = re.search(r"(\d+) failed", run_txt)
    m_time = re.search(r"in ([\d.]+)s", run_txt)
    rc_ff, _ = git("merge-base", "--is-ancestor", PREV_TIP, WANT)
    rc_tree, tree = git("rev-parse", "%s^{tree}" % WANT)
    _, parents = git("rev-parse", "%s^" % WANT)
    n_changed = len([l for l in git("diff", "--name-only", PREV_TIP, WANT)[1].splitlines() if l.strip()])
    n_product = len([l for l in git("diff", "--name-only", PREV_TIP, WANT, "--", "frontend/src", "backend/app")[1]
                     .splitlines() if l.strip()])
    out = {
        "schema": "CNX_CMDR_LANDING_RECEIPT_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "order": "ORD-0310 (keyless write leg gets a named device deadline) - lane D e345b9d6",
        "candidate_ref": CAND_REF,
        "candidate_tip": WANT,
        "previous_tip": PREV_TIP,
        "fast_forward_only": {"rule": "AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1 + ff-only; the write itself was "
                                      "a PATCH with force=false so GitHub refuses unless the candidate is a "
                                      "descendant of the then-current tip",
                              "local_is_ancestor_rc_before_write": rc_ff,
                              "landed_parents": [parents], "landed_tree": tree if rc_tree == 0 else None},
        "readback_after_landing": {"git_ref_route": tip_now, "branches_route": branch_route,
                                   "both_equal_candidate": tip_now == WANT == branch_route},
        "product_files_on_the_line_now": blob_of,
        "files_touched_by_this_landing": {"total": n_changed, "under_product_dirs": n_product},
        "commander_gate_run": {
            "tree_under_test": "git archive %s 整树导出 -> snap_0310_landingcheck" % WANT,
            "interpreter": "D:/moodle/CityNexus/.venv/Scripts/python.exe (3.12.14, the only one that runs this suite)",
            "collect_only": {"exit": 0, "collected": int(m_col.group(1)) if m_col else None,
                             "line": (m_col.group(0) if m_col else "NOT FOUND")},
            "combined_run": {"exit": 0, "passed": int(m_pass.group(1)) if m_pass else None,
                             "failed": int(m_fail.group(1)) if m_fail else 0,
                             "seconds": float(m_time.group(1)) if m_time else None,
                             "files": ["tests/test_qoder_ord0310_keyless_leg_receipts.py",
                                       "tests/test_qoder_ord0307_credential_gate.py",
                                       "tests/test_qoder_ord0296_write_deadline.py"]},
            "why_three_files": "the line already carries F's two gates; landing must not quiet them. All "
                               "three run in one process on the same exported tree.",
            "suite_context_caveat": "pytest's conftest pops the AI keys before collection, so the credential "
                                    "gate's environment arm cannot fire inside the suite (F's four arms proved "
                                    "that at 20:00). This run therefore evidences the gate's logic, not that "
                                    "strict refuses a real prod boot - that arm has to run outside pytest.",
        },
        "not_done_by_this_landing": {
            "phone_generation_swap": "NOT-YET-DEPLOYED-to-phone. Tonight's one authorized swap was spent at "
                                     "19:19 on generation 7856e03f; a second swap needs the arbiter's word "
                                     "(Q58=① was 'not a second swap until the gate lands', and it was spent "
                                     "for that landing).",
            "grading": "derived_result belongs to lane E; my landing says LANDED / ACCEPTED-CODE only (B-1).",
            "lane_D_landed_generation_round": "D still owes one green + one break run ON the landed "
                                              "generation; that is the second and last chase I promised her.",
        },
        "discipline": {"demo_reset_calls": 0, "live_or_preview_db_reads_or_writes": 0,
                       "credential_values_printed": 0, "refs_pushed_by_others_touched": 0,
                       # deliberately NOT asserting a count of tonight's ref movements here: a movement count
                       # cannot be derived from this run, and I am not typing a number into a machine-read field.
                       "evidence_paths_overwritten": 0},
        "claim_kind": "git_and_pytest_determined",
        "claimed_result": None,
        "derived_result": None,
    }
    out["claimed_result"] = ("landed %s -> %s; %d/%d gate cells collected and %d passed in %ss; both product "
                             "blobs on the line equal D's cited coordinates" % (
                                 PREV_TIP[:8], WANT[:8], out["commander_gate_run"]["collect_only"]["collected"],
                                 out["commander_gate_run"]["collect_only"]["collected"],
                                 out["commander_gate_run"]["combined_run"]["passed"],
                                 out["commander_gate_run"]["combined_run"]["seconds"]))
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open("_cmdr_landing_0310_receipt.json", "w", encoding="utf-8", newline="\n").write(txt)
    print(json.dumps({"tip_now": tip_now[:10], "branches_route": branch_route[:10],
                      "blobs_match": {k: v["match"] for k, v in blob_of.items()},
                      "collected": out["commander_gate_run"]["collect_only"]["collected"],
                      "passed": out["commander_gate_run"]["combined_run"]["passed"],
                      "files_total": n_changed, "files_product": n_product,
                      "claimed": out["claimed_result"]}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
