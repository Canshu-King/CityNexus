"""ORD-0504 book-screen hand -- the two passes the order asks for, on the restored tip source.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/book_screen_post_r1.py

The control cycle finishes by writing the original bytes back and leaving the *mutant* bundle on the
port, so this re-builds from the restored tree, points this lane's own front at that bundle, witnesses
that the bytes the port answers are the bytes on disk, and only then runs the arms twice. Two passes
because one reading of a screen is a anecdote; a state the arms cannot reproduce is not evidence.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_screen_controls_r1 as ctl  # noqa: E402  (main is guarded, import is inert)

OUT = ctl.TREE / "review" / "ord0504" / "book_screen_post_r1.txt"
PASSES = ["review/ord0504/book_screen_pass_post1_r1.json",
          "review/ord0504/book_screen_pass_post2_r1.json"]


def disk_sha1(entry: str) -> str:
    return ctl.sha1((ctl.LANE / "dist_book_tip" / entry.lstrip("/")).read_bytes())


def main() -> int:
    source_before = ctl.sha1(ctl.TARGET.read_bytes())
    lines = [
        "ORD-0504 book-screen post-cycle passes",
        "V8Experience.tsx sha1 at the start of this run = %s" % source_before,
        "git status --porcelain -- frontend/src/app/V8Experience.tsx = %r"
        % ctl.run(["git", "status", "--porcelain", "--",
                   "frontend/src/app/V8Experience.tsx"], cwd=ctl.TREE).stdout,
        "",
    ]
    ctl.rebuild("dist_book_tip")
    ctl.restart_front("dist_book_tip")
    served = ctl.served_entry()
    on_disk = disk_sha1(served["entry"])
    lines += [
        "served entry %s sha1 %s (%d B)" % (served["entry"], served["sha1"], served["bytes"]),
        "bytes of dist_book_tip on disk: sha1 %s" % on_disk,
        "served bytes == bytes of the clean bundle this run built: %s" % (on_disk == served["sha1"]),
        "",
    ]
    if on_disk != served["sha1"]:
        lines.append("REFUSE: the port is not answering the bundle just built")
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("\n".join(lines))
        return 1

    for index, out_path in enumerate(PASSES, start=1):
        env = dict(os.environ, BOOK_OUT=out_path)
        r = subprocess.run([ctl.NODE, "review/ord0504/book_screen_facts_r1.js"], cwd=str(ctl.TREE),
                           capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        payload = json.loads((ctl.TREE / out_path).read_text(encoding="utf-8"))
        reds = [x["arm"] for x in payload.get("results", []) if not x.get("pass")]
        lines += [
            "=== pass %d -> %s" % (index, out_path),
            "    exit=%s  %s" % (r.returncode, [line for line in r.stdout.splitlines()
                                                if line.startswith("ARMS=")] or ["no-summary"]),
            "    driver errors: %s" % (payload.get("driver_error") or "none"),
            "    red arms: %s" % (sorted(reds) or "none"),
            "",
        ]
    lines.append("V8Experience.tsx sha1 at the end of this run = %s"
                 % ctl.sha1(ctl.TARGET.read_bytes()))
    lines.append("source unchanged by this run: %s"
                 % (ctl.sha1(ctl.TARGET.read_bytes()) == source_before))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
