"""evidence_provenance_sweep.py - how much published evidence touches a file that changed between two generations.

Why: the arbiter Q24 rule makes every cross-generation citation decidable per cell, but nobody knows the
SIZE of the backlog.  This sweeps `evidence/**` on `commander/control`, and for each receipt records whether
it names the files that changed between the two generations and which commit shas it pins.  Output is a
count plus a named list - a denominator, not an impression.

Read-only.  Bounded by --max so a sweep cannot pretend to be exhaustive while silently timing out; when the
cap bites, the receipt says `coverage: NOT EXHAUSTIVE`.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request

TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
API = "https://api.github.com"
REPO = "Canshu-King/CityNexus"
REF = "commander/control"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "receipts",
                   "evidence_provenance_sweep.json")

SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
MAIN_PY = re.compile(r"app/main\.py|backend/app/main")


def _get(path):
    tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
    req = urllib.request.Request(API + path, headers={
        "Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-provenance-sweep", "X-GitHub-Api-Version": "2022-11-28"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))


def tree_of(ref):
    """The commit's tree sha, then the recursive entry list (one call, proved non-truncated or flagged).

    Note the route: `/commits/{ref}` returns a LIST of commits, not a commit object - asking for the tip
    means `/commits?sha=<ref>&per_page=1`.  (Measured: the first version of this file crashed on exactly
    that with KeyError 'tree'.)
    """
    page = _get("/repos/%s/commits?sha=%s&per_page=1" % (REPO, ref))
    c = page[0] if isinstance(page, list) and page else page
    sha = c["sha"]
    t = _get("/repos/%s/git/trees/%s?recursive=1" % (REPO, c["commit"]["tree"]["sha"]))
    return sha, [e for e in (t.get("tree") or []) if e.get("type") == "blob"], bool(t.get("truncated"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    max_files = int(os.environ.get("CNX_SWEEP_MAX", "120"))
    tip, blobs, truncated = tree_of(REF)
    ev = sorted(e["path"] for e in blobs if e["path"].startswith("evidence/") and e["path"].endswith(".json"))
    # r2: the first version only wrote at the very end, so a wall-clock kill during a 681-file sweep left
    # NOTHING behind.  The receipt is now flushed every `flush_every` files, and a re-run resumes from the
    # paths already scanned against the same ref tip - a killed sweep still yields a real denominator.
    touched, failures = [], []
    scanned = []
    if os.path.exists(OUT):
        try:
            prev = json.load(io.open(OUT, encoding="utf-8"))
            if prev.get("ref_tip_read") == tip:
                scanned = list(prev.get("scanned_paths") or [])
                touched = list(prev.get("list") or [])
        except Exception:
            pass
    done = set(scanned)
    todo = [x for x in ev if x not in done]
    flush_every = 25

    def flush():
        doc = {
            "schema": "CNX_EVIDENCE_PROVENANCE_SWEEP_V2",
            "ref": REF, "ref_tip_read": tip, "tree_truncated": truncated,
            "evidence_json_total": len(ev), "scanned": len(scanned), "cap": max_files,
            "coverage": "EXHAUSTIVE" if len(scanned) == len(ev) and not truncated else "NOT EXHAUSTIVE",
            "read_failures": len(failures), "failures_sample": failures[:5],
            "cite_main_py": len(touched), "scanned_paths": sorted(scanned), "list": touched,
            "meaning": "each listed receipt names backend/app/main.py, whose blob differs between "
                       "c79e2b4f and dcae1bc96 - those are the receipts a cross-generation quote must re-derive",
        }
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("progress %d/%d cite_main_py=%d coverage=%s"
              % (len(scanned), len(ev), len(touched), doc["coverage"]), flush=True)

    for p in todo:
        try:
            meta = _get("/repos/%s/contents/%s?ref=%s" % (REPO, p, REF))
            body = meta.get("content") or ""
            import base64
            raw = base64.b64decode(body.replace("\n", "")).decode("utf-8", "replace") if body else ""
            if not raw and meta.get("sha"):
                b = _get("/repos/%s/git/blobs/%s" % (REPO, meta["sha"]))
                import base64 as b64
                raw = b64.b64decode(b.get("content", "").replace("\n", "")).decode("utf-8", "replace")
        except Exception as exc:
            failures.append({"path": p, "error": type(exc).__name__})
            continue
        scanned.append(p)
        hit_main = bool(MAIN_PY.search(raw))
        shas = sorted(set(SHA40.findall(raw)))
        if hit_main:
            touched.append({"path": p, "cited_40hex": shas[:8], "n_shas": len(shas)})
        if len(scanned) % flush_every == 0:
            flush()
    flush()

    print("ref tip %s  evidence json=%d  scanned=%d  coverage=%s  cite main.py=%d  read_failures=%d"
          % (tip[:9], len(ev), len(scanned), doc["coverage"], len(touched), len(failures)))
    for t in touched[:20]:
        print("  %-72s shas=%d" % (t["path"][-72:], t["n_shas"]))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
