#!/usr/bin/env python3
"""ORD-0324: turn "the Hermes harness collects and runs" from luck into a gate.

The property this guards is the one that made candidate afbbf5be3256d76eac0453ab3ad8e6dd1356d7cc
unlandable: a single test module that cannot import aborts the whole pytest session
("Interrupted: N errors during collection") so ZERO tests run while a green-looking caller still
reads a summary line. Two readings are therefore mandatory and are reported separately here:
the WHOLE backend/tests collection (does the gate stay open at all) and the HARNESS run (does the
ported surface pass).

The export directory set is not cosmetic: without `scripts` the harness tests cannot resolve
`from scripts.hermes_* import ...` and the suite reports 19 collection errors with 0 executed, and
without `agent-mcp` the r4/r20 chain cannot resolve `citynexus_mcp`. This script therefore refuses any
export set that omits either one.

Usage:
  run_hermes_suite_r1.py [--ref SHA|ref] [--selftest] [--keep] [--work DIR] [--out FILE]
Exit: 0 green | 3 gate red | 4 selftest red | 7 unsafe work dir | 8 export/setup failure
"""
from __future__ import annotations

import argparse, datetime, json, os, pathlib, re, shutil, subprocess, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_DEFAULT = r"D:/moodle/CityNexus"
VENV_DEFAULT = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
BRANCH_DEFAULT = "refs/heads/mirror/integration-frontend-apple-pass1"
EXPORT_SET = ["backend", "data", "contracts", "tools", "scripts", "agent-mcp"]
# scripts: the harness tests do `from scripts.hermes_* import ...`; agent-mcp: hermes_r4_contract_probe
# resolves citynexus_mcp through its own sys.path.insert, and backend/pyproject.toml puts ../agent-mcp on
# the pytest path. Missing either one silently changes what "the suite" means, so both are asserted below.
REQUIRED_EXPORTS = ("scripts", "agent-mcp")
MUTANT_IMPORT = "import ord0324_no_such_module_zz  # injected by run_hermes_suite_r1 --selftest\n"


