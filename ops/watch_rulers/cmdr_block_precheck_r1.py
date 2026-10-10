"""CMDR block pre-check r1 - let a lane test its own delivery block against the SAME door before submitting.

Why: four blocks stalled at the ledger door tonight for the same reason - a three-digit number on a line with no
resolvable coordinate next to it. The door refuses (correctly), the lane only learns later, and I have to relay
the verdict back. This wrapper calls the ruler the door calls - it does not reimplement, weaken, or replace it -
so a lane can self-check in one command before writing the file into the inbox.

Usage:
    python cmdr_block_precheck_r1.py <path-to-block.md>
Exit codes mirror the ruler: 0 = would pass, 8 = the ruler says RED (offending lines printed), other = tool error.
"""
import os
import subprocess
import sys

LIVE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def main() -> int:
    # Lanes were told the CLI takes --file, so accept either form.  This only affects argument
    # parsing; the ruler call and its exit semantics below are unchanged.
    argv = [a for a in sys.argv[1:]]
    if "--file" in argv:
        argv = [a for a in argv if a != "--file"]
    if len(argv) < 1:
        print("usage: cmdr_block_precheck_r1.py <block-file>")
        return 2
    target = argv[0]
    if not os.path.isfile(target):
        print("NOT_A_FILE %s" % target)
        return 2
    env = {k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY")}
    # --expect-clean is the flag the door itself uses; without it the ruler's own exit semantics differ,
    # so a selftest that "passed" here could still be refused there. Call it the same way the door does.
    p = subprocess.run([PY, "claim_coordinate_check_r7.py", "--text", target, "--expect-clean"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=LIVE, env=env, timeout=900)
    out = (p.stdout or "") + (p.stderr or "")
    print(out.strip()[:4000])
    if p.returncode == 0:
        print("PRECHECK=GREEN you may drop the file into D:\\moodle\\_qoder_ledger_inbox\\<lane>_<HHMM>.md")
    else:
        print("PRECHECK=RED fix the flagged lines by ADDING a same-line coordinate (a 40-hex that "
              "git cat-file -t resolves, or path:line inside the authoritative tree, or a unit-bearing "
              "form like 1203 B / :4921 / http_status=200). Do not delete the number, do not ask for a bypass.")
    return p.returncode


if __name__ == "__main__":
    raise SystemExit(main())
