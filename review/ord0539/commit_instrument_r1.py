"""ORD-0539 -- publish the 390 px read of the trip list's order, stacked on ORD-0518 r2.

Same plumbing as the two commits under it (temporary index over the parent's tree, every coordinate
read back out of the tree being published, and a hard refusal if the new tree drops any path the parent
carries). This one is small on purpose: it adds one e2e file and the readings it produced. No product
byte changes, because the read did not find a product defect to fix -- it found that the *arm* had been
mounting before it seeded, and the reason that reads a stale list is itself the finding (pressing the
tier already in use asks the door nothing).
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE_DIR = LANE / "ord0477cut_7862c6de"
PARENT = "705922f7ca60390d0afb250180a9d325781b5cb5"  # ORD-0518 r2
REF = "refs/heads/review/8ac89982-ord0539-trip-order-read-at-390-r1"
INDEX = LANE / "run/ord0539_index_r1"
REPORT = LANE / "run/ord0539_commit_r1.txt"

PRODUCT = ["frontend/e2e/qoder-0539-trip-order-read-at-390.spec.ts"]
EVIDENCE_DIR = LANE / "evidence/ord0477/e2e/ord0539-read-at-390"
EVIDENCE_SOURCES = [
    ("run/ord0539_commit_r1.py", "commit_instrument_r1.py"),
    ("evidence/ord0477/gate/ord0539a.log", "gate_first_cut_r1.log"),
    ("evidence/ord0477/gate/ord0539b.log", "gate_first_cut_r2_wrong_scroll.log"),
    ("evidence/ord0477/gate/ord0539c.log", "gate_first_cut_r3_end_under_bar.log"),
    ("evidence/ord0477/gate/ord0539d.log", "gate_first_cut_r4_recent_arm_reads_no_rows.log"),
    ("evidence/ord0477/gate/ord0539e.log", "gate_final_r5.log"),
    ("ord0477cut_7862c6de/frontend/e2e/qoder-0539-trip-order-read-at-390.spec.ts", "spec_as_shipped_r1.ts"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def main() -> int:
    entries = [(p, TREE_DIR / p) for p in PRODUCT]
    for source, name in EVIDENCE_SOURCES:
        entries.append(("review/ord0539/" + name, LANE / source))
    # every per-arm reading this order produced, JSON only; the screenshots stay in the lane
    for arm in sorted(EVIDENCE_DIR.glob("ord0539e_*.json")):
        entries.append(("review/ord0539/readings/" + arm.name, arm))
    # and the one reading that showed the stale list, kept as the provenance of the finding
    for arm in sorted(EVIDENCE_DIR.glob("ord0539d_read-RECENT_UPDATE.json")):
        entries.append(("review/ord0539/readings/" + arm.name, arm))
    missing = [str(path) for _, path in entries if not path.exists()]
    if missing:
        print("REFUSE: missing paths (nothing is written):")
        for line in missing:
            print("   ", line)
        return 2

    if INDEX.exists():
        INDEX.unlink()
    out = ["PARENT=%s (ORD-0518 r2)" % PARENT, "REF=%s" % REF, "product_files=%d" % len(PRODUCT),
           "readings_shipped=%d" % len([1 for p, _ in entries if p.startswith("review/ord0539/readings/")])]
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        git("read-tree", "%s^{tree}" % PARENT)
        for repo_path, source in entries:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        out.append("TREE=%s" % tree)
        status = git("diff", "--name-status", PARENT, tree).splitlines()
        deleted = [line for line in status if line.startswith("D")]
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        out.append("against the parent: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted)))
        for line in deleted:
            out.append("DELETED %s" % line)
        if deleted:
            out.append("REFUSE: this tree drops %d path(s) the parent carries -- nothing is committed" % len(deleted))
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        for repo_path, _ in entries:
            resolved = git("rev-parse", "%s:%s" % (tree, repo_path))
            out.append("%s %sB %s" % (resolved, git("cat-file", "-s", resolved), repo_path))
        message = (
            "ORD-0539: the trip list's order, read by eye at the phone width\n"
            "\n"
            "Stacked on ORD-0518 r2 (%s). ORD-0518 judged reachability at 390x844 and read the roster\n"
            "at one tier; what nobody had said out loud at that width is the thing this order asked\n"
            "for: after each tier is pressed, which trip is the first row and which is the last, as\n"
            "painted. One arm per tier, plus an arm for whether the two ends ever share a screen and an\n"
            "arm for what pressing a tier actually asks. No product byte changes: the read found an\n"
            "instrument mistake of mine, and the reason that mistake was possible is the finding.\n"
            "\n"
            "Measured at 390x844 on this generation (7 arms, 7 passed, run id ord0539e): the four tiers\n"
            "paint four different pairs -- CREATION_ORDER first 'O539-CREATION_ORDER delta' last '...北京'\n"
            "and says it cannot check (no created moment in a row); RECENT_UPDATE first '...北京' last\n"
            "'...delta' and says the same for updated_at; DEPARTURE_DATE first '...Alpha' last '...delta'\n"
            "and says 逐行核过 over each trip's departure time; TITLE first '...Alpha' last '...北京' and\n"
            "says 逐行核过 over the name. No end row ever showed a uuid, and the tier words on the glass\n"
            "are the dictionary's, not the server's tokens.\n"
            "\n"
            "The two readings a traveller cannot get from any existing arm: at this width the roster\n"
            "holds 21 rows and only 3 of them are in the reachable band at the top of the page; nine fit\n"
            "at once at the deepest position, and the first and last row never share one screen -- so\n"
            "'read the first and the last trip' is a two-glance act here, which is a consequence of the\n"
            "list door having no pagination (named in ORD-0518's block, still true). Both ends are\n"
            "reachable though: scrolling the last row to the middle puts it under a finger, and focus\n"
            "places it at y 400 of 844, above the 768 px line -- the keyboard is not stranded.\n"
            "\n"
            "And the finding the first cut fell into: pressing the tier already in use asks the door 0\n"
            "requests, while pressing a different tier asks exactly 1 ('?sort=DEPARTURE_DATE'). That is\n"
            "why an arm that seeds after mounting reads the previous list, and it is also what happens\n"
            "to a traveller who adds a trip elsewhere and taps the tier again: the list does not move\n"
            "and nothing says why. Whether that should refresh is a product decision, not a bug this\n"
            "order was told to fix, so it is recorded with its request count rather than asserted away.\n"
            "The stale reading that showed it ships too (review/ord0539/readings/ord0539d_read-\n"
            "RECENT_UPDATE.json) beside the corrected one.\n"
            % PARENT
        )
        commit = git("commit-tree", tree, "-p", PARENT, "-m", message)
        out.append("COMMIT=%s" % commit)
        out.append(git("log", "-1", "--format=%h %ad %s", commit).replace("\n", " | "))
        if "--push" in sys.argv:
            out.append(git("update-ref", REF, commit) or "update-ref ok")
            pushed = subprocess.run(
                ["git", "-C", REPO, "push", "--atomic", "origin", "%s:%s" % (commit, REF)],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            out.append("PUSH rc=%s %s" % (pushed.returncode, (pushed.stderr or "").strip()[:600]))
        else:
            out.append("PUSH=not requested (ref not written)")
    finally:
        if saved is None:
            os.environ.pop("GIT_INDEX_FILE", None)
        else:
            os.environ["GIT_INDEX_FILE"] = saved
    REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    head = [line for line in out if line.startswith(("PARENT", "REF", "TREE", "COMMIT", "against", "PUSH", "DELETED", "product_files", "readings_shipped"))]
    sys.stdout.buffer.write(("\n".join(head) + "\n").encode("utf-8", "replace"))
    print("wrote %s (%d lines)" % (REPORT, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
