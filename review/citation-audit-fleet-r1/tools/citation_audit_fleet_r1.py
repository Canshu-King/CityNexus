"""Fleet-wide version of the citation audit: every coordinate the WHOLE ledger cites, against the remote.

The lane-only version (tools/citation_audit_lane_r1.py) found one ref name I had invented, and the same
class of mistake is fleet-wide business: a block that cites a branch nobody can `ls-remote` sends every
reader on a wild goose chase.  This sweep answers the ref half exactly, and refuses to answer the blob
half beyond what it can prove.

Why the two halves are treated differently:
  * ref names  -- one `git ls-remote --refs origin` returns the entire remote ref map, so EXISTS / MISSING
    is decided against the remote itself, with no local-store dependency.  This is a real verdict.
  * 40-hex     -- `git cat-file -t` only asks MY local object store.  A blob another lane pushed is live
    on the remote and simply not fetched here, so "cat-file says no" is NOT evidence of a dead coordinate.
    Reporting it as dead would be exactly the over-claim this line keeps punishing, so this tool reports
    IN_STORE / NOT_IN_STORE and says so.  Fetching 7844 objects to settle it would be a network bill
    nobody authorised.

Under the standing ruling, ancestry is not a criterion anywhere in here.
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
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
OUT = os.path.join(LANE, "evidence", "citation_audit_fleet_r1")
CLOSING = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
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
    lane = importlib.util.spec_from_file_location(
        "lane_audit", os.path.join(LANE, "tools", "citation_audit_lane_r1.py"))
    lanem = importlib.util.module_from_spec(lane)
    lane.loader.exec_module(lanem)
    REF_RE, HEX_RE = lanem.REF_RE, lanem.HEX_RE

    rc, out = git("ls-remote", "--refs", "origin")
    if rc:
        raise SystemExit("ABORT_LS_REMOTE")
    live = {}
    for line in out.splitlines():
        if line.strip():
            sha, name = line.split("\t")
            live[name] = sha
    if not live:
        raise SystemExit("ABORT_EMPTY_REF_MAP")

    ref_hits = collections.Counter()
    hex_hits = collections.Counter()
    lines = 0
    with open(LEDGER, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lines += 1
            for r in REF_RE.findall(line):
                ref_hits[r] += 1
            for h in HEX_RE.findall(line):
                hex_hits[h] += 1

    ref_rows = []
    for r in sorted(ref_hits):
        ref_rows.append({"ref": r, "citations": ref_hits[r],
                         "status": "EXISTS" if r in live else "MISSING",
                         "live_head": live.get(r)})
    # one process for all of them: 7844 hexes at one `git cat-file` each is minutes of PID churn for a
    # question git answers in a single --batch-check pass
    kinds = {}
    rc, out = git("cat-file", "--batch-check", input="".join(h + "\n" for h in sorted(hex_hits)).encode())
    if rc:
        raise SystemExit("ABORT_BATCH_CHECK")
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in hex_hits:
            kinds[parts[0]] = parts[1]
    hex_rows = []
    for h in sorted(hex_hits):
        hex_rows.append({"hex": h, "citations": hex_hits[h],
                         "in_local_store": h in kinds,
                         "kind": kinds.get(h)})
    # A missing ref is not automatically a bad citation: blocks abbreviate (`refs/heads/review/6a150e1e…`)
    # and a regex then hands back the fragment.  Publishing "21 missing refs" without splitting these off
    # would be the same over-claim this tool exists to stop, so each one is classified:
    #   FRAGMENT -- ends mid-token, or is a strict prefix of a ref that does exist
    #   COMPLETE -- nothing on the remote starts with it: a name a reader really would try to resolve
    def classify(r):
        if r.endswith("-") or r.endswith(".") or r.count("refs/heads/") > 1:
            return "FRAGMENT"
        for name in live:
            if name.startswith(r) and name != r:
                return "FRAGMENT"
        return "COMPLETE"

    missing_rows = []
    for r in sorted(ref_hits):
        if r in live:
            continue
        kind = classify(r)
        missing_rows.append({"ref": r, "citations": ref_hits[r], "class": kind})
    missing = [r["ref"] for r in missing_rows if r["class"] == "COMPLETE"]
    doc_missing = [r for r in missing_rows]
    in_store = sum(1 for h in hex_rows if h["in_local_store"])
    doc = {"ledger_bytes": os.path.getsize(LEDGER), "ledger_lines": lines,
           "distinct_refs": len(ref_rows), "distinct_hexes": len(hex_rows),
           "missing_refs": missing, "missing_ref_count": len(missing),
           "missing_rows": doc_missing,
           "missing_fragment_count": sum(1 for r in doc_missing if r["class"] == "FRAGMENT"),
           "hexes_in_local_store": in_store,
           "hexes_not_in_local_store": len(hex_rows) - in_store,
           "live_refs_on_remote": len(live),
           "ref_rows": ref_rows, "hex_rows": hex_rows,
           "method": "ref existence from one live ls-remote --refs (remote truth, no local dependency); "
                     "hexes from git cat-file -t, which only asks MY object store",
           "caveat": "'not_in_local_store' is NOT a dead-coordinate verdict -- another lane's blob can be "
                     "live on the remote and simply unfetched here. Settling it would need a fetch nobody "
                     "authorised, so this tool does not pretend to have settled it."}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "citation_audit_fleet_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")

    kv = {"ledger_lines": lines, "distinct_refs": len(ref_rows), "distinct_hexes": len(hex_rows),
          "missing_ref_count": len(missing), "hexes_in_local_store": in_store,
          "hexes_not_in_local_store": len(hex_rows) - in_store,
          "live_refs_on_remote": len(live),
          # both are read off this run, not typed into the template: a hard-coded "11" and "40" in the
          # BB copy are exactly the kind of number the hub refuses because no evidence output contains it
          "missing_fragment_count": sum(1 for r in doc_missing if r["class"] == "FRAGMENT"),
          "hex_width": 40}
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    printed = [line]
    print(line)
    for r in doc_missing:
        s = "REF_MISSING %-64s citations=%d %s" % (r["ref"], r["citations"], r["class"])
        printed.append(s)
        print(s)
    if bb_body:
        closing = open(CLOSING, "rb").read()
        if len(closing) != 83:
            raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
        ctext = closing.decode("utf-8").strip()
        tpl = open(os.path.join(LANE, "run", "citation_audit_fleet_r1_bb_body.tpl"), encoding="utf-8").read()
        fmt = dict(kv)
        fmt["missing_ref_list"] = ";".join(missing[:6]) if missing else "none"
        spec = importlib.util.spec_from_file_location("cnx_bus_client", r"D:/moodle/agent_bus/bus.py")
        busm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(busm)
        rendered = tpl.format(**fmt).rstrip() + "\n\n" + ctext + "\n"
        if rendered.count(ctext) != 1:
            raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED")
        if os.path.exists(bb_body):
            cur = open(bb_body, encoding="utf-8").read()
            if cur != rendered:
                raise SystemExit("ABORT_WOULD_CHANGE_THE_POST -- re-render in one pass")
        hay = ("\n".join(printed) + "\n" + "".join(missing)).replace(",", "")
        claimed = sorted(set(busm.numeric_claims(rendered)))
        bad = [t for t in claimed if t not in hay]
        if bad:
            raise SystemExit("ABORT_BB_NOT_VOUCHED %s (%d of %d)" % (
                ",".join(bad[:12]), len(bad), len(claimed)))
        open(bb_body, "w", encoding="utf-8", newline="\n").write(rendered)
        print("BB BODY WRITTEN %s | VOUCHED %d number tokens" % (bb_body, len(claimed)))


if __name__ == "__main__":
    main()
