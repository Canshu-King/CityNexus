"""ORD-0060 kill evidence -- the three promises the wizard now makes about a destination."""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
WIZARD_REL = "frontend/src/features/setup/JourneyTrialSetup.tsx"
SPEC = "e2e/qoder-wizard-city-copy.spec.ts"
LOGDIR = f"{ROOT}/review"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()

proc = subprocess.run(f'git show "HEAD:{WIZARD_REL}"', cwd=ROOT, capture_output=True, shell=True)
if proc.returncode != 0:
    raise SystemExit("cannot read HEAD baseline")
PRISTINE = f"{LOGDIR}/JourneyTrialSetup.tsx.ord60-pristine"
with open(PRISTINE, "wb") as fh:
    fh.write(proc.stdout)
BASELINE = sha1(PRISTINE)
shutil.copyfile(PRISTINE, f"{ROOT}/{WIZARD_REL}")

CASES = [
    (
        # The label stops following the recognised city -- the sentence the traveller reads.
        "kill60-a-label-stops-following-the-city",
        '  const identifiedCity = facts ? draft.cityName.trim() : "";\n',
        '  const identifiedCity = "";\n',
        ["city-label-follows-the-recognised-city"],
    ),
    (
        # The assumption goes back to being silent; Next still works.
        "kill60-b-assumption-goes-quiet-again",
        "          {unrecognizedCity && (\n            /* ORD-0060 #2:",
        "          {false && (\n            /* ORD-0060 #2:",
        ["unrecognised-city-assumption-is-said-out-loud"],
    ),
    (
        # The list exists but only shows one name -- which is what my own gate caught live.
        "kill60-c-supported-list-shows-one-name",
        "              {(zh ? SUPPORTED_CITIES.zh : SUPPORTED_CITIES.en).map((name) => (\n",
        "              {(zh ? SUPPORTED_CITIES.zh.slice(0, 1) : SUPPORTED_CITIES.en.slice(0, 1)).map((name) => (\n",
        ["supported-destinations-are-reachable-without-an-invented-count"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print(f"baseline {WIZARD_REL.rsplit('/',1)[-1]}={BASELINE}", flush=True)

for name, old, new, expected_nodes in CASES:
    if name not in only:
        continue
    path = f"{ROOT}/{WIZARD_REL}"
    text = open(PRISTINE, encoding="utf-8", newline="").read()
    hits = text.count(old)
    mutated = text.replace(old, new, 1)
    open(path, "w", encoding="utf-8", newline="").write(mutated)
    applied = hits == 1 and mutated != text
    print(f"{name}: anchor hits={hits} applied={applied}", flush=True)
    if not applied:
        print("  MUTANT NOT APPLIED — skipped; the suite would judge an untouched build")
        shutil.copyfile(PRISTINE, path)
        continue

    run_id = f"{name.replace('-', '_')[:10]}{int(time.time()) % 100000:05d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": "4430",
            "CITYNEXUS_BACKEND_PORT": "8430",
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": f"sqlite:///{ROOT}/review/evidence/_{run_id}.db",
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    result = subprocess.run(
        f"npx playwright test {SPEC} --reporter=list",
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
    if "was not able to start" in out or "refuses to start" in out:
        print("  INVALID RUN: a server never started; this says nothing about any node")
    else:
        for line in out.splitlines():
            if " :: " in line and ("Error" in line or "expect(" in line):
                print(f"  red message: {line.strip()[:210]}")
                break
        for node_id in expected_nodes:
            print(f"  node {node_id}: {'NAMED IN A RED' if f':: {node_id} ' in out else 'SURVIVED'}", flush=True)

    shutil.copyfile(PRISTINE, path)
    now = sha1(path)
    print(f"  restored {now} {'OK' if now == BASELINE else 'MISMATCH — STOP'}")
    if now != BASELINE:
        sys.exit(2)
