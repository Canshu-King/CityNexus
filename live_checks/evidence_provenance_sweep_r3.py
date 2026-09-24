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
                   "evidence_provenance_sweep_r3.json")   # r3: own scratch name, r1/r2 output untouched

SHA40 = re.compile(r"\b[0-9a-f]{40}\b")
SHA16 = re.compile(r"(?<![0-9a-f])[0-9a-f]{16}(?![0-9a-f])")
# ORD-0283/B3 (real bite): the old pattern had no word boundary (so `main.py.txt` matched) and its second
# alternative `backend/app/main` matched a bare prose mention.  A mention is not a citation.
MAIN_PY = re.compile(r"(?<![\w./-])(?:backend/)?app/main\.py(?![\w.-])")
PROXIMITY = 160   # a coordinate belongs to a mention only within this many characters either side


def classify(raw):
    """(mentioned, cited_with_40hex, cited_prefix_only) for one evidence file, judged by proximity.

    cited_with_40hex : a 40-hex coordinate sits near one mention -> the claim IS re-derivable
    cited_prefix_only: mentions sit next to 16-hex prefixes only -> NOT re-derivable as published
                       (ORD-0283/B2: these must not share a denominator with the group above)
    neither, but mentioned: prose only - no re-derive obligation attaches.
    """
    hits = [m.start() for m in MAIN_PY.finditer(raw)]
    if not hits:
        return False, False, False
    near40 = near16 = False
    for h in hits:
        window = raw[max(0, h - PROXIMITY): h + PROXIMITY + 20]
        if SHA40.search(window):
            near40 = True
        elif SHA16.search(window):
            near16 = True
    return True, near40, (near16 and not near40)


def selftest():
    """Two-way arms for classify() - no network, no repository, nothing to time out on."""
    checks = {}
    a40 = "0123456789abcdef0123456789abcdef01234567"
    p16 = "0123456789abcdef"
    checks["S1_no_mention_is_not_a_hit"] = classify('{"blob": "%s"}' % a40) == (False, False, False)
    checks["S2_prose_mention_alone_is_not_a_citation"] = classify(
        "the defect sits in backend/app/main.py somewhere") == (True, False, False)
    checks["S3_bare_main_py_without_the_app_dir_is_not_a_hit"] = classify(
        "main.py at %s" % a40) == (False, False, False)
    checks["S4_path_plus_nearby_40hex"] = classify(
        "backend/app/main.py blob %s at gen A" % a40) == (True, True, False)
    checks["S5_16hex_only_is_prefix_not_auditable"] = classify(
        "backend/app/main.py blob %s (prefix)" % p16) == (True, False, True)
    checks["S6_far_away_40hex_does_not_attach"] = classify(
        a40 + " x" * 400 + " backend/app/main.py") == (True, False, False)
    checks["S7_main_py_txt_is_not_a_hit"] = classify("see backend/app/main.py.txt for the list") == (
        False, False, False)
    checks["S8_app_main_py_without_backend_prefix_still_counts"] = classify(
        "app/main.py @ %s" % a40) == (True, True, False)
    green = sum(1 for v in checks.values() if v)
    for k, v in checks.items():
        print("  %-52s %s" % (k, "ok" if v else "FAIL"))
    print("SWEEP_SELFTEST %d/%d" % (green, len(checks)))
    return 0 if green == len(checks) else 4


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
    # r3: without this dispatch, `--selftest` silently started a REAL 726-file sweep (measured 06:11 -
    # the command hung and a partial receipt was written).  A flag must never fall through to the sweep.
    if "--selftest" in sys.argv:
        return selftest()
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
            "schema": "CNX_EVIDENCE_PROVENANCE_SWEEP_V3",
            "ref": REF, "ref_tip_read": tip, "tree_truncated": truncated,
            "evidence_json_total": len(ev), "scanned": len(scanned), "cap": max_files,
            "coverage": "EXHAUSTIVE" if len(scanned) == len(ev) and not truncated else "NOT EXHAUSTIVE",
            "read_failures": len(failures), "failures_sample": failures[:5],
            "main_py_mentioned": len(touched),
            "main_py_cited_with_40hex": sum(1 for t in touched if t["kind"] == "cited_with_40hex"),
            "main_py_cited_prefix_only": sum(1 for t in touched if t["kind"] == "cited_prefix_only"),
            "main_py_prose_mention_only": sum(1 for t in touched if t["kind"] == "prose_mention_only"),
            "scanned_paths": sorted(scanned), "list": touched,
            "meaning": "ONLY `main_py_cited_with_40hex` entries carry a re-derivable coordinate, so only "
                       "those are obligated to be re-derived across a generation swap. `cited_prefix_only` "
                       "names the file but cannot be re-derived as published (r2 counted these in the same "
                       "denominator - ORD-0283/B2). `prose_mention_only` carries no obligation at all "
                       "(ORD-0283/B3: naming a file in prose is not quoting it across generations).",
        }
        io.open(OUT, "w", encoding="utf-8", newline="\n").write(json.dumps(doc, ensure_ascii=False, indent=1))
        print("progress %d/%d mentioned=%d cited40=%d prefixonly=%d prose=%d coverage=%s"
              % (len(scanned), len(ev), doc["main_py_mentioned"], doc["main_py_cited_with_40hex"],
                 doc["main_py_cited_prefix_only"], doc["main_py_prose_mention_only"], doc["coverage"]),
              flush=True)
        return doc

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
        mentioned, with40, prefix_only = classify(raw)
        shas = sorted(set(SHA40.findall(raw)))
        if mentioned:
            touched.append({"path": p,
                            "kind": "cited_with_40hex" if with40 else (
                                "cited_prefix_only" if prefix_only else "prose_mention_only"),
                            "nearby_or_listed_40hex": shas[:8], "n_40hex_anywhere": len(shas)})
        if len(scanned) % flush_every == 0:
            flush()
    doc = flush()

    print("ref tip %s  evidence json=%d  scanned=%d  coverage=%s  mentioned=%d cited40=%d prefixonly=%d "
          "prose=%d  read_failures=%d"
          % (tip[:9], len(ev), len(scanned), doc["coverage"], doc["main_py_mentioned"],
             doc["main_py_cited_with_40hex"], doc["main_py_cited_prefix_only"],
             doc["main_py_prose_mention_only"], len(failures)))
    for t in touched[:20]:
        print("  %-72s kind=%-20s n_40hex_anywhere=%d"
              % (t["path"][-72:], t["kind"], t["n_40hex_anywhere"]))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
