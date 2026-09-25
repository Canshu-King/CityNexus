"""Pull my own ORD-0310 block back out of the ledger, byte for byte, and gauge that copy.

The point of gauging the copy that came out of the ledger (not the file I handed to the insert tool)
is that the stamp is then real: the minute the clock wrote is inside the bytes the rulers judged.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

LEDGER = Path("D:/moodle/CITYNEXUS_AGENT_CONTROL.md")
SC = Path("D:/moodle/_qoder_d_lane_20260923/_scratch_0310")
RULERS = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks")
PY = "D:/moodle/CityNexus/.venv/Scripts/python.exe"
# which generation is being pulled back out of the ledger: argv[1] = heading prefix, argv[2] = tag
START = (sys.argv[1] if len(sys.argv) > 1
         else "### SESSION=e345b9d6 @2026-09-25 19:54+08 —— **ORD-0310 交付")
TAG = sys.argv[2] if len(sys.argv) > 2 else ""
STAMP = START.split("——")[0].replace("### SESSION=e345b9d6 ", "").strip()
OUT_BLOCK = SC / f"ord0310-ledger-block{TAG}.md"

with open(LEDGER, encoding="utf-8", newline="") as handle:
    text = handle.read()
i = text.index(START)
rest = text[i + len(START):]
j = rest.index("\n### ")
block = text[i:i + len(START) + j].rstrip("\n") + "\n"
out = OUT_BLOCK
out.write_bytes(block.encode("utf-8"))


def sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


print(f"wrote {out} {out.stat().st_size} B blob={sha1(out.read_bytes())}")
print(f"stamp inside the bytes: {STAMP in block}")
for ruler, tag in (("claim_coordinate_check_r4b.py", "q43r4b"), ("claim_coordinate_check_r3.py", "q43r3")):
    proc = subprocess.run([PY, str(RULERS / ruler), "--text", str(out),
                           "--out", str(SC / f"ord0310-{tag}-on-block{TAG}.json")],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    line = [l for l in proc.stdout.splitlines() if "overall" in l or "CLEAN" in l or "GREEN" in l]
    print(f"{tag}: exit={proc.returncode} | {line[0] if line else proc.stdout[:200]}")
print("gauges: " + ", ".join(
    f"{p.name} blob={sha1(p.read_bytes())}" for p in sorted(SC.glob(f"ord0310-q43*-on-block{TAG}.json"))))
