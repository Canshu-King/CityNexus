"""ORD-0500 lane -- fleet-wide landed-content re-scan (third generation of the ruler).

r1 and r2 scanned only the hands this lane published (42 refs).  The commander's standing
ruling is that landed-ness is byte equality against the live tip and that ancestry is
permanently unusable as a predicate, so the same question is worth asking of every candidate
the fleet ever pushed:  refs/heads/review/*, counted live below.

Everything is one pass of git over the local object store, and every head is resolved from a
ref the remote itself answers for -- no typed sha appears anywhere in this file.

Deliberately NOT done here: no fetch, no write, no ref is moved, nothing is landed, and no
verdict is claimed for a hand whose head cannot be read locally (that is reported as its own
class instead of being folded into ABSENT).
"""
import collections
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
OUT = os.path.join(LANE, "evidence", "fleet_rescan_r1")
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"

PRODUCT_PREFIXES = ("backend/", "frontend/", "contracts/", "tools/", "demo/", "docs/")


def git(*args, stdin=None):
    p = subprocess.run(["git", "-C", REPO] + list(args), input=stdin,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV, timeout=900)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


def lsremote(refspec=None):
    args = ["ls-remote", "--refs", "origin"] + ([refspec] if refspec else [])
    rc, out, err = git(*args)
    if rc:
        raise SystemExit("ABORT_LS_REMOTE " + err[:200])
    rows = []
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, name = line.split("\t")
        rows.append((name, sha))
    return rows


def tip_tree(tip):
    rc, out, err = git("ls-tree", "-r", tip)
    if rc:
        raise SystemExit("ABORT_TIP_TREE_UNREADABLE " + err[:200])
    tree = {}
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, sha = meta.split()
        tree[path] = sha
    return tree


def own_paths(heads):
    """path -> expected blob for each head, from diff-tree -r --raw -m --root.

    -m so a merge head is compared against EACH parent (a merge that carried someone else's
    file in is still that hand's published path), --root so the handful of history-less heads
    are not silently emitted as empty diffs, --full-index so both object names print in full.
    """
    rc, out, err = git("diff-tree", "-r", "--raw", "-m", "--root", "--full-index", "--stdin",
                       stdin="\n".join(heads).encode())
    if rc:
        raise SystemExit("ABORT_DIFF_TREE " + err[:200])
    by_head = collections.defaultdict(dict)
    cur = None
    for line in out.splitlines():
        line = line.rstrip("\n")
        if not line.startswith(":"):
            if len(line) >= 40:
                cur = line.split()[0]
                by_head.setdefault(cur, {})
            continue
        if cur is None:
            continue
        meta, path = line[1:].split("\t", 1)
        bits = meta.split()
        status = bits[-1]
        old, new = bits[-3], bits[-2]
        if status == "D":
            by_head[cur].setdefault(path, {"deleted": True, "expect": ""})
        else:
            if new == "0" * 40:
                continue
            by_head[cur].setdefault(path, {"deleted": False, "expect": new})
    return by_head


