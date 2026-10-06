# -*- coding: utf-8 -*-
"""Cadence hook for the ledger-mirror self-check: one call after each insertion, one append-only line, exit code.

Ruling: "节拍随代插腿即可，别新开长循环" - so this is not a daemon. The inserter (the sequencer's own gate, which
this file never touches) calls it once per applied block; it does one thing else: it appends one JSON line to a
trail so the cadence is auditable later without anyone having kept a process alive.

    import sys; sys.path.insert(0, "<repo root>")
    from tools.cnx_ledger_mirror_sync_hook_r1 import run_after_insert
    st = run_after_insert()                    # or run_after_insert(trail="D:/…/mirror_sync_trail.jsonl")
    if st["exit_code"] != 0:
        ...alarm with st["verdict"] - CURRENT / LAGGING / DIVERGED / NOT_ANSWERED...

It delegates the measurement to the empty-floor revision of the standing tool
(`cnx_ledger_mirror_sync_check_r2`, ORD-0574: a both-sides-empty comparison is NOT_ANSWERED, not
CURRENT), which in turn
delegates the remote read to the reader (`cnx_ledger_mirror_reader_r1`); nothing here re-implements a proof, so
there is exactly one place where "is this body complete" is decided.

Trail line shape (append-only, one json object per call):

    {"at","hook","tool","verdict","exit_code","local_blob","remote_blob","points":[matched,compared],
     "self_proved","local_bytes","remote_bytes","first_differing_line"}

Exit codes: 0 CURRENT / 7 LAGGING / 8 DIVERGED / 9 the reader refused or the empty floor fired
(NOT_ANSWERED) / 6 this hook's own guard fired.

Counter-arms, run by `--self-test` before anyone trusts the hook. Each must fail closed, and the arm itself is
checked - an arm that passes is reported as a defect of this file, not as a green:
  flip_a_byte    one byte of the local ledger flipped IN MEMORY must stop the hook reporting CURRENT
  empty_trail    with a fresh trail the history query must answer "no previous line", never an implied ok
  unwritable_trail  a trail path that cannot be written must raise `hook_guard` naming it, and the measurement
                    must still be returned - losing the reading is worse than losing the log line
"""
import argparse
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.cnx_ledger_mirror_sync_check_r2 import check_sync  # noqa: E402
from tools.cnx_ledger_mirror_reader_r1 import IncompleteRemoteRead  # noqa: E402

HOOK = "cnx_ledger_mirror_sync_hook_r2"
TOOL = "cnx_ledger_mirror_sync_check_r2"
# the trail deliberately does NOT live in the human inbox: the inserter globs that directory for candidate
# blocks, and a machine audit line must never look like one. Override with CITYNEXUS_MIRROR_SYNC_TRAIL.
DEFAULT_TRAIL = os.environ.get("CITYNEXUS_MIRROR_SYNC_TRAIL") or r"D:\moodle\_mirror_sync\trail.jsonl"


class HookGuard(Exception):
    """Raised when this hook's own guard fires (an unwritable trail, an arm that did not bite)."""

    def __init__(self, leg, detail):
        Exception.__init__(self, "%s: %s" % (leg, detail))
        self.leg, self.detail = leg, detail


def trail_line_count(trail):
    if not os.path.exists(trail):
        return 0
    return sum(1 for l in io.open(trail, encoding="utf-8", errors="replace") if l.strip())


