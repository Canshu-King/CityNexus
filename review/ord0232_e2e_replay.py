"""ORD-0232 end-to-end replay: run the real-chain arm, or refuse and say exactly why.

The rendering arm (`frontend/e2e/qoder-dropped-candidates-say-why.spec.ts`) proves the screen with
B's real envelope replayed through a route stub.  This script exists so the remaining claim --
"a real `plans/generate` really puts that sentence on the screen" -- is either measured or
explicitly not measured, never quietly assumed.

Why the refusal: the emitter is `a96fabf` ("a candidate the gate drops now leaves a named durable
fact", +39 lines in `backend/app/services.py`), which sits on branch
`agent/canary-ord198-20260922` and is not an ancestor of this tip.  Running the real chain here
would produce zero rejection events, and "zero events" is indistinguishable from "the renderer
works" -- that is how a vacuous green gets signed.

Exit codes: 7 = BLOCKED_ON_MERGE, 0 = the arm ran green, anything else = Playwright's own.
"""

from __future__ import annotations

import subprocess
import sys

ROOT = "D:/moodle/_qoder_integration_20260919"
PYTHON = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
EMITTER = "a96fabf"
SPEC = "e2e-ord0232-real/ord0232-real-chain.spec.ts"
CONFIG = "playwright.ord0232-real.config.ts"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.strip()


def main() -> int:
    port = sys.argv[1] if len(sys.argv) > 1 else "4960"
    subject = git("log", "-1", "--format=%h %ad %s", "--date=format:%Y-%m-%d %H:%M", EMITTER)
    branches = git("branch", "-a", "--contains", EMITTER)
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EMITTER, "HEAD"], cwd=ROOT, capture_output=True, text=True
    ).returncode
    print(f"tip            {git('rev-parse', '--short', 'HEAD')}  ({git('log', '-1', '--format=%s')})")
    print(f"emitter commit {subject or EMITTER + ' (unreadable)'}")
    print(f"branches that hold it: {branches.splitlines()}")
    if ancestor != 0:
        print(
            "STATUS: BLOCKED_ON_MERGE -- the emitter is not an ancestor of this tip, so the real feed\n"
            "        cannot carry plans.candidate_rejected here.  The arm was NOT run, and no green is\n"
            "        claimed for it.  Unblocking action: merge " + EMITTER.split()[0] + " into the integration line."
        )
        return 7
    print(f"running {SPEC} against {CONFIG} on :{port}/{int(port) + 4000}")
    return subprocess.run(
        [PYTHON, f"{ROOT}/review/run_spec.py", SPEC, port, "--config", CONFIG], cwd=ROOT
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
