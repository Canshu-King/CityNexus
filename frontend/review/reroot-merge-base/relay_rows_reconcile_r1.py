"""Reconcile the newest relay round's named rows against what the line actually says today.

Each row the relay block prints is re-asked, live: does that ref exist on the remote at all, which
of the four ancestry buckets is it in against the current tip, and does it still owe anything the
line does not carry (write-set paths absent at the tip, split into product paths versus the lane's
own review/e2e artifacts).  Rows are written one per line so a block can cite the row it claims.
"""

import io
import json
import os
import re
import subprocess
import sys
import time

REPO = "D:/moodle/CityNexus"
LEDGER = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
OUTDIR = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot"
TXT = os.path.join(OUTDIR, "relay_rows_reconciled.txt")
JSON_OUT = os.path.join(OUTDIR, "relay_rows_reconciled_r1.json")
ENVS = dict(os.environ, NO_PROXY="*")
PRESCRIPTION = "把现尖 merge 进你自己的 review 枝"


def run(args):
    p = subprocess.run(args, cwd=REPO, capture_output=True, env=ENVS)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip(), p.stderr.decode("utf-8", "replace").strip()


def newest_relay():
    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
    start = None
    head = ""
    for i, l in enumerate(lines):
        if l.startswith("### ") and "待并枝回话" in l:
            for j in range(i, min(i + 30, len(lines))):
                if PRESCRIPTION in lines[j]:
                    scan = ""
                    for k in range(max(i - 2, 0), min(i + 30, len(lines))):
                        if "这一拍扫描" in lines[k]:
                            scan = lines[k]
                            break
                    return i, lines[i], scan
    if start is None and head is None:
        die("no relay block in the newest ledger region carries the prescription")
    return start, head, ""


def die(msg):
    sys.stdout.buffer.write(("ABORT " + msg).encode("utf-8", "replace"))
    sys.exit(3)


def main():
    i_head, head, scan_line = newest_relay()
    tip = run(["git", "ls-remote", "origin",
               "refs/heads/mirror/integration-frontend-apple-pass1"])[1].split("\t")[0]
    if len(tip) != 40:
        die("no live tip")

    lines = io.open(LEDGER, encoding="utf-8", errors="replace").read().split("\n")
    rows = []
    for k in range(i_head, min(i_head + 200, len(lines))):
        l = lines[k]
        if l.startswith("### ") and k > i_head:
            break
        m = re.match(r"^· (.+?)：枝 (refs/heads/review/\S+) 与现尖不相交，撞在 (.+)$", l.strip())
        if m:
            rows.append({"line": k + 1, "owner": m.group(1), "ref": m.group(2),
                         "claimed_collisions": m.group(3)})
    if len(rows) < 5:
        die("the relay block yielded " + str(len(rows)) + " rows -- the pattern moved, not the fleet")

    remote = {}
    rc, out, err = run(["git", "ls-remote", "origin", "refs/heads/review/*"])
    for l in out.splitlines():
        p2 = l.split("\t")
        if len(p2) == 2 and len(p2[0]) == 40:
            remote[p2[1]] = p2[0]

    fh = io.open(TXT, "w", encoding="utf-8", errors="replace")
    fh.write("最新一轮转达块（账本第 %d 行）%s\n" % (i_head + 1, head[4:78]))
    fh.write("扫描原判那行 %s\n" % scan_line.strip()[:150])
    fh.write("对照现尖 %s 逐行复核（取于 %s）\n" % (tip, time.strftime("%Y-%m-%d %H:%M:%S")))
    counts = {"ghost": 0, "no_base": 0, "clean": 0, "conflict": 0, "in_line": 0, "nothing_owed": 0}
    for r in rows:
        sha = remote.get(r["ref"], "")
        if not sha:
            r["exists_on_remote"] = False
            r["bucket"] = "ghost：远端读不到这枚枝"
            counts["ghost"] += 1
        else:
            r["exists_on_remote"] = True
            r["sha"] = sha
            if run(["git", "cat-file", "-e", sha + "^{commit}"])[0] != 0:
                r["bucket"] = "本机无对象"
            elif run(["git", "merge-base", "--is-ancestor", sha, tip])[0] == 0:
                r["bucket"] = "已在现尖世系内"
                counts["in_line"] += 1
            else:
                base = run(["git", "merge-base", tip, sha])[1]
                if not base:
                    r["bucket"] = "与现尖无共同祖先（merge 被 git 拒）"
                    counts["no_base"] += 1
                else:
                    rc, mout, merr = run(["git", "merge-tree", "--write-tree", tip, sha])
                    if rc == 0:
                        r["bucket"] = "有共同祖先且能干净合并"
                        counts["clean"] += 1
                    elif rc == 1:
                        r["bucket"] = "有共同祖先但真有冲突"
                        counts["conflict"] += 1
                    else:
                        r["bucket"] = "别的非零 rc=%s %s" % (rc, " ".join(merr.split()[:5]))
                # what it still owes the line
                parent = run(["git", "rev-parse", sha + "^"])[1]
                rc, listing, _ = run(["git", "diff-tree", "-r", "--name-only", "--no-commit-id", sha, parent])
                ws = [p for p in listing.splitlines() if p.strip()]
                missing = []
                for p in ws:
                    if not run(["git", "rev-parse", "-q", "--verify", tip + ":" + p])[1]:
                        missing.append(p)
                r["writeset"] = len(ws)
                r["absent_at_tip"] = len(missing)
                r["absent_product_paths"] = [p for p in missing
                                             if "/review/" not in p and "/e2e/" not in p]
                if r["absent_at_tip"] == 0:
                    counts["nothing_owed"] += 1
        fh.write("行 %s | %s | %s | 远端可读=%s | 今判=%s | 写集=%s | 现尖缺=%s | 其中产品面=%s | 转达说撞在=%s\n"
                 % (r["line"], r["owner"], os.path.basename(r["ref"]), r["exists_on_remote"],
                    r.get("bucket", ""), r.get("writeset", "-"), r.get("absent_at_tip", "-"),
                    len(r.get("absent_product_paths", []) or []) if r.get("exists_on_remote") else "-",
                    r["claimed_collisions"][:44]))
    fh.write("复核合计：本轮回话列出 %d 行｜远端读不到（幽灵）%d 行｜无共同祖先 %d 行｜真有冲突 %d 行｜干净可并 %d 行｜已在世系内 %d 行｜写集已全部在现尖 %d 行\n"
             % (len(rows), counts["ghost"], counts["no_base"], counts["conflict"],
                counts["clean"], counts["in_line"], counts["nothing_owed"]))
    fh.close()

    receipt = {"measured_at": time.strftime("%Y-%m-%d %H:%M:%S"), "live_tip": tip,
               "relay_head_line": i_head + 1, "relay_head": head[4:110],
               "scan_line": scan_line.strip(), "rows": len(rows), "counts": counts, "detail": rows}
    io.open(JSON_OUT, "w", encoding="utf-8").write(json.dumps(receipt, ensure_ascii=False, indent=1))
    sys.stdout.buffer.write(json.dumps({"tip": tip, "rows": len(rows), "counts": counts},
                                       ensure_ascii=False).encode("utf-8", "replace"))
    print("\nRELAY-ROWS-RECONCILED")


if __name__ == "__main__":
    main()
