#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q43=① standing gate, mechanical: a forwarded number must carry its coordinate.

Ratified text (arbiter stamp `5824811888`, 2026-09-25 08:5x +08):
  "anyone -- the commander especially -- who forwards a numeric value must attach `file:line` or a
   blob/commit coordinate; without one the only allowed sentence is 'I need a field reading',
   never 'it says / somewhere it says'."

Why this exists: my own 07:1x ledger block wrote `它说：现草案 DEFAULT_WRITE_DEADLINE_MS = 10000` and
dispatched a lane to reconcile a number that no artifact ever carried (measured: 6 occurrences in the
ledger, 3 of them mine; 32 blobs in that lane's evidence, the only `= 10000` lines quoting my sentence).

Families it judges (scope is printed, this is NOT "every number in prose"):
  F1 named-constant value claim   `[A-Z][A-Z0-9_]{4,} = <digits>`
  F2 relay sentence               contains one of RELAY_WORDS
Both are satisfied by a COORDINATE within WINDOW chars: `path.ext:123`, a 40-hex, `blob <hex7-40>`,
`issuecomment-<digits>`, `refs/heads/...`, or a commit sha cited as such.

Exit codes: 0 no finding; 3 finding(s); 4 no claim found in this input (NOT_APPLICABLE -- not a pass);
2 bad input; 5 expectation mismatch.
"""

import argparse
import json
import os
import re
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RELAY_WORDS = ("它说", "他说", "她说", "某处", "车道报", "lane says", "reports that", "per the lane",
               "据车道", "随件给了", "as reported")
CONSTANT_CLAIM = re.compile(r"\b[A-Z][A-Z0-9_]{4,}\s*=\s*[\d][\d_]*\b")
COORD_PATTERNS = [
    re.compile(r"[\w./\\-]+\.(?:py|ts|tsx|js|md|json|yaml|yml|c|css|html):\d+"),
    re.compile(r"\b[0-9a-f]{40}\b"),
    re.compile(r"\bblob[^\n]{0,12}[0-9a-f]{7,40}\b", re.IGNORECASE),
    re.compile(r"issuecomment-\d+"),
    re.compile(r"refs/heads/[\w./-]+"),
    re.compile(r"CITYNEXUS_AGENT_CONTROL\.md:\d+"),
]
WINDOW = 200
STRUCTURAL = re.compile(r"^(ORD-\d+|Q\d+|R\d+|S\d+|A\d+|B\d+|C\d+|D\d+|K\d+|T-\w+|P\d+)$")


def has_coordinate(text, pos):
    lo = max(0, pos - WINDOW)
    hi = min(len(text), pos + WINDOW)
    window = text[lo:hi]
    for pat in COORD_PATTERNS:
        m = pat.search(window)
        if m:
            return True, m.group(0)[:60]
    return False, None


def scan(text):
    findings = []
    claims = 0
    for m in CONSTANT_CLAIM.finditer(text):
        claims += 1
        ok, coord = has_coordinate(text, m.start())
        if not ok:
            findings.append({"kind": "F1_constant_value_claim", "matched": m.group(0)[:60],
                             "code": "CONSTANT_VALUE_CLAIM_WITHOUT_COORDINATE",
                             "line": text.count("\n", 0, m.start()) + 1})
    for w in RELAY_WORDS:
        start = 0
        while True:
            i = text.find(w, start)
            if i < 0:
                break
            start = i + len(w)
            claims += 1
            ok, coord = has_coordinate(text, i)
            if not ok:
                findings.append({"kind": "F2_relay_sentence", "matched": w,
                                 "code": "NO_COORDINATE_FOR_RELAY",
                                 "line": text.count("\n", 0, i) + 1})
    overall = ("NO_CLAIM_FOUND_NOT_APPLICABLE" if claims == 0
               else ("Q43_GATE_RED" if findings else "Q43_GATE_CLEAN"))
    return {"overall": overall,
            "exit": 4 if claims == 0 else (3 if findings else 0),
            "claims_checked": claims, "finding_count": len(findings),
            "findings": findings,
            "scope": "F1 named-constant `NAME = digits` and F2 relay wording only; "
                     "structural ids (ORD-####, Q#, cell names) and timestamps are not claims",
            "window_chars": WINDOW,
            "meaning": {"NO_CLAIM_FOUND_NOT_APPLICABLE": "this instrument found no claim to judge -- NOT a pass",
                        "Q43_GATE_RED": "a number is asserted or relayed with nothing to check it against",
                        "Q43_GATE_CLEAN": "every claim in this text names a coordinate within %d chars" % WINDOW}[overall]}


def selftest(tmp):
    arms = []
    HEX = "d" * 40

    def check(name, text, want_overall, want_codes=()):
        p = os.path.join(tmp, name + ".txt")
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        r = scan(open(p, encoding="utf-8").read())
        codes = sorted(set(x["code"] for x in r["findings"]))
        ok = r["overall"] == want_overall and all(c in codes for c in want_codes)
        arms.append({"arm": name, "got": r["overall"], "got_codes": codes, "want": want_overall,
                     "want_codes": sorted(want_codes), "claims_checked": r["claims_checked"],
                     "pass": bool(ok)})

    check("S1_relay_with_coordinate",
          "它说：`app/main.py:4774` 有那枚谓词", "Q43_GATE_CLEAN")
    check("S2_relay_without_coordinate",
          "它说：现草案那个期限比超时短，所以永不触发。", "Q43_GATE_RED", ["NO_COORDINATE_FOR_RELAY"])
    check("S3_constant_with_40hex",
          "DEFAULT_WRITE_DEADLINE_MS = 10000 见 %s 那件收据" % HEX, "Q43_GATE_CLEAN")
    check("S4_constant_without_coordinate",
          "DEFAULT_WRITE_DEADLINE_MS = 10000", "Q43_GATE_RED",
          ["CONSTANT_VALUE_CLAIM_WITHOUT_COORDINATE"])
    check("S5_no_claims_at_all",
          "ORD-0288 的形状已验收；07:49 量过手机；Q36=① 那条门不受影响。", "NO_CLAIM_FOUND_NOT_APPLICABLE")
    check("S6_coordinate_too_far",
          "见 " + HEX + "。\n" + ("填充行\n" * 80) + "它说：那个期限小于超时。", "Q43_GATE_RED",
          ["NO_COORDINATE_FOR_RELAY"])
    check("S7_structural_numbers_are_not_claims",
          "evidence/x/receipt.json 里 blob 1d60e42d235e1cb48d9c350274cd1dab92759a6e 是 2100 B，"
          "申报 12 件真落 10 件；ORD-0292 有 7 枚臂。", "Q43_GATE_CLEAN")
    bad = [a["arm"] for a in arms if not a["pass"]]
    return {"overall": "SELFTEST_RED" if bad else "SELFTEST_GREEN", "exit": 3 if bad else 0,
            "arms_run": len(arms), "arms_passed": len(arms) - len(bad), "failed_arms": bad, "arms": arms}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", help="file to judge (a ledger block, a bus post, a receipt body)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--expect", choices=["Q43_GATE_CLEAN", "Q43_GATE_RED", "NO_CLAIM_FOUND_NOT_APPLICABLE"])
    a = ap.parse_args()

    if a.selftest:
        with tempfile.TemporaryDirectory(prefix="q43_selftest_") as tmp:
            res = selftest(tmp)
        print("selftest", res["overall"], "| arms run", res["arms_run"], "passed", res["arms_passed"],
              "| failed:", res["failed_arms"])
        for arm in res["arms"]:
            print("  arm", arm["arm"], "claims", arm["claims_checked"], "got", arm["got"], arm["got_codes"],
                  "| want", arm["want"], arm["want_codes"], "->", "ok" if arm["pass"] else "MISBEHAVED")
        return res["exit"]

    if not a.text:
        print("need --text or --selftest")
        return 2
    if not os.path.exists(a.text):
        print("NO_SUCH_FILE", a.text)
        return 2
    body = open(a.text, encoding="utf-8", errors="replace").read()
    res = scan(body)
    res["input"] = {"path": os.path.basename(a.text), "bytes": len(body.encode("utf-8")),
                    "lines": body.count("\n") + 1}
    print("input", res["input"]["path"], res["input"]["bytes"], "B", res["input"]["lines"], "lines")
    print("claims checked", res["claims_checked"], "| overall", res["overall"], "| findings", res["finding_count"])
    for f in res["findings"]:
        print("  line", f["line"], f["kind"], f["code"], "|", f["matched"][:70])
    print("scope:", res["scope"])
    print("meaning:", res["meaning"])
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, sort_keys=True, indent=1)
        print("wrote", a.out, os.path.getsize(a.out), "B")
    if a.expect:
        if res["overall"] != a.expect:
            print("EXPECTATION_MISMATCH want", a.expect, "got", res["overall"])
            return 5
        print("expectation held:", a.expect)
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())
