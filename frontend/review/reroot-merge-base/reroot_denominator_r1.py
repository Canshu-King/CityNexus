"""The 15:35 and 18:30 relay blocks tell every listed owner to merge the live tip into their own
review branch.  This ruler asks git, for the branches that relay actually names, whether such a
merge exists at all -- and records what the scanner's own call answers, so a refusal for lack of a
common ancestor is not reported to the fleet as a file conflict.
"""

import io
import json
import os
import re
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
RELAY = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_stale_branch_state_1010.txt"
SCAN = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_disjoint_scan_r1.py"
OUTDIR = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot"
MINE = "fe972aecf50478622215544adbdf572e6171d2ce"
MINE_R2 = "f4fc92c62c487f76e3bcadd1a2957223e18199f7"


def run(args):
    p = subprocess.run(args, cwd=REPO, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def out(s):
    sys.stdout.buffer.write((s + "\n").encode("utf-8", "replace"))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    rc, line, err = run(["git", "ls-remote", "origin",
                         "refs/heads/mirror/integration-frontend-apple-pass1"])
    tip = line.split()[0] if line else ""
    if len(tip) != 40:
        out("ABORT no live tip :: " + err)
        sys.exit(3)

    rc, cnt, _ = run(["git", "rev-list", "--count", tip])
    rc, roots, _ = run(["git", "rev-list", "--max-parents=0", tip])
    root_rows = []
    for r in [x for x in roots.splitlines() if x.strip()]:
        rc, one, _ = run(["git", "log", "-1", "--date=format:%Y-%m-%d %H:%M",
                          "--format=%H|%ad|%s", r])
        root_rows.append(one)

    text = io.open(RELAY, encoding="utf-8", errors="replace").read()
    named = re.findall(r"refs/heads/review/[^\s，、]+", text)
    seen, listed = set(), []
    for b in named:
        if b not in seen:
            seen.add(b)
            listed.append(b)

    # one network read for the whole remote review population, then resolve names from it
    rc, allheads, err2 = run(["git", "ls-remote", "origin", "refs/heads/review/*"])
    remote = {}
    for l in allheads.splitlines():
        parts = l.split("\t")
        if len(parts) == 2 and len(parts[0]) == 40:
            remote[parts[1]] = parts[0]

    rows = []
    for b in listed[:24]:
        full = "refs/heads/" + b if not b.startswith("refs/") else b
        sha = remote.get(full, "")
        if len(sha) != 40:
            rows.append({"branch": b, "resolvable": False})
            continue
        rc, _, _ = run(["git", "cat-file", "-e", sha + "^{commit}"])
        if rc != 0:
            rows.append({"branch": b, "sha": sha, "local_object": False})
            continue
        mb_rc, mb, _ = run(["git", "merge-base", tip, sha])
        anc_rc, _, _ = run(["git", "merge-base", "--is-ancestor", sha, tip])
        mt_rc, mt_out, mt_err = run(["git", "merge-tree", "--write-tree", tip, sha])
        rows.append({
            "branch": b,
            "sha": sha,
            "local_object": True,
            "merge_base_present": bool(mb),
            "already_ancestor": anc_rc == 0,
            "merge_tree_rc": mt_rc,
            "merge_tree_first_stderr_words": " ".join(mt_err.split()[:6]) if mt_err else "",
        })

    # the two of mine the fleet relay does not name: the stranded candidate and its re-issue
    for tag, sha in (("stranded -r1", MINE), ("re-issued -r2", MINE_R2)):
        mb_rc, mb, _ = run(["git", "merge-base", tip, sha])
        mt_rc, mt_out, mt_err = run(["git", "merge-tree", "--write-tree", tip, sha])
        rows.append({
            "branch": tag,
            "sha": sha,
            "local_object": True,
            "merge_base_present": bool(mb),
            "already_ancestor": run(["git", "merge-base", "--is-ancestor", sha, tip])[0] == 0,
            "merge_tree_rc": mt_rc,
            "merge_tree_first_stderr_words": " ".join(mt_err.split()[:6]) if mt_err else "",
        })

    measured_with_base = [r for r in rows if r.get("local_object")]
    refused = [r for r in measured_with_base if r["merge_tree_rc"] != 0]
    unrelated = [r for r in refused if "unrelated histories" in r["merge_tree_first_stderr_words"]
                 or "refusing to merge unrelated" in str(r)]

    scan_line = ""
    for i, l in enumerate(io.open(SCAN, encoding="utf-8", errors="replace").read().splitlines()):
        if "判有冲突" in l:
            scan_line = "%s:%d:%s" % (os.path.basename(SCAN), i + 1, l.strip())

    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    txt = io.open(os.path.join(OUTDIR, "reroot_denominator_r1.txt"), "w", encoding="utf-8", newline="")
    txt.write("分母读数取于 %s｜现尖 %s｜该枝历史可达提交数 %s｜根数 %s\n" % (stamp, tip, cnt, len(root_rows)))
    head0 = text.splitlines()[0] if text.splitlines() else ""
    txt.write("点名册原文首行 %s\n" % head0)
    for r in root_rows:
        txt.write("根 | %s\n" % r[:120])
    txt.write("逐枝（合并基准 = 现尖 %s）\n" % tip[:12])
    for idx, r in enumerate(rows):
        txt.write("枝 %s | %s | 本地有对象=%s | 有共同祖先=%s | 已在现尖世系内=%s | merge-tree rc=%s | 首段成因=%s\n"
                  % (idx + 1, r.get("branch"), r.get("local_object"),
                     r.get("merge_base_present"), r.get("already_ancestor"),
                     r.get("merge_tree_rc"), r.get("merge_tree_first_stderr_words", "")))
    txt.write("合计 %s 枝：可测 %s 枝，merge-tree 非零 %s 枝，其中成因是无共同祖先 %s 枝\n"
              % (len(rows), len(measured_with_base), len(refused), len(unrelated)))
    txt.write("尺的判语原文 %s\n" % scan_line)
    txt.close()

    receipt = {
        "measured_at": stamp,
        "live_tip": tip,
        "tip_commits_reachable": int(cnt),
        "tip_root_count": len(root_rows),
        "tip_roots": root_rows,
        "relay_rows_read": len(listed),
        "branches_probed": len(rows),
        "probed_with_local_object": len(measured_with_base),
        "merge_tree_nonzero": len(refused),
        "cause_unrelated_histories": len(unrelated),
        "scanner_verdict_line": scan_line,
        "rows": rows,
    }
    io.open(os.path.join(OUTDIR, "reroot_denominator_r1.json"), "w", encoding="utf-8").write(
        json.dumps(receipt, ensure_ascii=False, indent=1))
    out(json.dumps({k: v for k, v in receipt.items() if k != "rows"}, ensure_ascii=False, indent=1))
    out("REROOT-DENOMINATOR-DONE")


if __name__ == "__main__":
    main()
