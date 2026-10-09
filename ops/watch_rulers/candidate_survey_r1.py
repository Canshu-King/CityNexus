"""Read-only survey of one or more candidate refs against the live authoritative tip.

Why: I now have a landing door (preflight_and_land_r1.py) that refuses unless everything is clean, but it runs
the suite, which is minutes of work. Before I spend that I want the cheap structural facts for every candidate
that exists right now, in one pass, so I can tell a lane "you are landing-ready except for X" instead of
"waiting". Nothing here writes or moves a ref.

Per candidate it answers:
  * is it a descendant of the tip (ff possible) or does it sit on an older generation;
  * ahead/behind counts measured at this instant, not remembered;
  * merge-tree prediction against the tip: exit code + the files a union merge would conflict on;
  * the files it changes relative to the tip, and the intersection with every OTHER candidate in the same call
    (that intersection is what decides whether two lanes will collide when both land).
"""
import argparse
import io
import json
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = "D:/moodle/CityNexus"


def git(*a):
    p = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True, timeout=600)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tip", required=True)
    ap.add_argument("--candidate", action="append", required=True, dest="cands")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rc, tip, err = git("rev-parse", "--revs-only", args.tip)
    assert rc == 0 and len(tip) == 40, "tip did not resolve: %r %s" % (tip, err)
    rc, _t, err = git("cat-file", "-t", tip)
    assert rc == 0, "tip object missing locally - fetch first: %s" % err

    rows = []
    for ref in args.cands:
        rc, sha, err = git("rev-parse", "--revs-only", ref)
        if rc != 0 or len(sha) != 40:
            rows.append({"ref": ref, "error": "ref did not resolve locally (fetch it): %s" % err[:120]})
            continue
        rc, obj, _ = git("cat-file", "-t", sha)
        if rc != 0:
            rows.append({"ref": ref, "sha": sha, "error": "object missing locally - fetch this ref"})
            continue
        _, ab, _ = git("rev-list", "--left-right", "--count", "%s...%s" % (tip, sha))
        behind, ahead = (int(x) for x in ab.split())
        rcanc, _o, _e = git("merge-base", "--is-ancestor", tip, sha)
        ff_possible = rcanc == 0
        rcm, mt, mte = git("merge-tree", "--write-tree", tip, sha)
        conflict_lines = [l for l in mt.splitlines()[1:] if l.strip()] if rcm != 0 else []
        _, names, _ = git("diff", "--name-only", tip, sha)
        files = [l for l in names.splitlines() if l.strip()]
        _, subj, _ = git("log", "-1", "--format=%s", sha)
        _, ad, _ = git("log", "-1", "--format=%ad", "--date=iso-strict", sha)
        rows.append({"ref": ref.replace("refs/heads/", ""), "sha": sha, "object_type": obj,
                     "commit_subject": subj, "commit_date": ad,
                     "behind_the_tip": behind, "ahead_of_tip": ahead,
                     "ff_possible_from_tip": ff_possible,
                     "merge_tree_exit": rcm,
                     "merge_tree_prediction": "CLEAN_UNION" if rcm == 0 else "CONFLICT_PREDICTED",
                     "conflict_surface": conflict_lines,
                     "files_changed_vs_tip": files, "n_files": len(files)})

    inter = []
    ok = [r for r in rows if "sha" in r]
    for i in range(len(ok)):
        for j in range(i + 1, len(ok)):
            a, b = set(ok[i]["files_changed_vs_tip"]), set(ok[j]["files_changed_vs_tip"])
            inter.append({"pair": [ok[i]["ref"], ok[j]["ref"]], "shared_files": sorted(a & b),
                          "collision": bool(a & b)})
    out = {
        "schema": "CNX_CMDR_CANDIDATE_SURVEY_V1",
        "lane": "commander 494abfd7",
        "at_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "what": "structural landing survey of candidate refs against the live tip - no suite run, no ref move",
        "tip": tip,
        "candidates": rows,
        "pairwise_intersections": inter,
        "standing_rule": "ff_possible is computed against the tip read at this instant; a candidate that is not a "
                         "descendant must be re-cut by its owner before the suite is worth running. Two "
                         "candidates sharing a file will collide whoever lands second, so the order between them "
                         "is a decision, not an accident.",
        "discipline": {"refs_pushed": 0, "authoritative_branch_moved": 0, "suites_run": 0,
                       "databases_opened": 0, "credential_values_printed": 0},
        "claim_kind": "git_determined",
        "claimed_result": None, "derived_result": None,
    }
    out["claimed_result"] = ("%s: " % tip[:10]) + "; ".join(
        "%s ahead=%d behind=%d ff=%s %s files=%d" % (r["ref"], r["ahead_of_tip"], r["behind_the_tip"],
                                                     r["ff_possible_from_tip"], r["merge_tree_prediction"],
                                                     r["n_files"]) if "sha" in r else "%s UNRESOLVED" % r["ref"]
        for r in rows)
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(out["claimed_result"])
    for r in rows:
        if "sha" not in r:
            print("   %-52s %s" % (r["ref"], r["error"][:90]))
            continue
        print("   %-52s %s  ff=%-5s %s  files=%d" % (r["ref"], r["sha"][:10], r["ff_possible_from_tip"],
                                                    r["merge_tree_prediction"], r["n_files"]))
        for f in r["conflict_surface"][:6]:
            print("        conflict:", f[:120])
    for x in inter:
        print("   pair %s shared=%s" % ("|".join(p[:28] for p in x["pair"]), x["shared_files"]))
    print("file=%s bytes=%d" % (args.out, len(txt.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
