"""ORD-0504 C -- prove the comment-citation fix bites, and prove a comment costs the bundle nothing.

    D:/moodle/CityNexus/.venv/Scripts/python.exe review/ord0504/comment_ref_fixC_cycle_r1.py

Four generations of one comment line, graded by the shipped-citation ruler:

  tip    the comment exactly as the authoritative tip writes it   -> the named citation is reported broken
  fix    the shipped correction (full path, the line the symbol is really on) -> that citation is OK
  MC1    the old text put back                                    -> broken again, on the same row
  MC2    right path, wrong line (`backend/app/main.py:6100`)      -> broken, which is the point: the ruler
         reads the number, not just the filename

Then the two bundles are compared byte for byte. A comment that only prose changed must produce the same
entry asset, and if it did not, this would not be a documentation-only paper.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import book_screen_controls_r1 as ctl  # noqa: E402

TARGET = ctl.TARGET  # frontend/src/app/V8Experience.tsx
SCANNER = "review/ord0504/shipped_citation_scan_r1.py"
TIP = "b168b428f4ed0c9719a1aecf0bb38d98035cec9e"
OUT = ctl.TREE / "review" / "ord0504" / "comment_ref_fixC_cycle_r1.txt"
PY = str(ctl.PY)

OLD_COMMENT = b"""    /* `_reservation_payload` (main.py:3527) links a reservation to the commitment it became.  This is
       the only honest source for a "\xe5\x8f\x97\xe4\xbf\x9d\xe6\x8a\xa4" badge: without it the card was asserting a promise the
       server had not made (ORD-0146 \xe2\x91\xa2). */"""

FIX_COMMENT = b"""    /* `_reservation_payload` (`backend/app/main.py:6204`) links a reservation to the commitment it became.
       This is the only honest source for a "\xe5\x8f\x97\xe4\xbf\x9d\xe6\x8a\xa4" badge: without it the card was asserting a promise the
       server had not made (ORD-0146 \xe2\x91\xa2). */"""

MC2_COMMENT = FIX_COMMENT.replace(b"main.py:6204", b"main.py:6100")

NAMED_CITING = "frontend/src/app/V8Experience.tsx"


def replace_once(data: bytes, find: bytes, replace: bytes, label: str) -> bytes:
    if data.count(find) != 1:
        raise SystemExit("REFUSE: %s found %d times; the generation is not single-variable"
                         % (label, data.count(find)))
    return data.replace(find, replace, 1)


def scan(tag: str) -> dict:
    out_name = "citation_scan_%s.json" % tag
    report_name = "citation_scan_%s.txt" % tag
    env = dict(os.environ, CITATION_SCAN_OUT=out_name, CITATION_SCAN_REPORT=report_name)
    done = subprocess.run([PY, SCANNER], cwd=str(ctl.TREE), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)
    payload = json.loads((ctl.LANE / "run" / out_name).read_text(encoding="utf-8"))
    rows = [r for r in payload["rows"] if r["citing"].startswith(NAMED_CITING)]
    return {"tag": tag, "rc": done.returncode, "checked": payload["citations_checked"],
            "totals": payload["totals"], "hard": len(payload["hard_rotten"]),
            "named_rows": rows}


def main() -> int:
    shipped = TARGET.read_bytes()
    tip_text = subprocess.run(["git", "-C", str(ctl.TREE), "show",
                               "%s:frontend/src/app/V8Experience.tsx" % TIP],
                              capture_output=True).stdout
    mc1 = replace_once(shipped, FIX_COMMENT, OLD_COMMENT, "the shipped comment")
    mc2 = replace_once(shipped, FIX_COMMENT, MC2_COMMENT, "the shipped comment with a wrong line")

    lines = ["ORD-0504 C cycle | tip file bytes sha1 %s | shipped file sha1 %s"
             % (ctl.sha1(tip_text), ctl.sha1(shipped)), ""]
    results = {}
    for tag, data in (("tip", tip_text), ("fix", shipped), ("mc1", mc1), ("mc2", mc2)):
        TARGET.write_bytes(data)
        results[tag] = scan(tag)

    for tag in ("tip", "fix", "mc1", "mc2"):
        res = results[tag]
        lines.append("=== %s | citations checked %s | hard rotten %s | totals %s"
                     % (tag, res["checked"], res["hard"], json.dumps(res["totals"], ensure_ascii=False)))
        for row in res["named_rows"]:
            if row["verdict"] != "OK":
                lines.append("    BAD %s cites %s :: %s" % (row["citing"], row["citation"], row["detail"]))
        row148 = [r for r in res["named_rows"] if r["citing"].endswith(":148")]
        lines.append("    the named row: %s"
                     % (", ".join("%s citing %s" % (r["verdict"], r["citation"]) for r in row148)
                        or "no citation on line 148"))
        lines.append("")

    tip_hard, fix_hard = results["tip"]["hard"], results["fix"]["hard"]
    lines.append("verdict: the named citation is broken on the tip = %s"
                 % any(r["verdict"] != "OK" for r in results["tip"]["named_rows"]
                       if r["citing"].endswith(":148")))
    lines.append("verdict: the named citation is OK with the fix = %s"
                 % all(r["verdict"] == "OK" for r in results["fix"]["named_rows"]
                       if r["citing"].endswith(":148")))
    lines.append("verdict: MC1 puts the breakage back = %s"
                 % any(r["verdict"] != "OK" for r in results["mc1"]["named_rows"]
                       if r["citing"].endswith(":148")))
    lines.append("verdict: MC2 (right path, wrong line) is caught on its own row = %s"
                 % all(r["verdict"] != "OK" for r in results["mc2"]["named_rows"]
                       if r["citing"].endswith(":148")))
    lines.append("       MC2 lands in the loose bucket (`symbol exists in that file, just not at that "
                 "line`), so it does not move the hard count -- which is why this verdict reads the row, "
                 "not the total: mc2 row verdicts = %s"
                 % ", ".join(sorted({r["verdict"] for r in results["mc2"]["named_rows"]
                                     if r["citing"].endswith(":148")})))
    lines.append("verdict: the fix removes exactly one hard-rotten citation (tip %d -> fix %d) = %s"
                 % (tip_hard, fix_hard, tip_hard - fix_hard == 1))
    lines.append("verdict: MC1 restores exactly that one (fix %d -> mc1 %d) = %s"
                 % (fix_hard, results["mc1"]["hard"], results["mc1"]["hard"] - fix_hard == 1))

    # and the behaviour claim: a comment-only change must not move the bundle
    builds = {}
    for tag, data in (("tip", tip_text), ("fix", shipped)):
        TARGET.write_bytes(data)
        dist = "dist_cycleC_%s" % tag
        ctl.rebuild(dist)
        index_html = (ctl.LANE / dist / "index.html").read_bytes()
        match = re.search(rb"/?[A-Za-z0-9_./-]*assets/index-[A-Za-z0-9_-]+\.js", index_html)
        if not match:
            raise SystemExit("REFUSE: no entry asset in %s/index.html -- an empty comparison would read "
                             "as 'identical' and prove nothing" % dist)
        entry = match.group(0).decode().lstrip("/")
        blob = (ctl.LANE / dist / entry).read_bytes()
        builds[tag] = {"entry": entry, "bytes": len(blob), "sha1": ctl.sha1(blob),
                       "index_sha1": ctl.sha1(index_html)}
    lines.append("")
    lines.append("tip bundle  index sha1 %s | entry %s (%d B) sha1 %s"
                 % (builds["tip"]["index_sha1"], builds["tip"]["entry"], builds["tip"]["bytes"],
                    builds["tip"]["sha1"]))
    lines.append("fix bundle  index sha1 %s | entry %s (%d B) sha1 %s"
                 % (builds["fix"]["index_sha1"], builds["fix"]["entry"], builds["fix"]["bytes"],
                    builds["fix"]["sha1"]))
    lines.append("comment-only change leaves the built entry bytes identical: %s"
                 % (builds["tip"]["sha1"] == builds["fix"]["sha1"]))

    TARGET.write_bytes(shipped)
    lines.append("")
    lines.append("restored: bytes_equal_to_shipped=%s sha1=%s"
                 % (TARGET.read_bytes() == shipped, ctl.sha1(TARGET.read_bytes())))
    lines.append("git status --porcelain -- frontend/src/app/V8Experience.tsx = %r"
                 % subprocess.run(["git", "-C", str(ctl.TREE), "status", "--porcelain", "--",
                                   "frontend/src/app/V8Experience.tsx"],
                                  capture_output=True, text=True).stdout)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join([line for line in lines if not line.startswith("    BAD")]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
