# -*- coding: utf-8 -*-
"""Census round 3 - the two shapes round one declared it could not see.

The first two rounds of this census found 16 candidate sites across two generations and none of them was a
second drift bomb, but the block said plainly that it would miss (a) a row number handed to a helper as an
argument and (b) an equality against a frozen collection of keys. This script adds exactly those two, plus a
line-name tracker so `lines = src.splitlines()` … `lines[41]` is no longer invisible.

Nothing is edited: it lists sites, resolves what each site names, and reports whether the named row still
holds something like the arm's own literal. Anything it cannot resolve is left UNRESOLVED rather than
cleared.
"""
import io
import json
import os
import re
import subprocess
import sys

REPO = "D:/moodle/CityNexus"
OUT = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
ENV = dict(os.environ, HTTPS_PROXY="", HTTP_PROXY="", NO_PROXY="*")
PREFIX = "backend/tests/"
PAREN = re.compile(r"==\s*[\[\{\(]\s*((?:\s*[\"'][^\"']+[\"']\s*,?)+)\s*[\]\}\)]")
HELPER = re.compile(r"\b([a-zA-Z_][\w]*)\s*\(\s*([^,()\'\"]+)\s*,\s*(\d{1,4})\s*\)")
VAR_LINE = re.compile(r"^\s*(\w+)\s*=\s*[\w.]*\.splitlines\(\)")
VAR_INDEX = re.compile(r"\b(\w+)\s*\[\s*(\d{1,4})\s*\]")
PATH_CONST = re.compile(r'^([A-Z][A-Z0-9_]*)\s*=\s*"((?:frontend|backend|contracts|tools|data)/[^"]+)"',
                        re.M)


def git(*a):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ENV, timeout=900)
    if r.returncode != 0:
        raise SystemExit("git failed %s :: %s" % (a[:2], (r.stderr or "")[-200:]))
    return (r.stdout or "").strip()


def main():
    tip = (sys.argv[1] if len(sys.argv) > 1 else
           git("ls-remote", "--refs", "origin",
               "refs/heads/mirror/integration-frontend-apple-pass1").split()[0])
    files = [f for f in git("ls-tree", "-r", "--name-only", tip, PREFIX).splitlines()
             if f.endswith(".py")]
    # ORD-0574, the same family as the ledger mirror self-check: an empty scan is not a clean scan.
    # Two sides being equally absent is equality, not "no drift" - measured on r3, an empty tree in
    # produced rc 0 with "files": 0 and "sites": 0, which reads as green to any caller.
    if not files:
        raise SystemExit("ABORT: no .py files under %s at tip %s - refusing to call an empty "
                         "survey a clean one" % (PREFIX, tip))
    cache = {}

    def show(rel):
        if rel not in cache:
            rc = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (tip, rel)],
                                capture_output=True, text=True, encoding="utf-8",
                                errors="replace", env=ENV, timeout=600)
            cache[rel] = rc.stdout.split("\n") if rc.returncode == 0 else None
        return cache[rel]

    rows = []
    for f in files:
        src = show(f) or []
        text = "\n".join(src)
        consts = {m.group(1): m.group(2) for m in PATH_CONST.finditer(text)}
        for i, line in enumerate(src, 1):
            if line.strip().startswith("#"):
                continue
            for m in PAREN.finditer(line):
                items = re.findall(r"[\"']([^\"']+)[\"']", m.group(1))
                left = line.split("==")[0]
                # a list on the right of `==` is only drift-prone when the left side is a tree inventory:
                # a hand-written vocabulary list IS the guard, a derived one grows by itself upstream
                derived = bool(re.search(
                    r"rglob|iterdir|listdir|\.keys\(|sorted\(|read_text|ast\.|\bwalk\(|inspect\.|"
                    r"__all__|glob\(", left))
                rows.append({"file": f, "line": i, "form": "frozen_key_collection",
                             "literal": line.strip()[:130], "entries": len(items),
                             "left_hand_is_derived_inventory": derived,
                             "path_like_entries": any(
                                 re.search(r"\.(py|tsx?|css|json|ya?ml|md)$", x) for x in items),
                             "sample": items[:6]})
            for m in HELPER.finditer(line):
                fn, first, num = m.group(1), m.group(2).strip(), int(m.group(3))
                target = consts.get(first) or (first.strip("\"'") if first.startswith(('"', "'")) else None)
                if not target or not target.startswith(("frontend/", "backend/", "contracts/",
                                                         "tools/", "data/")):
                    continue
                tl = show(target)
                if tl is None:
                    rows.append({"file": f, "line": i, "form": "line_number_as_argument",
                                 "literal": line.strip()[:130], "helper": fn, "named_target": target,
                                 "row": num, "check": "TARGET_NOT_IN_TREE"})
                    continue
                rows.append({"file": f, "line": i, "form": "line_number_as_argument",
                             "literal": line.strip()[:130], "helper": fn, "named_target": target,
                             "row": num,
                             "check": ("row_exists" if 0 < num <= len(tl)
                                       else "row_past_end_of_file(%d lines)" % len(tl))})
        tracked = {}
        for i, line in enumerate(src, 1):
            mv = VAR_LINE.match(line)
            if mv:
                tracked[mv.group(1)] = True
            mi = VAR_INDEX.match(line)
            if mi and mi.group(1) in tracked:
                rows.append({"file": f, "line": i, "form": "index_through_tracked_variable",
                             "literal": line.strip()[:130], "variable": mi.group(1),
                             "row": int(mi.group(2)), "check": "needs_human_read"})
    stale = [r for r in rows if r.get("check") not in (None, "row_exists", "needs_human_read")]
    coll = [r for r in rows if r["form"] == "frozen_key_collection"]
    risky = [r for r in coll if r["left_hand_is_derived_inventory"] or r["path_like_entries"]]
    doc = {"tip": tip, "test_files_scanned": len(files), "sites": len(rows),
           "by_form": {k: sum(1 for r in rows if r["form"] == k) for k in
                       ("frozen_key_collection", "line_number_as_argument",
                        "index_through_tracked_variable")},
           "frozen_collections": len(coll),
           "collections_on_derived_inventory": sum(1 for r in coll if r["left_hand_is_derived_inventory"]),
           "collections_of_file_names": sum(1 for r in coll if r["path_like_entries"]),
           "collections_worth_opening": [{k: r[k] for k in
                                          ("file", "line", "entries", "sample",
                                           "left_hand_is_derived_inventory", "path_like_entries")}
                                         for r in risky],
           "unresolved_or_stale": stale, "rows": rows}
    io.open(os.path.join(OUT, "anchor_drift_survey_r3.json"), "w", encoding="utf-8").write(
        json.dumps(doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip, "files": len(files), "sites": len(rows),
                      "by_form": doc["by_form"], "stale_or_unresolved": len(stale),
                      "collections": doc["frozen_collections"],
                      "on_derived_inventory": doc["collections_on_derived_inventory"],
                      "file_name_lists": doc["collections_of_file_names"],
                      "worth_opening": len(doc["collections_worth_opening"])}, ensure_ascii=False))


raise SystemExit(main())
