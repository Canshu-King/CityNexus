"""ORD-0417 lane commit r1 -- build the review commit without touching the frozen working tree.

D:/moodle/CityNexus holds a shared, dirty working tree (another lane has backend files open in it).
Checking my own bytes out there would either overwrite their work or put mine on the line by
accident, and the order says the tree is frozen.  So the commit is assembled entirely in a throwaway
index:

  read-tree <authoritative tip>   -> a pristine copy of the tip's tree, in a temp index file
  update-index --cacheinfo        -> four path replacements, from blobs hashed with --no-filters
  write-tree / commit-tree        -> one commit whose only parent is the tip
  update-ref                      -> refs/heads/review/R-ord0417-tap-names-stop-r1

The index file is removed at the end; `.git/index` (the working tree's) is never opened.
`--no-filters` is not cosmetic: every file this lane ships is LF in the repo and LF on disk here, and
letting a textconv/CRLF filter run would silently change the bytes the bundle is built from.
Three files this lane did NOT touch are re-hashed and compared against the tip first, which is what
proves the export round-trips byte-exactly and therefore that the four new hashes mean what they say.

usage: python ord0417_commit_r1.py [--tip <40-hex>] [--dry]
"""
import argparse
import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
EXP = pathlib.Path(os.environ.get("ORD0417_EXP") or r"D:/moodle/_qoder_b_ord0417_20260928/exp2")
BRANCH_DEFAULT = "refs/heads/review/R-ord0417-tap-names-stop-r1"
DEFAULT_TIP = "8a7665be2061a2f38aa2227f81c57003ca4caacb"

SHIPPED = [
    "frontend/src/i18n/LocaleContext.tsx",
    "frontend/src/components/v8/MapPanel.tsx",
    "frontend/src/map-selection.css",
    "frontend/e2e/qoder-ord0417-tap-names-the-stop.spec.ts",
]
# Files this lane reads but does not change. If these hash differently from the tip's own blobs the
# export is not carrying the tip's bytes, and every number derived from it is about a fiction.
CONTROL = [
    "frontend/src/app/V8Experience.tsx",
    "frontend/src/i18n/mapPanelCopy.ts",
    "frontend/e2e/qoder-map-ord0390-selection-both-ways.spec.ts",
    "frontend/e2e/qoder-map-ord0403-named-control-and-labels.spec.ts",
    "frontend/src/components/JourneyMap.tsx",
]

MESSAGE = """ORD-0417: a tap on a map pin now says, on the glass, which stop it was

The v8 map's markers painted a number and kept the stop's name in `aria-label` only, with
`title` empty, so a traveller with working eyes got no answer to the thing they just did.
Measured on 214ab0ff by `_map_tap_names_stop_r1.js` and re-measured on this lane's own
private stack: 6 markers, tap on marker 2 (Riverside Museum), caption and overlay
byte-identical, name_shown_anywhere_after_tap=false.

`.v8-map-selected-stop` now paints the dictionary's sentence inside `.v8-map-caption`,
which is the one box on the glass whose height `fitBounds` has already reserved.  Two
other placements were tried and rejected on measurements this lane's gate took: a line
added to the overlay stack grew the band 139->184 px and covered three pins, and a
permanently reserved line raised the band's top edge 43 px and still covered a pin the
untouched tip leaves clear.  Both spent the framing's `safetyGap`.

Both arms live in `frontend/src/i18n/LocaleContext.tsx` --
`mapComp.selectedStopOnMap`, "图上选中的这一站 · {name}" and
"Selected on the map · {name}" -- because the copy has to be readable by the pairing
ruler, not embedded in a component.

New gate `frontend/e2e/qoder-ord0417-tap-names-the-stop.spec.ts`, 17 arms: the painted
name after a real pointer tap, in zh and en; visibility judged off `innerText` and the
cell's own box rather than off an attribute; a negative control that the glass names no
stop before anything is picked; ORD-0390's two directions re-measured; and lane N3's
frozen hit-floor census (768 px, `elementFromPoint` at each control's centre) at
390x844 / 360x800 / 320x653 / 414x896 in both languages, asserting no reachable control
lost, no control added, and band growth within the 16 px the camera already paid for.

Rebased onto the authoritative line as read at build time, not onto the line quoted in
the ticket: ORD-0410 landed `frontend/src/components/v8/MapPanel.tsx` underneath this
work, in the `fitBounds` block.  The two changes do not overlap textually, and this
commit's parent is the tip, so `framePositions` and the `refitRef` path ORD-0410 shipped
are still in the file -- asserted, not trusted: the diff against the tip is four paths and
nothing else.
"""

