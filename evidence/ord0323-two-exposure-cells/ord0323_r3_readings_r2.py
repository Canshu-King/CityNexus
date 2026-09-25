"""ORD-0323 requirement (3): the same ruler (r3) measuring the cell's file on both sides of the change.

Readings come from `git show <sha>:<path>`, never from the working tree -- while the arms run, the working
tree holds a mutant. Two invocations of the commander's own r3, one per generation, each writing its own
JSON, so the before/after line sets are derived from the artifacts rather than retyped here.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
R3 = LANE / "live_checks/ui_exposure_field_check_r3.py"
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
PATHS = {
    "ProductErrorBoundary.tsx": "frontend/src/components/ProductErrorBoundary.tsx",
    "PlanWithAiSheet.tsx": "frontend/src/features/planning/PlanWithAiSheet.tsx",
    "JourneyInboxWorkbench.tsx": "frontend/src/features/inbox/JourneyInboxWorkbench.tsx",
}
CAND = subprocess.run(["git", "-C", str(LANE), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
if subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, "HEAD"],
                  capture_output=True).returncode != 0:
    raise SystemExit("the order's baseline is not an ancestor of HEAD; the generations would be mislabelled")
SPAN = int(subprocess.run(["git", "-C", str(LANE), "rev-list", "--count", f"{BASE}..HEAD"],
                          capture_output=True, text=True).stdout.strip())

out_dir = WORK / "r3"
out_dir.mkdir(exist_ok=True)


def materialize(sha: str, tag: str) -> list[str]:
    files = []
    for name, path in PATHS.items():
        body = subprocess.run(["git", "-C", str(LANE), "show", f"{sha}:{path}"],
                              capture_output=True, check=True).stdout
        f = out_dir / f"{tag}_{sha[:12]}__{name}"
        f.write_bytes(body)
        assert f.read_bytes() == body, f"blob did not read back for {f}"
        files.append(str(f))
    return files


def run(files: list[str], json_name: str) -> dict:
    target = out_dir / json_name
    r = subprocess.run([sys.executable, str(R3), "--file", ",".join(files), "--out", str(target)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"r3 exited {r.returncode}: {(r.stdout or '')[-400:]}{(r.stderr or '')[-400:]}")
    return json.loads(target.read_text(encoding="utf-8"))


def line_set(body: dict) -> set:
    return {(h["rule"], h["file"].split("__")[-1], h["line"]) for h in body["hits"]}


def identities(body: dict) -> list:
    """(rule, file, snippet) is the shape's identity; the line number is a coordinate that my own edit
    moves. Matching on the snippet is what keeps 'cleared' from meaning 'renumbered'."""
    return [(h["rule"], h["file"].split("__")[-1], h["snippet"]) for h in body["hits"]]


before_files = materialize(BASE, "baseline")
after_files = materialize(CAND, "candidate")
before = run(before_files, "r3_before.json")
after = run(after_files, "r3_after.json")
b, a = line_set(before), line_set(after)

bi, ai = {}, {}
for h in before["hits"]:
    bi.setdefault((h["rule"], h["file"].split("__")[-1], h["snippet"]), []).append(h["line"])
for h in after["hits"]:
    ai.setdefault((h["rule"], h["file"].split("__")[-1], h["snippet"]), []).append(h["line"])
same_shape = [
    {"rule": k[0], "file": k[1], "snippet": k[2], "lines_before": sorted(v),
     "lines_after": sorted(ai[k]),
     "line_delta": sorted(ai[k][i] - sorted(v)[i] for i in range(min(len(v), len(ai[k]))))}
    for k, v in bi.items() if k in ai]
gone = [{"rule": k[0], "file": k[1], "snippet": k[2], "lines_before": sorted(v)}
        for k, v in bi.items() if k not in ai]
new = [{"rule": k[0], "file": k[1], "snippet": k[2], "lines_after": sorted(v)}
       for k, v in ai.items() if k not in bi]

report = {
    "schema": "CNX_ORD0323_R3_READINGS_R1",
    "order": "ORD-0323",
    "lane": "B c01d72a3",
    "ruler": {"path": "live_checks/ui_exposure_field_check_r3.py",
              "published_blob": "44e062e6ce9c7b5d97d78e09e432072da102292c",
              "local_git_blob_hash": subprocess.run(
                  ["git", "-C", str(LANE), "hash-object", str(R3)], capture_output=True,
                  text=True).stdout.strip(),
              "selftest": json.loads(subprocess.run(
                  [sys.executable, str(R3), "--selftest"], capture_output=True, text=True,
                  encoding="utf-8").stdout)["verdict"],
              "local_sha256": __import__("hashlib").sha256(R3.read_bytes()).hexdigest()},
    "generations": {"before": BASE, "after": CAND, "commits_between": SPAN,
                    "after_contains_before_as_ancestor": True},
    "before": {"verdict": before["verdict"], "hit_count": len(before["hits"]),
               "hits": sorted("%s@%s:%d" % t for t in b)},
    "after": {"verdict": after["verdict"], "hit_count": len(after["hits"]),
              "hits": sorted("%s@%s:%d" % t for t in a)},
    "coordinate_diff": {
        "why": "raw hit coordinates on each side; NOT a claim that the difference is a fix -- the identity "
               "block below is what says which shapes actually went away",
        "before_lines": sorted("%s@%s:%d" % t for t in b),
        "after_lines": sorted("%s@%s:%d" % t for t in a),
    },
    "shape_identity": {
        "why": "line numbers move when I add lines above them; matching a shape by (rule, file, snippet) is "
               "what separates 'this shape is gone' from 'this shape got renumbered'",
        "same_shape_renumbered": same_shape,
        "shapes_gone": gone,
        "shapes_new": new,
    },
    "named_cells": {
        "cell1_ProductErrorBoundary:104-105": {
            "before": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                             for h in before["hits"] if h["file"].endswith("ProductErrorBoundary.tsx")),
            "after": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                            for h in after["hits"] if h["file"].endswith("ProductErrorBoundary.tsx")),
        },
        "cell3_PlanWithAiSheet:155_reason_code_slot": {
            "before": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                             for h in before["hits"] if h["file"].endswith("PlanWithAiSheet.tsx")),
            "after": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                            for h in after["hits"] if h["file"].endswith("PlanWithAiSheet.tsx")),
        },
        "cell2_JourneyInboxWorkbench:88_surfacing_at_687_691_731": {
            "before": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                             for h in before["hits"] if h["file"].endswith("JourneyInboxWorkbench.tsx")),
            "after": sorted("%s@%s:%d %s" % (h["rule"], h["file"].split("__")[-1], h["line"], h["snippet"])
                            for h in after["hits"] if h["file"].endswith("JourneyInboxWorkbench.tsx")),
        },
    },
    "reading": (f"before {len(before['hits'])} hit(s) -> after {len(after['hits'])} hit(s); "
                f"{len(gone)} shape(s) gone, {len(new)} new, "
                f"{sum(len(x['lines_before']) for x in same_shape)} unchanged shape occurrence(s) "
                f"renumbered by "
                f"{sorted({d for x in same_shape for d in x['line_delta']})} line(s)"),
    "interpretation_limit": "r3 is a pattern ruler over source text: it names shapes, not defects, and it "
                            "cannot see what a string holds at runtime. The lines that still fire are catch "
                            "blocks reading the message of the error this file now composes itself; whether "
                            "that message carries upstream words is judged by the e2e arms, not by r3.",
    "claim_kind": "pattern_determined",
    "claimed_result": None,
    "derived_result": None,
}
txt = json.dumps(report, ensure_ascii=False, indent=1)
(WORK / "ord0323_r3_readings.json").write_text(txt, "utf-8", newline="\n")
print(report["reading"])
print("shapes gone:", json.dumps([x["rule"] + "@" + x["file"] + str(x["lines_before"])
                                  for x in report["shape_identity"]["shapes_gone"]], ensure_ascii=False))
print("new       :", json.dumps(report["shape_identity"]["shapes_new"], ensure_ascii=False))
print("cell1 after:", json.dumps(report["named_cells"]["cell1_ProductErrorBoundary:104-105"]["after"]))
print("ruler selftest:", report["ruler"]["selftest"], "blob", report["ruler"]["local_git_blob_hash"])
print("->", WORK / "ord0323_r3_readings.json", "bytes", len(txt.encode("utf-8")))