def sh(args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def resolve_generation(repo, ref, branch, allow_refresh=True):
    """40-hex the gate actually measures, plus an independent ls-remote reading of the live line.

    `refs/heads/mirror/...` usually exists only as a remote-tracking ref in a working clone, so a
    single rev-parse of the requested name is not enough - try the candidates and record which hit.
    """
    tail = branch[len("refs/heads/"):] if branch.startswith("refs/heads/") else branch
    live = sh(["git", "-C", repo, "ls-remote", "origin", branch])
    live_sha = live.stdout.split("\t")[0].strip() if live.returncode == 0 and live.stdout else ""
    attempts = [ref, branch, "refs/remotes/origin/" + tail, "origin/" + tail, tail]
    if re.fullmatch(r"[0-9a-f]{40}", live_sha or ""):
        attempts.append(live_sha)
    tried = []
    gen = None
    hit = ""
    for a in attempts:
        if not a or a in tried:
            continue
        tried.append(a)
        r = sh(["git", "-C", repo, "rev-parse", "--verify", a + "^{commit}"])
        if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", r.stdout.strip()):
            gen = r.stdout.strip()
            hit = a
            break
    if not gen:
        return None, ("unresolvable locally via " + " | ".join(tried) +
                      ("; live tip read from origin is %s but the object is not in this clone - "
                       "run: git fetch origin %s" % (live_sha, branch) if live_sha else
                       "; ls-remote also failed")), {}
    fetch_performed = False
    if allow_refresh and live_sha and gen != live_sha and hit != live_sha:
        # Only when the caller asked for the branch itself: refresh so a stale remote-tracking ref
        # cannot certify an old tree. An explicit --ref is never swapped for another commit.
        subprocess.run(["git", "-C", repo, "fetch", "origin", branch],
                       capture_output=True, text=True)
        fetch_performed = True
        r2 = sh(["git", "-C", repo, "rev-parse", "--verify", "refs/remotes/origin/" + tail +
                 "^{commit}"])
        if r2.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", r2.stdout.strip()):
            gen = r2.stdout.strip()
            hit = "refs/remotes/origin/" + tail + " (after fetch)"
            live = sh(["git", "-C", repo, "ls-remote", "origin", branch])
            live_sha = live.stdout.split("\t")[0].strip() if live.returncode == 0 and live.stdout else live_sha
        else:
            return None, "fetch did not produce a resolvable " + branch, {}
    ctx = {"ref_requested": ref, "resolved_via": hit, "resolved_40": gen,
           "tried": tried, "fetch_performed": fetch_performed,
           "live_branch": branch, "live_branch_sha": live_sha,
           "equals_live_branch": bool(live_sha) and gen == live_sha}
    return gen, "", ctx


def export(repo, gen, work):
    root = pathlib.Path(work)
    root.mkdir(parents=True, exist_ok=True)
    p = subprocess.Popen(["git", "-C", repo, "archive", gen] + EXPORT_SET,
                         stdout=subprocess.PIPE)
    t = subprocess.Popen(["tar", "-x", "-C", str(root)], stdin=p.stdout)
    p.stdout.close()
    trc = t.wait()
    prc = p.wait()
    files = [f for f in root.rglob("*") if f.is_file()]
    return {"git_archive_exit": prc, "tar_exit": trc, "files": len(files),
            "bytes": sum(f.stat().st_size for f in files)}


def harness_tests(root):
    d = pathlib.Path(root) / "backend" / "tests"
    return sorted(f.name for f in d.glob("test_*.py") if "hermes" in f.name.lower())


def parse(out):
    txt = out.replace("\r", "")
    def g(pat):
        m = re.search(pat, txt)
        return int(m.group(1)) if m else 0
    return {
        "collected": g(r"(\d+) tests? collected"),
        "passed": g(r"(\d+) passed"),
        "failed": g(r"(\d+) failed"),
        "skipped": g(r"(\d+) skipped"),
        "collect_errors": max(g(r"(\d+) errors? during collection"), g(r"(\d+) errors?\b")),
        "error_lines": len([l for l in txt.splitlines() if l.startswith("ERROR ")]),
        "interrupted": "Interrupted:" in txt,
        "wallclock": (re.search(r"in (\d+\.\d+)s", txt.strip().splitlines()[-1]).group(1) + " s")
                      if txt.strip() and re.search(r"in (\d+\.\d+)s", txt.strip().splitlines()[-1]) else "n/a",
        "error_modules": sorted({l.split("::")[0].split(" ")[-1].split("\\")[-1].split("/")[-1]
                                 for l in txt.splitlines() if l.startswith("ERROR ")}),
    }


def run_pytest(root, py, args, files=None):
    cwd = pathlib.Path(root) / "backend"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root)
    cmd = [py, "-X", "utf8", "-m", "pytest", "-q"] + args + (files or [])
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
    res = parse(r.stdout + "\n" + r.stderr)
    res["exit"] = r.returncode
    res["argv"] = " ".join(["pytest"] + args + (files or []))
    return res


def arms(root, py, tests):
    whole = run_pytest(root, py, ["--collect-only", "tests"])
    hc = run_pytest(root, py, ["--collect-only"] + ["tests/" + t for t in tests])
    hr = run_pytest(root, py, [], ["tests/" + t for t in tests])
    return {"whole_backend_tests_collect": whole, "harness_collect": hc, "harness_run": hr}


