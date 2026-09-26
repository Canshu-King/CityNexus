"""One patrol round: new lane commits, inbox drain, and what the ledger's top now says.

Written because a shift is mostly this loop, and doing it by hand each time is how a delivery gets
missed (a lane's work is only undelivered for as long as nobody looks).  It never lands anything --
it reports, and the landing is a deliberate separate call with the re-cut door and the gate.

  python cmdr_patrol_r1.py [--state FILE]
"""
import glob
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
INBOX = r"D:\moodle\_qoder_ledger_inbox"
LINE_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
LANDESH = "landed_" + LINE_REF.split("/")[-1]


def git(*args, **kw):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=kw.get("timeout", 600))
    return p.returncode, p.stdout, p.stderr


def main():
    state_path = os.path.join(HERE, "patrol", "cmdr_patrol_state.json")
    if "--state" in sys.argv:
        state_path = sys.argv[sys.argv.index("--state") + 1]
    seen = {}
    if os.path.isfile(state_path):
        seen = json.load(io.open(state_path, encoding="utf-8"))
    report = {"at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "new_activity": [],
              "inbox": None, "ledger_top": [], "errors": []}

    rc, _, err = git("fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--quiet", timeout=900)
    if rc:
        report["errors"].append("fetch rc=%d %s" % (rc, err.strip()[:200]))
    rc, out, _ = git("ls-remote", "origin")
    refs = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[1]] = parts[0]
    tip = refs.get(LINE_REF)
    report["tip"] = tip
    rc, subj, _ = git("log", "-1", "--format=%h %ad %s", tip or "HEAD")
    report["tip_subject"] = subj.strip()[:160]

    # Any lane branch whose tip I have not seen, and which is not already inside the line, is work
    # that exists and has not been landed.  Superseded drafts are excluded by the ancestor test.
    for ref, sha in sorted(refs.items()):
        if not re.match(r"refs/heads/(review/|agent/|cmdr/)", ref):
            continue
        if seen.get(ref) == sha:
            continue
        rc, _, _ = git("merge-base", "--is-ancestor", sha, tip or "HEAD")
        # `git()` returns (rc, stdout, stderr): --is-ancestor answers with the EXIT CODE, not the text.
        rc, meta, _ = git("log", "-1", "--format=%h|%ad|%s", sha)
        report["new_activity"].append({
            "ref": ref, "sha": sha, "meta": meta.strip()[:150],
            "already_in_the_line": rc == 0, "first_time_seen": ref not in seen})
        seen[ref] = sha

    p = subprocess.run([sys.executable, os.path.join(HERE, "ledger_inbox_apply_r1.py"), "--apply"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=900, cwd=HERE)
    report["inbox"] = {"rc": p.returncode, "lines": [l for l in (p.stdout or "").splitlines()
                                                     if re.search(r"inbox blocks|tally|INSERTED|REFUSED", l)][:12]}

    text = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    heads = re.findall(r"(?m)^### .*$", text)
    report["ledger_top"] = heads[:4]

    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    io.open(state_path, "w", encoding="utf-8", newline="\n").write(json.dumps(seen, indent=1))
    blob = hashlib.sha1(b"blob %d\0" % len(json.dumps(report).encode()) + json.dumps(report).encode())
    out_path = os.path.join(HERE, "patrol", "patrol_%s.json" % time.strftime("%H%M%S"))
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(json.dumps(report, ensure_ascii=False, indent=1))

    print("TIP %s  %s" % ((tip or "?")[:12], report["tip_subject"]))
    # Only things that are NOT already inside the line are actionable; superseded drafts stay in the file.
    fresh = [a for a in report["new_activity"] if not a["already_in_the_line"]]
    print("activity not yet in the line: %d (full list in the report)" % len(fresh))
    for a in fresh[:8]:
        print("   %-56s %-12s first_seen=%s  %s" % (a["ref"].replace("refs/heads/", ""), a["sha"][:12],
                                                    a["first_time_seen"], a["meta"][:96]))
    print("inbox: %s" % " | ".join(report["inbox"]["lines"][:4]))
    print("ledger top: %s" % (report["ledger_top"][0][:100] if report["ledger_top"] else "-"))
    print("report=%s (%d B)" % (out_path, os.path.getsize(out_path)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
