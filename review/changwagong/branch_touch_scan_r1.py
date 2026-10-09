#!/usr/bin/env python3
"""Which branches -- local AND remote -- have a commit touching a given file.

Why: `git ls-remote` cannot see a lane branch that lives only in the shared object store on this
machine.  A collision this lane hit today (ORD-0553, the discovery batch row) was exactly such a
branch: named under refs/heads/, 2 minutes older than my own commit, absent from the remote.
"""

import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TARGETS = {
    "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
    "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx",
    "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx",
}


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout


def main():
    out = git("for-each-ref", "--format=%(refname)%09%(committerdate:iso8601)%09%(objectname)",
              "refs/heads", "refs/remotes/origin")
    rows = [ln.split("\t") for ln in out.splitlines() if ln.strip()]
    rows = [r for r in rows if len(r) == 3]
    rows.sort(key=lambda r: r[1], reverse=True)
    recent = rows[:70]
    print("refs_seen=%d scanned=%d (newest first)" % (len(rows), len(recent)))
    for ref, when, sha in recent:
        stat = git("show", "--format=", "--numstat", sha)
        touched = sorted({t for t in TARGETS if any(t in ln for ln in stat.splitlines())})
        if touched:
            head = git("log", "-1", "--format=%h %ad %s", "--date=format:%m-%d %H:%M", sha).strip()
            print("TOUCH %-62s %s | %s" % (ref, when, head))
            for t in touched:
                print("      file: %s" % t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
