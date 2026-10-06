#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q38 standing gate, mechanical: every cell of a machine-verified receipt must justify ITSELF.

r2 delta (found on a real artifact, not in the abstract): r1's collector only understood a `cells`
container, sibling cell dicts and a per-cell verdict map.  Lane D's ORD-0292 receipt keeps its cells
in a LIST under a key named `arms` -- r1 read that as NOT_ASSESSABLE, i.e. my尺 blind to a shape lanes
actually ship.  r2 collects lists of per-cell records from ANY key name and pins it with selftest arm
S10.  r1 stays published and frozen as history (blob 35caa42c0697faf0a8eeb0929a3e11cb53c9709a).

Ratified wording (arbiter window answer ①, 2026-09-25 ~07:5x +08; bus stamp pending):
  (a) when a receipt carries >= 2 cells, each cell's verdict/why must be derivable from THAT cell's own readings;
  (b) any two cells whose `why` strings are identical after whitespace folding => RED;
  (c) exemption channel: two cells MAY share one sentence only if each also carries a `derived_from`
      whose tokens hit a reading that is UNIQUE to that cell (otherwise the exemption is fake).

Severity, because (a) read as a hard rule also flags good receipts (measured, not assumed):
  HARD  -> DUPLICATE_WHY_LITERALS, MISSING_WHY, FAKE_OR_INEFFECTIVE_DERIVED_FROM
  SOFT  -> WHY_CARRIES_NO_EVIDENCE_TOKEN, WHY_NOT_FROM_OWN_READINGS
A SOFT-only run never prints a word that contains "GREEN", so it cannot be sold as a pass.

Exit codes: 0 no hard finding; 3 hard finding (or a selftest arm that misbehaved);
            4 fewer assessable cells than --min-cells (NOT a pass); 2 bad input; 5 expectation mismatch.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERDICT_KEYS = ("verdict", "derived", "derived_result", "result", "claimed_result", "status_verdict", "outcome")
WHY_KEYS = ("why", "reason", "because", "rationale", "explanation", "derived_text", "note")
READ_KEYS = ("measured", "readings", "observations", "results", "rows", "arms", "triples", "evidence",
             "draft_evidence", "write_evidence", "isolation", "same_key_precondition", "claim_under_test")
DERIVED_FROM_KEYS = ("derived_from", "derived_from_readings", "evidence_pointers")
CELL_CONTAINER_KEYS = ("cells", "cell_matrix", "matrix", "per_cell")

MIN_WHY_PROSE_LEN = 25
FOLD = re.compile(r"\s+")

TOKEN_PATTERNS = [
    re.compile(r"\b[0-9a-f]{40}\b"),
    re.compile(r"\b[0-9a-f]{7,39}\b"),
    re.compile(r"\bindex-[A-Za-z0-9_-]{6,}(?:\.js)?\b"),
    re.compile(r"\b[A-Za-z0-9_.\-]+\.(?:tsx?|jsx?|json|md|py|css|db)\b"),
    re.compile(r"/api/v1/[\w/{}.\-]+"),
    re.compile(r"\b[1-5]\d{2}\b"),
    re.compile(r"\b\d+\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]{5,}\b"),
    re.compile(r"ORD-\d{4}"),
    re.compile(r"\bR\d+\b"),
]
HARD_CODES = ("DUPLICATE_WHY_LITERALS", "MISSING_WHY", "FAKE_OR_INEFFECTIVE_DERIVED_FROM")


