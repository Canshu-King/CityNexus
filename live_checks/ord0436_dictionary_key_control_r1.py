"""Control on the ORD-0462 dictionary-keyed sentences: rename the key, the arms must go red.

The claim under test is "the scope sentence on screen is the shared dictionary's value for the key
the ACL door named". A mutant that renames the dictionary key (leaving the door's key alone) makes
the lookup miss, so the screen must fall back to the unread-key sentence -- and both the ladder arm
and the member-row arm must fail. If they stay green, the sentence was never coming from the
dictionary and the arms are decoration.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
LEX = REPO / "frontend/src/i18n/LocaleContext.tsx"
# The bundle lives in this lane's export directory; the reading is served from there, so the
# mutant has to be copied in as well as written to the lane tree.
BUILD = pathlib.Path(os.environ.get("CNX_BUILD_EXPORT", "D:/moodle/_qoder_ord0436_build"))
KEY = '"member.scope.collaborator"'


def run(cmd: list[str], cwd: pathlib.Path, tail: int = 1) -> str:
    got = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
                         errors="replace", check=False)
    return "\n".join((got.stdout or "").splitlines()[-tail:])


def verdicts() -> dict[str, str]:
    data = json.loads((REPO / "review/ord0436-access/TWO_ARMS_R1.json").read_text(encoding="utf-8"))
    return {c["name"]: c["verdict"] for c in data["reading"]["checks"]}


text = LEX.read_text(encoding="utf-8")
assert text.count(KEY) == 2, text.count(KEY)
original = text
mutated = text.replace(KEY, '"member.scope.collaboratorX"')
LEX.write_text(mutated, encoding="utf-8", newline="\n")
print("mutant installed: dictionary key renamed in both arms")

try:
    subprocess.run(["cp", "-f", str(LEX), str(BUILD / "frontend/src/i18n/LocaleContext.tsx")], check=True)
    print("build:", run(["node", "node_modules/vite/bin/vite.js", "build"], BUILD / "frontend"))
    reading = subprocess.run(
        [sys.executable, "-X", "utf8", "live_checks/ord0436_two_arms_r1.py"],
        cwd=str(REPO), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
        env={k: v for k, v in __import__("os").environ.items() if "PROXY" not in k.upper()},
    )
    lines = [l for l in (reading.stdout or "").splitlines() if l.strip()]
    print("run tail:", lines[-1] if lines else "(no output)")
    after = verdicts()
    red = sorted(name for name, verdict in after.items() if verdict == "FAIL")
    print("RED_UNDER_MUTANT", json.dumps(red, ensure_ascii=False))
finally:
    LEX.write_text(original, encoding="utf-8", newline="\n")
    subprocess.run(["cp", "-f", str(LEX), str(BUILD / "frontend/src/i18n/LocaleContext.tsx")], check=True)
    print("reverted:", KEY in LEX.read_text(encoding="utf-8"))
