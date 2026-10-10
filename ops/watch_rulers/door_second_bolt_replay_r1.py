"""Read-only replay of the ledger door's SECOND bolt (every literal 40-hex must resolve in
D:/moodle/CityNexus, unless the same line declares it non-retrievable AND the same paragraph carries a
value that does resolve).

This does not reimplement the rule: it execs lines 42..112 of `ledger_insert_after_r2.py` verbatim, so
the regexes and the paragraph logic are the door's own, not my memory of them. The only thing dropped
is the JSON side-effect write on line 113+, and the `git fetch` line is kept because an unfetched lane
commit is exactly what produced the 21:42 / 00:45 false alarms. The verdict is still a rehearsal: the
door is the door.

    python door_second_bolt_replay_r1.py <block.md> [<more blocks>]
"""
import io
import json
import os
import re
import subprocess
import sys
import textwrap

DOOR = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/ledger_insert_after_r2.py"
LO, HI = 42, 112   # inclusive, 1-based: `import re as _re` .. the carried-value print


def bolt(block_file):
    src = io.open(DOOR, encoding="utf-8").read().splitlines()[LO - 1:HI]
    body = textwrap.dedent("\n".join(src))
    if "return 9" not in body or "_NON_RETRIEVABLE_PAT" not in body:
        raise SystemExit("REFUSE: the extracted range is not the bolt I meant to replay")
    ns = {"io": io, "json": json, "os": os, "subprocess": subprocess, "sys": sys, "re": re}
    exec("def _bolt(block_file):\n" + "".join("    " + l + "\n" for l in body.splitlines()), ns)
    return ns["_bolt"](block_file)


def main():
    for path in sys.argv[1:]:
        rc = bolt(path)
        verdict = "WOULD REFUSE (rc=%d)" % rc if rc else "WOULD CARRY"
        print("%-28s -> %s   [rehearsal, not a verdict]" % (os.path.basename(path), verdict))


if __name__ == "__main__":
    main()