APPEND_MESSAGE = """ORD-0417 gate r2: the mutant proved my own A1/A2 assertions were not reporting

The first mutant run (visible output removed, dictionary and CSS left in place) reddened 14 of the
17 arms -- which is the intended reach -- but `tap-named-*` and `not-aria-*` reported

    Error: expect(received).toContain(expected) // Matcher error: received value must not be null

instead of naming the cell a traveller could not see.  The cause is in this lane's gate, not in the
product: I wrote

    if (!glass.present) { expect(false, node("A1", "...")); }

and `expect()` with no matcher is a no-op, so the arm fell through to the next line.  The guard is
now the first assertion of each arm, `expect(glass.present, node("A1", ...)).toBe(true)`, which
aborts the arm and prints what is missing.  `copy-*` and `geometry-*` already asserted this way and
did name themselves under the mutant.

No product byte changes in this commit: `git diff --name-status` against the parent is the one spec
file.
"""


def git(*args, index=None, binary=False):
    env = dict(os.environ)
    if index:
        env["GIT_INDEX_FILE"] = index
    p = subprocess.run(["git", "-C", REPO, *args], capture_output=True, env=env)
    if p.returncode:
        raise SystemExit(f"ABORT git {' '.join(args)} -> {p.stderr.decode('utf-8','replace').strip()[:300]}")
    return (p.stdout if binary else p.stdout.decode("utf-8", "replace")).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default=BRANCH_DEFAULT)
    ap.add_argument("--tip", default=None)
    ap.add_argument("--append", action="store_true",
                    help="parent the commit on the branch's own head instead of starting it fresh")
    ap.add_argument("--dry", action="store_true", help="build the commit object but do not move the ref")
    a = ap.parse_args()

    # The authoritative line moves while lanes work; re-read it rather than trusting the ticket.
    BRANCH = a.branch
    branch_head = subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", BRANCH],
                                 capture_output=True, text=True).stdout.strip()
    tip = a.tip or (branch_head if a.append else
                    git("rev-parse", "refs/remotes/origin/mirror/integration-frontend-apple-pass1"))
    if len(tip) != 40:
        raise SystemExit(f"ABORT the parent rev did not read as 40 hex: {tip!r}")
    print("PARENT_OF_RECORD", tip, "branch_head", branch_head or "(none)",
          "mode", "append" if a.append else "fresh")

    for rel in CONTROL:
        want = git("rev-parse", f"{tip}:{rel}")
        have = git("hash-object", "--no-filters", str(EXP / rel.replace("/", os.sep)))
        if want != have:
            raise SystemExit(f"ABORT export does not round-trip: {rel} tip={want} here={have}")
        print("ROUNDTRIP", rel, want, "same=YES")

    idx = str(pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928/run") / f"ord0417.index.{tip[:8]}")
    if os.path.exists(idx):
        os.remove(idx)
    git("read-tree", tip, index=idx)

    blobs = {}
    for rel in SHIPPED:
        path = EXP / rel.replace("/", os.sep)
        if not path.is_file():
            raise SystemExit(f"ABORT {rel} is not in the export")
        blobs[rel] = git("hash-object", "-w", "--no-filters", str(path), index=idx)
        git("update-index", "--add", "--cacheinfo", f"100644,{blobs[rel]},{rel}", index=idx)
        print("STAGE", rel, blobs[rel])

    tree = git("write-tree", index=idx)
    message = APPEND_MESSAGE if a.append else MESSAGE
    commit = git("commit-tree", tree, "-p", tip, "-m", message, index=idx)
    print("TREE", tree)
    print("COMMIT", commit)

    # 0 overwrites, proved rather than asserted: the commit's parent IS the tip, and the diff is the
    # four paths and nothing else.
    parent = git("rev-parse", f"{commit}^")
    name_status = git("diff", "--name-status", tip, commit).splitlines()
    print("PARENT", parent, "equals TIP:", parent == tip)
    print("DIFF_LINES", len(name_status))
    for line in name_status:
        print("  ", line)
    if parent != tip:
        raise SystemExit("ABORT the commit is not a direct child of its recorded parent -- rebase first")
    touched = [l.split("\t")[-1] for l in name_status]
    stray = [t for t in touched if t not in SHIPPED]
    if stray:
        raise SystemExit(f"ABORT this commit touches paths the order did not name: {stray}")
    if not a.append and len(touched) != len(SHIPPED):
        raise SystemExit(f"ABORT the fresh branch should carry all {len(SHIPPED)} paths, got {len(touched)}")

    if a.dry:
        os.remove(idx)
        print("DRY: ref not moved")
        return 0

    before = branch_head
    if a.append:
        if before != tip:
            raise SystemExit(f"ABORT the branch moved while this commit was being built: {before} != {tip}")
    elif before:
        raise SystemExit(f"ABORT {BRANCH} already exists at {before}; a new branch must have 0 overwrites")
    git("update-ref", BRANCH, commit)
    after = git("rev-parse", BRANCH)
    print("REF", BRANCH, after, "matches COMMIT:", after == commit)
    # append mode must be a pure addition to history: the previous head has to be the parent, and the
    # paths touched have to be the ones this lane owns.
    if a.append:
        print("FAST_FORWARD_FROM", before, "is parent:", parent == before)
        if parent != before:
            raise SystemExit("ABORT append produced a commit that is not a fast-forward of the branch")
    os.remove(idx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
