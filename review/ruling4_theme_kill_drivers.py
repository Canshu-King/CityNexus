"""Ruling ④ theme-control kill evidence -- one mutant per defect the control could have.

A switch is not a cover for a theme that does not change: each mutant breaks exactly one
promise the gate makes (it responds, it offers all three, it applies and persists what it
claims), and the red has to name `theme-control-cycles-all-three-choices`.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
SPEC = "e2e/qoder-theme-contract.spec.ts"
LOGDIR = f"{ROOT}/review"
NODE = "theme-control-cycles-all-three-choices"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()

proc = subprocess.run(f'git show "HEAD:{SHELL_REL}"', cwd=ROOT, capture_output=True, shell=True)
if proc.returncode != 0:
    raise SystemExit("cannot read HEAD baseline")
PRISTINE = f"{LOGDIR}/V8Experience.tsx.theme-pristine"
with open(PRISTINE, "wb") as fh:
    fh.write(proc.stdout)
BASELINE = sha1(PRISTINE)
shutil.copyfile(PRISTINE, f"{ROOT}/{SHELL_REL}")

CASES = [
    ("killT-a-control-dead", '              onClick={cycleTheme}\n', "              onClick={() => undefined}\n"),
    ("killT-b-two-state-toggle", '  dark: "system",\n', '  dark: "light",\n'),
    ("killT-c-choice-never-applied", "    setThemeChoice(next);\n", "    void next;\n"),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print(f"baseline {SHELL_REL.rsplit('/',1)[-1]}={BASELINE}", flush=True)

for name, old, new in CASES:
    if name not in only:
        continue
    path = f"{ROOT}/{SHELL_REL}"
    text = open(PRISTINE, encoding="utf-8", newline="").read()
    hits = text.count(old)
    mutated = text.replace(old, new, 1)
    open(path, "w", encoding="utf-8", newline="").write(mutated)
    applied = hits == 1 and mutated != text
    print(f"{name}: anchor hits={hits} applied={applied}", flush=True)
    if not applied:
        shutil.copyfile(PRISTINE, path)
        continue

    run_id = f"t{name[-7:].replace('-','_')}{int(time.time()) % 100000:05d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": "4460",
            "CITYNEXUS_BACKEND_PORT": "8460",
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    result = subprocess.run(
        f'npx playwright test {SPEC} --reporter=list',
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = result.stdout + result.stderr
    with open(f"{LOGDIR}/{name}.log", "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print(f"  exit={result.returncode}", flush=True)
    for line in out.splitlines():
        if " :: " in line and ("Error" in line or "expect(" in line):
            print(f"  red message: {line.strip()[:200]}")
            break
    print(f"  node {NODE}: {'NAMED IN A RED' if f':: {NODE} ' in out else 'SURVIVED'}", flush=True)

    shutil.copyfile(PRISTINE, path)
    now = sha1(path)
    print(f"  restored {now} {'OK' if now == BASELINE else 'MISMATCH — STOP'}")
    if now != BASELINE:
        sys.exit(2)
