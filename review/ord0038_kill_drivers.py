"""ORD-0038 kill evidence driver.

One mutant per named node in e2e/qoder-plan-ai-thinking.spec.ts.  Each mutant is the shape
of the claim the node forbids, not an unrelated break, and PlanWithAiSheet.tsx is restored
from the committed file and sha1-checked after every run.
"""

import hashlib
import os
import shutil
import subprocess
import sys
import time

ROOT = "D:/moodle/_qoder_ui_overnight_20260920"
REL = "frontend/src/features/planning/PlanWithAiSheet.tsx"
SRC = f"{ROOT}/{REL}"
PRISTINE = f"{ROOT}/review/PlanWithAiSheet.tsx.pristine"
LOGDIR = f"{ROOT}/review"
SPEC = "e2e/qoder-plan-ai-thinking.spec.ts"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()


def seed_pristine_from_git() -> None:
    """The restore baseline is the committed file, never a hand-made copy that can go stale."""
    proc = subprocess.run(
        f"git show HEAD:{REL}",
        cwd=ROOT,
        capture_output=True,
        shell=True,
    )
    if proc.returncode != 0:
        raise SystemExit(f"cannot read {REL} from HEAD: {proc.stderr[:200]!r}")
    with open(PRISTINE, "wb") as fh:
        fh.write(proc.stdout)


seed_pristine_from_git()

CASES = [
    (
        "kill38-a-frozen-seconds",
        "4341",
        [("`已等待 ${elapsed} 秒`", "`已等待 0 秒`")],
        "plan-ai-elapsed-ticks",
    ),
    (
        # Same node, the other render arm: the first round's Chinese mutant survived only
        # because the suite ran in English and never executed that line.
        "kill38-a2-frozen-seconds-en",
        "4348",
        [("`waiting ${elapsed}s`", "`waiting 0s`")],
        "plan-ai-elapsed-ticks",
    ),
    (
        "kill38-b-everything-claims-done",
        "4342",
        [
            (
                '                const state = index < here ? "done" : index === here ? "active" : "";\n',
                '                const state = "done";\n',
            )
        ],
        "plan-ai-no-fabricated-stage",
    ),
    (
        "kill38-c-cancel-cannot-stop-the-post",
        "4343",
        [
            (
                '        body: JSON.stringify({ command }),\n        signal,\n',
                "        body: JSON.stringify({ command }),\n",
            )
        ],
        "plan-ai-cancel-aborts-request",
    ),
    (
        "kill38-d-cancel-cannot-stop-the-baseline",
        "4344",
        [
            (
                '      const response = await fetch(`/api/v1/journeys/${journeyId}/plans`, {\n'
                '        headers: { Accept: "application/json" },\n'
                "        signal,\n"
                "      });\n",
                '      const response = await fetch(`/api/v1/journeys/${journeyId}/plans`, {\n'
                '        headers: { Accept: "application/json" },\n'
                "      });\n",
            )
        ],
        "plan-ai-cancel-before-send",
    ),
    (
        "kill38-e-refused-request-falls-through",
        "4345",
        [
            (
                "      if (!response.ok) {\n        /* A refused or failed request is reported as what it is.",
                "      if (false) {\n        /* A refused or failed request is reported as what it is.",
            )
        ],
        "plan-ai-failure-not-loading",
    ),
    (
        "kill38-f-unreadable-status-reads-as-ready",
        "4346",
        [('        if (!stale) setAiState("unknown");', '        if (!stale) setAiState("ready");')],
        "plan-ai-preflight-honest",
    ),
    (
        # The shape the production walk exposed: a mission that said it never ran, rows the
        # component assembled itself, and the sheet calling that success.
        "kill38-g-any-rows-count-as-ai-success",
        "4350",
        [
            (
                "      } else if (planCount > 0 && missionCompleted) {\n",
                "      } else if (planCount > 0) {\n",
            )
        ],
        "plan-ai-no-synthetic-success",
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
baseline = sha1(PRISTINE)
print(f"pristine sha1 {baseline}")

for name, port, subs, expected_node in CASES:
    if name not in only:
        continue
    text = open(PRISTINE, "r", encoding="utf-8", newline="").read()
    mutated = text
    hits = []
    for old, new in subs:
        hits.append(mutated.count(old))
        mutated = mutated.replace(old, new, 1)
    if any(count == 0 for count in hits):
        print(f"{name}: ANCHOR NOT FOUND (counts={hits}) — mutant not applied, result invalid")
        continue
    if mutated == text:
        print(f"{name}: substitution was a no-op — result invalid")
        continue
    open(SRC, "w", encoding="utf-8", newline="").write(mutated)
    print(f"{name}: mutant applied ({len(text)} -> {len(mutated)} bytes)")

    # A fresh run id per attempt: the backend refuses to reopen an existing e2e
    # database, which is what made the first re-run of every mutant "invalid".
    run_id = f"{name.replace(chr(45), chr(0x5f))[:12]}{int(time.time()) % 100000:05d}"
    env = dict(os.environ)
    env.update(
        {
            "CITYNEXUS_E2E_AUTHORITATIVE": "1",
            "CITYNEXUS_E2E_RUN_ID": run_id,
            "CITYNEXUS_E2E_PORT": port,
            "CITYNEXUS_BACKEND_PORT": str(8300 + int(port[-2:])),
            "CITYNEXUS_PYTHON": "D:/moodle/CityNexus/.venv/Scripts/python.exe",
            "CITYNEXUS_DATABASE_URL": (
                f"sqlite:///{ROOT}/review/evidence/_{run_id}.db"
            ),
            "CITYNEXUS_AI_ENABLED": "false",
            "CITYNEXUS_EVIDENCE_DIR": f"{ROOT}/review/evidence",
        }
    )
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    proc = subprocess.run(
        f"npx playwright test {SPEC} --reporter=list",
        cwd=f"{ROOT}/frontend",
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=True,
    )
    out = proc.stdout + proc.stderr
    lines = out.splitlines()
    log = f"{LOGDIR}/{name}.log"
    with open(log, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  exit={proc.returncode}  log={log}")
    for line in lines:
        if " :: " in line and "Error" in line:
            print(f"  red message: {line.strip()[:230]}")
    if "was not able to start" in out:
        print(f"  INVALID RUN: the webServer never started, so this says nothing about {expected_node}")
    else:
        named = f":: {expected_node} " in out
        print(f"  expected node {expected_node}: {'NAMED IN A RED' if named else 'SURVIVED'}")

    shutil.copyfile(PRISTINE, SRC)
    now = sha1(SRC)
    print(f"  restored sha1 {now} {'OK' if now == baseline else 'MISMATCH — STOP'}")
    if now != baseline:
        sys.exit(2)
