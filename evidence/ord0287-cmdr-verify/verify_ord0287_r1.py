"""Commander first-hand verification of ORD-0287 (lane F commit c31ba195): streak + one-carrier kill.

Every verdict below is DERIVED from parsed junit outcomes -- nothing here can print a literal PASS.
Runs only inside my snap export; the mutation is applied to the snap copy and restored, and the
restore is proved by re-hashing the file.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SNAP = r"D:/moodle/_qoder_snap_0287_0805/backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TEST = "tests/test_qoder_ord0287_k8_carrier.py"
MAIN = os.path.join(SNAP, "app", "main.py")
GUARD_LINE = "IdempotencyKey.response_json.is_(None)"
RUNS = 3
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts", "ord0287_verify_commander.json")


def sha(path):
    raw = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


def guard_hits(path=MAIN):
    src = open(path, encoding="utf-8").read()
    return src.count(GUARD_LINE)


def run_pytest(tag):
    xmlp = os.path.join(SNAP, "_junit_%s.xml" % tag)
    if os.path.exists(xmlp):
        os.remove(xmlp)
    cmd = [PY, "-m", "pytest", TEST, "-q", "--no-header", "-p", "no:cacheprovider",
           "--tb=line", "--junitxml", xmlp]
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=SNAP, capture_output=True, text=True, encoding="utf-8", errors="replace")
    cases = []
    if os.path.exists(xmlp):
        for tc in ET.parse(xmlp).getroot().iter("testcase"):
            outcome = "passed"
            for kind in ("failure", "error", "skipped"):
                if tc.find(kind) is not None:
                    outcome = kind
                    break
            cases.append({"nodeid": "%s::%s" % (tc.get("classname"), tc.get("name")), "outcome": outcome})
    tail = [l for l in (proc.stdout or "").splitlines() if " passed" in l or " failed" in l or "error" in l]
    return {"tag": tag, "rc": proc.returncode, "seconds": round(time.time() - t0, 1),
            "cases": cases, "summary_lines": tail[-2:], "collected": len(cases)}


def fresh_db():
    removed = []
    for name in ("citynexus.db", "citynexus.db-wal", "citynexus.db-shm"):
        p = os.path.join(SNAP, name)
        if os.path.exists(p):
            os.remove(p)
            removed.append(name)
    return removed


def mutate(on):
    src = open(MAIN, encoding="utf-8", newline="").read()
    if on:
        assert guard_hits() == 1, "expected exactly one carrier before mutation, got %d" % guard_hits()
        old = (".where(IdempotencyKey.key == key,\n"
               "                           IdempotencyKey.response_json.is_(None))")
        new = ".where(IdempotencyKey.key == key)"
        assert src.count(old) == 1, "mutation anchor hit %d times" % src.count(old)
        out = src.replace(old, new)
        assert GUARD_LINE not in out
        with open(MAIN, "w", encoding="utf-8", newline="") as f:
            f.write(out)
    else:
        shutil.copyfile(MAIN + ".cmdrbak", MAIN)
    return guard_hits()


def main():
    base_sha, base_size = sha(MAIN)
    shutil.copyfile(MAIN, MAIN + ".cmdrbak")
    report = {"order": "ORD-0287", "candidate": {"sha": "c31ba195d94a", "parent": "45b0a5e2",
                                               "file": "backend/" + TEST},
              "verified_by": "commander 494abfd7 (first-hand)",
              "snap": SNAP, "interpreter": PY,
              "main_py_before": {"sha1": base_sha, "bytes": base_size, "guard_carrier_hits": guard_hits()},
              "runs": [], "kill": None, "restore": None}

    clean = []
    for i in range(RUNS):
        removed = fresh_db()
        r = run_pytest("clean%d" % (i + 1))
        r["db_removed_before_run"] = removed
        r["all_passed"] = bool(r["collected"] > 0) and all(c["outcome"] == "passed" for c in r["cases"])
        clean.append(r)
        print("clean run", i + 1, "rc", r["rc"], "collected", r["collected"],
              "all_passed", r["all_passed"], r["summary_lines"], "%.1fs" % r["seconds"])
        for c in r["cases"]:
            print("   ", c["outcome"], c["nodeid"])

    print("--- mutation: drop the only carrier of the guard ---")
    hits_after = mutate(True)
    removed = fresh_db()
    kill = run_pytest("killed")
    kill["guard_carrier_hits_after_mutation"] = hits_after
    kill["db_removed_before_run"] = removed
    kill["survived"] = bool(kill["collected"] > 0) and all(c["outcome"] == "passed" for c in kill["cases"])
    print("kill run rc", kill["rc"], "collected", kill["collected"], "carrier hits", hits_after,
          kill["summary_lines"])
    for c in kill["cases"]:
        print("   ", c["outcome"], c["nodeid"])
    report["kill"] = kill

    hits_restored = mutate(False)
    after_sha, after_size = sha(MAIN)
    report["restore"] = {"guard_carrier_hits": hits_restored, "sha1": after_sha,
                         "identical_to_before": (after_sha == base_sha and after_size == base_size)}
    print("restore: carrier hits", hits_restored, "sha identical to pre-mutation",
          report["restore"]["identical_to_before"])

    greens = [r["all_passed"] for r in clean]
    streak = 0
    for g in greens:
        streak = streak + 1 if g else 0
    if hits_after != 0:
        # my own instrument failed to apply the mutation -- that is NOT a survivor and NOT a kill
        derived = "MUTATION_NOT_APPLIED_BY_MY_INSTRUMENT"
    elif streak != RUNS:
        derived = "STREAK_BROKEN"
    elif kill["survived"]:
        derived = "SURVIVED_GUARD_MAY_BE_REDUNDANT"
    elif not report["restore"]["identical_to_before"]:
        derived = "TREE_NOT_RESTORED_RECEIPT_VOID"
    else:
        derived = "KILLED_CANDIDATE_ALL_ROUNDS_GREEN_AND_GUARD_IS_LOAD_BEARING"
    report["clean_runs"] = clean
    report["streak_green_runs"] = streak
    report["guard_carrier_unique"] = (base_size > 0 and report["main_py_before"]["guard_carrier_hits"] == 1)
    report["claimed_result_by_lane"] = None
    report["derived_result"] = derived
    report["how_derived"] = {
        "streak": "clean runs with a fresh db each: %d/%d all_passed" % (streak, RUNS),
        "kill": "carrier hits 1 -> %d, run rc %s, every case passed? %s" % (hits_after, kill["rc"], kill["survived"]),
        "restore": "main.py re-hash identical to pre-mutation: %s" % report["restore"]["identical_to_before"],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(report, f, ensure_ascii=False, sort_keys=True, indent=1)
    print("derived_result:", derived)
    print("wrote", OUT, os.path.getsize(OUT), "B", sha(OUT)[0])
    return 0 if derived.startswith("KILLED") else 3


sys.exit(main())
