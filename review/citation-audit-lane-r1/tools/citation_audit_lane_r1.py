"""Audit the coordinates MY OWN delivered blocks cite, against what the remote answers right now.

Why this exists: on 2026-10-06 I published three blocks citing
`refs/heads/review/0afdb49b-ord0500-anchor-form-r5`, a name that does not exist (the branch belongs to
another lane's namespace).  One wrong coordinate proved the class is worth sweeping, and the sweep is
cheap because everything it needs is either in the blocks themselves or one `ls-remote` away.

Three checks, each with its own honest reading:
  1. every `refs/heads/...` my blocks cite  -> EXISTS / MISSING against the live ref map
  2. where a block quotes a 40-hex on the SAME LINE as that ref -> does it still match the live head?
     (a moved head is not an error by itself on this line, but a block that pinned a head should be
     read with the pin in hand)
  3. every distinct 40-hex my blocks cite   -> does `git cat-file -t` still answer, and with what kind?

No fetch, no write, no ref moved.  A ref that is gone is reported as gone, not as "someone deleted my
work": branches get landed and cleaned up by their owners, and this tool cannot tell those apart -- it
says what the remote says.
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
INBOX = r"D:\moodle\_qoder_ledger_inbox"
OUT = os.path.join(LANE, "evidence", "citation_audit_lane_r1")
# A ref must be a real two-segment path, and must end in a name.  The loose version read the glob
# literal `refs/heads/review/*` as a ref (first `refs/heads/review/`, then `refs/heads/review`) and
# reported it missing -- two findings about my own ruler and zero about the remote.
REF_RE = re.compile(r"refs/heads/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*")
HEX_RE = re.compile(r"\b[0-9a-f]{40}\b")
ENV = {k: v for k, v in os.environ.items() if k.upper() not in ("HTTP_PROXY", "HTTPS_PROXY")}
ENV["NO_PROXY"] = "*"


def git(*args):
    p = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, timeout=600, env=ENV)
    return p.returncode, p.stdout.decode("utf-8", "replace")


def blocks():
    """Every block this lane delivered (applied or still queued), by path."""
    out = []
    for d in (os.path.join(INBOX, "_processed"), INBOX):
        for f in sorted(os.listdir(d)):
            if f.startswith("0afdb49b_") and ".md" in f:
                out.append(os.path.join(d, f))
    return out


def main():
    bb_body = None
    argv = sys.argv[1:]
    while argv:
        if argv[0] == "--write-body":
            bb_body = argv[1]; argv = argv[2:]
        else:
            raise SystemExit("ABORT_UNKNOWN_ARG " + argv[0])
    rc, out = git("ls-remote", "--refs", "origin")
    if rc:
        raise SystemExit("ABORT_LS_REMOTE")
    live = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        sha, name = line.split("\t")
        live[name] = sha
    if not live:
        raise SystemExit("ABORT_EMPTY_REF_MAP")

    ref_hits = collections.Counter()
    hex_hits = collections.Counter()
    ref_heads = {}          # ref -> {quoted_hex: count}
    per_file = {}
    for path in blocks():
        text = open(path, encoding="utf-8", errors="replace").read()
        refs = REF_RE.findall(text)
        hexes = HEX_RE.findall(text)
        for r in refs:
            ref_hits[r] += 1
        for h in hexes:
            hex_hits[h] += 1
        for line in text.splitlines():
            lrefs = REF_RE.findall(line)
            lhexes = HEX_RE.findall(line)
            if not lrefs or not lhexes:
                continue
            for r in lrefs:
                ref_heads.setdefault(r, collections.Counter())
                for h in lhexes:
                    ref_heads[r][h] += 1
        per_file[os.path.basename(path)] = {"refs": len(refs), "hexes": len(hexes)}

    ref_rows = []
    for r in sorted(ref_hits):
        now = live.get(r)
        quoted = ref_heads.get(r, {})
        if now is None:
            status = "MISSING"
            matches = []
        else:
            status = "EXISTS"
            matches = sorted({("MATCH" if h == now else "MOVED") for h in quoted}) if quoted else []
        ref_rows.append({"ref": r, "citations": ref_hits[r], "status": status,
                         "live_head": now, "quoted_heads": sorted(quoted),
                         "head_verdicts": matches})
    hex_rows = []
    for h in sorted(hex_hits):
        rc, kind = git("cat-file", "-t", h)
        hex_rows.append({"hex": h, "citations": hex_hits[h],
                         "kind": kind.strip() if rc == 0 else None,
                         "resolvable": rc == 0})
    missing_refs = [r["ref"] for r in ref_rows if r["status"] == "MISSING"]
    unresolvable = [h["hex"] for h in hex_rows if not h["resolvable"]]
    moved = [r["ref"] for r in ref_rows if "MOVED" in r["head_verdicts"]]
    doc = {"blocks_scanned": len(per_file), "per_file": per_file,
           "distinct_refs": len(ref_rows), "distinct_hexes": len(hex_rows),
           "missing_refs": missing_refs, "unresolvable_hexes": unresolvable,
           "refs_with_moved_head": moved,
           "ref_rows": ref_rows, "hex_rows": hex_rows,
           "method": "refs from the blocks, existence and head from one live ls-remote --refs; "
                     "hexes via git cat-file -t; no fetch, no write, no ref moved",
           "caveat": "a MISSING ref may simply have been landed and cleaned up by its owner -- this "
                     "tool reports what the remote answers, it does not assign blame"}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "citation_audit_lane_r1.json"), "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    kv = {"blocks_scanned": len(per_file), "distinct_refs": len(ref_rows),
          "distinct_hexes": len(hex_rows), "missing_refs": len(missing_refs),
          "unresolvable_hexes": len(unresolvable), "refs_with_moved_head": len(moved),
          "live_refs_on_remote": len(live)}
    line = " ".join("%s=%s" % (k, kv[k]) for k in sorted(kv))
    printed = [line]
    print(line)
    for r in ref_rows:
        s = "REF %-60s citations=%d %s head=%s verdicts=%s" % (
            r["ref"], r["citations"], r["status"], (r["live_head"] or "-")[:12],
            ",".join(r["head_verdicts"]) or "-")
        printed.append(s)
        print(s)
    for h in hex_rows:
        if not h["resolvable"]:
            s = "HEX %s citations=%d UNRESOLVABLE" % (h["hex"], h["citations"])
            printed.append(s)
            print(s)
    kv["all_moved_refs"] = sum(1 for r in ref_rows if r["head_verdicts"] == ["MOVED"])
    kv["missing_ref_list"] = ";".join(missing_refs) if missing_refs else "none"
    kv["live_refs_on_remote"] = len(live)
    kv["ref_line"] = line
    if bb_body:
        closing = open(r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt", "rb").read()
        if len(closing) != 83:
            raise SystemExit("ABORT_CLOSING_LINE_SIZE %d" % len(closing))
        ctext = closing.decode("utf-8").strip()
        tpl = open(os.path.join(LANE, "run", "citation_audit_lane_r1_bb_body.tpl"),
                   encoding="utf-8").read()
        spec = importlib.util.spec_from_file_location("cnx_bus_client", r"D:/moodle/agent_bus/bus.py")
        busm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(busm)
        rendered = tpl.format(**kv).rstrip() + "\n\n" + ctext + "\n"
        if rendered.count(ctext) != 1:
            raise SystemExit("ABORT_CLOSING_LINE_DUPLICATED")
        if os.path.exists(bb_body):
            cur = open(bb_body, encoding="utf-8").read()
            if cur != rendered:
                raise SystemExit("ABORT_WOULD_CHANGE_THE_POST -- re-render in one pass")
        hay = "\n".join(printed).replace(",", "")
        claimed = sorted(set(busm.numeric_claims(rendered)))
        missing = [t for t in claimed if t not in hay]
        if missing:
            raise SystemExit("ABORT_BB_NOT_VOUCHED %s (%d of %d)" % (
                ",".join(missing[:12]), len(missing), len(claimed)))
        open(bb_body, "w", encoding="utf-8", newline="\n").write(rendered)
        print("BB BODY WRITTEN %s | VOUCHED %d number tokens" % (bb_body, len(claimed)))


if __name__ == "__main__":
    main()
