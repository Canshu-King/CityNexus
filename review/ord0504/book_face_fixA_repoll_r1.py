"""ORD-0504 A -- re-poll the fixed generation with the delivered ruler, one evidence file per pass.

The cycle wrote both passes of a generation into one sink, so the first pass survived only as a summary
line. This run takes the same generation again with the ruler as delivered (its `vocabulary_source` label
was pointing at a rotted line) and gives each pass its own JSON.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/book_face_fixA_repoll_r1.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_screen_controls_r1 as ctl  # noqa: E402

DIST = "dist_fixA"
FIX_ENTRY_SHA1 = "094acbed0d8d9ef93514a4aad0e0924afd537af2"  # the cycle's fix generation, over bytes
OUT = ctl.TREE / "review" / "ord0504" / "book_face_fixA_repoll_r1.txt"
PASSES = [("pass1", "review/ord0504/book_screen_armsA_fixpass1.json"),
          ("pass2", "review/ord0504/book_screen_armsA_fixpass2.json")]


def main() -> int:
    lines = ["ORD-0504 A re-poll of the fixed generation"]
    shipped = ctl.TARGET.read_bytes()
    status = ctl.run(["git", "status", "--porcelain", "--", "frontend/src/app/V8Experience.tsx"],
                    cwd=ctl.TREE).stdout
    lines.append("V8Experience.tsx本机 sha1 %s | git status for that path = %r"
                 % (ctl.sha1(shipped), status))
    if status.strip():
        raise SystemExit("REFUSE: the product file is not the committed one; repolling would grade a mutant")

    ctl.rebuild(DIST)
    ctl.restart_front(DIST)
    served = ctl.served_entry()
    on_disk = ctl.sha1((ctl.LANE / DIST / served["entry"].lstrip("/")).read_bytes())
    lines.append("served %s sha1 %s | equals the bundle this run built: %s | equals the cycle's fix "
                 "generation (%s): %s"
                 % (served["entry"], served["sha1"], on_disk == served["sha1"], FIX_ENTRY_SHA1,
                    served["sha1"] == FIX_ENTRY_SHA1))
    if served["sha1"] != FIX_ENTRY_SHA1 or on_disk != served["sha1"]:
        raise SystemExit("REFUSE: the port is not answering the fix generation this paper claims")

    for name, sink in PASSES:
        env = dict(os.environ, BOOK_OUT=sink)
        done = subprocess.run([ctl.NODE, "review/ord0504/book_screen_facts_r1.js"], cwd=str(ctl.TREE),
                              capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        payload = json.loads((ctl.TREE / sink).read_text(encoding="utf-8"))
        reds = sorted(x["arm"] for x in payload.get("results", []) if not x.get("pass"))
        summary = [line for line in done.stdout.splitlines() if line.startswith("ARMS=")]
        lines.append("=== %s -> %s" % (name, sink))
        lines.append("    %s | exit %s | driver error: %s"
                     % (summary[-1] if summary else "no-summary", done.returncode,
                        payload.get("driver_error") or "none"))
        lines.append("    red arms: %s" % (reds or "none"))
        lines.append("    generated_at: %s" % payload.get("generated_at"))
        lines.append("")

    lines.append("both passes green with zero reds: %s"
                 % all("FAILED=0" in line for line in lines if line.strip().startswith("ARMS=")))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
