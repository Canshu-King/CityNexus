"""CMDR batch landing driver r1.

Why this exists: while I was verifying one generation, thirteen lane branches piled up.
Each one still has to pass the same two gates a single landing passes -- read-only re-cut
(lane-byte equality per changed file) then the preflight/land gate. This driver only
sequences those existing tools; it adds no judgement and bypasses nothing. If a re-cut or
a gate refuses, the candidate is skipped and reported, never hand-merged.

Order is priority order: the two big absorbed modules first, then the rest.
"""
import json
import os
import subprocess
import time
import sys

LIVE = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
REPO = "D:/moodle/CityNexus"
PY = sys.executable
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"

# (order, ref) -- the sha is resolved from the remote at run time, so a mistyped hash
# can never be landed by this driver.
#
# 2026-10-04 03:22: this default used to be ("ORD-0465", ...).  A `--help` invocation -- which
# the hand-rolled scan below does not recognise -- fell through to that default and landed
# ORD-0465 by accident (the merge commit 65195d1b, whose tree equals its first parent's, so
# zero bytes changed).  A sequencer that lands a remembered order when handed a flag it does
# not understand is a foot-gun, so the queue is now mandatory: there is no default to fall to.
QUEUE = []

# An overnight patrol has to fire this driver many times with different queues, and rewriting the literal above
# on every round is both slow and an edit to the sequencer's own source while it can be running.  So the queue
# may be handed in on the command line instead, in the same order semantics:
#   --queue ORD-0447:refs/heads/review/qoder-0447-share-copy-r1,ORD-0435:refs/heads/review/...
# Malformed or empty entries abort rather than silently landing nothing while reporting a clean run.
for _i, _a in enumerate(sys.argv):
    if _a == "--queue":
        _spec = sys.argv[_i + 1] if _i + 1 < len(sys.argv) else ""
        _parsed = []
        for _item in [s.strip() for s in _spec.split(",") if s.strip()]:
            if ":" not in _item:
                raise SystemExit("BAD_QUEUE_ITEM %r (expected ORDER:ref)" % _item)
            _o, _r = _item.split(":", 1)
            _parsed.append((_o.strip(), _r.strip()))
        if not _parsed:
            raise SystemExit("EMPTY_QUEUE_AFTER_PARSE %r" % _spec)
        QUEUE = _parsed
if not QUEUE:
    raise SystemExit("NO_QUEUE: refusing to run without an explicit --queue ORDER:ref[,ORDER:ref...]")
print("QUEUE = %s" % [o for o, _ in QUEUE], flush=True)

env = dict(os.environ)
env.pop("HTTP_PROXY", None)
env.pop("HTTPS_PROXY", None)


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=900)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def run(argv, timeout=1500):
    p = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=LIVE, env=env, timeout=timeout)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


results = []
rc, tip, _ = git("ls-remote", "origin", LINE)
tip = tip.split("\t")[0].strip() if tip else ""
print("START tip=%s" % tip[:12], flush=True)

for order, ref in QUEUE:
    row = {"order": order, "ref": ref, "cand": None, "recut": None, "landed": False, "tip_after": None, "note": ""}
    try:
        rrc, rout, rerr = git("ls-remote", "origin", ref)
        cand = (rout or "").split("\t")[0].strip() if rout else ""
        if rrc != 0 or len(cand) != 40:
            row["note"] = "REF_UNRESOLVED rc=%s out=%s err=%s" % (rrc, rout[:80], rerr[:80])
            results.append(row)
            print("SKIP  %s ref does not resolve to a 40-hex" % order, flush=True)
            continue
        row["cand"] = cand
        rc, out, err = run([PY, "cmdr_recut_r1.py", "--order", order, "--cand", cand], timeout=4200)
        lines = out.strip().splitlines()
        # The re-cut prints notes (network guard, shallow-boundary repair) before its verdict, so the verdict
        # is FOUND BY SCANNING, never by index -- reading line 0 as the verdict made a repair notice look
        # like a refusal and skipped a candidate that was about to merge cleanly (seen 16:58).
        ff_line = [l for l in lines if l.strip().startswith("FAST_FORWARD_POSSIBLE")]
        verdict_line = [l for l in lines if l.strip().startswith("RECUT")]
        head = verdict_line[0] if verdict_line else (lines[0] if lines else "")
        if ff_line:
            # the candidate is a descendant of the live tip: pure fast-forward, its own bytes, same gate.
            recut = cand
            row["recut"] = recut
            row["note"] = "FF " + ff_line[0].strip()[:160]
            print("FF    %s candidate is a descendant of the tip; sending to the gate as-is" % order, flush=True)
        elif rc != 0 or not head.startswith("RECUT"):
            row["note"] = "RECUT_" + (head[:120] if head else "NO_OUTPUT " + err[-200:]) + " || " + " / ".join(
                l.strip() for l in lines[1:4])
            results.append(row)
            print("SKIP  %s  %s" % (order, row["note"][:180]), flush=True)
            continue
        else:
            recut = head.split()[1]
            row["recut"] = recut
            row["note"] = " / ".join(l.strip() for l in lines[1:])[:200]
        # a batch ref must be unique per run: reusing a name from an earlier run makes the push
        # fail as non-fast-forward and hides a candidate that was actually clean
        ref = "refs/heads/review/cmdr-batch-%s-%s" % (order.lower(), time.strftime("%H%M%S"))
        prc, _, perr = git("push", "origin", "%s:%s" % (recut, ref))
        if prc != 0:
            row["note"] += " || PUSH_FAILED " + perr[:120]
            results.append(row)
            print("SKIP  %s push failed %s" % (order, perr[:100]), flush=True)
            continue
        lrc, lout, _ = run([PY, "preflight_and_land_r7.py", "--candidate-ref", ref.replace("refs/heads/", ""),
                            "--order", order, "--land", "--out", "%s/_pf_batch_%s.json" % (LIVE, order)])
        verdict = [l for l in lout.splitlines() if l.startswith("verdict=")]
        landed = '"landed": true' in lout
        row["gate"] = (verdict[0][:120] if verdict else "no-verdict-line rc=%s" % lrc)
        row["landed"] = bool(landed)
        _, tip2, _ = git("ls-remote", "origin", LINE)
        row["tip_after"] = tip2.split("\t")[0].strip()[:12] if tip2 else "?"
        results.append(row)
        print("%s  %s  %s  tip=%s" % ("LAND" if landed else "REFUSE", order, row["gate"][:70], row["tip_after"]), flush=True)
    except Exception as exc:
        row["note"] = "DRIVER_EXCEPTION %s: %s" % (type(exc).__name__, str(exc)[:200])
        results.append(row)
        print("ERROR %s  %s" % (order, row["note"][:170]), flush=True)

print(json.dumps(results, ensure_ascii=False, indent=1))
json.dump(results, open(LIVE + "/_batch_land_r1.json", "w", encoding="utf-8"), indent=1)
