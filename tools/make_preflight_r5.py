"""Derive preflight_and_land_r5.py from r4 by exact single-match anchors.

Why r5 exists: r4 built its per-file blob-equality list from `git diff --name-only base cand`, which
lists DELETED paths too, and then demanded every listed path exist in the export.  Any candidate that
renames or removes a file was therefore refused for a file it deliberately removed.  Measured on
c00703d1db9512e8c96099a26c08442b827a9357, where review/ord0369-phone-replan/gate-report-r2.json was
renamed to gate-report-r3-with-regressions.json.

r5 keeps the added/modified arm and adds the symmetric one: a path the candidate deletes must be ABSENT
in the export.  Nothing else in the gate is touched.
"""
import ast
import io
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
SRC = HERE / "preflight_and_land_r4.py"
DST = HERE / "preflight_and_land_r5.py"

EDITS = [
    (
        '    _, cand_files, _ = git("diff", "--name-only", base, cand)\n',
        '    _, cand_files, _ = git("diff", "--name-only", "--diff-filter=d", base, cand)\n'
        '    _, cand_deleted, _ = git("diff", "--name-only", "--diff-filter=D", base, cand)\n',
    ),
    (
        '    cf = sorted(x for x in cand_files.splitlines() if x.strip())\n',
        '    cf = sorted(x for x in cand_files.splitlines() if x.strip())\n'
        '    df = sorted(x for x in cand_deleted.splitlines() if x.strip())\n',
    ),
    (
        '        if any(not e["equal"] for e in run["blob_equality"]):\n'
        '            problems.append("export bytes differ from the candidate blobs")\n',
        '        if any(not e["equal"] for e in run["blob_equality"]):\n'
        '            problems.append("export bytes differ from the candidate blobs")\n'
        '        # r5: the deletion arm.  r4 demanded that paths the candidate REMOVED exist in the\n'
        '        # export, so every rename was refused for the file it deliberately deleted.  The check\n'
        '        # is kept, but pointed the other way: a deleted path must really be gone.\n'
        '        still_there = [rel for rel in df\n'
        '                       if os.path.exists(os.path.join(export, rel.replace("/", os.sep)))]\n'
        '        run["deletions"] = {"deleted_by_candidate": df, "still_present_in_export": still_there}\n'
        '        if still_there:\n'
        '            problems.append("candidate deletes %s but the exported tree still carries it"\n'
        '                            % ", ".join(still_there[:3]))\n',
    ),
]


def main():
    src = io.open(SRC, "r", encoding="utf-8").read()
    out = src
    for old, new in EDITS:
        n = out.count(old)
        if n != 1:
            raise SystemExit("ABORT: anchor matched %d times (expected 1): %r" % (n, old[:70]))
        out = out.replace(old, new)
    try:
        ast.parse(out)
    except SyntaxError as e:
        raise SystemExit("ABORT: derived file does not parse: %s" % e)
    if DST.exists():
        raise SystemExit("ABORT: %s already exists -- published paths do not get overwritten (Q57)" % DST.name)
    io.open(DST, "w", encoding="utf-8", newline="\n").write(out)
    print("wrote %s (%d B) from %s (%d B), edits=%d" % (DST.name, DST.stat().st_size, SRC.name, len(src), len(EDITS)))
    for i, (old, new) in enumerate(EDITS, 1):
        print("  edit %d: +%d bytes" % (i, len(new) - len(old)))


if __name__ == "__main__":
    main()
