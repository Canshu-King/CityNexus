"""Wait (bounded) for something that needs the commander: a new ledger block, a moved tip, or a new
review branch for an order I dispatched tonight.  Prints one line per change and exits.

usage: python _cmdr_wait_for_event_r1.py [--minutes 8] [--tag ORDER1,ORDER2,...]
Read-only: it never writes, never inserts, never lands.
"""
import argparse
import json
import os
import subprocess
import sys
import time

LIVE = os.path.dirname(os.path.abspath(__file__))
REPO = "D:/moodle/CityNexus"
INBOX = "D:/moodle/_qoder_ledger_inbox"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
OPEN = ["0517", "0520", "0521", "0523", "0524", "0525", "0526", "0527", "0528", "0529",
        "0510", "0511", "0512", "0504", "0507", "0461", "0495", "0513", "0509", "0500", "0502"]

env = {k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY")}


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env, timeout=180)
    return p.stdout.strip()


def snapshot():
    inbox = sorted(f for f in os.listdir(INBOX) if f.endswith(".md")) if os.path.isdir(INBOX) else []
    tip = git("ls-remote", "origin", LINE).split("\t")[0][:12]
    refs = {}
    for line in git("ls-remote", "origin", "refs/heads/review/*").splitlines():
        sha, _, ref = line.partition("\t")
        if any(o in ref for o in OPEN):
            refs[ref.strip()] = sha.strip()[:12]
    return {"inbox": inbox, "tip": tip, "refs": refs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=8.0)
    a = ap.parse_args()
    base = snapshot()
    print("BASELINE tip=%s inbox=%d open_refs=%d" % (base["tip"], len(base["inbox"]), len(base["refs"])), flush=True)
    deadline = time.time() + a.minutes * 60
    seen_inbox = set(base["inbox"])
    while time.time() < deadline:
        time.sleep(20)
        cur = snapshot()
        for f in cur["inbox"]:
            if f not in seen_inbox:
                print("INBOX_NEW %s" % f, flush=True)
                seen_inbox.add(f)
        if cur["tip"] != base["tip"]:
            print("TIP_MOVED %s -> %s" % (base["tip"], cur["tip"]), flush=True)
            base["tip"] = cur["tip"]
        for ref, sha in cur["refs"].items():
            if base["refs"].get(ref) != sha:
                print("REF_NEW %s = %s" % (ref, sha), flush=True)
        base["refs"] = cur["refs"]
    print("WAIT_DONE at %s" % time.strftime("%H:%M:%S"), flush=True)


if __name__ == "__main__":
    sys.exit(main())
