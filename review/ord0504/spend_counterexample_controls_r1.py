"""ORD-0504 -- run the order's two counterexamples against deliberately broken faces.

Ten green arms say the face is right only if each arm can go red. Two of those ten are the
counterexamples the order names, so each gets its own mutant here, built into its own bundle, served
on this lane's own front, and then reverted byte for byte:

  M1  a missing price becomes 0.  `spendFacts.ts` reads
      `amountMinor: typeof cost === "number" ? cost : null`; the mutant uses `: 0`. This is the fake
      green the order's clause 4 forbids -- a traveller sees "CNY 0.00" and reads an answer, while the
      server said nothing. It must turn `counterexample/no_server_fact_prints_no_total` red. The bare
      trip is seeded with one unpriced leg precisely so this mutant has something to lie about.

  M2  the estimated bucket stops following the store. `legStrength` answers KNOWN with "ESTIMATED";
      the mutant answers "UNNAMED", so changing a leg's real amount moves nothing on screen. It must
      turn `counterexample/changing_one_amount_moves_the_total` red (and the face arms with it), which
      is what shows that arm is comparing two readings and not printing a constant.

    /d/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/spend_counterexample_controls_r1.py

Leaves the source restored and the LAST mutant bundle served on :4931. Put the real one back with
`bash review/ord0465/rebuild_and_verify_r1.sh`.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

LANE = Path("D:/moodle/_qoder_r_ord0465_20260929")
TREE = LANE / "wt"
FACTS = TREE / "frontend" / "src" / "features" / "trip" / "spendFacts.ts"
OUT = TREE / "review" / "ord0504" / "spend_counterexample_controls_r1.txt"
PROXY = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_static_api_proxy_r1.py")
PY = Path("D:/moodle/CityNexus/.venv/Scripts/python.exe")

MUTANTS = [
    ("M1 a missing price becomes 0",
     b"amountMinor: typeof cost === \"number\" ? cost : null,",
     b"amountMinor: typeof cost === \"number\" ? cost : 0,",
     "counterexample/no_server_fact_prints_no_total"),
    ("M2 the estimated bucket stops following the store",
     b"if (status === \"KNOWN\") return \"ESTIMATED\";",
     b"if (status === \"KNOWN\") return \"UNNAMED\";",
     "counterexample/changing_one_amount_moves_the_total"),
]


def env() -> dict[str, str]:
    values = dict(os.environ)
    for key in ("HTTP_PROXY", "HTTPS_PROXY"):
        values.pop(key, None)
    values["NO_PROXY"] = "*"
    values["CITYNEXUS_DATABASE_URL"] = "sqlite:///" + (LANE / "run" / "ord0465_lane.db").as_posix()
    values["CITYNEXUS_DEMO_MODE"] = "true"
    values["PYTHONPATH"] = f"{TREE};{TREE / 'backend'}"
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
            with opener.open("http://127.0.0.1:4931/", timeout=3):
                return
        except Exception:
            time.sleep(1)
    raise SystemExit("REFUSE: the front never came up on :4931")


def main() -> int:
    original = FACTS.read_bytes()
    for _, old, _, _ in MUTANTS:
        if original.count(old) != 1:
            raise SystemExit(
                f"REFUSE: expected exactly one match for {old[:48]!r}, found "
                f"{original.count(old)}. Re-read the file before mutating it."
            )
    report = ["ORD-0504 counterexample controls",
              f"spendFacts.ts sha1 before = {hashlib.sha1(original).hexdigest()}", ""]
    try:
        for name, old, new, must_go_red in MUTANTS:
            FACTS.write_bytes(original.replace(old, new))
            dist = "dist_spend_mut_r1"
            build = subprocess.run(
                ["node", "node_modules/vite/bin/vite.js", "build", "--outDir", str(LANE / dist),
                 "--emptyOutDir"],
                cwd=TREE / "frontend", capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env(),
            )
            if build.returncode != 0:
                raise SystemExit(f"REFUSE: the {name} build failed\n{build.stdout[-500:]}")
            serve(dist)
            arms = subprocess.run(
                ["node", str(TREE / "review/ord0504/spend_arms_r1.js")],
                cwd=TREE, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env(),
            )
            lines = [line for line in (arms.stdout + arms.stderr).splitlines()
                     if line.startswith(("PASS", "FAIL", "ARMS=", "DRIVER_ERROR"))]
            reds = [line.split()[1] for line in lines if line.startswith("FAIL")]
            report += [f"=== {name}", f"    {old.decode()[:60]} -> {new.decode()[:60]}"]
            report += [f"  {line}" for line in lines if line.startswith(("FAIL", "ARMS=", "DRIVER_ERROR"))]
            report.append(f"  expected red: {must_go_red}")
            report.append(f"  verdict: {'CAUGHT' if must_go_red in reds else 'MISSED -- this arm is not a judge'}")
            report.append("")
            FACTS.write_bytes(original)
    finally:
        FACTS.write_bytes(original)
        restored = FACTS.read_bytes()
        report.append(f"restored: bytes_equal_to_before={restored == original} "
                      f"sha1={hashlib.sha1(restored).hexdigest()}")
    OUT.write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
