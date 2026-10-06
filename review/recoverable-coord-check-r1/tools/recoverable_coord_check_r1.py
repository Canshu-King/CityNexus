"""Check whether the recoverable coordinates from the missing-ref dossier really point at the same work.

The dossier said 4 of the 9 stale ref names had a resolvable 40-hex on the same line, and I reported
that as "the coordinate is still recoverable".  That was only half a proof: a resolvable commit is a
different thing from "this commit is the branch the stale name referred to".  Same name, different object
is the failure mode that matters, so this closes it with two independent readings per row:

  ANCESTOR_OF_NEAREST -- the cited commit is an ancestor of the nearest live ref's head, i.e. the block
    pinned an earlier generation of the very branch it names.  This is ancestry used as EVIDENCE about
    which object a coordinate denotes, which is a different question from the standing ruling that
    ancestry is not a criterion for whether work landed.
  TOUCHES_TOPIC_PATH  -- the cited commit's own change set contains a path under the topic prefix the
    stale name carries, which is byte-level evidence of the same association.

Anything else prints as UNRELATED.  If a row comes back UNRELATED the previous hand's "still
recoverable" is wrong for that row, and the block says so.
"""
import importlib.util
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
DOSSIER = os.path.join(LANE, "evidence", "missing_ref_dossier_r1", "missing_ref_dossier_r1.json")
OUT = os.path.join(LANE, "evidence", "recoverable_coord_check_r1")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args, **kw):
    stdin = kw.pop("input", None)
    p = subprocess.run(["git", "-C", REPO] + list(args), input=stdin, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=900, env=ENV, **kw)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def main():
    bb_body = None
    argv = sys.argv[1:]
    while argv:
        if argv[0] == "--write-body":
            bb_body = argv[1]; argv = argv[2:]
        else:
            raise SystemExit("ABORT_UNKNOWN_ARG " + argv[0])
    dossier = json.load(open(DOSSIER, encoding="utf-8"))
    rows = [r for r in dossier["rows"] if any(s["hex_on_line"] for s in r["first_sites"])]
    rc, out = git("ls-remote", "--refs", "origin")
    if rc:
        raise SystemExit("ABORT_LS_REMOTE")
    live = {}
    for l in out.splitlines():
        if l.strip():
            sha, name = l.split("\t")
            live[name] = sha

    results = []
    for r in rows:
        near = r["nearest_live_ref"]
        near_head = live.get(near)
        for s in r["first_sites"]:
            if not s["hex_on_line"]:
                continue
            for h in s["hex_on_line"]:
                rc, _k = git("cat-file", "-t", h)
                if rc:
                    results.append({"ref": r["ref"], "hex": h, "verdict": "NOT_RESOLVABLE",
                                    "nearest": near})
                    continue
                anc = False
                if near_head:
                    rc, bo = git("merge-base", "--is-ancestor", h, near_head)
                    anc = (rc == 0)
                rc, own = git("diff-tree", "-r", "--name-only", "--no-commit-id", h)
                paths = [p for p in own.splitlines() if p.strip()]
                # the topic token is whatever the stale name carries between the lane id and the trailing
                # generation marker; matching it against the commit's own paths is byte-level evidence
                topic = near.split("/")[-1].rsplit("-", 1)[0] if near else ""
                topic_hit = [p for p in paths if topic and topic in p]
                verdict = "UNRELATED"
                if anc:
                    verdict = "ANCESTOR_OF_NEAREST"
                elif topic_hit:
                    verdict = "TOUCHES_TOPIC_PATH"
                results.append({"ref": r["ref"], "hex": h, "verdict": verdict,
                                "ancestor_of_nearest": anc, "nearest": near,
                                "nearest_head": near_head, "own_paths": len(paths),
                                "topic": topic, "topic_hits": topic_hit[:3]})
    tally = {}
    for x in results:
        tally[x["verdict"]] = tally.get(x["verdict"], 0) + 1
    confirmed = sum(1 for x in results if x["verdict"] != "UNRELATED")
    doc = {"rows_checked": len(rows), "commits_checked": len(results),
           "verdict_tally": tally, "confirmed_same_work": confirmed,
           "unrelated": [x["hex"] for x in results if x["verdict"] == "UNRELATED"],
           "results": results,
           "method": "per same-line 40-hex: is it an ancestor of the nearest live ref's head (ancestry "
                     "used as evidence of which object a coordinate names), and does its own change set "
                     "touch that branch's topic path. UNRELATED otherwise.",
           "note": "ancestry here identifies WHICH object a coordinate points at; it is not used as a "
                   "landed/lost criterion, which on this line is blob equality only"}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "recoverable_coord_check_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    kv = {"rows_checked": len(rows), "commits_checked": len(results),
          "confirmed_same_work": confirmed, "unrelated": tally.get("UNRELATED", 0),
          "ancestor_confirmed": tally.get("ANCESTOR_OF_NEAREST", 0),
          "topic_confirmed": tally.get("TOUCHES_TOPIC_PATH", 0),
          "hex_width": 40}
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    printed = [line]
    print(line)
    for x in results:
        s = "HEX %s ref=%s verdict=%s nearest=%s own_paths=%d" % (
            x["hex"][:12], x["ref"].split("/")[-1], x["verdict"],
            (x.get("nearest") or "-").split("/")[-1], x.get("own_paths", 0))
        printed.append(s)
        print(s)
    if bb_body:
        _render_bb(bb_body, kv, results, line, printed)


def _render_bb(path, kv, results, line, printed):
    closing = open(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt", "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    ctext = closing.decode("utf-8").strip()
    tpl = open(os.path.join(LANE, "run", "recoverable_coord_check_r1_bb_body.tpl"),
               encoding="utf-8").read()
    fmt = dict(kv)
    fmt["title_line"] = ("【0afdb49b 交付副本】接着上一格往下钉：上一格说「坐标还取得到」，这一格验那 {rows_checked} 条的可取坐标**是不是同一件事**——{confirmed_same_work} 条确认同一件、{unrelated} 条不相干").format(**kv)
    spec = importlib.util.spec_from_file_location("cnx_bus_client", r"D:/moodle/agent_bus/bus.py")
    busm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(busm)
    rendered = tpl.format(**fmt).rstrip() + "\n\n" + ctext + "\n"
    if rendered.count(ctext) != 1:
        raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED")
    if os.path.exists(path):
        if open(path, encoding="utf-8").read() != rendered:
            raise SystemExit("ABORT_WOULD_CHANGE_THE_POST -- re-render in one pass")
    hay = "\n".join(printed).replace(",", "")
    claimed = sorted(set(busm.numeric_claims(rendered)))
    bad = [t for t in claimed if t not in hay]
    if bad:
        raise SystemExit("ABORT_BB_NOT_VOUCHED %s (%d of %d)" % (",".join(bad[:12]), len(bad), len(claimed)))
    open(path, "w", encoding="utf-8", newline="\n").write(rendered)
    print("BB BODY WRITTEN %s | VOUCHED %d number tokens" % (path, len(claimed)))


if __name__ == "__main__":
    main()
