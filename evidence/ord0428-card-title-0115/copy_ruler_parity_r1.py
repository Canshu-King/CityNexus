"""ORD-0428: the copy-tier ruler's hit list, compared row by row across the two trees.

The claim this has to support is narrow: the change adds no hardcoded-copy face. `cnx_copy_tiers_r1.py`
as it stands on the authoritative tip is run with `--src` against both trees, its per-row list is parsed
back out of the report, and the two lists are compared on (tier, shape, file name, literal) with the line
number reported separately -- because a line number moving is not a new hit, and calling it one would be
the same mistake in the other direction as ignoring it.
"""
import io
import json
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
RULER = os.path.join(WORK, "cnx_copy_tiers_r1_tip.py")
TREES = {"before_tip4037": os.path.join(WORK, "tip4037", "frontend"),
         "after_ord0428r1": r"D:\moodle\_qoder_lane_S4_0926\wt0428\frontend"}
ROW = re.compile(r"\s+([AB]) (T\d) \[([A-Z_]+) *\] (.+?):(\d+) (.*)  <-")


def run(label, tree):
    txt = os.path.join(WORK, "copy_%s_r1.txt" % label)
    r = subprocess.run([PY, RULER, "--i18n", os.path.join(tree, "src", "i18n", "LocaleContext.tsx"),
                        "--src", os.path.join(tree, "src"), "--list-fallbacks"],
                       capture_output=True, timeout=900,
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    body = r.stdout.decode("utf-8", "replace")
    io.open(txt, "w", encoding="utf-8").write(body)
    return txt, r.returncode


def rows(path):
    out = []
    for line in io.open(path, encoding="utf-8", errors="replace"):
        m = ROW.match(line)
        if m:
            out.append({"tier": m.group(1) + " " + m.group(2), "shape": m.group(3).strip(),
                        "file": os.path.basename(m.group(4)), "line": int(m.group(5)),
                        "literal": m.group(6).strip()})
    return out


def main():
    import hashlib
    out = {"ruler": {"file": os.path.basename(RULER),
                     "blob": hashlib.sha1(b"blob %d" % os.path.getsize(RULER) + chr(0).encode()
                                          + io.open(RULER, "rb").read()).hexdigest(),
                     "bytes": os.path.getsize(RULER),
                     "provenance": "git show <tip>:tools/cnx_copy_tiers_r1.py, not a lane copy"},
           "reports": {}, "comparison": {}}
    got = {}
    for label, tree in TREES.items():
        txt, rc = run(label, tree)
        rs = rows(txt)
        summary = [l for l in io.open(txt, encoding="utf-8", errors="replace")
                   if "HARDCODED_FALLBACK" in l]
        got[label] = rs
        out["reports"][label] = {"exit_code": rc, "rows": len(rs), "report": os.path.basename(txt),
                                 "face_line": summary[0].strip()[:300] if summary else None}
    a, b = got["before_tip4037"], got["after_ord0428r1"]
    key = lambda r: (r["tier"], r["shape"], r["file"], r["literal"])
    shifted = [(x, y) for x, y in zip(a, b) if x["line"] != y["line"]]
    out["comparison"] = {
        "rows_before": len(a), "rows_after": len(b),
        "row_lists_equal_when_line_ignored": [key(x) for x in a] == [key(y) for y in b],
        "rows_with_a_different_line_number": len(shifted),
        "shift_detail": [{"file": x["file"], "before_line": x["line"], "after_line": y["line"],
                          "delta": y["line"] - x["line"], "tier": x["tier"], "literal": x["literal"]}
                         for x, y in shifted],
        "all_shifts_inside": sorted({x["file"] for x, _ in shifted}),
        "verdict": ("NO_NEW_COPY_FACE_LINE_SHIFTS_ONLY"
                    if len(a) == len(b) and [key(x) for x in a] == [key(y) for y in b]
                    else "SEE_ROW_LISTS"),
    }
    io.open(os.path.join(WORK, "copy_ruler_parity_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out, ensure_ascii=False, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