def append_trail(trail, line):
    """Append one line, proving it landed. A trail that silently stops growing is how a cadence dies."""
    try:
        parent = os.path.dirname(trail)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with io.open(trail, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
            fh.flush()
    except (IOError, OSError) as e:
        raise HookGuard("trail_write", "cannot append to %r (%s) - the reading is returned, the log line is not"
                        % (trail, type(e).__name__))
    back = io.open(trail, encoding="utf-8", errors="replace").read().splitlines()
    if not back or json.loads(back[-1])["at"] != line["at"]:
        raise HookGuard("trail_readback", "appended to %s but the last line is not this reading" % trail)
    return len(back)


def run_after_insert(trail=DEFAULT_TRAIL, arm="", **kw):
    """One measurement, one trail line, one exit code. Returns the reading even when the trail guard fires."""
    st = check_sync(arm=arm, **kw)
    line = {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "hook": HOOK, "tool": TOOL, "verdict": st["verdict"],
            "exit_code": st["exit_code"], "local_blob": st["local_blob"], "remote_blob": st["remote_blob"],
            "points": [st["points_matched"], st["points_compared"]], "self_proved": st["remote_self_proved"],
            "local_bytes": st["local_bytes"], "remote_bytes": st["remote_bytes"],
            "first_differing_line": st["first_differing_line"], "arm": arm or "none"}
    before = trail_line_count(trail)
    line["trail_line"] = before + 1
    guard = None
    try:
        line["trail_lines_after"] = append_trail(trail, line)
        line["appended"] = True
    except HookGuard as e:
        guard = {"leg": e.leg, "detail": e.detail[:220]}
        line["appended"] = False
    line["trail_guard"] = guard
    line["trail_path"] = trail
    return line


def history_tail(trail=DEFAULT_TRAIL, n=3):
    if not os.path.exists(trail) or trail_line_count(trail) == 0:
        return {"trail": trail, "lines": 0, "last": None,
                "meaning": "no previous line - the cadence has not run here yet, which is NOT an ok"}
    rows = [json.loads(l) for l in io.open(trail, encoding="utf-8", errors="replace").read().splitlines()
            if l.strip()]
    return {"trail": trail, "lines": len(rows), "last": rows[-n:]}


def self_test(trail=DEFAULT_TRAIL, **kw):
    """Run the hook once for real, then every arm. An arm that does not fail closed is this file's defect.

    The arms write to a scratch trail, never to the production one: an arm's reading is a lie on purpose, and a
    log line is the audit of what the box actually looked like.
    """
    scratch = os.path.join(os.environ.get("TEMP", "/tmp"), "cnx_selftest_trail.jsonl")
    rows = []
    base = run_after_insert(trail=trail, **kw)
    rows.append({"arm": "none", "verdict": base["verdict"], "appended": base["appended"],
                 "trail_lines_after": base.get("trail_lines_after"), "exit_code": base["exit_code"],
                 "trail": trail})
    flip = run_after_insert(trail=scratch, arm="flip_a_byte", **kw)
    flip_ok = flip["verdict"] != "CURRENT" and flip["exit_code"] != 0
    rows.append({"arm": "flip_a_byte", "verdict": flip["verdict"], "exit_code": flip["exit_code"],
                 "refused_to_call_it_current": flip_ok,
                 "local_blob_is_not_the_base": flip["local_blob"] != base["local_blob"],
                 "wrote_only_to_scratch": flip["trail_path"] == scratch})
    hist = history_tail(trail)
    rows.append({"arm": "history_after_a_run", "lines": hist["lines"],
                 "last_verdict": (hist["last"] or [{}])[-1]["verdict"] if hist["last"] else None,
                 "reading": "the line this hook just wrote is readable back, so cadence is auditable without "
                            "a daemon"})
    empty = history_tail(os.path.join(os.environ.get("TEMP", "/tmp"),
                                      "cnx_no_such_trail_%d.jsonl" % os.getpid()))
    rows.append({"arm": "empty_trail", "lines": empty["lines"], "last_is_none": empty["last"] is None,
                 "refuses_to_imply_ok": empty["last"] is None and empty["lines"] == 0})
    blocker = os.path.join(os.environ.get("TEMP", "/tmp"), "cnx_trail_blocker_%d" % os.getpid())
    bad = os.path.join(blocker, "trail.jsonl")
    io.open(blocker, "w", encoding="utf-8").write("this path is a file, so it can never be a directory\n")
    try:
        broken = run_after_insert(trail=bad, **kw)
        guard_fired = broken["appended"] is False and (broken["trail_guard"] or {}).get("leg") == "trail_write"
        reading_kept = broken["verdict"] in ("CURRENT", "LAGGING", "DIVERGED")
        rows.append({"arm": "unwritable_trail", "guard_fired": guard_fired, "reading_kept": reading_kept,
                     "leg": (broken["trail_guard"] or {}).get("leg"),
                     "why_unwritable": "the intended directory is occupied by a file, so the append cannot "
                                       "create it - a real shape a trail dies by"})
    except HookGuard as e:
        rows.append({"arm": "unwritable_trail", "guard_fired": True, "leg": e.leg,
                     "detail": e.detail[:160], "reading_kept": False})
    try:
        os.remove(blocker)
    except OSError:
        pass
    for p in (scratch,):
        try:
            os.remove(p)
        except OSError:
            pass
    checks = {r["arm"]: r for r in rows}
    ok = bool(checks["flip_a_byte"]["refused_to_call_it_current"]
              and checks["flip_a_byte"]["wrote_only_to_scratch"]
              and checks["empty_trail"]["refuses_to_imply_ok"]
              and checks["unwritable_trail"].get("guard_fired")
              and checks["unwritable_trail"].get("reading_kept") and base["appended"])
    return rows, ok, base


def main():
    ap = argparse.ArgumentParser(prog="cnx_ledger_mirror_sync_hook_r1.py")
    ap.add_argument("--trail", default=DEFAULT_TRAIL)
    ap.add_argument("--last", type=int, default=0, help="print the last N trail lines instead of running")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--arm", default="", choices=("", "flip_a_byte"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    if a.last:
        h = history_tail(a.trail, a.last)
        print(json.dumps(h, ensure_ascii=False, indent=1))
        return 0 if h["lines"] else 7
    if a.self_test:
        rows, ok, base = self_test(a.trail)
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))
        doc = {"hook": HOOK, "base_reading": base, "arms": rows, "arms_all_correct": ok}
        if a.out:
            io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print(json.dumps({"verdict": base["verdict"], "arms_all_correct": ok,
                          "exit_code": base["exit_code"]}, ensure_ascii=False))
        return 0 if ok else 6
    line = run_after_insert(a.trail, arm=a.arm)
    if a.out:
        io.open(a.out, "w", encoding="utf-8").write(json.dumps(line, ensure_ascii=False, indent=1))
    print(json.dumps(line, ensure_ascii=False))
    return line["exit_code"]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IncompleteRemoteRead as e:
        print(json.dumps({"leg": e.leg, "detail": str(e)[:300], "note": "the reader refused; no bytes were "
                                                                        "accepted and no verdict is written"},
                         ensure_ascii=False))
        raise SystemExit(9)
