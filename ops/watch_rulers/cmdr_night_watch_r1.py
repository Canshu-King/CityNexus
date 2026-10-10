"""CMDR night-watch segment runner r1.

Why: the commander's turn budget is the scarce resource overnight. Polling by hand costs one turn per few
minutes and buys nothing; but landing must stay the commander's own action (AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1).
So this tool does ONLY the observation part of a watch cycle, and it does it for a whole segment in one shot:

  * drain the lane inbox through the same gated door the commander uses (the door itself refuses red blocks;
    nothing here edits a lane's words),
  * watch the authoritative line move,
  * watch for new / moved review refs and run the READ-ONLY re-cut gate over each new candidate,
  * print a compact event log plus one JSON summary at the end.

It never pushes, never lands, never writes the ledger by hand. If it prints LANDABLE, the commander still has
to run the landing gate herself - the marker is a prediction about the read-only re-cut, not a verdict.
"""
import io
import json
import os
import subprocess
import sys
import time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
REPO = "D:/moodle/CityNexus"
PY = sys.executable
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"

DURATION_MIN = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
INTERVAL_S = float(sys.argv[2]) if len(sys.argv) > 2 else 300.0

env = dict(os.environ)
env.pop("HTTP_PROXY", None)
env.pop("HTTPS_PROXY", None)


def emit(msg):
    print(time.strftime("%H:%M:%S ") + msg, flush=True)


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=900)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def tip():
    rc, out, _ = git("ls-remote", "origin", LINE)
    return (out.split("\t")[0].strip() if out else ""), rc


def review_heads():
    rc, out, _ = git("ls-remote", "--heads", "origin", "refs/heads/review/*")
    d = {}
    for line in out.splitlines():
        cols = line.split("\t")
        if len(cols) == 2 and len(cols[0].strip()) == 40:
            d[cols[1].strip()] = cols[0].strip()
    return d


def inbox_pending():
    try:
        return sorted(f for f in os.listdir(r"D:\moodle\_qoder_ledger_inbox") if f.endswith(".md"))
    except Exception:
        return []


emit("START segment duration_min=%s interval_s=%s" % (DURATION_MIN, INTERVAL_S))
last_tip, _ = tip()
seen = dict(review_heads())
known_inbox = set(inbox_pending())
recuted = set()
events = []
emit("baseline tip=%s review_refs=%d inbox=%d" % (last_tip[:12], len(seen), len(known_inbox)))

deadline = time.time() + DURATION_MIN * 60
while time.time() < deadline:
    time.sleep(INTERVAL_S)
    now = time.strftime("%H:%M:%S")
    try:
        t, _ = tip()
        if t and t != last_tip:
            emit("TIP_MOVED %s -> %s" % (last_tip[:12], t[:12]))
            events.append({"at": now, "kind": "tip_moved", "from": last_tip, "to": t})
            last_tip = t
        heads = review_heads()
        for ref, sha in sorted(heads.items()):
            if seen.get(ref) == sha:
                continue
            seen[ref] = sha
            if sha in recuted:
                continue
            short = ref.replace("refs/heads/", "")
            emit("REF_NEW %s = %s  (read-only re-cut next)" % (short, sha[:12]))
            recuted.add(sha)
            p = subprocess.run([PY, "cmdr_recut_r1.py", "--order", "WATCH", "--cand", sha],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               cwd=LIVE, env=env, timeout=1500)
            lines = [l.strip() for l in (p.stdout or "").splitlines() if l.strip()]
            verdict = "NO_OUTPUT"
            for l in lines:
                if l.startswith("RECUT "):
                    verdict = "LANDABLE_PREDICTION " + l.split()[1]
                    break
                if l.startswith("FAST_FORWARD_POSSIBLE"):
                    verdict = "FF " + l[:120]
                    break
                if l.startswith("ABORT"):
                    verdict = "RECUT_ABORT"
                    break
            other = " / ".join(l for l in lines[1:3])[:160]
            emit("   %s  %s" % (verdict, other))
            events.append({"at": now, "kind": "candidate", "ref": short, "sha": sha,
                           "verdict": verdict, "detail": other})
        pend = set(inbox_pending())
        fresh = sorted(pend - known_inbox)
        if fresh:
            # READ-ONLY BY RULE (2026-09-30): this loop must never run `ledger_inbox_apply_r2.py --apply`.
            # Why: my own segment ran the write door every 240 s while a second commander instance was
            # draining the same inbox, and the door's dedupe only sees files that co-exist at the moment
            # it runs - the result was blocks inserted twice and refusals reported as empty rc=1.
            # Insertion is a commander action, taken in its own turn with the ledger re-read first.
            emit("INBOX_NEW %s  (read-only: the commander inserts, this loop never does)" % ", ".join(fresh))
            events.append({"at": now, "kind": "inbox_new", "files": fresh})
            known_inbox = pend
    except Exception as exc:
        emit("CYCLE_ERROR %s: %s" % (type(exc).__name__, str(exc)[:200]))
        events.append({"at": now, "kind": "error", "detail": str(exc)[:200]})

summary = {"segment_end": time.strftime("%Y-%m-%d %H:%M:%S %z"), "tip_end": last_tip,
           "review_ref_count": len(seen), "events": events,
           "landable_predictions": [e for e in events if e.get("verdict", "").startswith(("LANDABLE", "FF"))]}
emit("END events=%d landable_predictions=%d" % (len(events), len(summary["landable_predictions"])))
print(json.dumps(summary, ensure_ascii=False, indent=1))
io.open(os.path.join(LIVE, "_night_watch_r1_last.json"), "w", encoding="utf-8", newline="\n").write(
    json.dumps(summary, ensure_ascii=False, indent=1))
