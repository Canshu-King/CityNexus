"""ORD-0500 CE-1 -- take the door's own 409 predicate out and show which arms still say green.

Two runs, one command shape, differing only in the tree:
  candidate  = the bytes this lane delivers (`wt6`)
  mutant     = a throwaway copy (`mutgen4`) whose duplicate lookup in `create_journey_checkin` is
               replaced by `existing = None`, so the only thing that can refuse a replayed tap is the
               `UNIQUE (journey_id, target_key)` index -- which answers the same 409, the same
               reason_code and the same `existing_stamped_at`, plus `caught_by: unique_index`.

Readings the order asks for, on both sides: collected, passed, failed, and the names of the failed
arms.  A status-only duplicate arm cannot tell those two layers apart, so it stays green on the
mutant; the arm that pins WHICH layer refused goes red.  That difference is the counter-example --
it is not a claim about what a mutation "should" do, both runs really execute.

Nothing here writes a shared store: each run gets its own `CITYNEXUS_DATABASE_URL` file, created
fresh, and the candidate's `main.py` is hashed before and after (the mutant tree is hardlinked from
it, so the hash pair is the proof the delivered bytes were never touched).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
TREES = [("candidate_wt6", "wt6"), ("mutant_wt6_ce1", "mutgen4")]
SUITES = ["tests/test_qoder_ord0500_journey_refusal.py", "tests/test_qoder_ord0476_checkins.py"]


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def run_pytest(label, tree):
    root = os.path.join(LANE, tree)
    db = os.path.join(LANE, "run", "pytest_%s.db" % label)
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(db + suffix):
            os.remove(db + suffix)
    env = {k: v for k, v in os.environ.items()
           if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY", "DEEPSEEK_API_KEY")}
    env.update({"PYTHONPATH": root, "PYTHONUTF8": "1",
                "CITYNEXUS_DATABASE_URL": "sqlite:///" + db.replace("\\", "/"),
                "CITYNEXUS_DEMO_MODE": "true", "CITYNEXUS_AI_ENABLED": "false"})
    cmd = [PY, "-X", "utf8", "-m", "pytest"] + SUITES + ["-v", "-p", "no:cacheprovider"]
    p = subprocess.run(cmd, cwd=os.path.join(root, "backend"), env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    text = p.stdout.decode("utf-8", "replace")
    log = os.path.join(LANE, "run", "gen4_ce1_pytest_%s.txt" % label)
    open(log, "w", encoding="utf-8").write(text)
    passed = re.findall(r"::([\w\.\[\]\-]+)\s+PASSED", text)
    failed = re.findall(r"::([\w\.\[\]\-]+)\s+FAILED", text)
    errored = re.findall(r"::([\w\.\[\]\-]+)\s+ERROR", text)
    collected = re.findall(r"(\d+) tests? collected", text)
    summary = [l for l in text.splitlines() if re.search(r"\d+ (passed|failed|error)", l)]
    return {"label": label, "tree": tree, "exit": p.returncode, "log": os.path.relpath(log, LANE),
            "db": os.path.relpath(db, LANE),
            "collected": collected[-1] if collected else "NOT_PARSED",
            "passed_names": passed, "failed_names": failed, "error_names": errored,
            "counts": {"passed": len(passed), "failed": len(failed), "errors": len(errored)},
            "summary_line": summary[-1].strip() if summary else text.strip().splitlines()[-1:],
            "fail_bodies": re.findall(r"=+ FAILURES =+(.{0,1400})", text, re.S)[:1]}


def main():
    out = {"tool": "gen4_ce1_r1", "took_local": datetime.now().astimezone().isoformat(),
           "candidate_main_sha256_before": sha(os.path.join(LANE, "wt6/backend/app/main.py")),
           "mutant_main_sha256": sha(os.path.join(LANE, "mutgen4/backend/app/main.py")),
           "runs": []}
    for label, tree in TREES:
        out["runs"].append(run_pytest(label, tree))
        print("%s counts=%s summary=%s" % (label, out["runs"][-1]["counts"],
                                           out["runs"][-1]["summary_line"]), flush=True)
        time.sleep(2)
    out["candidate_main_sha256_after"] = sha(os.path.join(LANE, "wt6/backend/app/main.py"))
    out["candidate_tree_untouched"] = (out["candidate_main_sha256_before"]
                                       == out["candidate_main_sha256_after"])
    # What actually differs between the delivered tree and the throwaway mutant: the arm is only a
    # counter-example if one file moved.  `mutgen4` is a hardlink copy carrying backend/ data/
    # contracts/ and frontend/src/generated (the contract arm reads the generated client too, and a
    # mutant red caused by a MISSING file is an instrument artifact, not a finding -- the first run
    # of this script produced exactly that fourth red and it is why this proof is here).
    skip = {"node_modules", ".git", "dist", "review", "run", "evidence"}
    files = {}
    for root, dirs, names in os.walk(os.path.join(LANE, "wt6")):
        dirs[:] = [d for d in dirs if d not in skip]
        for n in names:
            full = os.path.join(root, n)
            files[os.path.relpath(full, os.path.join(LANE, "wt6")).replace("\\", "/")] = full
    diff, missing = [], []
    for rel, full in sorted(files.items()):
        mate = os.path.join(LANE, "mutgen4", rel)
        if not os.path.exists(mate):
            missing.append(rel)
            continue
        if sha(full) != sha(mate):
            diff.append(rel)
    out["mutant_tree_files_differing"] = diff
    out["mutant_tree_files_absent"] = {"count": len(missing), "sample": missing[:6]}
    out["mutant_tree_file_denominator"] = len(files)
    st = subprocess.run(["git", "-C", os.path.join(LANE, "wt6"), "diff", "--cached", "--numstat"],
                        stdout=subprocess.PIPE, timeout=60).stdout.decode("utf-8", "replace")
    out["candidate_diff_vs_tip"] = [l.split("\t") for l in st.strip().splitlines()]
    path = os.path.join(LANE, "evidence", "gen4_ce1_r1.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(out, indent=2, ensure_ascii=False)[:3500])
    print("WROTE " + path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