def tokens_of(obj):
    out = []
    if isinstance(obj, str):
        for pat in TOKEN_PATTERNS:
            out.extend(m.group(0) for m in pat.finditer(obj))
    elif isinstance(obj, bool):
        pass
    elif isinstance(obj, (int, float)):
        out.append(str(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(tokens_of(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            out.extend(tokens_of(v))
    return out


def norm(text):
    return FOLD.sub(" ", (text or "").strip()).lower()


def get_by_keys(d, names):
    for n in names:
        if isinstance(d, dict) and n in d:
            return n, d[n]
    return None, None


def is_cell(d):
    return isinstance(d, dict) and get_by_keys(d, VERDICT_KEYS)[0] is not None


def paired_map_entry(doc, cid):
    """A doc-level per-cell verdict map (derived_result_<X>, verdicts, ...) keyed by a cell-id prefix."""
    for key, val in doc.items():
        if not isinstance(val, dict) or key in VERDICT_KEYS:
            continue
        head = cid.split("_")[0].rstrip(".")
        for k2, v2 in val.items():
            if isinstance(v2, str) and (k2 == cid or (head and k2.upper().startswith(head.upper()))):
                return key, k2, v2
    return None, None, None


def analyse(doc, min_cells=2):
    container = None
    for key in CELL_CONTAINER_KEYS:
        if isinstance(doc.get(key), (dict, list)):
            container = doc[key]
            break
    cells = []
    if container is not None:
        items = container.items() if isinstance(container, dict) else list(enumerate(container))
        for cid, body in items:
            if is_cell(body):
                cells.append((str(cid), body))
    if len(cells) < min_cells:
        cells = []
        for key, body in doc.items():
            if key in CELL_CONTAINER_KEYS:
                continue
            # a list of per-cell records under ANY key name (`arms`, `cases`, ...) -- a shape lanes really use
            if isinstance(body, list):
                items = [it for it in body if is_cell(it)]
                if len(items) >= min_cells:
                    for it in items:
                        cid = str(it.get("name") or it.get("arm") or it.get("id") or "")
                        cells.append((cid or "%s[%d]" % (key, body.index(it)), it))
                continue
            if not isinstance(body, dict):
                continue
            paired = paired_map_entry(doc, str(key))
            if not is_cell(body) and paired[2] is None:
                continue          # no verdict of its own and nothing keyed to it in a per-cell map
            has_readings = any(k in body for k in READ_KEYS) or any(
                isinstance(v, (dict, list)) for k, v in body.items() if k not in VERDICT_KEYS and k not in WHY_KEYS)
            if has_readings:
                cells.append((str(key), body))
    if len(cells) < min_cells:
        return {"overall": "NOT_ASSESSABLE", "exit": 4, "cells_found": len(cells), "findings": [], "cells": [],
                "meaning": "fewer than %d assessable cells -- this is NOT a pass and NOT a gate run" % min_cells}

    info, own_tokens = [], {}
    for cid, body in cells:
        vk, vv = get_by_keys(body, VERDICT_KEYS)
        wk, wv = get_by_keys(body, WHY_KEYS)
        src = wk or "absent"
        mk, k2, mv = paired_map_entry(doc, cid)
        if vv is None and mv is not None:
            vk, vv = "%s[%s]" % (mk, k2), mv          # verdict lives only in the per-cell map
        vtext = vv if isinstance(vv, str) else json.dumps(vv, ensure_ascii=False, sort_keys=True)
        prose_in_verdict = False
        if wv is None and isinstance(vv, str) and len(norm(vv)) >= MIN_WHY_PROSE_LEN:
            wv, src, prose_in_verdict = vv, (vk or "verdict") + " (prose)", True
        if wv is None and mv is not None:
            wv, src = mv, "%s[%s]" % (mk, k2)
        readings = {}
        for k, v in body.items():
            if k == vk and prose_in_verdict:
                continue
            if not prose_in_verdict and k in WHY_KEYS and k == wk:
                continue
            readings[k] = v
        own = tokens_of(readings)
        own_tokens[cid] = own
        dfk, dfv = get_by_keys(body, DERIVED_FROM_KEYS)
        info.append({"id": cid, "verdict": vtext, "why": wv if (wv is None or isinstance(wv, str)) else
                     json.dumps(wv, ensure_ascii=False, sort_keys=True),
                     "why_source": src, "derived_from_key": dfk, "derived_from": dfv,
                     "own_token_count": len(own)})

    ids = [c["id"] for c in info]
    uniq = {}
    for cid in ids:
        others = set()
        for other in ids:
            if other != cid:
                others.update(own_tokens[other])
        uniq[cid] = sorted(set(own_tokens[cid]) - others)

    findings = []
    for c in info:
        cid = c["id"]
        own_set = set(own_tokens[cid])
        if c["why"] is None:
            findings.append({"cell": cid, "code": "MISSING_WHY", "hard": True,
                             "detail": "no why field, verdict too short to be prose, no paired map entry"})
            c["why_token_count"] = 0
            c["own_hits"] = []
            c["unique_hits"] = []
            continue
        wt = set(tokens_of(c["why"]))
        hits = sorted(wt & own_set)
        c["why_token_count"] = len(wt)
        c["own_hits"] = hits
        if not wt:
            findings.append({"cell": cid, "code": "WHY_CARRIES_NO_EVIDENCE_TOKEN", "hard": False,
                             "detail": "the sentence names nothing machine-checkable (no hash/number/route/filename)"})
        elif not hits:
            findings.append({"cell": cid, "code": "WHY_NOT_FROM_OWN_READINGS", "hard": False,
                             "detail": "0 of %d tokens in this cell's sentence appear in that cell's own readings" % len(wt)})
        uhits = []
        if c["derived_from"] is not None:
            dft = set(tokens_of(c["derived_from"]))
            uhits = sorted(dft & set(uniq[cid]))
            if not uhits:
                findings.append({"cell": cid, "code": "FAKE_OR_INEFFECTIVE_DERIVED_FROM", "hard": True,
                                 "detail": "derived_from present but names no reading unique to this cell"})
        c["unique_hits"] = uhits

    by_norm = {}
    for c in info:
        if c["why"] is not None:
            by_norm.setdefault(norm(c["why"]), []).append(c["id"])
    for sentence, group in by_norm.items():
        if len(group) < 2:
            continue
        for c in info:
            if c["id"] in group:
                c["shares_why_with"] = [x for x in group if x != c["id"]]
        if all(info[[i["id"] for i in info].index(g)]["unique_hits"] for g in group):
            findings.append({"cells": group, "code": "SHARED_WHY_EXEMPTED_BY_DERIVED_FROM", "hard": False,
                             "blocking": False,
                             "detail": "identical sentence, but each cell names a reading unique to itself"})
        else:
            offenders = [i["id"] for i in info if i["id"] in group and not i["unique_hits"]]
            findings.append({"cells": group, "code": "DUPLICATE_WHY_LITERALS", "hard": True,
                             "detail": "%d cells share one folded-identical sentence; %d of them have no effective derived_from"
                                       % (len(group), len(offenders)),
                             "sentence": sentence[:200]})

    hard = [f for f in findings if f["hard"]]
    soft = [f for f in findings if not f["hard"] and f.get("blocking", True)]
    info_f = [f for f in findings if not f["hard"] and not f.get("blocking", True)]
    if hard:
        overall, exit_code = "Q38_GATE_RED_HARD", 3
    elif soft:
        overall, exit_code = "Q38_GATE_SOFT_FINDINGS", 0
    else:
        overall, exit_code = "Q38_GATE_GREEN", 0
    return {"overall": overall, "exit": exit_code, "cells_found": len(info),
            "hard_count": len(hard), "soft_count": len(soft), "info_count": len(info_f),
            "hard_codes": sorted(set(f["code"] for f in hard)),
            "soft_codes": sorted(set(f["code"] for f in soft)),
            "cells": [{k: v for k, v in c.items()} for c in info],
            "unique_reading_counts": {c: len(uniq[c]) for c in ids},
            "findings": findings,
            "meaning": {"Q38_GATE_GREEN": "no shared literal and every sentence names its own readings",
                        "Q38_GATE_SOFT_FINDINGS": "no hard defect, but some sentences carry nothing machine-checkable",
                        "Q38_GATE_RED_HARD": "at least one cell cannot be read as its own evidence"}[overall]}


def blob_sha(path):
    raw = open(path, "rb").read()
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest(), len(raw)


# ----------------------------------------------------------------------- selftest

def selftest(tmp):
    H1, H2, H3 = "a" * 40, "b" * 40, "c" * 40
    shared = "restored arm MET and not-restored arm RED on the same instrument"
    shared_num = "both arms moved after 4013 ms on the same instrument"
    arms = []

    def cell(installed, why, extra=None, verdict="FIXED"):
        d = {"triples": [{"installed": installed, "atMs": 4013}], "derived_result": verdict, }
        if why is not None:
            d["why"] = why
        if extra:
            d.update(extra)
        return d

    def check(name, doc, want_overall, want_codes=(), min_cells=2):
        p = os.path.join(tmp, name + ".json")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, sort_keys=True, indent=1)
        r = analyse(json.load(open(p, encoding="utf-8")), min_cells=min_cells)
        codes = set(f["code"] for f in r["findings"])
        ok = r["overall"] == want_overall and all(c in codes for c in want_codes)
        arms.append({"arm": name, "got_overall": r["overall"], "got_codes": sorted(codes),
                     "want_overall": want_overall, "want_codes": sorted(want_codes),
                     "cells_found": r["cells_found"], "pass": bool(ok)})

    check("S1_distinct_whys", {"cells": {
        "B2a": cell(H1, "own " + H1 + " converged"),
        "B2b": cell(H2, "own " + H2 + " converged"),
        "B2c": cell(H3, "own " + H3 + " converged")}}, "Q38_GATE_GREEN")

    check("S2_identical_why_three_cells", {"cells": {
        "B2a": cell(H1, shared), "B2b": cell(H2, shared), "B2c": cell(H3, shared)}},
        "Q38_GATE_RED_HARD", ["DUPLICATE_WHY_LITERALS"])

    check("S3_crosspointed_whys", {"cells": {
        "X": cell(H1, "saw " + H2 + " move"), "Y": cell(H2, "saw " + H1 + " move")}},
        "Q38_GATE_SOFT_FINDINGS", ["WHY_NOT_FROM_OWN_READINGS"])

    check("S4_shared_plus_fake_derived_from", {"cells": {
        "X": cell(H1, shared_num, {"derived_from": "the other arm " + H2}),
        "Y": cell(H2, shared_num, {"derived_from": "the other arm " + H1})}},
        "Q38_GATE_RED_HARD", ["DUPLICATE_WHY_LITERALS", "FAKE_OR_INEFFECTIVE_DERIVED_FROM"])

    check("S5_shared_but_each_cites_its_own_unique", {"cells": {
        "X": cell(H1, shared_num, {"derived_from": "own triple " + H1}),
        "Y": cell(H2, shared_num, {"derived_from": "own triple " + H2})}},
        "Q38_GATE_GREEN")

    check("S6_single_cell", {"cells": {"X": cell(H1, "own " + H1)}}, "NOT_ASSESSABLE", min_cells=2)

    check("S7_short_verdict_no_why", {"cells": {
        "X": cell(H1, None), "Y": cell(H2, None)}}, "Q38_GATE_RED_HARD", ["MISSING_WHY"])

    check("S8_sibling_cells_no_container",
          {"R1_leg": {"measured": {"statuses": [200, 200], "rows_delta": "+0"},
                      "derived": "IGNORED CONFIRMED: 200 and +0 rows"},
           "R2_leg": {"measured": {"statuses": [409], "rows_delta": "+1"},
                      "derived": "RECEIPT WRITTEN: 409 and +1 row"}}, "Q38_GATE_GREEN")

    check("S9_paired_map_entry",
          {"R1_leg": {"measured": {"statuses": [200], "missions": "0 -> 7"}},
           "R2_leg": {"measured": {"statuses": [409]}},
           "derived_result_X": {"R1": "CONFIRMED 200 and 0 -> 7", "R2": "CONFIRMED 409"}},
        "Q38_GATE_GREEN")

    # S10 shape (d): per-arm records in a LIST under an arbitrary key name (the ORD-0292 shape)
    check("S10_list_of_arms_under_any_key",
          {"arms": [
              {"name": "K1", "claimed_result": "KILLED", "why": "carrier " + H1 + " anchor hits 1",
               "anchor_hits": 1, "triple": [H1]},
              {"name": "K2", "claimed_result": "KILLED", "why": "carrier " + H2 + " anchor hits 2",
               "anchor_hits": 2, "triple": [H2]}]},
          "Q38_GATE_GREEN")

    bad = [a["arm"] for a in arms if not a["pass"]]
    return {"overall": "SELFTEST_RED" if bad else "SELFTEST_GREEN", "exit": 3 if bad else 0,
            "arms_run": len(arms), "arms_passed": len(arms) - len(bad), "failed_arms": bad, "arms": arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--receipt")
    ap.add_argument("--min-cells", type=int, default=2)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true", help="SOFT findings block too (exit 3)")
    ap.add_argument("--expect", choices=["Q38_GATE_GREEN", "Q38_GATE_SOFT_FINDINGS", "Q38_GATE_RED_HARD",
                                         "NOT_ASSESSABLE"])
    a = ap.parse_args()

    if a.selftest:
        with tempfile.TemporaryDirectory(prefix="q38_selftest_") as tmp:
            res = selftest(tmp)
        print("selftest", res["overall"], "| arms run", res["arms_run"], "passed", res["arms_passed"],
              "| failed:", res["failed_arms"])
        for arm in res["arms"]:
            print("  arm", arm["arm"], "cells", arm["cells_found"], "got", arm["got_overall"], arm["got_codes"],
                  "| want", arm["want_overall"], arm["want_codes"], "->", "ok" if arm["pass"] else "MISBEHAVED")
        return res["exit"]

    if not a.receipt:
        print("need --receipt or --selftest")
        return 2
    if not os.path.exists(a.receipt):
        print("NO_SUCH_RECEIPT", a.receipt)
        return 2
    sha, size = blob_sha(a.receipt)
    doc = json.load(open(a.receipt, encoding="utf-8"))
    res = analyse(doc, min_cells=a.min_cells)
    res["receipt"] = {"path": a.receipt.replace("\\", "/"), "blob_sha1": sha, "bytes": size}
    print("receipt", os.path.basename(a.receipt), size, "B", "blob_sha1", sha)
    print("cells", res["cells_found"], "| overall", res["overall"],
          "| hard", res.get("hard_count"), res.get("hard_codes"), "| soft", res.get("soft_count"), res.get("soft_codes"))
    for c in res.get("cells", []):
        print("  cell", c["id"], "| why_source", c["why_source"], "| why tokens", c.get("why_token_count"),
              "| own hits", len(c.get("own_hits", [])), "| unique hits", len(c.get("unique_hits", [])),
              "| shares why with", c.get("shares_why_with", []))
    for f in res["findings"]:
        print("  finding", f["code"], "HARD" if f["hard"] else "soft", f.get("cell") or f.get("cells"),
              "|", f["detail"][:170])
    print("meaning:", res["meaning"])
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, sort_keys=True, indent=1)
        print("wrote", a.out, os.path.getsize(a.out), "B")
    rc = res["exit"]
    if a.strict and res["overall"] == "Q38_GATE_SOFT_FINDINGS":
        rc = 3
        print("strict: SOFT findings treated as blocking")
    if a.expect:
        if res["overall"] != a.expect:
            print("EXPECTATION_MISMATCH want", a.expect, "got", res["overall"])
            return 5
        print("expectation held:", a.expect)
    return rc


if __name__ == "__main__":
    sys.exit(main())
