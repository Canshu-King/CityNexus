"""Fleet-wide census of why review branches cannot land on the current line, with owner tallies.

Four buckets per remote review head: already inside the line's ancestry; mergeable (a merge base
exists and git merges clean); a real conflict (base exists, git answers one); or no common ancestor
at all -- the class the standing prescription "merge the tip into your own branch" cannot reach.

The first cut of this ruler carried an owner tally nested inside the has-a-base branch, so every
owner read zero; the tallies are now summed where the bucket is decided, and the exception names
(mergeable, conflicting, already inside) are written out in full because those are the rows a human
actually has to look at.
"""

import io
import json
import os
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
OUTDIR = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot"
PROG = os.path.join(OUTDIR, "fleet_census_progress.txt")
ROWS = os.path.join(OUTDIR, "fleet_census_exceptions.txt")
JSON_OUT = os.path.join(OUTDIR, "fleet_census_r2.json")
ENVS = dict(os.environ, NO_PROXY="*")


def run(args):
    p = subprocess.run(args, cwd=REPO, capture_output=True, env=ENVS)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def owner_of(ref):
    return ref.split("/")[-1].split("-")[0]


def main():
    rc, out, err = run(["git", "ls-remote", "origin",
                        "refs/heads/mirror/integration-frontend-apple-pass1"])
    parts = out.split("\t")
    tip = parts[0] if len(parts) == 2 and len(parts[0]) == 40 else ""
    if not tip:
        print("ABORT no tip :: " + err[:120])
        sys.exit(3)

    rc, out, err = run(["git", "ls-remote", "origin", "refs/heads/review/*"])
    heads = []
    for l in out.splitlines():
        p2 = l.split("\t")
        if len(p2) == 2 and len(p2[0]) == 40:
            heads.append((p2[1], p2[0]))
    if len(heads) < 10:
        print("ABORT the remote review population read " + str(len(heads)) + " heads")
        sys.exit(3)

    buckets = {"in_line": 0, "clean_merge": 0, "real_conflict": 0,
               "no_common_ancestor": 0, "other_nonzero": 0, "no_local_object": 0}
    by_owner = {}
    exceptions = []
    started = time.time()

    prog = io.open(PROG, "w", encoding="utf-8", newline="\n")
    prog.write("census start %s tip %s heads %d\n" % (time.strftime("%H:%M:%S"), tip, len(heads)))
    prog.flush()

    for i, (ref, sha) in enumerate(heads):
        if run(["git", "cat-file", "-e", sha + "^{commit}"])[0] != 0:
            bucket = "no_local_object"
        else:
            inside = run(["git", "merge-base", "--is-ancestor", sha, tip])[0] == 0
            base = run(["git", "merge-base", tip, sha])[1]
            if inside:
                bucket = "in_line"
            elif not base:
                bucket = "no_common_ancestor"
            else:
                rc, mout, merr = run(["git", "merge-tree", "--write-tree", tip, sha])
                if rc == 0:
                    bucket = "clean_merge"
                elif rc == 1:
                    bucket = "real_conflict"
                else:
                    bucket = "other_nonzero"
        buckets[bucket] += 1
        own = owner_of(ref)
        cell = by_owner.setdefault(own, {k: 0 for k in buckets})
        cell[bucket] += 1
        cell["heads"] = cell.get("heads", 0) + 1
        if bucket in ("in_line", "clean_merge", "real_conflict", "other_nonzero"):
            exceptions.append({"ref": ref, "sha": sha, "bucket": bucket})
        if (i + 1) % 100 == 0:
            prog.write("拍 %d/%d 用去 %d 秒｜无共同祖先 %d｜已在线内 %d｜干净可并 %d｜真冲突 %d｜别的非零 %d｜本机无对象 %d\n"
                       % (i + 1, len(heads), int(time.time() - started),
                          buckets["no_common_ancestor"], buckets["in_line"], buckets["clean_merge"],
                          buckets["real_conflict"], buckets["other_nonzero"], buckets["no_local_object"]))
            prog.flush()

    ex = io.open(ROWS, "w", encoding="utf-8", newline="\n")
    ex.write("例外名单（与现尖有共同祖先、或已在世系内的枝）取于 %s｜现尖 %s\n"
             % (time.strftime("%Y-%m-%d %H:%M:%S"), tip))
    for e in exceptions:
        ex.write("%s | %s | %s\n" % (e["bucket"], e["ref"], e["sha"]))
    ex.write("例外合计 %d 枝\n" % len(exceptions))
    ex.close()

    total = "全量 %d 枝扫完，用去 %d 秒｜%s\n" % (len(heads), int(time.time() - started),
                                                json.dumps(buckets, ensure_ascii=False))
    prog.write(total)
    prog.close()

    ranked = sorted(by_owner.items(), key=lambda kv: -kv[1]["no_common_ancestor"])[:30]
    receipt = {
        "measured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "live_tip": tip,
        "remote_review_heads": len(heads),
        "seconds": int(time.time() - started),
        "buckets": buckets,
        "owners_ranked_by_no_common_ancestor": [
            {"owner": o, "no_common_ancestor": c["no_common_ancestor"], "heads": c["heads"],
             "in_line": c["in_line"], "clean_merge": c["clean_merge"],
             "real_conflict": c["real_conflict"]} for o, c in ranked],
        "exception_rows_written": len(exceptions),
        "owner_sum_selfcheck": sum(c["heads"] for c in by_owner.values()),
    }
    io.open(JSON_OUT, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    if receipt["owner_sum_selfcheck"] != len(heads):
        print("SELF-CHECK-FAIL owner sum %s != heads %s"
              % (receipt["owner_sum_selfcheck"], len(heads)))
    sys.stdout.buffer.write(json.dumps(
        {k: v for k, v in receipt.items() if k != "owners_ranked_by_no_common_ancestor"},
        ensure_ascii=False, indent=1).encode("utf-8", "replace"))
    print("\nFLEET-CENSUS-R2-DONE")


if __name__ == "__main__":
    main()
