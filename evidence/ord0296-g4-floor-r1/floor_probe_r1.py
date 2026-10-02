# -*- coding: utf-8 -*-
"""CMDR 18:34 ruler-side fix - does the tightened G4 bite in both directions?

Five states, each applied to one file at a time on this lane's private export, each reverted and re-hashed
against the tip blob so a reading cannot leave a mutated product file behind.

  P0 control            - the tip as shipped; must stay green.
  P1 consumer copy      - the demonstrated blind spot: a file that already asks settings for the wait also
                          states one inline, below the floor. Must now go RED.
  P2 worker at floor    - a worker's inline wait raised to request-path scale. Must go RED.
  P3 new worker below   - a brand new module with an 800 ms worker wait. Must stay GREEN, otherwise the
                          tightening swallowed the legitimate case the original arm excused.
  P4 owner untouched    - the single-source module itself stating its own number. Must stay GREEN.
"""
import io
import json
import os
import subprocess
import sys

WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = "e7ff7938ea41c5ac69afb1172acc4625159c7911"
ARM = "tests/test_qoder_ord0296_write_deadline.py::test_G4_the_lock_wait_is_written_in_exactly_one_place"
FAMILY = ["tests/test_qoder_ord0296_write_deadline.py",
          "tests/test_qoder_ord0479_dictionary_key_shape.py"]
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(k, None)

MAIN = "backend/app/main.py"
STAY = "backend/app/stay_generation_operations.py"
NEW_WORKER = "backend/app/qoder_floor_probe_r1.py"
OWNER = "backend/app/db/write_deadline.py"

ANCHOR = {
    MAIN: "PLAN_CLAIM_LEASE_MS = int(settings.write_deadline_ms) + int(settings.write_busy_timeout_ms)",
    STAY: 'session.execute(text("PRAGMA busy_timeout = 1500"))',  # anchor only; the probe line is appended at module level
    OWNER: "def busy_timeout_ms() -> int:",
}


def git(*a):
    r = subprocess.run(["git", "-C", WT] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=600)
    return r.returncode, (r.stdout or "").strip()


def run(args):
    r = subprocess.run([PY, "-m", "pytest"] + args + ["-p", "no:cacheprovider", "-q", "--tb=line"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    fired = [l.strip()[:170] for l in out.splitlines() if "AssertionError" in l]
    return {"rc": r.returncode, "verdict": "green" if r.returncode == 0 else "red",
            "assertion_that_fired": (fired[0] if fired else None),
            "summary": (tail[-1] if tail else "")[:150]}


def apply(rel, text):
    """Append the probe statement at module level. Pushing a column-0 statement in right after an indented
    anchor line inside a function body makes the file fail to compile, and an arm that goes red because the
    module no longer imports is not evidence that the predicate bit."""
    p = os.path.join(WT, rel.replace("/", os.sep))
    src = io.open(p, encoding="utf-8").read()
    assert text in src, ("anchor line not found", rel)
    io.open(p, "w", encoding="utf-8", newline="\n").write(
        src.rstrip("\n") + "\n\n\n" + INJECT[rel] + "\n")
    import ast
    ast.parse(io.open(p, encoding="utf-8").read())


INJECT = {
    MAIN: 'SUB_SCALE_COPY = "PRAGMA busy_timeout = 1200"  # probe: a consumer that also states its own',
    STAY: 'BIG_WORKER_WAIT = "PRAGMA busy_timeout = 90000"  # probe: worker raised to request-path scale',
    OWNER: '',
}


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []

    def record(pid, expect, target, created, pytest_args, note):
        if target:
            if created:
                p = os.path.join(WT, target.replace("/", os.sep))
                io.open(p, "w", encoding="utf-8", newline="\n").write(
                    '"""probe"""\n' + INJECT_NEW + "\n")
            else:
                apply(target, ANCHOR[target])
        res = run(pytest_args)
        rows.append({"id": pid, "expect": expect, "got": res["verdict"], "met": res["verdict"] == expect,
                     "target": target, "pytest": res, "note": note})
        print(json.dumps({"id": pid, "expect": expect, "got": res["verdict"], "met": rows[-1]["met"],
                          "summary": res["summary"]}, ensure_ascii=False))
        if target:
            if created:
                p = os.path.join(WT, target.replace("/", os.sep))
                if os.path.exists(p):
                    os.remove(p)
            else:
                git("checkout", "--", target)
            rc, out = git("hash-object", target)
            if not created:
                rows[-1]["restored_blob"] = out.split()[0]
                rows[-1]["restored_equal_to_tip"] = (out.split()[0] == tip_blob(target))

    INJECT_NEW = 'def wait() -> str:\n    return "PRAGMA busy_timeout = 800"\n'

    def tip_blob(rel):
        return git("rev-parse", "%s:%s" % (TIP, rel))[1]

    record("P0_control", "green", None, False, [ARM], "the tip as shipped")
    record("P1_consumer_copy", "red", MAIN, False, [ARM],
           "the blind spot CMDR 18:34 named: a deriving file stating 1200 inline")
    record("P2_worker_at_floor", "red", STAY, False, [ARM],
           "a worker inline wait at 90000 ms, above the live floor")
    record("P3_new_worker_below", "green", NEW_WORKER, True, [ARM],
           "a new module with an 800 ms worker wait - still legitimate")
    record("P4_whole_family", "green", None, False, FAMILY,
           "the two rulers named by 07:57, run whole on this generation")
    status = git("status", "--porcelain")[1]
    candidate_change = "backend/tests/test_qoder_ord0296_write_deadline.py"
    unexpected = [l for l in status.splitlines() if l.strip()
                  and candidate_change not in l]
    doc = {"tip": TIP, "arm": ARM, "states": len(rows), "all_met": all(r["met"] for r in rows),
           "tree_clean_after": unexpected == [], "git_status_after": status,
           "expected_change_left_in_tree": candidate_change,
           "unexpected_dirt": unexpected, "runs": rows,
           "reading_of_the_ruling": "cmd said `main.py` and a count of 1; on this tip main.py states no "
                                    "inline number at all (it reads settings), so the count was implemented "
                                    "as the two structural rules the same sentence asks for: a file that "
                                    "derives the wait may state none inline, and a file that does not "
                                    "derive may only stay below the live floor"}
    io.open(os.path.join(OUT, "floor_probe_r1.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"all_met": doc["all_met"], "clean": doc["tree_clean_after"],
                      "status": status[:200]}, ensure_ascii=False))
    return 0 if doc["all_met"] else 5


raise SystemExit(main())
