"""ORD-0047 kill evidence driver.

One mutant per named node, each a defect of that node's own shape: the waiting block, the
counting clock, the stop control, the zero-result face, and the two faces that must not be
confused.  Baselines are restored from `git show HEAD:<path>` and re-verified by sha1 after
every case, so a "kill" can never be judged against a half-mutated tree.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
WIZARD_REL = "frontend/src/features/setup/JourneyTrialSetup.tsx"
CLOCK_REL = "frontend/src/lib/waitClock.ts"
SPEC = "e2e/qoder-generation-wait.spec.ts"
LOGDIR = f"{ROOT}/review"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()


def seed(rel: str) -> str:
    proc = subprocess.run(f'git show "HEAD:{rel}"', cwd=ROOT, capture_output=True, shell=True)
    if proc.returncode != 0:
        raise SystemExit(f"cannot read {rel} from HEAD: {proc.stderr[:200]!r}")
    path = f"{LOGDIR}/{rel.rsplit('/', 1)[-1]}.pristine"
    with open(path, "wb") as fh:
        fh.write(proc.stdout)
    return path


FILES = [SHELL_REL, WIZARD_REL, CLOCK_REL]
PRISTINE = {rel: seed(rel) for rel in FILES}
BASELINE = {rel: sha1(PRISTINE[rel]) for rel in PRISTINE}
for rel in PRISTINE:
    shutil.copyfile(PRISTINE[rel], f"{ROOT}/{rel}")

CASES = [
    (
        # The order's own acceptance: remove the progress component and the node is red.
        "kill47-a-waiting-block-removed",
        WIZARD_REL,
        "      {busy && phaseLabel && (\n",
        "      {false && busy && phaseLabel && (\n",
        ["gen-wait-phase-stays-visible"],
    ),
    (
        # A number that never advances is a frozen screen with better typography.
        "kill47-b-clock-frozen-at-zero",
        CLOCK_REL,
        "    const tick = () => setElapsed(Math.floor((Date.now() - startedAt) / 1000));\n",
        "    const tick = () => setElapsed(0);\n",
        ["gen-wait-phase-stays-visible"],
    ),
    (
        # The stop control closes its own eyes: no abort, and the outcome line never shows.
        "kill47-c-stop-does-not-abort",
        SHELL_REL,
        "  const stopWaiting = () => {\n    setStoppedWaiting(true);\n    createAbortRef.current?.abort();\n  };",
        "  const stopWaiting = () => {\n    setStoppedWaiting(true);\n  };",
        ["gen-wait-stop-waiting-aborts"],
    ),
    (
        # `options=0` drawn as success: the 200 is believed, the body is not counted.
        "kill47-d-zero-options-called-success",
        SHELL_REL,
        '      setStaySearch(count === 0 ? "empty" : "found");\n',
        '      setStaySearch("found");\n',
        ["gen-empty-options-is-not-success"],
    ),
    (
        # Refused borrows the empty face: two of the three states become one sentence.
        "kill47-e-refused-wears-the-empty-face",
        SHELL_REL,
        '      if (!isAbort(cause)) setStaySearch("failed");\n',
        '      if (!isAbort(cause)) setStaySearch("empty");\n',
        ["gen-three-states-distinguishable"],
    ),
    (
        # The failure notice denies a journey whose row was already written.
        "kill47-f-notice-denies-a-trip-that-exists",
        WIZARD_REL,
        "            {journeyCreated\n",
        "            {false\n",
        ["gen-three-states-distinguishable"],
    ),
    (
        # A reported cause is thrown away: the block still says "empty", so the four faces
        # stay intact and only the node about causes can see this one.
        "kill47-g-drops-the-reported-cause",
        SHELL_REL,
        "  switch (outcome) {\n",
        "  switch (null) {\n",
        ["gen-empty-reason-comes-from-the-server"],
    ),
    (
        # The mirror defect: a silence is filled in with a cause nobody reported.
        "kill47-h-invents-a-cause-for-a-silence",
        SHELL_REL,
        "  switch (outcome) {\n",
        '  switch (outcome ?? "NO_OFFERS_FROM_PROVIDER") {\n',
        ["gen-empty-reason-comes-from-the-server"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print("baselines: " + ", ".join(f"{r.rsplit('/',1)[-1]}={BASELINE[r]}" for r in BASELINE), flush=True)

for name, rel, old, new, expected_nodes in CASES:
    if name not in only:
        continue
    path = f"{ROOT}/{rel}"
    text = open(PRISTINE[rel], encoding="utf-8", newline="").read()
    count = text.count(old)
    mutated = text.replace(old, new, 1)
    open(path, "w", encoding="utf-8", newline="").write(mutated)
    applied = count == 1 and mutated != text
    print(f"{name}: anchor hits={count} applied={applied}", flush=True)
    if not applied:
        print("  MUTANT NOT APPLIED — skipped; running the suite here would judge an untouched build")
        shutil.copyfile(PRISTINE[rel], path)
        continue

    run_id = f"{name.replace('-', '_')[:10]}{int(time.time()) % 100000:05d}"
    port = 4440 + only.index(name)
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": str(port),
            "CITYNEXUS_BACKEND_PORT": str(port + 4000),
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    proc = subprocess.run(
        f'npx playwright test {SPEC} --reporter=list',
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = proc.stdout + proc.stderr
    with open(f"{LOGDIR}/{name}.log", "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print(f"  exit={proc.returncode}", flush=True)
    if "was not able to start" in out or "refuses to start" in out:
        print("  INVALID RUN: a server never started; this says nothing about any node")
    else:
        for line in out.splitlines():
            if " :: " in line and ("Error" in line or "expect(" in line):
                print(f"  red message: {line.strip()[:200]}")
                break
        for node_id in expected_nodes:
            print(f"  node {node_id}: {'NAMED IN A RED' if f':: {node_id} ' in out else 'SURVIVED'}", flush=True)

    shutil.copyfile(PRISTINE[rel], path)
    now = sha1(path)
    print(f"  restored {rel.rsplit('/',1)[-1]} {now} {'OK' if now == BASELINE[rel] else 'MISMATCH — STOP'}")
    if now != BASELINE[rel]:
        sys.exit(2)
