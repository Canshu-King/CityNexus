"""Run the demo door under three environment arms and report which gate actually refuses.

The product's own classroom gate (backend/app/demo_access.py:14) reads environment values, so the
suite's DEMO_DATABASE_NOT_ISOLATED reds might be an environment-setup fact rather than a product
defect.  Three arms separate the two:

  A  exactly how the suite runs today (nothing declared),
  B  only the environment changed: the test database is declared externally and mirrored into
     CITYNEXUS_DEMO_DATABASE_PATH with CITYNEXUS_DEMO_MODE=true,
  C  arm B plus a configured presenter key.

What this refuses to do:
  * call an environment change a repair -- every row that fails in all repetitions of arm A must
    still fail in arms B and C, otherwise the run aborts;
  * treat a timing-sensitive row as a cause -- rows whose result varies between repetitions are
    reported with their ratio and excluded from the stable set, because two catalogue-hydration
    threading rows were measured failing in only some runs, in arms with and without the key.
Nothing outside the environment changes: no file is edited, the database is a throwaway path under
backend/.cmdr_demo_iso, and the presenter key the arms set is a filler string, never a real secret.
"""

import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BACKEND = os.path.join(ROOT, "backend")
ISO_DIR = os.path.join(BACKEND, ".cmdr_demo_iso")
DB_PATH = os.path.join(ISO_DIR, "gate_arms.db").replace("\\", "/")
TARGETS = ["tests/test_qoder_simulation_mode.py", "tests/test_qoder_catalog_hydration.py"]
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero", "bw223-demo-gate-arms.txt")
PYTHON = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
DECLARED = {
    "CITYNEXUS_DATABASE_URL": "sqlite:///" + DB_PATH,
    "CITYNEXUS_DEMO_DATABASE_PATH": DB_PATH,
    "CITYNEXUS_DEMO_MODE": "true",
}
CLEAR = ("CITYNEXUS_DATABASE_URL", "CITYNEXUS_DEMO_DATABASE_PATH",
         "CITYNEXUS_DEMO_MODE", "CITYNEXUS_DEMO_PRESENTER_KEY")
ARMS = (
    ("A_suite_default", {}),
    ("B_declared_isolation", dict(DECLARED)),
    ("C_declared_plus_presenter_key", dict(DECLARED, CITYNEXUS_DEMO_PRESENTER_KEY="q" * 40)),
)
REPS = 3


def run_arm(extra_env):
    os.makedirs(ISO_DIR, exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    env = dict(os.environ)
    for name in CLEAR:
        env.pop(name, None)
    env.update(extra_env)
    env["MSYS2_ARG_CONV_EXCL"] = "*"
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [PYTHON, "-m", "pytest", "-q", "-p", "no:warnings", "--tb=line"] + TARGETS,
        cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=900,
    )
    out = result.stdout or ""
    summary = re.search(r"(\d+) failed, (\d+) passed", out)
    names = set(re.findall(r"^FAILED \S+::(\w+)", out, re.M))
    seconds = re.search(r"in ([\d.]+)s", out)
    return {
        "failed": int(summary.group(1)) if summary else None,
        "passed": int(summary.group(2)) if summary else None,
        "refusals": sorted(set(re.findall(r"DEMO_[A-Z_]+", out))),
        "names": names,
        "seconds": float(seconds.group(1)) if seconds else None,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arms = {name: [run_arm(extra) for _ in range(REPS)] for name, extra in ARMS}

    stable_a = set.intersection(*(rep["names"] for rep in arms["A_suite_default"]))
    if not stable_a:
        print("ABORT arm A produced no row that failed in every repetition; nothing to compare")
        return 6
    for name in ("B_declared_isolation", "C_declared_plus_presenter_key"):
        for rep in arms[name]:
            repaired = stable_a - rep["names"]
            if repaired:
                print(
                    "ABORT arm %s made %s pass without any code change -- refusing to publish an"
                    " environment trick as a repair" % (name, sorted(repaired))
                )
                return 7

    b_refusals = set().union(*(set(rep["refusals"]) for rep in arms["B_declared_isolation"]))
    a_refusals = set().union(*(set(rep["refusals"]) for rep in arms["A_suite_default"]))
    if "DEMO_DATABASE_NOT_ISOLATED" not in a_refusals:
        print("ABORT arm A did not reproduce the isolation refusal the census reports")
        return 8
    if "DEMO_DATABASE_NOT_ISOLATED" in b_refusals or "DEMO_PRESENTER_REQUIRED" not in b_refusals:
        print("ABORT arm B did not move the refusal to the presenter gate; the declared path did not take")
        return 9

    counts = {name: [rep["failed"] for rep in reps] for name, reps in arms.items()}
    varying = sorted(
        row for row in set().union(*(rep["names"] for reps in arms.values() for rep in reps))
        if row not in stable_a
    )
    ratio = {}
    for row in varying:
        hits = sum(1 for reps in arms.values() for rep in reps if row in rep["names"])
        ratio[row] = "%d/%d" % (hits, REPS * len(ARMS))

    lines = [
        "DEMO GATE THREE-ARM MEASUREMENT bw223",
        "TARGETS %s" % " ".join(TARGETS),
        "REPS_PER_ARM %d" % REPS,
        "STABLE_CORE_ROWS %d failing in every repetition of arm A: %s"
        % (len(stable_a), " ".join(sorted(stable_a))),
        "ARM_A refusal=%s counts=%s" % (",".join(sorted(a_refusals)), counts["A_suite_default"]),
        "ARM_B refusal=%s counts=%s (only environment changed: declared DB mirrored into"
        " CITYNEXUS_DEMO_DATABASE_PATH + CITYNEXUS_DEMO_MODE)"
        % (",".join(sorted(b_refusals)), counts["B_declared_isolation"]),
        "ARM_C refusal=%s counts=%s (arm B plus a 40-character filler presenter key)"
        % (",".join(sorted(set().union(*(set(r["refusals"]) for r in arms["C_declared_plus_presenter_key"])))),
           counts["C_declared_plus_presenter_key"]),
        "NOTHING_REPAIRED_BY_ENVIRONMENT enforced above: no stable core row turned green in arms B or C",
        "TIMING_SENSITIVE_ROWS %s" % json.dumps(ratio, sort_keys=True),
        "GATE_READ app/demo_access.py:14 needs settings.demo_mode plus an absolute declared path"
        " equal to the bound database; app/demo_access.py:36 then needs either the presenter header"
        " or a signed traveler bound to that database",
        "PRODUCT_BYTES_CHANGED 0 -- the arms differ only by environment variables; the key set in"
        " arm C is a filler string, never a credential",
    ]
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
