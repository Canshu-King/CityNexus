"""ORD-0539 r2 -- rebase the whole chain onto the current tip as ONE self-contained candidate.

Why one commit and not three refs: the landing sequencer recuts each ref *independently* against the
tip. My three refs are stacked (0477 r3 -> 0518 r2 -> 0539 r1), so an independent recut of the top of
the chain sees the two lower links' files as "deleted in the tip, modified in mine" -- six conflicts of
that shape, measured, none of them a real content clash. A candidate whose parent *is* the tip cannot
produce that artifact, so this commit carries all three orders' content and nothing else.

The tree is assembled from this lane's working directory over `read-tree <tip>`, and the guard is the
same as the last two commits: any path the tip carries that the new tree lacks is a refusal. The list
of what changed is computed by hashing every file, not by trusting a hand-kept manifest.

usage: python ord0539_commit_r2.py            (build and print; writes no ref)
       python ord0539_commit_r2.py --push     (writes the new ref and pushes that one ref)
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LANE = pathlib.Path(r"D:/moodle/_qoder_b_ord0417_20260928")
TREE_DIR = LANE / "ord0539cut_c874b1d6"
TIP = "c874b1d6bac6735d4ad164379a76db7b73398bd8"
REF = "refs/heads/review/8ac89982-ord0539-trip-order-read-at-390-r2"
INDEX = LANE / "run/ord0539_index_r2"
REPORT = LANE / "run/ord0539_commit_r2.txt"

SKIP_ANY = {"__pycache__", ".pytest_cache", "node_modules", "dist", ".venv", ".git", "test-results",
            "playwright-report", "blob-storage", ".vite", "storybook-static"}
# what the gates leave behind in the directory they run in. A candidate must not carry a seed pointer or
# a database: `frontend/e2e/.qoder-seed-state.json` is written by the real-seed setup project and
# `citynexus.db` by the backend suite, and both were picked up when "changed" meant "differs from the
# tip" -- a run artifact in a delivery is a lie about what the code does.
RESIDUE = {"frontend/e2e/.qoder-seed-state.json", "citynexus.db", "frontend/e2e/.qoder-real-seed.json"}

# this generation's readings, shipped beside the earlier ones
EVIDENCE_SOURCES = [
    ("run/ord0539_commit_r2.py", "commit_instrument_r2.py"),
    ("run/ord0539_changed_vs_tip_r2.txt", "changed_files_vs_tip_r2.txt"),
    ("run/ord0477_mutant_r2_silent_default_on_unknown_word.txt", "mutant_r2_silent_default.txt"),
    ("run/ord0477_mutant_r2_characters_not_instants.txt", "mutant_r2_characters_not_instants.txt"),
    ("run/ord0477_mutant_r2_no_case_fold.txt", "mutant_r2_no_case_fold.txt"),
    ("run/ord0477_mutant_r2_pin_pre_tier_segment_swapped_in.txt", "mutant_r2_byte_pin.txt"),
    ("run/ord0518_mutant_server_order_masked_r1.txt", "mutant_r2_server_order_masked.txt"),
    ("run/ord0518_mutant_tier_switch_keeps_the_list_still_r1.txt", "mutant_r2_tier_switch_still.txt"),
    ("run/ord0518_mutant_verdict_stops_reading_the_rows_r1.txt", "mutant_r2_verdict_stops_reading.txt"),
    ("evidence/ord0477/gate/ord0539r2f.log", "gate_chain_pass_r2f.log"),
    ("evidence/ord0477/gate/ord0539r2e.log", "gate_cost_reading_r2e.log"),
    ("ord0539cut_c874b1d6/frontend/e2e/qoder-0539-trip-order-read-at-390.spec.ts", "spec_as_shipped_r2.ts"),
    ("ord0539cut_c874b1d6/frontend/src/features/access/access.css", "access_css_as_shipped_r2.css"),
]


def git(*args: str) -> str:
    done = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if done.returncode != 0:
        raise SystemExit("git %s -> rc=%d %s" % (" ".join(args), done.returncode, done.stderr[:400]))
    return done.stdout.strip()


def blob_id(data: bytes) -> str:
    digest = hashlib.sha1()
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def main() -> int:
    tip_files = {}
    for line in git("ls-tree", "-r", "--format=%(objectname) %(path)", TIP).splitlines():
        oid, _, path = line.partition(" ")
        tip_files[path] = oid

    present = {}
    for entry in TREE_DIR.rglob("*"):
        if entry.is_symlink() or not entry.is_file():
            continue
        relative = entry.relative_to(TREE_DIR).as_posix()
        if any(part in SKIP_ANY for part in relative.split("/")) or relative in RESIDUE:
            continue
        present[relative] = entry

    changed = [(path, node) for path, node in sorted(present.items()) if path not in tip_files or blob_id(node.read_bytes()) != tip_files[path]]
    missing_from_tree = sorted(path for path in tip_files if path not in present)
    if missing_from_tree:
        print("REFUSE: the working directory lacks %d path(s) the tip carries, e.g. %s" % (
            len(missing_from_tree), missing_from_tree[:3]))
        return 3

    entries = changed
    for source, name in EVIDENCE_SOURCES:
        target = "review/ord0539/" + name
        path = LANE / source
        if not path.exists():
            print("REFUSE: missing evidence %s" % path)
            return 2
        entries.append((target, path))

    if INDEX.exists():
        INDEX.unlink()
    out = ["TIP=%s" % TIP, "REF=%s" % REF,
           "changed_vs_tip=%d (product+e2e from the chain)" % len(changed),
           "evidence_shipped=%d" % len(EVIDENCE_SOURCES),
           "tip_paths_absent_from_this_tree=%d" % len(missing_from_tree)]
    saved = os.environ.get("GIT_INDEX_FILE")
    os.environ["GIT_INDEX_FILE"] = str(INDEX)
    try:
        git("read-tree", "%s^{tree}" % TIP)
        for repo_path, source in entries:
            blob = git("hash-object", "-w", "--no-filters", str(source))
            git("update-index", "--add", "--cacheinfo", "100644,%s,%s" % (blob, repo_path))
        tree = git("write-tree")
        out.append("TREE=%s" % tree)
        status = git("diff", "--name-status", TIP, tree).splitlines()
        deleted = [line for line in status if line.startswith("D")]
        added = [line.split("\t")[-1] for line in status if line.startswith("A")]
        modified = [line.split("\t")[-1] for line in status if line.startswith("M")]
        out.append("against the tip: added=%d modified=%d deleted=%d" % (len(added), len(modified), len(deleted)))
        out += ["ADDED %s" % p for p in added if p.startswith(("backend/", "contracts/", "frontend/"))]
        out += ["MODIFIED %s" % p for p in modified if p.startswith(("backend/", "contracts/", "frontend/"))]
        if deleted:
            out += ["DELETED %s" % line for line in deleted]
            out.append("REFUSE: this tree drops paths the tip carries -- nothing is committed")
            REPORT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
            print("\n".join(out))
            return 7
        message = (
            "ORD-0539 r2: the trip-list order, rebased onto the current tip as one candidate\n"
            "\n"
            "Parent is the tip itself (%s), so an independent recut of this ref cannot see the two\n"
            "lower links of my chain as deletions -- that artifact, not a content clash, is what\n"
            "rejected r1: six modify/delete and content conflicts, all in files this chain itself adds\n"
            "or edits (measured with `git merge-tree`, listed in review/ord0539/). Everything ORD-0477\n"
            "r3 and ORD-0518 r2 carried is here unchanged except the three things this round added.\n"
            "\n"
            "1. The commander's ruling (15:30 block, item 4) is now a regression assertion, not an\n"
            "   observation: pressing the tier already in use must ask the door 0 times, must leave the\n"
            "   painted roster identical, and pressing a *different* tier must still ask exactly 1 --\n"
            "   the pair is what makes the zero mean 'idempotent read' rather than 'dead control'.\n"
            "2. The trip roster is bounded to its own scroll box (`max-height: min(45vh, 320px)`,\n"
            "   `overscroll-behavior: contain`) and the region is focusable so the same rows a thumb\n"
            "   reaches, the keyboard reaches too. Before this the roster grew with the door's answer\n"
            "   and the door has no pagination: 21 rows meant 1050 px of list where a closed <select>\n"
            "   used to cost one line.\n"
            "3. The four tiers are a wrapping row of chips instead of four stacked full-width buttons,\n"
            "   which took the sort block from ~340 px to 247 px (measured at 390x844: y 215,\n"
            "   height 247) without weakening how the tier in use is shown.\n"
            "\n"
            "What is still red, and is not mine to fix by moving a ruler: ORD-0477's four\n"
            "`sort-geometry-*` arms report `lost: [access-empty-reload-roles]` at 390x844 and 320x653\n"
            "in both languages. That arm hides `.cn-access-sort` and compares the reachable set; the\n"
            "roles block's empty-state action is reachable without my 247 px of sort block and is not\n"
            "with it. The panel's content between the two is: my sort block, the verdict sentence, the\n"
            "two named absent orders with their reasons, and the roster -- all of it required by\n"
            "ORD-0477 and ORD-0518. Reclaiming the last ~250 px would mean deleting required copy or\n"
            "moving the picker below the ladder, so it is put to the commander with the numbers\n"
            "(review/ord0539/readings/ord0539r2e_both-ends.json) rather than resolved by editing the\n"
            "assertion. Everything else on this chain is green: 27 of 31 arms in the three specs, and\n"
            "all seven mutants bite with the mutated file reverted by sha256.\n"
            % TIP
        )
        commit = git("commit-tree", tree, "-p", TIP, "-m", message)
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
    head = [line for line in out if line.startswith(("TIP", "REF", "TREE", "COMMIT", "against", "PUSH", "changed_vs_tip", "evidence_shipped", "tip_paths", "DELETED", "ADDED backend", "ADDED frontend", "MODIFIED"))]
    sys.stdout.buffer.write(("\n".join(head[:40]) + "\n").encode("utf-8", "replace"))
    print("wrote %s (%d lines)" % (REPORT, len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
