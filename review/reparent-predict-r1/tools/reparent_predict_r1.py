"""ORD-0500 lane -- read-only prediction: can the two waiting branches be re-parented onto the live tip?

The 甲 question (re-parent anchor-form-r5 and staging-door-r7 onto the current tip) is the commander's to
answer, and this hand does NOT answer it: it moves no ref, writes no tree, and lands nothing.  What it
does is make the answer cheap -- a three-way, per-path prediction of what a replay would hit, computed
from blobs only.

Why three-way and not `merge-tree`: this line has been rebuilt at least once, so the two branches may
have no usable merge base with the current tip and a merge-tree run would report a whole-tree add that
says nothing about the three paths each branch actually carries.  Comparing (branch base blob, branch new
blob, tip blob) per path answers the only question a replay has: has the tip moved that path since the
branch was cut?

Vocabulary, byte-honest:
  CLEAN_REPLAY  -- tip blob == branch base blob; the branch's new blob applies untouched
  ALREADY_THERE -- tip blob == branch new blob; that path is already on the line
  CONFLICT      -- tip blob is a third value; a replay would overwrite someone's newer bytes
  ADD_IF_FREE   -- the branch adds a path that did not exist at its base (tip may or may not have it)
  CLEAN_DELETE  -- the branch deletes a path the tip still holds at the base blob
  DELETE_CONFLICT -- the branch deletes a path the tip has since changed
  DELETION_DONE -- the path the branch deletes is already gone from the tip
"""
import collections
import importlib.util
import json
import os
import re
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REFS = ["refs/heads/review/newlane-ord0500-phone-anchor-form-r5",
        "refs/heads/review/0afdb49b-ord0500-staging-door-r7"]
OUT = os.path.join(LANE, "evidence", "reparent_predict_r1")
ZERO = "0" * 40
HEX = re.compile(r"^[0-9a-f]{40}$")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def _r2():
    spec = importlib.util.spec_from_file_location(
        "lane_fleet_r2", os.path.join(LANE, "tools", "fleet_landed_rescan_r2.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(*args, stdin=None):
    p = subprocess.run(["git", "-C", REPO] + list(args), input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, env=ENV, timeout=900)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def own_paths(head):
    """{path: (base_blob_or_None, new_blob_or_None)} from the head's own diff against every parent.

    -m/--root so a merge is not read as empty and an orphan root is not silently dropped, and the
    trailing newline because git --stdin does not flush an unterminated final line.
    """
    rc, out, err = git("diff-tree", "-r", "--raw", "-m", "--root", "--full-index", "--stdin",
                       stdin=(head + "\n").encode())
    if rc:
        raise SystemExit("ABORT_DIFF_TREE rc=%d %s" % (rc, err[:200]))
    paths = {}
    for line in out.splitlines():
        if not line.startswith(":"):
            continue
        meta, path = line[1:].split("\t", 1)
        bits = meta.split()
        status, old, new = bits[-1], bits[-3], bits[-2]
        base = old if HEX.match(old) and old != ZERO else None
        if status == "D":
            paths[path] = (base, None)
            continue
        if HEX.match(new) and new != ZERO:
            paths[path] = (base, new)
    return paths


def main():
    r2 = _r2()
    rc, out, err = git("ls-remote", "--refs", "origin", TIP_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_NO_LIVE_TIP " + err[:160])
    tip = out.split()[0]
    tree = r2.tip_tree(tip)
    rows = []
    for ref in REFS:
        rc, out, err = git("ls-remote", "--refs", "origin", ref)
        if rc or not out.strip():
            raise SystemExit("ABORT_REF_NOT_ON_REMOTE " + ref)
        head = out.split()[0]
        rc, pars, _e = git("rev-list", "--parents", "--no-walk", head)
        parents = pars.split()[1:]
        per = []
        for path, (base, new) in sorted(own_paths(head).items()):
            tipb = tree.get(path)
            if new is None:
                if tipb is None:
                    verdict = "DELETION_DONE"
                elif base is not None and tipb == base:
                    verdict = "CLEAN_DELETE"
                else:
                    verdict = "DELETE_CONFLICT"
            elif base is None:
                verdict = "ALREADY_THERE" if tipb == new else "ADD_IF_FREE"
            elif tipb is None:
                verdict = "ADD_IF_FREE"
            elif tipb == base:
                verdict = "CLEAN_REPLAY"
            elif tipb == new:
                verdict = "ALREADY_THERE"
            else:
                verdict = "CONFLICT"
            per.append({"path": path, "base": base, "new": new, "tip_blob": tipb, "verdict": verdict})
        rows.append({"ref": ref, "head": head, "parents": parents, "paths": per,
                     "tally": dict(collections.Counter(p["verdict"] for p in per))})
    doc = {"tip": tip, "tip_tree_paths": len(tree), "refs": rows,
           "method": "per-path three-way (branch base, branch new, live tip blob); no merge-tree, "
                     "because a rebuilt line may leave no usable merge base",
           "writes": "none: no ref moved, no tree written, nothing landed, no fetch"}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "reparent_predict_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    tot = collections.Counter()
    for r in rows:
        tot.update(r["tally"])
    kv = {"tip": tip, "tip_tree_paths": len(tree), "refs": len(rows),
          "paths_total": sum(len(r["paths"]) for r in rows)}
    for r in rows:
        tag = r["ref"].split("0afdb49b-", 1)[-1].replace("-", "_")
        kv["head_" + tag] = r["head"]
        kv["paths_" + tag] = len(r["paths"])
        kv["parents_" + tag] = len(r["parents"])
        for v, n in sorted(r["tally"].items()):
            kv["%s_%s" % (v.lower(), tag)] = n
    for v, n in sorted(tot.items()):
        kv["total_" + v.lower()] = n
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    print(line)
    for r in rows:
        print("%s head=%s parents=%d paths=%d %s" % (
            r["ref"], r["head"], len(r["parents"]), len(r["paths"]),
            json.dumps(r["tally"], ensure_ascii=False)))
        for p in r["paths"]:
            print("   %-70s base=%s new=%s tip=%s %s" % (
                p["path"], (p["base"] or "-")[:12], (p["new"] or "-")[:12],
                (p["tip_blob"] or "-")[:12], p["verdict"]))


if __name__ == "__main__":
    main()
