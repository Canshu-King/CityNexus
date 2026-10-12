# -*- coding: utf-8 -*-
"""Landing readiness: is a pending branch still safe to land on the current authoritative tip?

Why this exists: the authoritative line is a rebuilt, parentless tree, so `merge-base` answers nothing and a
branch that read "one file, five added lines" at cut time can quietly start clobbering another lane's bytes
the moment the tip moves over the same file. That happened to
review/cff87c64-ord0562-english-count-nouns-r4 while its delivery block was still waiting to be landed.
Ancestry cannot see this; blob equality can, so that is the only test used here.

Read-only by construction: `git ls-remote` and `git rev-parse <sha>:<path>` and nothing else. It never
writes, never fetches into a working tree, never moves a ref, never opens a store.

Verdicts per item, in the order they are decided:
  LANDED           the tip's blob equals the branch's blob -- the bytes are already there, nothing to land
  DRIFTED_ON_TIP   the tip's blob is not the base this branch was cut against -- landing this file now
                   overwrites somebody else's change; re-cut first
  CLEAN            the tip still holds exactly the base bytes -- landing is a pure apply
  MISSING          a blob or a published head could not be read (renamed path, unpublished ref)

`--selftest` is the discriminating arm: it feeds one case that MUST read DRIFTED_ON_TIP and one that MUST
read LANDED, and exits non-zero when the ruler is deaf. A lock that never bites is not a lock.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"


def git(*args):
    proc = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True)
    out = proc.stdout.decode("utf-8", "replace").strip()
    err = proc.stderr.decode("utf-8", "replace").strip()
    return proc.returncode, out, err


def published_sha(ref):
    """Resolve a branch to the bytes the server actually holds for it."""
    rc, out, err = git("ls-remote", "--refs", "origin", ref)
    if rc == 0 and out:
        return out.split()[0], None
    rc, out, err = git("rev-parse", ref)          # a tip sha is passed straight through
    if rc == 0 and len(out) == 40:
        return out, None
    return None, "rc=%s %s" % (rc, (err or out).splitlines()[-1][:140] if (err or out) else "")


def blob_at(sha, path):
    rc, out, err = git("rev-parse", "%s:%s" % (sha, path))
    if rc != 0 or len(out) != 40:
        return None, "rc=%s %s" % (rc, err.splitlines()[-1][:140] if err else "no such path")
    return out, None


def judge(name, branch_ref, path, base_tip, tip_sha):
    row = {"name": name, "path": path, "branch": branch_ref, "base_tip": base_tip, "tip_sha": tip_sha}
    branch_sha, why = published_sha(branch_ref)
    if branch_sha is None:
        row.update(verdict="MISSING", reason="branch head: " + why)
        return row
    tip_blob, why = blob_at(tip_sha, path)
    if tip_blob is None:
        row.update(verdict="MISSING", reason="tip blob: " + why)
        return row
    branch_blob, why = blob_at(branch_sha, path)
    if branch_blob is None:
        row.update(verdict="MISSING", reason="branch blob: " + why)
        return row
    base_blob, why = blob_at(base_tip, path)
    if base_blob is None:
        row.update(verdict="MISSING", reason="base blob: " + why)
        return row
    row.update(branch_sha=branch_sha, tip_blob=tip_blob, branch_blob=branch_blob, base_blob=base_blob)
    if branch_blob == tip_blob:
        row["verdict"] = "LANDED"
    elif base_blob != tip_blob:
        row["verdict"] = "DRIFTED_ON_TIP"
    else:
        row["verdict"] = "CLEAN"
    return row


# What this lane has open. `base_tip` is the authoritative tip each branch was cut against, read at cut
# time: a branch stays landable only while the tip still holds those exact bytes for that path.
ITEMS = [
    {"name": "singular_plural_component",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r5",
     "path": "frontend/src/app/V8Experience.tsx",
     "base_tip": "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"},
    {"name": "route_provenance_vocabulary",
     "branch": "refs/heads/review/cff87c64-ord0568-route-provenance-gloss-r3",
     "path": "frontend/src/lib/displayVocabulary.ts",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
    {"name": "route_provenance_panel",
     "branch": "refs/heads/review/cff87c64-ord0568-route-provenance-gloss-r3",
     "path": "frontend/src/features/recovery/V14RecoveryTruthPanel.tsx",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
]

# The discriminating arm. r4's component file was cut on eaf4069e and the tip has since changed that same
# file, so a ruler that cannot see that is blind. LocaleContext's counted keys from that same branch did
# land, so a ruler that calls everything DRIFTED is equally blind.
SELFTEST = [
    {"name": "must_read_DRIFTED_ON_TIP", "expect": "DRIFTED_ON_TIP",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r4",
     "path": "frontend/src/app/V8Experience.tsx",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
    {"name": "must_read_LANDED", "expect": "LANDED",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r4",
     "path": "frontend/src/i18n/LocaleContext.tsx",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
    {"name": "must_read_MISSING", "expect": "MISSING",
     "branch": "refs/heads/review/cff87c64-ord0562-english-count-nouns-r4",
     "path": "frontend/src/i18n/NoSuchFile_r1.tsx",
     "base_tip": "eaf4069e5d07a3dacc1ec33a0be515119208e16e"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tip-ref", default=TIP_REF)
    ap.add_argument("--json", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    tip_sha, why = published_sha(args.tip_ref)
    if tip_sha is None:
        print("REFUSED: the tip could not be read: " + why)
        return 2

    rows = [judge(i["name"], i["branch"], i["path"], i["base_tip"], tip_sha) for i in ITEMS]
    report = {"tip_ref": args.tip_ref, "tip_sha": tip_sha, "items": rows}

    failures = []
    if args.selftest:
        probes = [judge(i["name"], i["branch"], i["path"], i["base_tip"], tip_sha) for i in SELFTEST]
        report["selftest"] = probes
        for probe, want in zip(probes, [s["expect"] for s in SELFTEST]):
            print("%-28s %-16s expected=%s" % (probe["name"], probe["verdict"], want))
            if probe["verdict"] != want:
                failures.append("%s read %s, the ruler must read %s" % (probe["name"], probe["verdict"], want))

    for row in rows:
        print("%-30s %-16s %s" % (row["name"], row["verdict"], row["path"]))
    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
    report["counts"] = counts
    print("counts: " + json.dumps(counts, sort_keys=True))

    if args.json:
        with open(args.json, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, ensure_ascii=False, indent=1)
        print("json: " + args.json)

    for line in failures:
        print("SELFTEST RED: " + line)
    return 3 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
