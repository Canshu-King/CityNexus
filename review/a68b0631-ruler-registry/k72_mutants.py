"""Counter-arms for the r5 hand: two mutants, each aimed at the leg its own arm walks.

m1  un-conditional bracket  -> 2a must name the sentence that claims a cursor while it is absent
m2  drop the prop wiring     -> 2b must name the stage journey with 0 counter-sentences
"""
import io
import json
import os
import re
import subprocess
import sys
import time

FE = "D:/moodle/_qoder_rel_ord0447_wt/frontend/"
WT = "D:/moodle/_qoder_rel_ord0447_wt/"
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
WK = "D:/moodle/_qoder_rel_ord0447_wk/"
SPEC = "e2e/qoder-a68b0631-ord0507-clock-attribution-r12.spec.ts"
if len(sys.argv) > 2:
    SPEC = sys.argv[2]
CLOCK = "src/app/V8Experience.tsx"
STAGE = "src/features/simulation/SimulationPanel.tsx"

MUT = [
    (CLOCK, 'const cursorAbsent = cursorStatus !== "VALID";', "const cursorAbsent = false;"),
    (STAGE, "              screenHasNoJourneyInView={screenHasNoJourneyInView}\n", ""),
]


def read(rel):
    return io.open(FE + rel, encoding="utf-8", newline="").read()


def write(rel, text):
    io.open(FE + rel, "w", encoding="utf-8", newline="").write(text)


def run(tag, port):
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_PORT": str(port),
            "CITYNEXUS_BACKEND_PORT": str(port + 1),
            "CITYNEXUS_DATABASE_URL": "sqlite:///./data/_%s_%d.db" % (tag, int(time.time())),
            "CITYNEXUS_E2E_RUN_ID": "ord0507-%s-%d" % (tag, int(time.time())),
            "CITYNEXUS_PYTHON": PY,
            "QODER_ARM_TAG": tag,
        }
    )
    proc = subprocess.run(
        "npx playwright test -c playwright.prod-gate.config.ts %s --reporter=line" % SPEC,
        cwd=FE, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=2400, shell=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    io.open(WK + "k72_%s.txt" % tag, "w", encoding="utf-8", newline="\n").write(out)
    print(json.dumps(
        {
            "tag": tag,
            "exit": proc.returncode,
            "summary": re.findall(r"\d+ (?:passed|failed|skipped)", out),
            "bites": [m.group(0)[:400] for m in
                      re.finditer(r"Error: e2e/qoder-a68b0631-ord0507[^\n]{0,400}", out)][:4],
        }, ensure_ascii=False), flush=True)
    return proc.returncode


orig = {rel: read(rel) for rel, _, _ in MUT}
for rel, a, b in MUT:
    assert orig[rel].count(a) == 1, "anchor not unique in %s: %d" % (rel, orig[rel].count(a))
    write(rel, orig[rel].replace(a, b, 1))
    assert read(rel) != orig[rel], "mutation did not land in %s" % rel
TAG = sys.argv[1] if len(sys.argv) > 1 else "r5mutants"
PORT = int(sys.argv[3]) if len(sys.argv) > 3 else 61610
rc = run(TAG, PORT)
for rel, _, _ in MUT:
    write(rel, orig[rel])
print("restored_byte_identical=", all(read(rel) == orig[rel] for rel in orig), flush=True)
print("dirty=", subprocess.run(["git", "status", "--short"], cwd=WT,
                               capture_output=True, text=True).stdout.strip()[:200], flush=True)
