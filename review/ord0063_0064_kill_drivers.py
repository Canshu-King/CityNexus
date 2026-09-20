"""ORD-0063 / ORD-0064(a) frontend kill evidence.

Four mutants, one per promise the merged patch makes: read the projected length (not derive
one), treat a missing projection as unknown, print the currency by code, and honour
`floor_comparable` instead of comparing yen against yuan.  Baseline from `git show HEAD:`,
restored and sha-verified after every case.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
SHELL_REL = "frontend/src/app/V8Experience.tsx"
SPEC = "e2e/qoder-trip-shape-and-budget.spec.ts"
LOGDIR = f"{ROOT}/review"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()

proc = subprocess.run(f'git show "HEAD:{SHELL_REL}"', cwd=ROOT, capture_output=True, shell=True)
if proc.returncode != 0:
    raise SystemExit("cannot read HEAD baseline")
PRISTINE = f"{LOGDIR}/V8Experience.tsx.ord63-pristine"
with open(PRISTINE, "wb") as fh:
    fh.write(proc.stdout)
BASELINE = sha1(PRISTINE)
shutil.copyfile(PRISTINE, f"{ROOT}/{SHELL_REL}")

PROJECTED = "  const tripDayCount = data.journey.temporal_shape?.day_count ?? null;\n"

CASES = [
    (
        # The defect the order named: the client counts days again.
        "kill63-a-client-derives-the-length",
        PROJECTED,
        "  const tripDayCount = Math.max(\n"
        "    1,\n"
        "    Math.round((Date.parse(data.journey.end_at) - Date.parse(data.journey.start_at)) / 86_400_000) + 1,\n"
        "  );\n",
        ["trip-length-comes-from-the-backend", "no-client-side-day-or-currency-invention"],
    ),
    (
        # A missing projection becomes a plausible number.
        "kill63-b-unknown-becomes-one-day",
        PROJECTED,
        "  const tripDayCount = data.journey.temporal_shape?.day_count ?? 1;\n",
        ["trip-length-comes-from-the-backend"],
    ),
    (
        # The ambiguous symbol returns.
        "kill64-a-symbol-instead-of-code",
        '      currencyDisplay: "code",\n',
        '      currencyDisplay: "symbol",\n',
        ["budget-line-never-borrows-a-symbol"],
    ),
    (
        # Yen is compared to yuan and the result is reported as advice.
        "kill64-b-floor-compared-anyway",
        "  const tight = Boolean(reference.floor_comparable) && perPersonPerDay < (reference.floor_minor ?? 0);\n",
        "  const tight = perPersonPerDay < (reference.floor_minor ?? 0);\n",
        ["budget-line-never-borrows-a-symbol"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print(f"baseline {SHELL_REL.rsplit('/',1)[-1]}={BASELINE}", flush=True)

for name, old, new, expected_nodes in CASES:
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
        print("  MUTANT NOT APPLIED — skipped; the suite would judge an untouched build")
        shutil.copyfile(PRISTINE, path)
        continue

    run_id = f"{name.replace('-', '_')[:10]}{int(time.time()) % 100000:05d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": "4440",
            "CITYNEXUS_BACKEND_PORT": "8440",
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
