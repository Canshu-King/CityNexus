"""ORD-0500 lane -- landing status of THIS lane's review refs, re-judged at the live tip.

Why a lane-scoped reading instead of another fleet pass: the fleet re-scan (r2) judged all 1081 review
refs at tip aac1142e, and the tip has moved twice since.  Re-running the whole fleet costs minutes and
its answer goes stale in the same way; what this lane actually needs to know is narrower -- which of its
OWN branches' bytes are on the line right now -- and that question is cheap enough to re-ask on demand.

Method is not re-derived: the per-hand path sets come from the published r2 tool's own published_paths()
(imported, so the two readings cannot drift apart), and landed-ness is byte equality against the live
tip tree, per the standing ruling that ancestry is not a criterion on this line.
"""
import collections
import importlib.util
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
REFSPEC = "refs/heads/review/0afdb49b-*"
OUT = os.path.join(LANE, "evidence", "lane_landing_status_r1")
SNAPSHOT_FRACTION = float(os.environ.get("SNAP_FRACTION", "0.5"))
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


def main():
    bb_body = None
    argv = sys.argv[1:]
    while argv:
        if argv[0] == "--write-body":
            bb_body = argv[1]; argv = argv[2:]
        else:
            raise SystemExit("ABORT_UNKNOWN_ARG " + argv[0])
    r2 = _r2()
    rc, out, err = git("ls-remote", "--refs", "origin", TIP_REF)
    if rc or not out.strip():
        raise SystemExit("ABORT_NO_LIVE_TIP " + err[:160])
    tip = out.split()[0]
    rows = r2.lsremote(REFSPEC)
    if not rows:
        raise SystemExit("ABORT_NO_LANE_REFS")
    tree = r2.tip_tree(tip)
    by_ref = collections.defaultdict(list)
    for name, sha in rows:
        by_ref[name].append(sha)
    heads = sorted({sha for _n, sha in rows})
    by_head = r2.published_paths(heads)
    quiet = [h for h in heads if h not in by_head]
    quiet_class = {}
    for h in quiet:
        rc, pars, _e = git("rev-list", "--parents", "--no-walk", h)
        rc, cur, _e = git("rev-parse", "%s^{tree}" % h)
        parents = pars.split()[1:]
        same = True
        for p in parents:
            rc, pt, _e = git("rev-parse", "%s^{tree}" % p)
            if pt.strip() != cur.strip():
                same = False
        quiet_class[h] = "EMPTY_COMMIT" if (parents and same) else "NO_PATHS_REPORTED"

    per_ref = []
    for name in sorted(by_ref):
        for head in sorted(set(by_ref[name])):
            own = by_head.get(head, {})
            if head in quiet_class:
                per_ref.append({"ref": name, "head": head, "own_paths": 0, "same": 0, "absent": 0,
                                "changed": 0, "deletion_held": 0, "deletion_undone": 0,
                                "label": quiet_class[head]})
                continue
            same = absent = changed = dheld = dundone = 0
            for path, spec in own.items():
                if spec.get("deleted"):
                    if path not in tree:
                        dheld += 1
                    else:
                        dundone += 1
                    continue
                if path not in tree:
                    absent += 1
                elif tree[path] == spec["expect"]:
                    same += 1
                else:
                    changed += 1
            n = len(own)
            if n and n >= SNAPSHOT_FRACTION * len(tree):
                label = "SNAPSHOT_SHAPED"
            elif same == n and n:
                label = "ALL_SAME"
            elif same == 0:
                label = "NONE_ON_LINE"
            else:
                label = "PARTIAL_SAME"
            per_ref.append({"ref": name, "head": head, "own_paths": n, "same": same,
                            "absent": absent, "changed": changed, "deletion_held": dheld,
                            "deletion_undone": dundone, "label": label})
    tally = collections.Counter(r["label"] for r in per_ref)
    doc = {"tip": tip, "tip_tree_paths": len(tree), "refspec": REFSPEC,
           "lane_refs": len(per_ref), "distinct_heads": len(heads),
           "quiet_heads": len(quiet), "per_ref": per_ref, "label_tally": dict(tally),
           "method": "own path set from the published r2 tool's published_paths(); landed-ness is "
                     "byte equality against the live tip tree; ancestry is not a criterion",
           "reads_nothing_else": "no fetch, no write, no ref moved"}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "lane_landing_status_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    tot = collections.Counter()
    for r in per_ref:
        for k in ("same", "absent", "changed", "deletion_held", "deletion_undone"):
            tot[k] += r[k]
    kv = {"tip": tip, "tip_tree_paths": len(tree), "lane_refs": len(per_ref),
          "distinct_heads": len(heads), "quiet_heads": len(quiet),
          "all_same": tally.get("ALL_SAME", 0), "partial_same": tally.get("PARTIAL_SAME", 0),
          "none_on_line": tally.get("NONE_ON_LINE", 0),
          "snapshot_shaped": tally.get("SNAPSHOT_SHAPED", 0),
          "empty_commit": tally.get("EMPTY_COMMIT", 0),
          "no_paths_reported": tally.get("NO_PATHS_REPORTED", 0),
          "paths_same": tot["same"], "paths_absent": tot["absent"], "paths_changed": tot["changed"],
          "deletion_held": tot["deletion_held"], "deletion_undone": tot["deletion_undone"],
          "own_paths_total": sum(r["own_paths"] for r in per_ref)}
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    out_lines = [line]
    for r in per_ref:
        out_lines.append("%-62s %s own=%d same=%d absent=%d changed=%d del_held=%d del_undone=%d %s" % (
            r["ref"], r["head"][:12], r["own_paths"], r["same"], r["absent"], r["changed"],
            r["deletion_held"], r["deletion_undone"], r["label"]))
    print("\n".join(out_lines))
    # the hub captures this command's whole stdout, so the voucher's haystack is the whole output --
    # keeping it to the kv line alone would refuse numbers this run demonstrably printed
    hay = "\n".join(out_lines).replace(",", "")
    if bb_body:
        closing = open(os.path.join(LANE, "..", "_qoder_cmdr_ref_20260921", "live_checks",
                                    "CLOSING_LINE.txt"), "rb").read()
        if len(closing) != 83:
            raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
        ctext = closing.decode("utf-8").strip()
        tpl = open(os.path.join(LANE, "run", "lane_status_r1_bb_body.tpl"), encoding="utf-8").read()
        fmt = dict(kv)
        fmt["all_same_names"] = "、".join(r["ref"].split("0afdb49b-", 1)[-1]
                                          for r in per_ref if r["label"] == "ALL_SAME")
        fmt["partial_names"] = "、".join(r["ref"].split("0afdb49b-", 1)[-1]
                                         for r in per_ref if r["label"] == "PARTIAL_SAME")
        rendered = tpl.format(**fmt).rstrip() + "\n\n" + ctext + "\n"
        if rendered.count(ctext) != 1:
            raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED %d" % rendered.count(ctext))
        if os.path.exists(bb_body):
            cur = open(bb_body, encoding="utf-8").read()
            if cur != rendered:
                raise SystemExit("ABORT_WOULD_CHANGE_THE_POST -- the body on disk is not what this "
                                 "kv map renders; post nothing and re-render in one pass")
        spec = importlib.util.spec_from_file_location("cnx_bus_client", r"D:/moodle/agent_bus/bus.py")
        busm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(busm)
        claimed = sorted(set(busm.numeric_claims(rendered)))
        missing = [t for t in claimed if t not in hay]
        if missing:
            raise SystemExit("ABORT_BB_NOT_VOUCHED %s (%d of %d) -- the hub would refuse this post" % (
                ",".join(missing[:12]), len(missing), len(claimed)))
        open(bb_body, "w", encoding="utf-8", newline="\n").write(rendered)
        print("BB BODY WRITTEN %s | VOUCHED %d number tokens" % (bb_body, len(claimed)))


if __name__ == "__main__":
    main()
