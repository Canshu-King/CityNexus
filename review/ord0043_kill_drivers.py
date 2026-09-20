"""ORD-0043 kill evidence -- the A4 mechanisms this lane landed, and its one deviation.

Three of the four mutants break a mechanism the ruling named; the fourth breaks the single
place this lane deviated from A4 byte-for-byte, which is the evidence for keeping that
deviation at all.  Baseline comes from `git show HEAD:` and is restored by sha1.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
SW_REL = "frontend/public/sw.js"
SPEC = "e2e/qoder-service-worker.spec.ts"
LOGDIR = f"{ROOT}/review"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()

proc = subprocess.run(f'git show "HEAD:{SW_REL}"', cwd=ROOT, capture_output=True, shell=True)
if proc.returncode != 0:
    raise SystemExit("cannot read HEAD baseline")
PRISTINE = f"{LOGDIR}/sw.js.ord43-pristine"
with open(PRISTINE, "wb") as fh:
    fh.write(proc.stdout)
BASELINE = sha1(PRISTINE)
shutil.copyfile(PRISTINE, f"{ROOT}/{SW_REL}")

ACTIVATE_FILTER = (
    "          (key.startsWith(CACHE_PREFIX) && key !== CACHE) ||\n"
    "          LEGACY_CACHE_NAMES.has(key) ||\n"
    '          key.startsWith("citynexus-trip-operations-v"),\n'
)

CASES = [
    (
        # A4's own guard, narrowed to documents: without the path test a window fetch() of a
        # .js URL arrives with an empty destination and the dev server's HTML passes through.
        "kill43-a-html-guard-loses-the-path-test",
        "    askedForCode ||\n",
        "",
        ["sw-never-answers-script-with-html"],
    ),
    (
        # The cleanup sweeps everything it does not own -- the original defect.
        "kill43-b-activate-wipes-foreign-caches",
        ACTIVATE_FILTER,
        "          key !== CACHE,\n",
        ["sw-activate-keeps-foreign-caches"],
    ),
    (
        # The cleanup is a no-op, so a retired strategy's poisoned entry keeps answering.
        "kill43-c-activate-retires-nothing",
        ACTIVATE_FILTER,
        "          false,\n",
        ["sw-activate-keeps-foreign-caches"],
    ),
    (
        # A4's byte-for-byte branch: code is network-only. This is the deviation, so the
        # mutant that restores it has to fail a gate.
        "kill43-d-code-requests-network-only",
        "      return cached && !isHtmlResponse(cached) ? cached : Response.error();\n",
        "      return Response.error();\n",
        ["sw-offline-boot-serves-cached-code"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print(f"baseline {SW_REL.rsplit('/',1)[-1]}={BASELINE}", flush=True)

for name, old, new, expected_nodes in CASES:
    if name not in only:
        continue
    path = f"{ROOT}/{SW_REL}"
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
            "CITYNEXUS_E2E_PORT": "4450",
            "CITYNEXUS_BACKEND_PORT": "8450",
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