def checks_of(a, tests_n):
    w, hc, hr = a["whole_backend_tests_collect"], a["harness_collect"], a["harness_run"]
    return {
        "harness_files_discovered": tests_n > 0,
        "whole_suite_collection_not_interrupted": w["exit"] == 0 and w["collect_errors"] == 0
            and w["error_lines"] == 0 and not w["interrupted"],
        "whole_suite_collected_positive": w["collected"] > 0,
        "harness_collected_positive_with_zero_errors": hc["collected"] > 0 and hc["collect_errors"] == 0
            and hc["error_lines"] == 0,
        "harness_passed_with_zero_failures": hr["exit"] == 0 and hr["failed"] == 0
            and hr["collect_errors"] == 0 and hr["passed"] > 0,
        "harness_run_executed_every_collected_test": hr["passed"] == hc["collected"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--branch", default=BRANCH_DEFAULT)
    ap.add_argument("--venv", default=VENV_DEFAULT)
    ap.add_argument("--work", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    repo = str(pathlib.Path(args.repo).resolve())
    py = args.venv
    ver = sh([py, "-V"])
    interpreter = (py + " (" + ver.stdout.strip() + ")") if ver.returncode == 0 else py + " UNVERIFIED"

    ref = args.ref or args.branch
    gen, err, ctx = resolve_generation(repo, ref, args.branch, allow_refresh=(args.ref is None))
    if not gen:
        print("SETUP FAIL:", err)
        return 8
    if args.ref is None and ctx.get("equals_live_branch") is not True:
        print("SETUP FAIL: asked for the live line but origin says", ctx.get("live_branch_sha"),
              "and this clone yields", gen, "- refusing to certify a stale tree")
        return 8

    porc_before = sh(["git", "-C", repo, "status", "--porcelain", "backend", "data",
                      "contracts", "tools", "scripts", "agent-mcp"])
    porc_before_list = [l for l in porc_before.stdout.split("\n") if l]

    work = args.work or str(pathlib.Path(r"D:/moodle") / ("_ord0324_gate_" +
                                datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    workp = pathlib.Path(work).resolve()
    if str(workp).lower().startswith(repo.lower()):
        print("UNSAFE: work dir", workp, "is inside the repo", repo, "- refusing")
        return 7
    exp = export(repo, gen, workp)
    if exp["git_archive_exit"] != 0 or exp["tar_exit"] != 0 or exp["files"] == 0:
        print("EXPORT FAIL", json.dumps(exp))
        return 8
    missing = [r for r in REQUIRED_EXPORTS if r not in [p.name for p in workp.iterdir()]]
    if missing:
        print("EXPORT FAIL: missing from the export set: " + ", ".join(missing)
              + " - suite numbers would be void")
        return 8

    tests = harness_tests(workp)
    a = arms(workp, py, tests)
    ck = checks_of(a, len(tests))
    green = all(ck.values())
    verdict = ("HERMES_GATE_GREEN whole_collected=%d harness_collected=%d harness_passed=%d" %
               (a["whole_backend_tests_collect"]["collected"], a["harness_collect"]["collected"],
                a["harness_run"]["passed"])) if green else \
              "HERMES_GATE_RED " + ",".join(sorted(k for k, v in ck.items() if not v))

    st = None
    if args.selftest:
        # (a) positive: the tree as exported must be green -> already established by `ck`
        pos = {"expect": "green", "observed": green, "checks": ck}
        # (b) negative: break ONE collected file in the throwaway copy; the gate must go red
        victim = pathlib.Path(workp) / "backend" / "tests" / tests[0]
        original = victim.read_bytes()
        victim.write_bytes(MUTANT_IMPORT.encode("ascii") + original)
        ma = arms(workp, py, tests)
        mck = checks_of(ma, len(tests))
        neg = {
            "mutant_file": "backend/tests/" + tests[0],
            "injected": MUTANT_IMPORT.strip(),
            "restored_ok": True,
            "expect": "collect_errors>=1 and non-zero exit",
            "whole_collect_errors": ma["whole_backend_tests_collect"]["collect_errors"],
            "harness_collect_errors": ma["harness_collect"]["collect_errors"],
            "harness_run_exit": ma["harness_run"]["exit"],
            "harness_passed_after_mutation": ma["harness_run"]["passed"],
            "executed_tests_after_mutation": ma["harness_run"]["passed"] + ma["harness_run"]["failed"],
        }
        neg["passed_negative"] = (neg["whole_collect_errors"] >= 1 and neg["harness_collect_errors"] >= 1
                                  and neg["harness_run_exit"] != 0)
        victim.write_bytes(original)  # restore inside the throwaway copy, never the repo
        ra = arms(workp, py, tests)
        rck = checks_of(ra, len(tests))
        post = {"observed_green": all(rck.values()),
                "whole_collected_after_restore": ra["whole_backend_tests_collect"]["collected"],
                "note": "same tree, same session: proves the red belonged to the injected import "
                        "and not to drift in the export"}
        st = {"positive_current_tree": pos, "negative_mutated_copy": neg, "post_restore_control": post}

    gone = None
    if not args.keep:
        shutil.rmtree(workp, ignore_errors=True)
        gone = not workp.exists()

    porc = sh(["git", "-C", repo, "status", "--porcelain", "backend", "data",
               "contracts", "tools", "scripts", "agent-mcp"])
    porc_list = [l for l in porc.stdout.split("\n") if l]
    selftest_ok = True if st is None else bool(
        st["positive_current_tree"]["observed"]
        and st["negative_mutated_copy"]["passed_negative"]
        and st["post_restore_control"]["observed_green"])
    code = 4 if (st is not None and not selftest_ok) else (0 if green else 3)
    out = args.out or str(pathlib.Path(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks") /
                          "_ord0324_gate_receipt.json")
    now = datetime.datetime.now().astimezone()
    rec = {
        "schema": "CNX_ORD0324_HERMES_SUITE_GATE_V1",
        "at_local": now.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "generation": gen,
        "generation_context": ctx,
        "interpreter": interpreter,
        "repo": repo,
        "export_set": EXPORT_SET,
        "export_receipt": exp,
        "work_dir": str(workp).replace("\\", "/"),
        "work_dir_removed": gone,
        "hardlink_or_junction_used": False,
        "harness_test_files_discovered": len(tests),
        "harness_test_files": tests,
        "arms": a,
        "collected": a["harness_collect"]["collected"],
        "collect_errors": a["harness_collect"]["collect_errors"],
        "whole_suite_collected": a["whole_backend_tests_collect"]["collected"],
        "whole_suite_collect_errors": a["whole_backend_tests_collect"]["collect_errors"],
        "passed": a["harness_run"]["passed"],
        "failed": a["harness_run"]["failed"],
        "checks": ck,
        "verdict": verdict,
        "verdict_derivation": "verdict is computed from the arm readings above: green only when every "
            "key in checks is true, and the string embeds the three measured counts; a red run names the "
            "failing checks rather than printing a fixed token",
        "selftest": st,
        "repo_write_attempted": 0,
        "repo_porcelain_after": porc_list,
        "refs_pushed": 0,
        "selftest_ok": selftest_ok,
        "repo_porcelain_unchanged": porc_list == porc_before_list,
        "repo_porcelain_before": porc_before_list,
        "exit_code": code,
    }
    pathlib.Path(out).write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8",
                                 newline="\n")
    print("generation", gen, "| equals live tip:", ctx.get("equals_live_branch"))
    print("harness files", len(tests), "| whole collected", rec["whole_suite_collected"],
          "errors", rec["whole_suite_collect_errors"])
    print("harness collected", rec["collected"], "errors", rec["collect_errors"],
          "| passed", rec["passed"], "failed", rec["failed"])
    for k, v in ck.items():
        print("check", k, v)
    if st:
        print("selftest positive_green", st["positive_current_tree"]["observed"],
              "| negative gate_red", st["negative_mutated_copy"]["passed_negative"],
              "| post-restore green", st["post_restore_control"]["observed_green"],
              "| mutant whole collect_errors", st["negative_mutated_copy"]["whole_collect_errors"])
    print("work_dir_removed", gone)
    print("verdict", verdict)
    print("receipt", out)
    if st and not selftest_ok:
        print("SELFTEST FAILED positive=%s negative=%s post_restore=%s" % (
            st["positive_current_tree"]["observed"],
            st["negative_mutated_copy"]["passed_negative"],
            st["post_restore_control"]["observed_green"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
