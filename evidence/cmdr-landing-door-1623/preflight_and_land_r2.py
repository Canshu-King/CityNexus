"""r2: same landing door as r1, but the Q64 arm now runs lane S4's r7b ruler AND verifies its identity.

Why r2 exists (measured 2026-09-26 16:17): r1 recorded `ruler_blob` as a CONSTANT beside the file it was
about to execute, without ever hashing that file.  Had the local ruler drifted from the published blob, the
receipt would still have printed the published value -- a door trusting its own label instead of reading the
thing it stands on.  r2 computes the blob of the file it runs and REFUSES the landing on any drift, and it
upgrades the ruler to r7b (blob d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2, signed ALL_MET by lane E at 16:2x),
which closes the blind spot I measured this morning: r6 could not see a device fact taken into an ATTRIBUTE
position -- exactly the shape Q71 forbids.  r1 stays on disk, untouched and still runnable, so old receipts
remain re-derivable.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-preflight", "X-GitHub-Api-Version": "2022-11-28"}
REPO = "D:/moodle/CityNexus"
LINE = "mirror/integration-frontend-apple-pass1"
PROJ = "Canshu-King/CityNexus"
VENV_PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
NODE_EXE = "node"                     # resolved from PATH; the ruler is the AST one, not a regex
EXPOSURE_RULER = "ui_exposure_taint_ast_r7b.cjs"         # published name: r7b (lane S4)
EXPOSURE_RULER_BLOB = "d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2"
_nul = chr(0).encode()  # the git object header separator, spelled so no source byte is a raw NUL
GATE_PUBLISHER = "publish_evidence_gated_r1.py"


def gh(path, method="GET", payload=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    data = json.dumps(payload).encode() if payload is not None else None
    if data:
        req.add_header("Content-Length", str(len(data)))
    try:
        with urllib.request.urlopen(req, data, timeout=240) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:300]


def ref_sha(branch):
    """Accept `review/x` or `refs/heads/review/x`; normalising matters because a double-prefixed path 404s,
    and a 404 here would be read as "the lane did not push" (it would not mean that)."""
    short = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else branch
    st, d = gh("/repos/%s/git/ref/heads/%s" % (PROJ, urllib.parse.quote(short, safe="")))
    if st != 200:
        raise SystemExit("REFROUTE_FAIL %s %s -> %s" % (branch, st, str(d)[:160]))
    return d["object"]["sha"]


def git(*a, binary=False):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=900)
    if binary:
        return p.returncode, p.stdout
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def blob(b):
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


def cell_key(cell):
    """`File.tsx:1042|RULE` -> `File.tsx|RULE`: the identity the ruler can actually stand behind."""
    m = re.match(r"^(.+?):(\d+)\|(.+)$", cell)
    return "%s|%s" % (m.group(1), m.group(3)) if m else cell


def pair_added(added, removed):
    """Line-exact additions that cannot be matched one-for-one by a line-exact removal under the same
    (file, rule) key.  This is what makes a pure line shift free while a swapped-in sink is not: the
    count-per-key view alone would let 'three cells became two, at different lines' through."""
    pool = {}
    for c in removed:
        pool.setdefault(cell_key(c), []).append(c)
    out = []
    for c in sorted(added, key=cell_key):
        if pool.get(cell_key(c)):
            pool[cell_key(c)].pop()
        else:
            out.append(c)
    return out


def exposure_counts(cells):
    """(file, rule) -> how many cells.  This is the comparison the door refuses on, because it is the
    one that survives a shifted line number."""
    out = {}
    for key in cells:
        m = re.match(r"^(.+):(\d+)\|(.+)$", key)
        k = "%s|%s" % (m.group(1), m.group(3)) if m else key
        out[k] = out.get(k, 0) + 1
    return out


def exposure_cells(rev, sub):
    """Return the set of "file:line|rule" Q64 cells the AST ruler finds in `rev`:frontend/src.

    Read-only: the tree is unpacked with `git archive` into its own scratch dir, never into a work tree.
    A cell key is (basename, line, rule); a shifted line reads as add+remove, which is honest for a
    no-GROW test (a genuinely new sink still shows up as an add with no matching remove)."""
    out = os.path.join(r"D:/moodle/_qoder_cmdr_ref_20260921", sub)
    if os.path.isdir(out):
        subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", out.replace("/", "\\")], timeout=600)
    os.makedirs(out, exist_ok=True)
    p = subprocess.run("git -C %s archive %s frontend/src | tar -x -C %s" % (REPO, rev, out),
                       shell=True, capture_output=True, timeout=900)
    if p.returncode:
        raise RuntimeError("git archive of %s failed: %s" % (rev[:12], p.stderr.decode("utf-8", "replace")[:200]))
    ruler = os.path.join(os.path.dirname(os.path.abspath(__file__)), EXPOSURE_RULER)
    # r2 bolt: the ruler's identity is MEASURED, not declared.  A door that prints a blob it never
    # checked would certify a stale or substituted ruler, so the sha1 header is built without any
    # escape sequences at all (a literal NUL via chr(0) -- see the toolchain trap list).
    with open(ruler, "rb") as _fh:
        _raw = _fh.read()
    _computed = hashlib.sha1(b"blob %d" % len(_raw) + _nul + _raw).hexdigest()
    if _computed != EXPOSURE_RULER_BLOB:
        raise RuntimeError("exposure ruler identity drift: %s is blob %s, door declares %s -- "
                           "re-point the constant or fix the file; do not land on an unverified ruler"
                           % (EXPOSURE_RULER, _computed[:12], EXPOSURE_RULER_BLOB[:12]))
    os.environ["CNX_EXPOSURE_RULER_COMPUTED"] = _computed
    js = os.path.join(out, "ruler.json")
    r = subprocess.run([NODE_EXE, ruler, "--tree", os.path.join(out, "frontend", "src"), "--out", js],
                       capture_output=True, timeout=1800)
    if not os.path.isfile(js):
        raise RuntimeError("ruler wrote no output (rc %s): %s" % (r.returncode,
                                                                r.stderr.decode("utf-8", "replace")[:200]))
    doc = json.load(io.open(js, encoding="utf-8"))
    return {"%s:%s|%s" % (h["file"].split("/")[-1], h["line"], h.get("rule")) for h in doc.get("hits", [])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-ref", required=True, help="refs/heads/review/... (the lane's own ref)")
    ap.add_argument("--tests", default="", help="comma-separated backend test files to run on the export")
    ap.add_argument("--exposure-arm", default="on", choices=["on", "off"],
                    help="Q64 no-new-cells check: run the AST ruler over frontend/src at the tip AND on the "
                         "candidate tree, and refuse when the candidate introduces an exposure cell the tip "
                         "does not have. Shrinking is always welcome; growing needs a ruling, not a landing.")
    ap.add_argument("--keep-export", default="off", choices=["on", "off"],
                    help="leave the ~213 MB candidate export on disk after the run")
    ap.add_argument("--suite-collect", default="on", choices=["on", "off"],
                    help="WHOLE backend-suite collection arm (default on).  A candidate carrying one "
                         "unimportable test file turns the entire suite into ZERO executed tests, and a "
                         "per-file collection cannot see that (observed on afbbf5be: 22 files -> 2 "
                         "collection errors -> `Interrupted` -> nothing ran).")
    ap.add_argument("--land", action="store_true", help="actually move the authoritative line (default: dry run)")
    ap.add_argument("--order", default="", help="order id for the receipt path")
    ap.add_argument("--out", default="", help="receipt json path")
    a = ap.parse_args()

    stamp = time.strftime("%H%M%S")
    out_path = a.out or ("_cmdr_preflight_%s_%s.json" % (a.order or "order", stamp))
    tip = ref_sha(LINE)
    cand = ref_sha(a.candidate_ref)
    subprocess.run(["git", "-C", REPO, "fetch", "origin",
                    "refs/heads/%s:refs/remotes/origin/_preflight_cand" % a.candidate_ref.replace("refs/heads/", ""),
                    "--force"], capture_output=True, timeout=600)
    rc_anc, _, _ = git("merge-base", "--is-ancestor", tip, cand)
    rc_lr, lr, _ = git("rev-list", "--left-right", "--count", "%s...%s" % (tip, cand))
    behind, ahead = [int(x) for x in lr.split()] if rc_lr == 0 else (None, None)
    rc_mb, base, _ = git("merge-base", tip, cand)
    _, line_files, _ = git("diff", "--name-only", base, tip)
    _, cand_files, _ = git("diff", "--name-only", base, cand)
    lf = sorted(x for x in line_files.splitlines() if x.strip())
    cf = sorted(x for x in cand_files.splitlines() if x.strip())
    inter = sorted(set(lf) & set(cf))
    # direction matters: `tip cand` on a behind-candidate lists what the LINE added, which reads as if the
    # candidate were deleting it. The question a landing asks is "what does the candidate introduce",
    # so measure from the merge base to the candidate.
    # What counts as "product" here was `frontend/src` + `backend/app` only, which is too narrow: ORD-0328
    # changed `agent-mcp/citynexus_mcp/schemas.py` - a real contract change on the MCP surface the product
    # ships - and this door reported `product introduced: (none)` for it.  A change the gate cannot see is a
    # change that never triggers the "does the phone bundle / the MCP surface need re-publishing?" question.
    PRODUCT_WATCH = ("frontend/src", "backend/app", "agent-mcp", "scripts")
    _, product_files, _ = git("diff", "--name-only", base, cand, "--")
    pf = [x for x in product_files.splitlines()
          if x.strip() and x.startswith(PRODUCT_WATCH)]
    rc_mt, mt_out, mt_err = git("merge-tree", "--write-tree", tip, cand)
    mt_lines = [l for l in mt_out.splitlines() if l.strip()]

    run = {"requested": [], "collect_exit": None, "collected": None, "test_exit": None, "summary": None,
           "export": None, "blob_equality": [], "whole_suite": None}
    tests = [t.strip() for t in a.tests.split(",") if t.strip()]
    verdict = "REFUSED"
    problems = []
    if tests or a.suite_collect == "on":
        export = r"D:/moodle/_qoder_cmdr_ref_20260921/snap_preflight_%s" % stamp
        os.makedirs(export, exist_ok=True)
        run["export"] = export
        pr = subprocess.run(["git", "-C", REPO, "archive", cand], capture_output=True, timeout=900)
        with open(os.path.join(export, "_tree.tar"), "wb") as fh:
            fh.write(pr.stdout)
        pt = subprocess.run(["tar", "-xf", os.path.join(export, "_tree.tar"), "-C", export],
                            capture_output=True, timeout=900)
        if pt.returncode:
            problems.append("export failed: %s" % pt.stderr.decode("utf-8", "replace")[:200])
        # blob equality: what I am about to test must be the candidate's bytes
        for rel in cf:
            if "/" not in rel:
                continue
            rcb, want, _ = git("rev-parse", "%s:%s" % (cand, rel))
            local = os.path.join(export, rel.replace("/", os.sep))
            if not os.path.exists(local):
                problems.append("exported tree has no %s" % rel)
                continue
            got = blob(io.open(local, "rb").read())
            run["blob_equality"].append({"path": rel, "candidate_blob": want, "export_blob": got, "equal": got == want})
        if any(not e["equal"] for e in run["blob_equality"]):
            problems.append("export bytes differ from the candidate blobs")
        # run the requested files in ONE process so cross-file import effects are visible, and collect first
        if tests:
            # PYTHONPATH must carry the export root here too.  It does NOT inherit it from the whole-suite arm
            # below, and a named test that imports a sibling package (`scripts.hermes_*`, `citynexus_mcp`) then
            # dies with ModuleNotFoundError during collection while the suite collects fine - i.e. the door
            # reports a red gate on a clean candidate.  Measured at 04:19 on 0f8b925fac: whole-suite collected
            # 1319 with exit 0, the same named file alone gave `Interrupted: 1 error during collection`.
            _env = dict(os.environ, PYTHONPATH=export)
            _backend_targets = ["tests/" + t for t in tests if "/" not in t]
            p_col = subprocess.run([VENV_PY, "-m", "pytest"] + (["--collect-only", "-q"] if _backend_targets else [])
                                   + (_backend_targets or ["--collect-only", "-q", "tests"]),
                                   cwd=os.path.join(export, "backend"), capture_output=True, timeout=900, env=_env)
            p_run = subprocess.run([VENV_PY, "-m", "pytest", "-p", "no:cacheprovider", "-q"] + _backend_targets,
                                   cwd=os.path.join(export, "backend"), capture_output=True, timeout=1800, env=_env) if _backend_targets else None
            run["requested"] = tests
            run["collect_exit"] = p_col.returncode
            run["collect_stdout_tail"] = p_col.stdout.decode("utf-8", "replace").strip().splitlines()[-3:]
            run["test_exit"] = p_run.returncode if p_run else 0
            run["summary"] = ([l for l in (p_run.stdout.decode("utf-8", "replace").splitlines() if p_run else [])
                               if ("passed" in l or "failed" in l or "error" in l)][-3:]
                              or (["no backend-relative targets in this request"] if not p_run else []))
            # A lane's test may live outside backend/tests (ORD-0334 put its witness in
            # `agent-mcp/tests/test_client_error_detail.py`).  Names containing "/" are repo-root-relative and
            # run from the export root; without this split the door reads pytest rc 4 ("no tests ran") and
            # refuses a candidate whose evidence is simply in another package.
            rooted = [t for t in tests if "/" in t]
            if rooted:
                p_rt = subprocess.run([VENV_PY, "-m", "pytest", "-p", "no:cacheprovider", "-q"] + rooted,
                                      cwd=export, capture_output=True, timeout=1800, env=_env)
                rt_out = p_rt.stdout.decode("utf-8", "replace")
                run["rooted_tests"] = {"paths": rooted, "exit": p_rt.returncode,
                                       "summary": [l for l in rt_out.splitlines()
                                                   if ("passed" in l or "failed" in l or "error" in l)][-3:]}
                if p_rt.returncode:
                    run["test_exit"] = p_rt.returncode
                    run["summary"] = run["rooted_tests"]["summary"]
        # WHOLE-SUITE COLLECTION ARM.  Why this exists: a candidate that carries one unimportable test file
        # makes pytest abort during collection of the whole tree, so the suite reports a tidy summary for the
        # files I named while ZERO of the rest ever ran.  Per-file collection cannot see it.  The export is the
        # FULL tree (git archive <candidate>), which also means scripts/ is present - a partial export is its
        # own flavour of the same lie (see evidence/cmdr-harness-suite-check/suite_check_r1.json).
        if a.suite_collect == "on":
            env = dict(os.environ, PYTHONPATH=export)
            p_w = subprocess.run([VENV_PY, "-m", "pytest", "--collect-only", "-q", "tests"],
                                 cwd=os.path.join(export, "backend"), capture_output=True, timeout=900, env=env)
            w_out = p_w.stdout.decode("utf-8", "replace") + p_w.stderr.decode("utf-8", "replace")
            nums = re.findall(r"(\d+) tests? collected", w_out)
            run["whole_suite"] = {"collect_exit": p_w.returncode,
                                  "collected": int(nums[-1]) if nums else None,
                                  "interrupted": "Interrupted" in w_out,
                                  "error_lines": [l for l in w_out.splitlines()
                                                  if "error" in l.lower()][-3:],
                                  "tail": [l for l in w_out.strip().splitlines() if l.strip()][-3:],
                                  "cmd": "%s -m pytest --collect-only -q tests  (cwd=<export>/backend, "
                                         "PYTHONPATH=<export>)" % VENV_PY}
        try:
            run["interpreter"] = subprocess.run([VENV_PY, "-VV"], capture_output=True, timeout=60,
                                                text=True).stdout.strip().splitlines()[0]
        except Exception:  # noqa: BLE001
            run["interpreter"] = "NOT_READ"

    # EXPOSURE NO-GROW ARM.  Why this belongs on the door and not in my memory: every frontend order this
    # shift had to be measured against the Q64 ruler by hand (tip vs merged), and a hand step is the step
    # that gets skipped at 04:00.  Cells may disappear (that is the point of the orders) but a NEW cell on
    # the authoritative line is a ruling question, so the door asks it before the line moves.
    fe_cand = [f for f in pf if f.startswith("frontend/src")]
    if a.exposure_arm == "on" and fe_cand:
        run["exposure"] = {"ruler_blob": EXPOSURE_RULER_BLOB,
                       "ruler_blob_computed": os.environ.get("CNX_EXPOSURE_RULER_COMPUTED"),
                       "ruler_file": EXPOSURE_RULER,
                           "candidate_files_in_view": len(fe_cand)}
        try:
            cells_tip = exposure_cells(tip, "exp_tip_%s" % stamp)
            cells_cand = exposure_cells(cand, "exp_cand_%s" % stamp)
            added = sorted(cells_cand - cells_tip)
            removed = sorted(cells_tip - cells_cand)
            # Refuse on GROWTH BY (file, rule), not on a changed line: an unrelated edit above a flagged
            # sink shifts its line number, and refusing that would teach lanes to fear touching the file.
            # The selftest keeps both cases: a reintroduced sink in a zero-cell file must fire, and the
            # same number of cells at moved lines must not.
            ct, cc = exposure_counts(cells_tip), exposure_counts(cells_cand)
            growth = {k: cc[k] - ct.get(k, 0) for k in cc if cc[k] > ct.get(k, 0)}
            # E's judgement on the first version was "it will miss things", and it is right twice over, so
            # this block states what it does NOT do.  (file, rule) count growth catches a cell appearing
            # under a key the tip does not have.  It cannot catch "one cell swapped for another under the
            # same key": same counts, different sink.  I tried to close that by pairing line-exact adds
            # with line-exact removes; `pair_added` is provably a subset of the count test (if every key's
            # count fails to grow, every add has a partner), so it adds no teeth - it stays only as a
            # readable diagnostic.  The real fix is cell identity in the ruler, which is ORD-0354/S4's r7
            # job, not something the door can invent.  See `disclosed_slip` in the receipt.
            unpaired = pair_added(added, removed)
            run["exposure"].update({"tip_cells": len(cells_tip), "cand_cells": len(cells_cand),
                                    "growth_by_file_and_rule": growth, "unpaired_added": unpaired,
                                    "added_line_exact": added,
                                    "shifted_only": (bool(added) and not growth and not unpaired),
                                    "removed_count": len(removed), "removed": removed[:12],
                                    "disclosed_slip": "a same-file, same-rule relocation with equal counts "
                                                     "reads as a shift; the AST ruler has no cell identity"})
            if growth or unpaired:
                problems.append("candidate grows Q64 exposure by %s over the tip - that is a ruling "
                                "question (Q64/Q67/Q70/Q71), not a landing"
                                % json.dumps(growth, ensure_ascii=False)[:300])
        except Exception as e:  # noqa: BLE001
            run["exposure"]["error"] = "%s: %s" % (type(e).__name__, str(e)[:300])
            problems.append("exposure arm never measured (instrument failed) - refusing blind")
    else:
        run["exposure"] = {"skipped": ("no frontend/src file changed" if fe_cand == [] else "arm off")}

    if rc_mb != 0:
        problems.append("no merge-base between tip and candidate")
    # THE dangerous case, caught by smoke-testing this tool against a candidate that is BEHIND the line:
    # ff impossible means a PATCH force=false would be rejected - but if this tool ever said READY and a
    # later caller flipped force, the line would be rewound. Refuse here, loudly.
    if rc_anc != 0:
        problems.append("candidate is NOT a descendant of the tip (merge-base --is-ancestor rc=%d) - landing it "
                        "would move the authoritative line backwards" % rc_anc)
    if behind:
        problems.append("candidate misses %d commit(s) the line already has - ask the lane to re-cut onto the tip" % behind)
    if ahead == 0:
        problems.append("candidate adds nothing over the tip (ahead=0) - there is nothing to land")
    if inter:
        problems.append("file intersection with the line is non-empty: %s" % ", ".join(inter[:5]))
    if mt_lines and mt_out.strip() != "" and "CONFLICT" in mt_out:
        problems.append("merge-tree reports CONFLICT")
    if tests and (run["collect_exit"] != 0 or run["test_exit"] != 0):
        problems.append("gate run not green (collect rc=%s test rc=%s)" % (run["collect_exit"], run["test_exit"]))
    if tests and not run["summary"]:
        problems.append("gate run produced no summary line - instrument did not measure")
    ws = run.get("whole_suite")
    if a.suite_collect == "on" and not ws:
        problems.append("suite collection never measured (arm requested but no reading) - refusing blind")
    if ws and ws["collect_exit"] != 0:
        problems.append("whole-suite collection exit=%s on the candidate tree: %s"
                        % (ws["collect_exit"], " | ".join(ws["error_lines"])[:200]))
    if ws and ws["interrupted"]:
        problems.append("whole-suite collection says Interrupted - the suite would execute ZERO tests "
                        "if this landed")
    if ws and not ws["collected"]:
        problems.append("whole-suite collection collected nothing measurable (collected=%s)" % ws["collected"])
    verdict = "READY_TO_LAND" if not problems else "REFUSED"

    result = {
        "schema": "CNX_CMDR_LANDING_PREFLIGHT_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "mode": "LAND" if a.land else "DRY_RUN",
        "authoritative_line": LINE,
        "tip_re_read_from_github_before": tip,
        "candidate_ref": a.candidate_ref, "candidate_tip": cand,
        "genealogy": {"ff_possible_rc": rc_anc, "ff_possible": rc_anc == 0, "merge_base": base if rc_mb == 0 else None,
                      "line_only_commits": behind, "candidate_only_commits": ahead},
        "file_sets": {"line_side_since_base": lf, "candidate_side_since_base": cf, "intersection": inter,
                      "product_introduced_by_candidate": pf},
        "merge_tree": {"exit": rc_mt, "first_line": mt_lines[0] if mt_lines else None,
                       "conflict_reported": "CONFLICT" in mt_out, "stderr_head": (mt_err or "")[:200]},
        "gate_run": run,
        "problems": problems,
        "verdict": verdict,
        "landing": None,
        "discipline": {"evidence_paths_overwritten": 0, "databases_opened": 0, "surfaces_started_or_stopped": 0,
                       "credential_values_printed": 0, "candidate_refs_pushed_by_commander": 0},
        "claim_kind": "git_and_pytest_determined",
        "claimed_result": None, "derived_result": None,
    }
    if a.land and verdict == "READY_TO_LAND":
        tip_now = ref_sha(LINE)
        if tip_now != tip:
            result["landing"] = {"decision": "ABORT_TIP_MOVED", "expected": tip, "found": tip_now}
        else:
            st, body = gh("/repos/%s/git/refs/heads/%s" % (PROJ, urllib.parse.quote(LINE, safe="")),
                          method="PATCH", payload={"sha": cand, "force": False})
            after = ref_sha(LINE)
            br = gh("/repos/%s/branches/%s" % (PROJ, urllib.parse.quote(LINE, safe="")))
            result["landing"] = {"http": st, "response_head": str(body)[:200], "tip_after": after,
                                 "branches_route": br[1]["commit"]["sha"] if br[0] == 200 else str(br[1])[:120],
                                 "both_routes_agree": (br[0] == 200 and br[1]["commit"]["sha"] == after),
                                 "landed": after == cand}
            if result["gate_run"]["export"]:
                shutil.rmtree(result["gate_run"]["export"], ignore_errors=True)
    elif verdict == "READY_TO_LAND":
        result["claimed_result"] = ("dry run: candidate %s is ff-able onto %s, intersection %d, gate %s" % (
            cand[:10], tip[:10], len(inter), json.dumps(run["summary"], ensure_ascii=False)))
    else:
        result["claimed_result"] = "refused: " + " | ".join(problems)
    txt = json.dumps(result, ensure_ascii=False, indent=1)
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(txt)
    print("verdict=%s mode=%s tip=%s cand=%s ff=%s ahead=%s behind=%s intersection=%d" % (
        verdict, result["mode"], tip[:10], cand[:10], rc_anc == 0, ahead, behind, len(inter)))
    print("product introduced:", ", ".join(pf) if pf else "(none)")
    print("gate:", json.dumps({"collect_exit": run["collect_exit"], "test_exit": run["test_exit"],
                               "summary": run["summary"], "blob_equality_all":
                                   all(e["equal"] for e in run["blob_equality"]) if run["blob_equality"] else None},
                              ensure_ascii=False))
    if result["landing"]:
        print("landing:", json.dumps(result["landing"], ensure_ascii=False))
    # A run leaves a full archive of the candidate tree (~213 MB) plus two ruler exports behind.  It is
    # all re-creatable from the commit this receipt names, so the door sweeps it unless asked not to; a
    # previous shift filled the disk because a tool wrote scratch and never took it back.  Junctions go
    # first with bare rmdir - a recursive delete through a node_modules junction eats the real one.
    if a.keep_export != "on":
        sweeps = []
        if run.get("export"):
            sweeps.append(run["export"])
        # the ruler's two exports are named by this run's stamp; they are small but they are mine, and
        # "small" is how a thousand of them become a full disk
        for pat in ("exp_tip_", "exp_cand_"):
            base = r"D:/moodle/_qoder_cmdr_ref_20260921"
            for d in os.listdir(base):
                if d.startswith(pat + stamp):
                    sweeps.append(os.path.join(base, d))
        swept = []
        for path in [x for x in sweeps if x]:
            nm = os.path.join(path, "frontend", "node_modules")
            if os.path.isdir(nm):
                subprocess.run(["cmd", "/c", "rmdir", nm.replace("/", chr(92))], timeout=300)
            if os.path.isdir(nm):
                print("NOT swept (junction survived rmdir), leaving in place:", path)
                continue
            rr = subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", path.replace("/", chr(92))], timeout=900)
            if rr.returncode == 0 and not os.path.exists(path):
                swept.append(os.path.basename(path))
        print("scratch swept:", ", ".join(swept) if swept else "(nothing to sweep)")
    print("receipt=%s (%d B) -> publish with %s --local %s --path evidence/cmdr-landing-<order>-<hhmm>/preflight_r1.json" % (
        out_path, len(txt.encode("utf-8")), GATE_PUBLISHER, out_path))
    return 0 if verdict == "READY_TO_LAND" else 5


if __name__ == "__main__":
    sys.exit(main())
