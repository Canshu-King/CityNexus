"""ORD-0044 kill evidence driver.

One mutant per named node.  Note the correction recorded in the run: the order asked for
"remove the stay-options call and the node must go red", but `createJourney` continues to
`load()` and `setSetupOpen(false)` after that await, so deleting the call still reaches the
shell -- that mutant cannot turn this node red, and saying so is better than reporting a
kill that did not happen.  The stall's actual shape is reproduced instead.
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
SPEC = "e2e/qoder-onboarding-failure.spec.ts"
LOGDIR = f"{ROOT}/review"

sha1 = lambda p: hashlib.sha1(open(p, "rb").read()).hexdigest()


def seed(rel: str) -> str:
    """Restore baseline is the committed file, never a hand copy."""
    proc = subprocess.run(f'git show "HEAD:{rel}"', cwd=ROOT, capture_output=True, shell=True)
    if proc.returncode != 0:
        raise SystemExit(f"cannot read {rel} from HEAD: {proc.stderr[:200]!r}")
    path = f"{LOGDIR}/{rel.rsplit('/', 1)[-1]}.pristine"
    with open(path, "wb") as fh:
        fh.write(proc.stdout)
    return path


PRISTINE = {rel: seed(rel) for rel in (SHELL_REL, WIZARD_REL)}
BASELINE = {rel: sha1(PRISTINE[rel]) for rel in PRISTINE}
for rel in PRISTINE:
    shutil.copyfile(PRISTINE[rel], f"{ROOT}/{rel}")

STALLED = (
    '      localStorage.setItem("citynexus.v8.journey_id", journey.id);\n'
    "      await v8Request(`/api/v1/journeys/${journey.id}/stay-options/generate`, {\n"
)
CLOSED = (
    "      await load(journey.id);\n"
    "      setSetupOpen(false);\n"
    "      // Land on Today and open the planning entry: the next thing a traveller\n"
)

CASES = [
    (
        "kill44-a-stalls-after-the-journey-row",
        SHELL_REL,
        STALLED,
        STALLED.replace(
            "      await v8Request(",
            '      throw new Error("mutant: stalled after writing the journey row");\n'
            "      void 0 as unknown as typeof fetch;\n      await v8Request(",
            1,
        ),
        ["legal-window-create-advances"],
    ),
    (
        "kill44-b-never-opens-the-shell",
        SHELL_REL,
        CLOSED,
        CLOSED.replace("      setSetupOpen(false);\n", "", 1),
        ["legal-window-create-advances"],
    ),
    (
        "kill44-c-anchor-not-required",
        WIZARD_REL,
        "  const step1Ready = missingStep1.length === 0;\n",
        "  const step1Ready = draft.cityName.trim().length > 0;\n",
        ["missing-anchor-is-named-before-submit"],
    ),
    (
        "kill44-d-drops-the-named-reason",
        SHELL_REL,
        "        busy={setupBusy}\n        message={message}\n",
        "        busy={setupBusy}\n",
        ["named reason inside trial-create-error"],
    ),
    (
        # Ruling (1a): a disabled button the assistive tech cannot tie to a reason is still a
        # silent blocker.  Two mutants, because the gate checks two distinct attributes.
        "kill44-e-says-the-field-is-not-required",
        WIZARD_REL,
        '              placeholder={zh ? "例如：厦门高崎国际机场" : "e.g. Xiamen Gaoqi Intl Airport"}\n'
        '              aria-required="true"\n',
        '              placeholder={zh ? "例如：厦门高崎国际机场" : "e.g. Xiamen Gaoqi Intl Airport"}\n',
        ["missing-anchor-is-named-before-submit"],
    ),
    (
        "kill44-f-leaves-the-reason-unassociated",
        WIZARD_REL,
        """              aria-describedby={
                arrivalProblem
                  ? "trial-required-hint trial-arrival-problem"
                  : draft.arrivalLocation.trim()
                    ? undefined
                    : "trial-required-hint"
              }
""",
        "              aria-describedby={undefined}\n",
        ["missing-anchor-is-named-before-submit"],
    ),
    (
        # Ruling (1b): a bare em-dash reads as an acceptable blank.
        "kill44-g-reviews-a-blank-anchor-as-a-dash",
        WIZARD_REL,
        '                {draft.arrivalLocation.trim() || (zh ? "未填写 · 必填" : "not filled in · required")}\n',
        '                {draft.arrivalLocation.trim() || "—"}\n',
        ["review-page-says-missing-anchor-is-required"],
    ),
    (
        # Ruling (1c): the backend stays the authority, so its complaint must land on the
        # field it named.  Dropping the loc routing keeps the headline honest and smears the
        # arrival sentence onto the departure box, which is what the node's last assertion is
        # for -- the first assertion still passes under this mutant.
        "kill44-h-ignores-which-field-the-backend-named",
        WIZARD_REL,
        "  const arrivalProblem = fieldProblem(message, /arrival_anchor/);\n"
        "  const departureProblem = fieldProblem(message, /departure_anchor/);\n",
        "  const arrivalProblem = fieldProblem(message, /.*/);\n"
        "  const departureProblem = fieldProblem(message, /.*/);\n",
        ["backend-reason-lands-on-its-own-field"],
    ),
    (
        # The 500 node: an unhandled server error crosses the wire as plain text, so the
        # status is the only fact the client may state.  Hiding it leaves "it failed" with no
        # way to tell a refused request from a dropped one.
        "kill44-i-hides-the-status-the-server-sent",
        SHELL_REL,
        "    `Request failed (${status})`;\n",
        '    "The request failed";\n',
        ["a 500 stays silent"],
    ),
]

only = sys.argv[1:] or [c[0] for c in CASES]
print("baselines: " + ", ".join(f"{rel.rsplit('/',1)[-1]}={BASELINE[rel]}" for rel in BASELINE))

for name, rel, old, new, expected_nodes in CASES:
    if name not in only:
        continue
    path = f"{ROOT}/{rel}"
    text = open(PRISTINE[rel], encoding="utf-8", newline="").read()
    count = text.count(old)
    mutated = text.replace(old, new, 1)
    open(path, "w", encoding="utf-8", newline="").write(mutated)
    applied = count == 1 and mutated != text
    print(f"{name}: anchor hits={count} applied={applied}")
    if not applied:
        print("  MUTANT NOT APPLIED — skipped; running the suite here would judge an untouched build")
        shutil.copyfile(PRISTINE[rel], path)
        continue

    run_id = f"{name.replace('-', '_')[:10]}{int(time.time()) % 100000:05d}"
    port = 4430 + only.index(name)
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
    with open(f"{LOGDIR}/{name}.log", "w", encoding="utf-8", newline="") as fh:
        fh.write(out)
    print(f"  exit={proc.returncode}")
    if "was not able to start" in out or "refuses to start" in out:
        print("  INVALID RUN: a server never started; this says nothing about any node")
    else:
        for line in out.splitlines():
            if " :: " in line and ("Error" in line or "expect(" in line):
                print(f"  red message: {line.strip()[:190]}")
                break
        for node_id in expected_nodes:
            print(f"  node {node_id}: {'NAMED IN A RED' if f':: {node_id} ' in out else 'SURVIVED'}")

    shutil.copyfile(PRISTINE[rel], path)
    now = sha1(path)
    print(f"  restored {rel.rsplit('/',1)[-1]} {now} {'OK' if now == BASELINE[rel] else 'MISMATCH — STOP'}")
    if now != BASELINE[rel]:
        sys.exit(2)
