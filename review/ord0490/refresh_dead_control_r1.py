"""ORD-0490 screen mutation control -- prove the re-read arms are watching the re-read.

Ten green screen arms say nothing if the judge cannot see the difference between "this page asked
the door again" and "this page painted the same answer it already had".  So the one line the order
depends on is switched off here, in a copy that is restored in the same `finally`:

    frontend/src/features/shared/SharedJourneyPanel.tsx  `readAgain` bumps the `attempt` state that
    the read effect is keyed on.  Making it do nothing is exactly the defect a reviewer would fear:
    the traveller taps 再读一次 after the owner brings the trip back, and the screen keeps painting the
    refusal it was given before.

Expected, and asserted by nothing but a human reading the receipt: the two arms that tap the control
on the already-open page go red, the arms that enter the address cold stay green (a fresh mount does
not need the control), and the refusal-face arms stay green (nothing about the refusal changed).
That split is what shows the cold-load and the in-place tap are measuring different things -- which is
the whole reason ORD-0490 asks for both shapes.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0490/refresh_dead_control_r1.py

It leaves the source restored but the MUTANT bundle still being served on :4931.  Put the real bundle
back with `bash review/ord0465/rebuild_and_verify_r1.sh` afterwards.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
PANEL = TREE / "frontend" / "src" / "features" / "shared" / "SharedJourneyPanel.tsx"
OUT = TREE / "review" / "ord0490" / "refresh_dead_control_r1.txt"
PROXY = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")

LIVE = b"const readAgain = useCallback(() => setAttempt((n) => n + 1), []);"
DEAD = b"const readAgain = useCallback(() => undefined, []);"

SWAP = (LIVE, DEAD)


def env() -> dict[str, str]:
    values = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        values.pop(key, None)
    values["NO_PROXY"] = "*"
    return values


def serve(dist: str) -> None:
    """Move :4931 onto `dist`, the way `rebuild_and_verify_r1.sh` does."""
    listening = subprocess.run(
        ["netstat", "-ano"], capture_output=True, text=True, env=env()
    ).stdout
    for line in listening.splitlines():
        if ":4931 " in line and "LISTENING" in line:
            subprocess.run(["taskkill", "/PID", line.split()[-1], "/F"],
                           capture_output=True, env=env())
            time.sleep(1)
    subprocess.Popen(
        [str(PY), str(PROXY), "--dist", str(LANE / dist), "--port", "4931", "--api", "8731",
         "--log", str(LANE / "run" / f"front_4931_{dist}.log")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env(),
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(60):
        try:
            with opener.open("http://127.0.0.1:4931/", timeout=3) as answer:
                answer.read()
                return
        except Exception:
            time.sleep(1)
    raise SystemExit("REFUSE: the front never came up on :4931")


def build(tag: str) -> str:
    dist = f"dist_mut_{tag}"
    answer = subprocess.run(
        ["node", "node_modules/vite/bin/vite.js", "build",
         "--outDir", str(LANE / dist), "--emptyOutDir"],
        cwd=TREE / "frontend", capture_output=True, text=True, encoding="utf-8",
        errors="replace", env=env(),
    )
    if answer.returncode != 0:
        raise SystemExit(f"REFUSE: the mutant build failed\n{answer.stdout[-800:]}{answer.stderr[-800:]}")
    return dist


def arms() -> tuple[int, list[str]]:
    answer = subprocess.run(
        ["node", str(TREE / "review/ord0490/restore_arms_r1.js")],
        cwd=TREE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env(),
    )
    lines = [line for line in (answer.stdout + answer.stderr).splitlines()
             if line.startswith(("PASS", "FAIL", "ARMS=", "DRIVER_ERROR"))]
    return answer.returncode, lines


def main() -> int:
    original = PANEL.read_bytes()
    if original.count(SWAP[0]) != 1:
        raise SystemExit(
            f"REFUSE: this control names one line and found {original.count(SWAP[0])} matches. "
            "The file moved; re-read `readAgain` before mutating anything."
        )
    report = [
        "ORD-0490 screen mutation control",
        f"SharedJourneyPanel.tsx sha1 before = {hashlib.sha1(original).hexdigest()}",
        "edit: readAgain bumps `attempt` -> readAgain does nothing",
        "      (the tap still fires, the effect keyed on [trimmed, attempt] never re-runs,"
        " so the door is never asked again)",
        "",
    ]
    try:
        PANEL.write_bytes(original.replace(*SWAP))
        dist = build("r1")
        serve(dist)
        code, lines = arms()
        report.append(f"mutant: dist={dist} arms exit={code}")
        report.extend(f"  {line}" for line in lines)
        reds = sorted(re.findall(r"FAIL\s+(\S+)", "\n".join(lines)))
        greens = sorted(re.findall(r"PASS\s+(\S+)", "\n".join(lines)))
        report.append("")
        report.append(
            "expected split: the arms that read what the tap produced are red -- "
            "restored_face/same_page_rereads_into_the_trip and back_in_bin/the_open_screen_refuses_again "
            "(both tap the control), and restored_face/no_token_no_bare_instant_no_machine_word with "
            "them, because the face it is reading is still the refusal and that face does print the "
            "server's UPPER_SNAKE name. Every arm that enters the address cold stays green: a fresh "
            "mount does not need the control. That split is the point -- the cold load and the "
            "in-place tap are two different properties, and only one of them is switched off here."
        )
        report.append(f"red   = {reds}")
        report.append(f"green = {greens}")
    finally:
        PANEL.write_bytes(original)
        restored = PANEL.read_bytes()
        report.append("")
        report.append(
            f"restored: bytes_equal_to_before={restored == original} "
            f"sha1={hashlib.sha1(restored).hexdigest()}"
        )
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(report).encode("utf-8", "replace").decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
