#!/usr/bin/env python3
"""ORD-0371 r5f: run the three generations side by side over the WHOLE inbox, the way the commander
does (`--text <file>`), and name the residual instead of just counting it.

Nothing here edits a ruler. The residual table is what the acceptance asks for: "哪几行还拒、为什么该
拒", computed from the ruler's own findings, with the coordinate test it failed.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
INBOX = r"D:/moodle/_qoder_ledger_inbox"
WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0371"
GENS = ("r4e", "r5e", "r5f")
NAMED = ["n2_0213.md", "n2_0228.md", "qoder-0370_0148.md", "rel_0338.md"]


def run(gen, path, out):
    r = subprocess.run([sys.executable, os.path.join(LIVE, "claim_coordinate_check_%s.py" % gen),
                        "--text", path, "--out", out], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=600)
    doc = json.load(io.open(out, encoding="utf-8")) if os.path.exists(out) else {}
    return {"exit": r.returncode, "verdict": doc.get("verdict"),
            "claims": doc.get("claims_checked"), "exempt": doc.get("exempt_classes"),
            "findings": doc.get("findings", []), "total": doc.get("finding_total", len(doc.get(
                "findings", [])))}


def main():
    files = sorted(f for f in os.listdir(INBOX)
                   if f.endswith(".md") and re.match(r"^[A-Za-z0-9._-]+_[0-9]{4}\.md$", f))
    rows = []
    for f in files:
        path = os.path.join(INBOX, f)
        per = {}
        for g in GENS:
            out = os.path.join(WORK, "_tmp", "bk_%s_%s.json" % (g, f.replace(".md", "")))
            per[g] = run(g, path, out)
        rows.append({"file": f, "named_by_commander": f in NAMED,
                     "bytes": os.path.getsize(path),
                     **{g: {k: per[g][k] for k in ("exit", "verdict", "claims", "total", "exempt")}
                        for g in GENS}})
    # the named residual for rel_0338: every line that still burns, why, and what it holds.
    # (r1 of this tool read `per` after the file loop, which held the LAST block's findings and printed
    # them against rel_0338's line numbers - an instrument bug of exactly the kind the ruler exists to
    # catch.  The residual is now computed from a run of THIS file, named and re-read here.)
    sys.path.insert(0, LIVE)
    m5f = __import__("claim_coordinate_check_r5f")
    rel_path = os.path.join(INBOX, "rel_0338.md")
    rel_out = os.path.join(WORK, "_tmp", "residual_rel_0338_r5f.json")
    rel_run = run("r5f", rel_path, rel_out)
    assert rel_run["total"] == [r for r in rows if r["file"] == "rel_0338.md"][0]["r5f"]["total"], (
        rel_run["total"], "the residual must be computed from the same run as the table")
    text = io.open(rel_path, encoding="utf-8").read()
    _, f_rows = m5f.occurrences(text)
    lines = text.split("\n")
    res = {}
    for x in rows:
        if x["file"] != "rel_0338.md":
            continue
        for fd in rel_run["findings"]:
            ln = fd["line"]
            e = res.setdefault(ln, {"line": ln, "tokens": [], "classes": set(), "predicates": set(),
                                    "headings": None})
            e["tokens"].append(fd["matched"])
            e["classes"].add(str(fd["class_assigned_by_shape"]))
            e["predicates"].add(fd["predicate"])
    residual = []
    for ln in sorted(res):
        e = res[ln]
        has_coord = bool(m5f.DURABLE.search(lines[ln - 1]))
        residual.append({"line": ln, "tokens": sorted(set(e["tokens"])),
                         "classes": sorted(e["classes"]), "predicates": sorted(e["predicates"]),
                         "line_carries_resolvable_coordinate": has_coord,
                         "line_text_head": lines[ln - 1][:70],
                         "why_it_burns": ("no `path:line` and no full 40-hex on this line"
                                          if not has_coord else "UNEXPECTED - a coordinate is present")})
    green_r5f = [r["file"] for r in rows if r["r5f"]["exit"] == 0]
    summary = {"inbox_blocks": len(rows),
               "green": {g: len([r for r in rows if r[g]["exit"] == 0]) for g in GENS},
               "red": {g: len([r for r in rows if r[g]["exit"] == 3]) for g in GENS},
               "other_exit": {g: sorted({str(r[g]["exit"]) for r in rows
                                         if r[g]["exit"] not in (0, 3)}) for g in GENS},
               "total_findings": {g: sum(r[g]["total"] for r in rows) for g in GENS},
               "r5f_stricter_than_r5e_on": sorted({r["file"] for r in rows
                                                   if r["r5f"]["total"] > r["r5e"]["total"]}),
               "r5f_looser_than_r5e_on": sorted({r["file"] for r in rows
                                                 if r["r5f"]["total"] < r["r5e"]["total"]})}
    out = {"generations": {g: {"file": "claim_coordinate_check_%s.py" % g,
                               "blob": hashlib.sha1(
                                   b"blob %d\x00" % len(open(os.path.join(LIVE, "claim_coordinate_check_%s.py" % g), "rb").read())
                                   + open(os.path.join(LIVE, "claim_coordinate_check_%s.py" % g), "rb").read()).hexdigest()}
                           for g in GENS},
           "named_by_commander": NAMED, "summary": summary, "blocks": rows,
           "rel_0338_named_residual": residual}
    io.open(os.path.join(WORK, "backlog_r5f_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print()
    for r in rows:
        print("%-26s bytes %6d  r4e %3s  r5e %3s  r5f %3s  %s" % (
            r["file"], r["bytes"], r["r4e"]["total"], r["r5e"]["total"], r["r5f"]["total"],
            "NAMED" if r["named_by_commander"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