def main():
    os.makedirs(OUT, exist_ok=True)
    all_refs = lsremote()
    tip_rows = [r for r in all_refs if r[0] == TIP_REF]
    if len(tip_rows) != 1:
        raise SystemExit("ABORT_TIP_NOT_ANSWERED %d" % len(tip_rows))
    tip = tip_rows[0][1]
    tree = tip_tree(tip)

    review = [(n, s) for n, s in all_refs if n.startswith("refs/heads/review/")]
    heads = sorted({s for _, s in review})
    rc, out, err = git("cat-file", "--batch-check", stdin="\n".join(heads).encode())
    kinds = collections.Counter()
    unreadable = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "commit":
            kinds["commit"] += 1
        else:
            kinds[parts[1] if len(parts) > 1 else "missing"] += 1
            unreadable.append(parts[0])

    rc, out, err = git("rev-list", "--parents", "--stdin", stdin="\n".join(heads).encode())
    parents = {}
    for line in out.splitlines():
        bits = line.split()
        parents[bits[0]] = bits[1:]
    pc = collections.Counter(len(v) for v in parents.values())

    by_head = own_paths(heads)

    rows = []
    tally = collections.Counter()
    for name, sha in sorted(review):
        coords = by_head.get(sha, {})
        if not coords:
            tally["NO_PATHS_REPORTED"] += 1
            rows.append({"ref": name, "head": sha, "paths": 0, "class": "NO_PATHS_REPORTED",
                         "same": 0, "absent": 0, "changed": 0, "product_paths": 0})
            continue
        same = absent = changed = 0
        absent_list, changed_list = [], []
        product = 0
        for path, info in sorted(coords.items()):
            if path.startswith(PRODUCT_PREFIXES) or path.endswith((".py", ".ts", ".tsx", ".json", ".yaml")):
                product += 1
            if info["deleted"]:
                if path in tree:
                    changed += 1
                    changed_list.append({"path": path, "why": "DELETION_UNDONE", "on_line": tree[path]})
                else:
                    same += 1
                continue
            if path not in tree:
                absent += 1
                absent_list.append({"path": path, "expect": info["expect"]})
            elif tree[path] == info["expect"]:
                same += 1
            else:
                changed += 1
                changed_list.append({"path": path, "expect": info["expect"], "on_line": tree[path]})
        cls = "HELD" if (same and not absent and not changed) else (
            "MIXED" if (same and (absent or changed)) else
            ("ALL_ABSENT" if absent and not same and not changed else
             ("ALL_CHANGED" if changed and not same and not absent else "OTHER")))
        tally[cls] += 1
        rows.append({"ref": name, "head": sha, "paths": len(coords), "class": cls,
                     "same": same, "absent": absent, "changed": changed, "product_paths": product,
                     "absent_sample": absent_list[:4], "changed_sample": changed_list[:4],
                     "n_parents": len(parents.get(sha, [])),
                     "head_resolvable": sha not in unreadable})

    prods = [r for r in rows if r["class"] != "NO_PATHS_REPORTED"]
    out_doc = {
        "tool": "fleet_rescan_r1",
        "tip_ref": TIP_REF,
        "tip": tip,
        "tip_tree_paths": len(tree),
        "refs_total_on_origin": len(all_refs),
        "review_refs": len(review),
        "distinct_review_heads": len(heads),
        "head_object_kinds": dict(kinds),
        "heads_unresolvable_locally": len(unreadable),
        "parent_count_distribution": {str(k): v for k, v in sorted(pc.items())},
        "class_tally": dict(tally),
        "refs_with_reported_paths": len(prods),
        "rows": rows,
    }
    doc = json.dumps(out_doc, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "fleet_rescan_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(doc + "\n")

    print("tip=%s tip_tree_paths=%d" % (tip, len(tree)))
    print("refs_total_on_origin=%d review_refs=%d distinct_heads=%d" % (len(all_refs), len(review), len(heads)))
    print("head_object_kinds=%s unresolvable_locally=%d" % (dict(kinds), len(unreadable)))
    print("parent_count_distribution=%s" % dict(sorted(pc.items())))
    print("class_tally=%s" % dict(tally))
    print("refs_with_reported_paths=%d" % len(prods))
    for cls in ("HELD", "MIXED", "ALL_ABSENT", "ALL_CHANGED", "OTHER"):
        sel = [r for r in rows if r["class"] == cls]
        if sel:
            print("--- %s (%d refs, %d paths) ---" % (cls, len(sel), sum(r["paths"] for r in sel)))
            for r in sorted(sel, key=lambda x: -x["paths"])[:6]:
                print("   %-64s head=%s paths=%d same=%d absent=%d changed=%d product=%d parents=%d"
                      % (r["ref"][-64:], r["head"][:10], r["paths"], r["same"], r["absent"],
                         r["changed"], r["product_paths"], r["n_parents"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
