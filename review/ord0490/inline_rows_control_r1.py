"""ORD-0490 counter-example control -- the readability arm has to be able to see a run-on line.

`bin_face/each_measured_row_is_on_a_line_of_its_own` was written after this lane's own screenshot of
the bin face showed the server's refusal name running into the next label
("SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN回读的媒体类型 application/json这台设备数到的字节 372").  The fix is
one rule in `frontend/src/features/shared/sharedJourney.css`.  An arm that only ever passes is not
evidence, so the rule is taken out here, the bundle is rebuilt without it, and the arm is run against
that -- it must go red, and the arms that do not look at those rows must stay green.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0490/inline_rows_control_r1.py

Leaves the source restored and the COUNTER-EXAMPLE bundle served on :4931.  Put the real one back with
`bash review/ord0465/rebuild_and_verify_r1.sh`.
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
CSS = TREE / "frontend" / "src" / "features" / "shared" / "sharedJourney.css"
OUT = TREE / "review" / "ord0490" / "inline_rows_control_r1.txt"
PROXY = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")

RULE = re.compile(rb"\n\.cn-shared-details \.cnx-measured-fact \{\n[^}]*\}\n")


def env() -> dict[str, str]:
    values = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        values.pop(key, None)
    values["NO_PROXY"] = "*"
    return values


def serve(dist: str) -> None:
    listening = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, env=env()).stdout
    for line in listening.splitlines():
        if ":4931 " in line and "LISTENING" in line:
            subprocess.run(["taskkill", "/PID", line.split()[-1], "/F"], capture_output=True, env=env())
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


def main() -> int:
    original = CSS.read_bytes()
    found = RULE.findall(original)
    if len(found) != 1:
        raise SystemExit(f"REFUSE: expected one rule to remove, found {len(found)}. Re-read the sheet.")
    report = [
        "ORD-0490 counter-example control -- the one-line-per-measured-row rule taken out",
        f"sharedJourney.css sha1 before = {hashlib.sha1(original).hexdigest()}",
        f"removed {len(found[0])} bytes: {found[0].decode('utf-8').strip().splitlines()[0]}",
        "",
    ]
    try:
        CSS.write_bytes(RULE.sub(b"", original, count=1))
        dist = "dist_neg_r1"
        build = subprocess.run(
            ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", str(LANE / dist),
             "--emptyOutDir"],
            cwd=TREE / "frontend", capture_output=True, text=True, encoding="utf-8",
            errors="replace", env=env(),
        )
        if build.returncode != 0:
            raise SystemExit(f"REFUSE: the counter-example build failed\n{build.stdout[-600:]}")
        serve(dist)
        arms = subprocess.run(
            ["node", str(TREE / "review/ord0490/restore_arms_r1.js")],
            cwd=TREE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env(),
        )
        lines = [line for line in (arms.stdout + arms.stderr).splitlines()
                 if line.startswith(("PASS", "FAIL", "ARMS=", "DRIVER_ERROR"))]
        report.append(f"counter-example: dist={dist} arms exit={arms.returncode}")
        report.extend(f"  {line}" for line in lines)
        report.append("")
        report.append(
            "expected: bin_face/each_measured_row_is_on_a_line_of_its_own is red, and it is the only "
            "arm that changes -- the refusal is still the same refusal, with the same words and the "
            "same server name for itself."
        )
        reds = sorted(re.findall(r"FAIL\s+(\S+)", "\n".join(lines)))
        report.append(f"red   = {reds}")
    finally:
        CSS.write_bytes(original)
        restored = CSS.read_bytes()
        report.append("")
        report.append(
            f"restored: bytes_equal_to_before={restored == original} "
            f"sha1={hashlib.sha1(restored).hexdigest()}"
        )
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
