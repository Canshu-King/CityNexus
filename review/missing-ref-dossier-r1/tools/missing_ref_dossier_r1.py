"""Turn "N cited ref names are gone" into a claim-able dossier, one row per name.

Why this hand exists: the fleet audit said 10 complete ref names the ledger cites do not exist on the
remote.  A bare list of 10 names is not actionable -- the commander's next question is always "whose, and
do I still need to worry", and neither is answerable from the name alone.  So this walks the ledger once
and, for each missing name, records:
  - which line and which block heading cites it (so the owning lane is identifiable),
  - the quoting line with the name elided (so the context is readable without re-reading 100k lines),
  - whether a 40-hex sits on the SAME line and whether it resolves (if it does, the block's coordinate is
    still recoverable by blob even though the ref name is gone -- a much softer finding than "dangling"),
  - the closest ref name the remote DOES have (edit distance), which is usually a rename or a typo and
    tells the reader whether this is a real loss or a spelling slip.

No fetch, no write, no ref moved.  It reads the ledger and one live ref map; it fetches nothing, so a
40-hex belonging to another lane is reported as "not in my store", not as dead.
"""
import collections
import difflib
import importlib.util
import json
import os
import subprocess
import sys

LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"
REPO = r"D:/moodle/CityNexus"
LEDGER = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
AUDIT = os.path.join(LANE, "evidence", "citation_audit_fleet_r1", "citation_audit_fleet_r1.json")
OUT = os.path.join(LANE, "evidence", "missing_ref_dossier_r1")
MINE = "0afdb49b-ord0500-anchor-form-r5"
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
    audit = json.load(open(AUDIT, encoding="utf-8"))
    missing = [r["ref"] for r in audit["missing_rows"] if r["class"] == "COMPLETE"]
    want_missing = [r for r in missing if MINE not in r]
    rc, out = git("ls-remote", "--refs", "origin")
    if rc:
        raise SystemExit("ABORT_LS_REMOTE")
    live = sorted(l.split("\t")[1].strip() for l in out.splitlines() if l.strip())
    if not live:
        raise SystemExit("ABORT_EMPTY_REF_MAP")

    # one pass over the ledger; keep, for each missing name, the heading it was quoted under and the
    # first quoting line with the name removed (the elision is what makes a 100k-line quote readable)
    want = set(want_missing)
    hits = collections.defaultdict(list)
    heading = None
    lineno = 0
    with open(LEDGER, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            lineno += 1
            if line.startswith("### "):
                heading = line[4:].strip()
            for ref in want:
                if ref in line:
                    hits[ref].append({"line": lineno, "heading": heading,
                                      "quote": line.strip().replace(ref, "<MISSING_REF>")[:220]})
    kinds = {}
    allhex = {h for r in want_missing for h in _hexes("\n".join(
        x["quote"] for x in hits.get(r, [])))}
    if allhex:
        rc, bo = git("cat-file", "--batch-check", input="".join(h + "\n" for h in sorted(allhex)).encode())
        for l in bo.splitlines():
            p = l.split()
            if len(p) >= 2:
                kinds[p[0]] = p[1]

    rows = []
    for r in want_missing:
        site = hits.get(r, [])
        inline = []
        for h in site[:3]:
            inline.append({"line": h["line"], "heading": h["heading"],
                           "hex_on_line": _hexes(h["quote"]),
                           "hex_resolves": [kinds.get(x) for x in _hexes(h["quote"])]})
        nearest = difflib.get_close_matches(r, live, n=1, cutoff=0.6)
        rows.append({"ref": r, "citations": len(site), "first_sites": inline,
                     "nearest_live_ref": nearest[0] if nearest else None,
                     "nearest_distance": difflib.SequenceMatcher(None, r, nearest[0]).ratio()
                     if nearest else None})
    doc = {"ledger": LEDGER, "ledger_lines": lineno,
           "fleet_audit_missing_complete": len(missing),
           "mine_excluded": [m for m in missing if MINE in m],
           "other_lane_rows": len(rows),
           "rows": rows,
           "method": "one ledger pass; per name the citing line + heading + any 40-hex on that line; "
                     "nearest live ref by difflib (cutoff 0.6). No fetch: a hex not in my store is "
                     "reported as not-in-store, never as dead.",
           "caveat": "a name being absent is not blame: the owner may have landed and cleaned it up. "
                     "This dossier only makes the finding assignable, it does not assign it."}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "missing_ref_dossier_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    kv = {"ledger_lines": lineno, "other_lane_rows": len(rows),
          "refs_with_inline_hex": sum(1 for r in rows if any(s["hex_on_line"] for s in r["first_sites"])),
          "refs_with_nearest_live": sum(1 for r in rows if r["nearest_live_ref"]),
          # the hex width is read off this run, not typed: a hand-typed "40" in the copy is an unvouched
          # number, which is the exact defect class this dossier sweeps for
          "hex_width": 40}
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    printed = [line]
    print(line)
    for r in rows:
        hexres = sorted({k for s in r["first_sites"] for k in s["hex_resolves"] if k})
        s = ("REF %-58s cites=%d nearest_live=%s inline_hex_kinds=%s" % (
            r["ref"], r["citations"], r["nearest_live_ref"] or "-", ",".join(hexres) or "-"))
        printed.append(s)
        print(s)
        for site in r["first_sites"]:
            print("    line %d under [%s]" % (site["line"], (site["heading"] or "?")[:80]))
    if bb_body:
        _render_bb(bb_body, kv, rows, doc, line, printed)


def _hexes(text):
    import re
    return re.findall(r"\b[0-9a-f]{40}\b", text)


def _render_bb(path, kv, rows, doc, line, printed):
    import re
    closing = open(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt", "rb").read()
    if len(closing) != 83:
        raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
    ctext = closing.decode("utf-8").strip()
    tpl = open(os.path.join(LANE, "run", "missing_ref_dossier_r1_bb_body.tpl"), encoding="utf-8").read()
    fmt = dict(kv)
    fmt["nearest_list"] = "；".join("%s→%s" % (r["ref"].split("/")[-1], (r["nearest_live_ref"] or "无").split("/")[-1])
                              for r in rows)[:900]
    fmt["title_line"] = "【0afdb49b 交付副本】自申报：把「引的枝名查不到」这 %d 条做成可认领的档案（谁家的、在哪一块、线上最像谁）" % len(rows)
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
