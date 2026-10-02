# -*- coding: utf-8 -*-
"""Census round 3, second half: open each site the new shapes found, then RUN the arm that holds it.

Rounds one and two listed sites and judged them by reading. That leaves a gap: an arm nobody executed can be
a stale anchor and still sit in a green suite. So every site this round flags is resolved to its enclosing
test function, and each of those functions is executed by nodeid in this lane's export of the survey tip.
The export's own dirt is measured and reported rather than assumed away (`worktree_dirty_files` /
`worktree_dirty_outside_review`), and the tree shape the arms need is measured too (`review` in
sparse-checkout), because two of the files assert that committed readouts beside them exist. The classification below is a measured predicate, not a typed label: `negation_lines`
are the arm's own words inside its own body, and the two classes differ by whether the arm states that
growth is the defect (`closed_set_guard`) or only asserts the set it saw today (`open_set_equality`) - the
second is the one that reddens when an unrelated order legitimately widens the same schema.
"""
import io
import json
import os
import re
import subprocess

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord_anchors"
WT = r"D:\moodle\_qoder_lane_S4_0926\wt0391"
BACKEND = os.path.join(WT, "backend")
REPO = "D:/moodle/CityNexus"
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
ENV = dict(os.environ, PYTHONIOENCODING="utf-8", NO_PROXY="*")
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    ENV.pop(_k, None)

NEGATION = re.compile(r"\bno \w|must not|cannot|never|takes no|only\b|不许|不要|单一|唯一", re.I)
READS = {
    "contract_yaml": re.compile(r"yaml\.safe_load|_contract\(|_door\("),
    "live_http": re.compile(r"client\.(get|post|patch|delete)\(|_ics\(|\.json\(\)"),
    "tree_walk": re.compile(r"rglob|iterdir|ast\.parse|\.read_text\("),
    "inline_input": re.compile(r"H\.canon\(|canon\("),
}


def show(tip, rel):
    r = subprocess.run(["git", "-C", REPO, "show", "%s:%s" % (tip, rel)], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=ENV, timeout=600)
    if r.returncode != 0:
        raise SystemExit("cannot read %s at %s" % (rel, tip))
    return (r.stdout or "").split("\n")


def enclosing(src, n):
    for i in range(n - 1, -1, -1):
        m = re.match(r"def (\w+)", src[i])
        if m:
            return m.group(1), i
    return None, None


def body(src, start):
    out = [src[start]]
    for line in src[start + 1:]:
        if line.strip() and not line.startswith((" ", "\t")):
            break
        out.append(line)
    return out


def main():
    doc = json.load(io.open(os.path.join(WORK, "anchor_drift_survey_r3.json"), encoding="utf-8"))
    tip = doc["tip"]
    sites = [(r["file"], r["line"], "frozen_key_collection", r["left_hand_is_derived_inventory"],
              r["path_like_entries"], r["sample"]) for r in doc["collections_worth_opening"]]
    sites += [(r["file"], r["line"], r["form"], False, False, [])
              for r in doc["unresolved_or_stale"]]

    judged = []
    for rel, line, form, derived, paths, sample in sites:
        src = show(tip, rel)
        fn, start = enclosing(src, line)
        b = body(src, start) if start is not None else []
        text = "\n".join(b)
        reads = sorted(k for k, rx in READS.items() if rx.search(text))
        neg = [(i + start + 1, l.strip()[:120]) for i, l in enumerate(b)
               if (l.strip().startswith("#") or i == 0 or l.strip().startswith('"""'))
               and NEGATION.search(l)]
        shape = "equality_against_a_set" if form == "frozen_key_collection" else "row_number_argument"
        cls = ("closed_set_guard" if neg else "open_set_equality") if form == "frozen_key_collection" \
            else "unresolved_by_ruler"
        judged.append({"file": rel, "line": line, "form": form, "shape": shape,
                       "arm_function": fn, "arm_def_line": (start + 1) if start is not None else None,
                       "named_entries": sample, "left_hand_is_derived_inventory": derived,
                       "path_like_entries": paths, "left_hand_reads": reads,
                       "states_growth_is_the_defect": bool(neg), "negation_lines": neg[:3],
                       "class": cls, "assertion_text": src[line - 1].strip()[:150],
                       "nodeid": ("tests/" + rel.split("backend/tests/")[-1] + "::" + fn) if fn else None})

    nodeids = sorted({j["nodeid"] for j in judged if j["nodeid"]})
    dirty = subprocess.run(["git", "-C", WT, "status", "--porcelain"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=ENV,
                           timeout=600).stdout.splitlines()
    sparse = subprocess.run(["git", "-C", WT, "sparse-checkout", "list"], capture_output=True,
                            text=True, encoding="utf-8", errors="replace", env=ENV,
                            timeout=300).stdout.split()
    r = subprocess.run([PY, "-m", "pytest"] + nodeids +
                       ["-p", "no:cacheprovider", "-v", "--tb=line", "-rA"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=ENV, cwd=BACKEND, timeout=3600)
    out = (r.stdout or "") + (r.stderr or "")
    per = {}
    for line in out.splitlines():
        m = re.match(r"(PASSED|FAILED|ERROR|SKIPPED)\s+(\S+::\S+)", line.strip())
        if m:
            per[m.group(2)] = m.group(1)
    tail = [l for l in out.splitlines() if " passed" in l or " failed" in l or " error" in l]
    for j in judged:
        j["arm_ran_as"] = per.get(j["nodeid"], "NOT_IN_OUTPUT")
    out_doc = {"tip": tip, "worktree_head": subprocess.run(
        ["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=ENV, timeout=300).stdout.strip(),
        "worktree_dirty_files": len(dirty),
        "worktree_dirty_outside_review": sum(1 for d in dirty if not d[3:].startswith("review/")),
        "sparse_roots": sparse, "review_in_tree_shape": "review" in sparse,
        "sites": len(judged), "arms_executed": len(nodeids),
        "pytest_rc": r.returncode, "pytest_summary": (tail[-1] if tail else "")[:150],
        "per_arm": per, "by_class": {},
        "by_how_the_left_hand_is_obtained": {}, "sites_out": judged}
    for j in judged:
        out_doc["by_class"][j["class"]] = out_doc["by_class"].get(j["class"], 0) + 1
        key = "+".join(j["left_hand_reads"]) or "none_of_the_named_readers"
        out_doc["by_how_the_left_hand_is_obtained"][key] = \
            out_doc["by_how_the_left_hand_is_obtained"].get(key, 0) + 1
    io.open(os.path.join(WORK, "census_r3_arms_r1.json"), "w", encoding="utf-8").write(
        json.dumps(out_doc, ensure_ascii=False, indent=1))
    print(json.dumps({"tip": tip[:12], "sites": out_doc["sites"], "arms": len(nodeids),
                      "rc": out_doc["pytest_rc"], "summary": out_doc["pytest_summary"],
                      "by_class": out_doc["by_class"], "reads": out_doc["by_how_the_left_hand_is_obtained"],
                      "not_green": {k: v for k, v in per.items() if v != "PASSED"}},
                     ensure_ascii=False, indent=1))


raise SystemExit(main())
