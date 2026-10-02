"""Where does the r3/r4 flip come from? Ask the same set without my test file, on both heads.

Set = the 11 affected files minus `test_qoder_city_failure_reasons.py`, so:
  * at the delivered head the product narrowing is present but none of my new arms run;
  * at the clean tip neither is present.
If `test_qoder_ord197_four_class_receipt.py::r3/r4` flip on both sides, the flip is not produced by
my bytes; if it only flips with the narrowing in the tree, it is, and I have to fix it.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt543tip")
BACKEND = ROOT / "backend"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
HEAD = "qoder-fb549-recut"
TIP = "00b5f25e9b6b408fba8906ef3ffd49caa5eb84b9"
FILES = [f for f in pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run/fb549_affected_files.txt")
         .read_text(encoding="utf-8").split() if "city_failure_reasons" not in f]
FILES.append("tests/test_qoder_ord0531_bin_ownership.py")
WATCH = ("test_r3_an_empty_answer_proves_it_came_from_a_reply_and_not_from_an_outage",
         "test_r4_a_failed_source_is_named_retryable_and_never_becomes_no_match")
PASSES = 4


def log(*a):
    print(*a, flush=True)


def sh(args):
    return subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def main() -> int:
    log(f"set: {len(FILES)} file(s), my own city file excluded")
    results = {}
    for label, rev in (("delivered head (narrowing in, my arms out)", HEAD),
                       ("clean tip (both out)", TIP)):
        co = sh(["git", "checkout", rev])
        if co.returncode != 0:
            log("checkout failed:", (co.stdout + co.stderr)[-300:])
            return 8
        head = sh(["git", "rev-parse", "HEAD"]).stdout.strip()
        log(f"{label}: HEAD={head}")
        flips, other = [], set()
        for i in range(PASSES):
            p = subprocess.run([PY, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--no-header",
                                "--tb=no"] + FILES, cwd=str(BACKEND), capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
            reds = {line.split("::")[-1] for line in p.stdout.splitlines() if line.startswith("FAILED")}
            flips.append(tuple(sorted(n for n in reds if n in WATCH)))
            other |= reds
            last = [l for l in p.stdout.splitlines() if " passed" in l or " failed" in l]
            log(f"  pass {i+1}: {last[-1] if last else '(no summary)'}  r3/r4={flips[-1]}")
        results[label] = (flips, sorted(other))
        log(f"  -> {label}: r3/r4 per pass {flips}; union of all reds {sorted(other)}\n")
    names = {"delivered head (narrowing in, my arms out)": HEAD, "clean tip (both out)": TIP}
    flips_head = [x for x in results["delivered head (narrowing in, my arms out)"][0] if x]
    flips_tip = [x for x in results["clean tip (both out)"][0] if x]
    log(f"flip count, narrowing in the tree and my arms out: {len(flips_head)}/{PASSES} passes -> {flips_head}")
    log(f"flip count, authoritative tip with none of my bytes: {len(flips_tip)}/{PASSES} passes -> {flips_tip}")
    log("reading: the tip side is measured on the authoritative head with neither my product change nor my "
          "test file in the tree. If it flips there, the flip is not produced by these bytes; if only the "
          "head side flips, it is mine and gets fixed. Both counts and node names are printed, no inference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
