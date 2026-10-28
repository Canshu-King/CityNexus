"""Give the raw-error ruler a control made of real product history, not a shape I typed myself.

840534ec11 is the generation whose screen receipt literally read
"CityNexus API 409: /journeys/<uuid>/agent/goal-tasks/<uuid>/resume" -- that line was later routed
through travelerErrorMessage.  So the old file body is a negative control the product itself
authored: any ruler that claims to catch that leak must report it when handed that exact text.
The current generation is the positive control and must be clean.
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _raw_error_sink_ruler_r1 import scan  # noqa: E402

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
PATHS = [
    "frontend/src/trial/mobile/WorkspaceActions.tsx",
    "frontend/src/trial/mobile/DraftDepartureCard.tsx",
    "frontend/src/trial/mobile/GoalDraftEditor.tsx",
]
OLD = sys.argv[1] if len(sys.argv) > 1 else "840534ec11"


def show(rev: str, path: str) -> str:
    proc = subprocess.run(["git", "-C", ROOT, "show", f"{rev}:{path}"],
                          capture_output=True)
    if proc.returncode != 0:
        return ""
    return proc.stdout.decode("utf-8", errors="replace")


def main() -> int:
    tip = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short=10", "HEAD"],
                         capture_output=True).stdout.decode().strip()
    print("CONTROLS old=" + OLD + " current=" + tip)
    old_caught = 0
    current_leaks = 0
    for path in PATHS:
        old_hits = scan(show(OLD, path))
        new_hits = scan(show(tip, path))
        print("  " + path + " old_hits=" + str(len(old_hits)) + " current_hits=" + str(len(new_hits))
              + (" at:" + ",".join(str(n) for n in old_hits) if old_hits else ""))
        old_caught += len(old_hits)
        current_leaks += len(new_hits)
    if old_caught == 0:
        print("CONTROL_RED: the ruler does not see the leak that really reached a traveller screen"
              " -- it is decoration")
        return 2
    if current_leaks:
        print("CONTROL_RED: the current generation still carries " + str(current_leaks) + " mouths")
        return 3
    print("CONTROL_OK old_caught=" + str(old_caught) + " current=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
