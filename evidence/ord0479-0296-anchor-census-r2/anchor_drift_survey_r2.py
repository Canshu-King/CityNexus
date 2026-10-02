# -*- coding: utf-8 -*-
"""Drift survey r2 - the same four patterns re-run on a later generation (the r1 files stay
published untouched; this one exists so the census has two generations, not one snapshot).

The original question: which other arms in the suite pin a row number or a frozen name list, and which of them
 are already stale on this tip.

The CMDR 07:57 order fixed two rulers by name. The same failure mode exists wherever an arm says
"(FILE, 45)", "splitlines()[9]" or "== [five file names]": it goes red when the tree moves without any
product change. This is a measurement, not a dispatch: for every hit it records the arm, the literal
anchor, the file it points at, and whether that file still has anything at that row today.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
TIP = sys.argv[1] if len(sys.argv) > 1 else "65bc4c4ede83a3718535a37aaae3698681c8eda4"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
PREFIX = "backend/tests/"

NUMERIC = [
    (re.compile(r"\(\s*([A-Z_][A-Z0-9_]*)\s*,\s*(\d{1,4})\s*\)"), "named_path_with_row"),
    (re.compile(r"\(\s*[\"']((?:frontend|backend|contracts|tools|data)/[^\"']+)[\"']\s*,\s*(\d{1,4})\s*\)"),
     "literal_path_with_row"),
    (re.compile(r"splitlines\(\)\s*\[\s*(\d{1,4})\s*(?:-\s*1)?\s*\]"), "index_into_splitlines"),
    (re.compile(r"\[\s*(\d{1,4})\s*:\s*(\d{1,4})\s*\]"), "line_slice"),
]
FROZEN = re.compile(r"==\s*\[\s*(\"[^\"]+\.py\"[^\]]*)\]")
#: a frozen list is usually written across lines, which the single-line form above misses entirely
FROZEN_MULTILINE = re.compile(r"==\s*\[\s*((?:\s*\"[^\"]+\.py\",?)+)\s*\]", re.S)
CACHE = {}


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    return r.returncode, (r.stdout or "")


def files():
    rc, out = git("ls-tree", "-r", "--name-only", TIP, PREFIX)
    return [f for f in out.splitlines() if f.endswith(".py")]


def lines_of(rel):
    if rel not in CACHE:
        rc, out = git("show", "%s:%s" % (TIP, rel))
        CACHE[rel] = out.split("\n") if rc == 0 else None
    return CACHE[rel]


LAST_COMMIT = {}


def last_commit_date(test_rel):
    if test_rel not in LAST_COMMIT:
        rc, out = git("log", "-1", "--format=%cI", TIP, "--", test_rel)
        LAST_COMMIT[test_rel] = out.strip() if rc == 0 and out.strip() else None
    return LAST_COMMIT[test_rel]


def churn_since(test_rel, target):
    """How many commits have moved `target` since the arm that pins it was last written - that is the
    drift pressure, measured rather than asserted."""
    since = last_commit_date(test_rel)
    if not since:
        return None
    rc, out = git("rev-list", "--count", "--since=%s" % since, TIP, "--", target)
    return int(out.strip()) if rc == 0 and out.strip().isdigit() else None


def resolve_basename(test_rel, name):
    """A frozen list usually holds basenames; find the real path they name under backend/."""
    rc, out = git("ls-tree", "-r", "--name-only", TIP, "backend/")
    hits = [p for p in out.splitlines() if p.endswith("/" + name) or p.endswith(name)]
    return hits


def main():
    rows = []
    for f in files():
        src = lines_of(f)
        if src is None:
            continue
        path_consts = {}
        for m in re.finditer(r'^([A-Z][A-Z0-9_]*)\s*=\s*"((?:frontend|backend|contracts|tools|data)/[^"]+)"',
                             "\n".join(src), re.M):
            path_consts[m.group(1)] = m.group(2)
        for i, line in enumerate(src, 1):
            if line.strip().startswith("#"):
                continue
            for pat, kind in NUMERIC:
                for m in pat.finditer(line):
                    nums = [int(g) for g in m.groups() if g and g.isdigit()]
                    named = m.group(1) if not m.group(1).isdigit() else None
                    target = path_consts.get(named)
                    if target is None and named and named.endswith(".py"):
                        # some arms write the path as a bare string in the tuple instead of a const
                        target = named if lines_of(named) else ("backend/" + named
                                                                if lines_of("backend/" + named) else named)
                    if target is None and named:
                        cand = [v for k, v in path_consts.items() if k in line and v]
                        target = cand[0] if cand else None
                    present = None
                    if target:
                        # a path the arm injects into its own temporary root is not a coordinate into the
                        # shipped tree; separating that from a real repo path is the difference between a
                        # drift risk and my checker shouting at a fixture it wrote itself
                        src_text = "\n".join(src)
                        writes_it = any((named in l) and re.search(
                            r"write_text|_write\(|touch\(|mkdir", l) for l in src)
                        tl = lines_of(target)
                        if tl is None:
                            present = "self_written_fixture" if writes_it else "TARGET_NOT_IN_TREE"
                        else:
                            row = nums[0] if nums else 0
                            present = ("row_exists" if 0 < row <= len(tl)
                                       else "row_past_end_of_file(%d lines)" % len(tl))
                    else:
                        present = "target_unresolved"
                    rows.append({"arm_file": f, "arm_line": i, "form": kind,
                                 "literal": line.strip()[:120], "named_target": target,
                                 "row_named": (nums[0] if nums else None), "check_on_tip": present,
                                 "churn_since_arm_written": (churn_since(f, target) if target else None)})
            for m in FROZEN.finditer(line):
                names = re.findall(r"\"([^\"]+\.py)\"", m.group(1))
                churns = {}
                for n in names:
                    for p in resolve_basename(f, n):
                        churns[p] = churn_since(f, p)
                rows.append({"arm_file": f, "arm_line": i, "form": "frozen_name_list",
                             "literal": line.strip()[:120], "named_target": None,
                             "row_named": None, "names": names, "resolved": churns,
                             "check_on_tip": "names %d entries" % len(names)})
        whole = "\n".join(src)
        seen_lines = {r["arm_line"] for r in rows if r["arm_file"] == f}
        for m in FROZEN_MULTILINE.finditer(whole):
            at = whole[:m.start()].count("\n") + 1
            if at in seen_lines:
                continue
            names = re.findall(r"\"([^\"]+\.py)\"", m.group(1))
            churns = {}
            for n in names:
                for p in resolve_basename(f, n):
                    churns[p] = churn_since(f, p)
            rows.append({"arm_file": f, "arm_line": at, "form": "frozen_name_list",
                         "literal": " ".join(x.strip() for x in m.group(0).splitlines())[:150],
                         "named_target": None, "row_named": None, "names": names,
                         "resolved": churns,
                         "check_on_tip": "names %d entries" % len(names)})
    stale = [r for r in rows if r["check_on_tip"] and r["check_on_tip"] != "row_exists"
             and r["form"] != "frozen_name_list"]
    frozen = [r for r in rows if r["form"] == "frozen_name_list"]
    doc = {"tip": TIP, "test_files_scanned": len(files()), "anchors_found": len(rows),
           "by_form": {k: sum(1 for r in rows if r["form"] == k) for k in
                       ("named_path_with_row", "index_into_splitlines", "line_slice",
                        "frozen_name_list")},
           "already_stale": stale, "frozen_lists": frozen, "rows": rows}
    os.makedirs(OUT, exist_ok=True)
    io.open(os.path.join(OUT, "anchor_drift_survey_r2.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": TIP, "files": doc["test_files_scanned"], "anchors": len(rows),
                      "by_form": doc["by_form"], "stale": len(stale),
                      "frozen": len(frozen)}, ensure_ascii=False))


raise SystemExit(main())
