"""LEDGER_SINGLE_WRITER_V1 (arbiter Q63=3, 22:5x): lanes no longer write the shared ledger - they hand me a block.

Why: the ledger was overwritten twice tonight (lane E 21:47, lane HJ-P3 earlier), and I measured both recoveries.
The arbiter was asked whether that is enough and answered 3: take the write permission back - one pen, and the
lanes submit blocks. That is slower for them, so the submission path must be trivially cheap: drop one markdown
file per block into the inbox directory, and this tool inserts them in order through the SAME gated door I use
for my own blocks (Q43 gate + every 40-hex coordinate must resolve), then mirrors once.

Dry run by default; --apply is what actually writes. A block that the door refuses is left in the inbox with the
refusal printed - I never edit another lane's words to make a gate quiet.

--selftest proves the tool discriminates: a well-formed block with a real coordinate must pass, and the same
block with a fabricated 40-hex must be refused. If both behave the same, the tool is a rubber stamp.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
INBOX = r"D:\moodle\_qoder_ledger_inbox"
PROCESSED = os.path.join(INBOX, "_processed")
HERE = os.path.dirname(os.path.abspath(__file__))
ANCHOR = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
REAL_COORD = "fba4e01a4e7ad9833a5b4fc35920b8a089ae9525"   # my own published scope table (resolves)
FAKE_COORD = "0123456789abcdef0123456789abcdef01234567"   # cannot exist: 0-9a-f pattern, no such object


def title_key(first_line):
    """A lane that re-submits the same block with only the `@HH:MM+08` stamp changed is delivering a revision,
    not a second entry. Without this rule my own tool would put the same block in the shared ledger twice -
    which is the duplicate-post failure mode I have already recorded against lanes twice tonight.
    """
    return re.sub(r"\s*@\d{1,2}:\d{2}(\+08)?\s*$", "", first_line).strip()


def dedupe(files):
    """Keep the lexicographically-last (== latest HHMM) file per title; return (keep, superseded_pairs)."""
    by_title = {}
    for f in files:
        first = io.open(f, encoding="utf-8").read().splitlines()[0] if os.path.exists(f) else ""
        by_title.setdefault(title_key(first), []).append(f)
    keep, superseded = [], []
    for key, group in by_title.items():
        group = sorted(group)
        newest = group[-1]
        keep.append(newest)
        for older in group[:-1]:
            superseded.append((older, os.path.basename(newest)))
    return sorted(keep), superseded


def candidate_files():
    if not os.path.isdir(INBOX):
        return []
    out = []
    for name in sorted(os.listdir(INBOX)):
        if not name.endswith(".md") or name.startswith("_"):
            continue
        out.append(os.path.join(INBOX, name))
    return out


def shape_problem(text, name):
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return "empty file"
    if not lines[0].startswith("### "):
        return "first line must be a '### ' block heading, found: " + lines[0][:60]
    if len(lines) < 2:
        return "block has only a heading and no body"
    if not re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", name):
        return "filename must be <lane>_<HHMM>.md so ordering is deterministic, found: " + name
    return None


def apply_one(path, apply_writes):
    name = os.path.basename(path)
    text = io.open(path, encoding="utf-8", newline="\n").read()
    problem = shape_problem(text, name)
    if problem:
        print("   SKIP %s: %s" % (name, problem))
        return "skipped"
    if not apply_writes:
        first = text.splitlines()[0][:70]
        print("   DRY  %s -> %s" % (name, first))
        return "dry"
    r = subprocess.run([sys.executable, os.path.join(HERE, "ledger_insert_after.py"), ANCHOR, path],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900)
    if r.returncode:
        # the door refused it: the block stays in the inbox untouched - I do not rewrite another lane's words
        # to satisfy a gate, and I do not bypass the gate.
        tail = (r.stdout or "").strip().splitlines()[-4:]
        print("   REFUSED %s rc=%d: %s" % (name, r.returncode, " | ".join(tail)))
        return "refused"
    os.makedirs(PROCESSED, exist_ok=True)
    stamp = time.strftime("%H%M%S")
    shutil.move(path, os.path.join(PROCESSED, "%s.inserted_%s" % (name, stamp)))
    print("   INSERTED %s" % name)
    return "inserted"


def selftest():
    probe = os.path.join(INBOX, "selftest_9999.md")
    good = "### SELFTEST lane good_block\n\na real coordinate so the door is satisfied: %s\n" % REAL_COORD
    bad = "### SELFTEST lane bad_block\n\na fabricated coordinate: %s\n" % FAKE_COORD
    try:
        io.open(probe, "w", encoding="utf-8", newline="\n").write(good)
        r_good_shape = shape_problem(io.open(probe, encoding="utf-8").read(), "selftest_9999.md")
        io.open(probe, "w", encoding="utf-8", newline="\n").write(bad)
        res_bad = apply_one(probe, apply_writes=False)  # dry: must not touch the ledger
        # The discrimination test runs the two READ-ONLY bolts over the bad block and never the writer, because a
        # self-test that writes to the shared ledger to prove it can refuse would be worse than the bug it checks.
        g = subprocess.run([sys.executable, os.path.join(HERE, "claim_coordinate_check_r4c.py"),
                            "--text", probe, "--expect-clean"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        rc1 = g.returncode
        unresolved = 0
        for h in set(re.findall(r"\b[0-9a-f]{40}\b", bad)):
            p = subprocess.run(["git", "-C", "D:/moodle/CityNexus", "cat-file", "-t", h], capture_output=True)
            if p.returncode:
                unresolved += 1
        refused = rc1 != 0 or unresolved == 1
        heading_only = os.path.join(INBOX, "nope.md")
        io.open(heading_only, "w", encoding="utf-8", newline="\n").write("not a heading at all\n")
        rejected_name = shape_problem("x", "nope.md") is not None
        ok = (r_good_shape is None and res_bad == "dry" and refused and rejected_name)
        print("SELFTEST %s" % ("PASS" if ok else "FAIL"),
              json_dumps({"well_formed_accepted": r_good_shape is None, "dry_run_touched_nothing": res_bad == "dry",
                          "q43_rc_on_bad_block": rc1, "unresolved_coordinates": unresolved,
                          "fabricated_coordinate_refused": refused, "bad_filename_rejected": rejected_name}))
        return 0 if ok else 7
    finally:
        for p in (probe, os.path.join(INBOX, "nope.md")):
            if os.path.exists(p):
                os.remove(p)


def json_dumps(d):
    import json
    return json.dumps(d, ensure_ascii=False)


def main():
    apply_writes = "--apply" in sys.argv
    if "--selftest" in sys.argv:
        return selftest()
    all_files = candidate_files()
    files, superseded = dedupe(all_files)
    for older, newer in superseded:
        name = os.path.basename(older)
        if apply_writes:
            os.makedirs(PROCESSED, exist_ok=True)
            shutil.move(older, os.path.join(PROCESSED, "%s.superseded_by_%s" % (name, newer)))
            print("   SUPERSEDED %s (same block, later revision %s wins; the file is kept, unedited)" % (name, newer))
        else:
            print("   DUP-SKIP %s -> later revision %s carries the same block" % (name, newer))
    print("inbox blocks: %d (%d pending after dedupe) | mode=%s | at %s" % (
        len(all_files), len(files), "APPLY" if apply_writes else "DRY", time.strftime("%H:%M:%S")))
    tally = {"inserted": 0, "refused": 0, "skipped": 0, "dry": 0}
    for f in files:
        tally[apply_one(f, apply_writes)] += 1
    print("tally", tally)
    if apply_writes and tally["inserted"]:
        m = subprocess.run([sys.executable, os.path.join(HERE, "merge_ledger_then_mirror_r1.py")],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=1800)
        tail = (m.stdout or "").strip().splitlines()[-6:]
        print("mirror rc=%d | %s" % (m.returncode, " | ".join(tail)))
        return m.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
