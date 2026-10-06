"""Counter-arms for the r8 hand, ONE MUTANT AT A TIME.

The previous generation's driver applied both mutants before a single run, so a red on arm 2a could
have come from either one -- "each mutant bites its own arm" was not measurable from that run.  Here
each mutant is applied alone, the spec is run, and the verdicts are read per test title, so the bite
is attributed.  Restores from in-memory originals and verifies by sha256 after every mutant.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

WT = "D:/moodle/_qoder_rel_ord0447_wt/"
FE = WT + "frontend/"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
WK = "D:/moodle/_qoder_rel_ord0447_wk/"
SPEC = "e2e/qoder-a68b0631-ord0507-clock-attribution-r12.spec.ts"
CLOCK = "frontend/src/app/V8Experience.tsx"
STAGE = "frontend/src/features/simulation/SimulationPanel.tsx"

MUTANTS = {
    "m1_bracket_never_dropped": (CLOCK, 'const cursorAbsent = cursorStatus !== "VALID";',
                                 "const cursorAbsent = false;"),
    "m2_prop_not_wired": (STAGE, "              screenHasNoJourneyInView={screenHasNoJourneyInView}\n", ""),
}

ORIG = {p: io.open(WT + p, encoding="utf-8", newline="").read() for p in (CLOCK, STAGE)}
SHA = {p: hashlib.sha256(ORIG[p].encode("utf-8")).hexdigest() for p in ORIG}


def restore():
    for p in ORIG:
        io.open(WT + p, "w", encoding="utf-8", newline="").write(ORIG[p])
    for p in ORIG:
        now = hashlib.sha256(io.open(WT + p, encoding="utf-8", newline="").read().encode("utf-8")).hexdigest()
        assert now == SHA[p], "restore failed for %s" % p


def run(tag, port):
    env = dict(os.environ)
    env.update({
        "CITYNEXUS_E2E_PORT": str(port),
        "CITYNEXUS_BACKEND_PORT": str(port + 1),
        "CITYNEXUS_DATABASE_URL": "sqlite:///./data/_%s_%d.db" % (tag, int(time.time())),
        "CITYNEXUS_E2E_RUN_ID": "ord0507-%s-%d" % (tag, int(time.time())),
        "CITYNEXUS_PYTHON": PY,
        "QODER_ARM_TAG": tag,
    })
    cmd = "npx playwright test -c playwright.prod-gate.config.ts %s --reporter=line" % SPEC
    p = subprocess.run(cmd, cwd=FE, env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=2400, shell=True)
    out = (p.stdout or "") + (p.stderr or "")
    io.open(WK + "k119_%s.txt" % tag, "w", encoding="utf-8", newline="\n").write(out)
    # per-test verdicts, by the arm each title names
    verdicts = {}
    for m in re.finditer(r"^\s*(✓|✘|×|-)\s+(\d+)\s+.*?(ord0507-[a-z0-9-]+)", out, re.M):
        verdicts[m.group(3)] = "pass" if m.group(1) == "✓" else "fail"
    for m in re.finditer(r"^\s*(✓|✘|×|-)\s+.*?(ord0507-[a-z0-9-]+)", out, re.M):
        verdicts.setdefault(m.group(2), "pass" if m.group(1) == "✓" else "fail")
    return {"rc": p.returncode, "summary": re.findall(r"\d+ (?:passed|failed|skipped)", out),
            "per_test": verdicts}


results = {}
try:
    for name, (rel, a, b) in MUTANTS.items():
        assert ORIG[rel].count(a) == 1, "anchor not unique in %s: %d" % (rel, ORIG[rel].count(a))
        io.open(WT + rel, "w", encoding="utf-8", newline="").write(ORIG[rel].replace(a, b, 1))
        assert io.open(WT + rel, encoding="utf-8", newline="").read() != ORIG[rel], \
            "the mutation did not land in %s" % rel
        try:
            results[name] = run(name.split("_")[0], int(sys.argv[1]) + 10 * len(results))
        finally:
            restore()
        print("%-26s %s" % (name, json.dumps(results[name], ensure_ascii=False)), flush=True)
finally:
    restore()

print("restored_byte_identical=%s" % all(
    hashlib.sha256(io.open(WT + p, encoding="utf-8", newline="").read().encode("utf-8")).hexdigest() == SHA[p]
    for p in ORIG))
io.open(WK + "k119_mutants_separated.json", "w", encoding="utf-8").write(
    json.dumps(results, indent=2, ensure_ascii=False))
print("wrote k119_mutants_separated.json")
