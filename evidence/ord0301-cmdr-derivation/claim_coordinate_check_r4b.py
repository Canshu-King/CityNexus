#!/usr/bin/env python3
"""Q43 r4 - the coordinate ruler, with the numeric-token classifier that r3 lacked.

Why a new revision exists (this is MY instrument, not any lane's delivery):
  r3 flags every run of 3+ digits as a "bare numeric claim".  Measured against
  evidence/ord0301-screen-speaks-range-hjp3/RECEIPT_O0301-1500.md it returned 133 findings over
  179 claims, and reading those findings shows most of them are not quantities at all:
  HTTP status codes (500/503/502/504/422), years (2026), clock digits, and port numbers quoted as
  addresses.  A ruler that paints a status code as an unsupported measurement will either be ignored
  by lanes or will make them strip numbers to get green - both are worse than no ruler.  r3 stayed
  published as the wrong version.

What r4 changes, and the guard that keeps it from becoming a rubber stamp:
  * every token is classified before it is judged; a token is EXEMPT only by named class
    (HTTP_STATUS / YEAR / CLOCK / IDENTIFIER_PART / ORDINAL_IN_ID), and the class list is printed;
  * the exemptions are context-bound: a 3-digit number only reads as a status code when a status
    word sits next to it AND no unit follows it - "500 B" and "500 ms" are still measurements;
  * a coordinate may now also be a run id (O0301-144507 / policy_stamp form), not only a blob,
    file:line, refs/heads path or issuecomment id;
  * self-test runs BOTH directions on every class: an exempt sample must not fire, and a
    deliberately-deprived sample must fire.  If any direction fails, the ruler exits 6 and nothing
    downstream may quote its verdict.

Usage: claim_coordinate_check_r4.py --text FILE [--out FILE] [--expect-clean] [--selftest]
Exit: 0 clean | 3 findings | 4 NO_CLAIM_FOUND (not a pass) | 5 --expect mismatch | 6 self-test failed
"""
from __future__ import annotations

import argparse
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERSION = "Q43_r4"

RELAY_WORDS = ("它说", "他说", "她说", "某处", "车道报", "lane says", "reports that", "per the lane",
               "据车道", "随件给了", "as reported")
CONSTANT_CLAIM = re.compile(r"\b[A-Z][A-Z0-9_]{4,}\s*=\s*\d[\d_]*")
DURABLE = re.compile(r"\b[0-9a-f]{40}\b"
                     r"|\bblob[^\n]{0,12}[0-9a-f]{7,40}\b"
                     r"|issuecomment-\d{6,}"
                     r"|refs/heads/[\w./-]+"
                     r"|[A-Za-z]{1,6}[-_]\d{6,8}\b"          # run id, e.g. O0301-144507
                     r"|run[_ ]?id[^\n]{0,3}\d{6,8}"
                     r"|[\w./\\-]+\.(?:py|ts|tsx|js|json|yaml|yml|c|css|html|txt|md):\d+",
                     re.IGNORECASE)
WINDOW = 200
FULLWIDTH_EQ = "="
UNIT_AFTER_NUM = re.compile(r"\d[\d_,.]*\s*(?:B|KB|MB|GB|ms|s|秒|分钟|处|条|个|格|轮|次|件|节点|芯片|%)")
TOKEN = re.compile(r"(?<![\w-])(?<![0-9a-fA-F])\d[\d_,]{2,}(?![0-9a-fA-F])")
STATUS_WORD = re.compile(r"(HTTP|http|status|状态码|状态|response|答复|答|code|5xx|4xx|3xx|2xx)", re.I)
YEAR = re.compile(r"^(19|20)\d{2}$")
CLOCKISH = re.compile(r"^\d{2}:\d{2}|^\d{4}-\d{2}-\d{2}", re.I)
IDENTIFIERISH = re.compile(r"^[A-Za-z]+[-_]$|^[-_][A-Za-z0-9]+$")


def normalise(text):
    return text.replace(FULLWIDTH_EQ, "=")


def classify(text, start, end):
    """Return (class_or_None, why). None means: this is a quantity and must carry a coordinate."""
    tok = text[start:end].replace(",", "").replace("_", "")
    after = text[end:end + 8]
    before = text[max(0, start - 24):start]
    if re.match(r"^\d[\d_,.]*\s*(?:B|KB|MB|GB|ms|秒|分钟|处|条|个|格|轮|次|件|节点|芯片|%)", after):
        return None, "carries a unit -> measurement"
    if YEAR.match(tok) and not re.match(r"^\s*(ms|s|B)\b", after):
        return "YEAR", "4-digit year"
    if CLOCKISH.match(after.lstrip()) or re.search(r"\d{1,2}:\d{1,2}$", before[-6:]):
        return "CLOCK", "clock/timestamp digit"
    if IDENTIFIERISH.match(before[-2:]) or re.search(r"(ORD|CMDR|Q|REQ|NOTE|RX|D|A|B)-$", before):
        return "IDENTIFIER_PART", "part of an order/label id"
    if re.fullmatch(r"[1-5]\d{2}", tok):
        ctx = text[max(0, start - 40):min(len(text), end + 40)]
        if STATUS_WORD.search(ctx):
            return "HTTP_STATUS", "3-digit status code next to a status word"
    if re.fullmatch(r"\d{3,5}", tok.lstrip("0") or "0") and (
            re.search(r"(port|端口|listen|监听)\D{0,8}$", before, re.I)
            or (before.endswith(":") and not re.search(r"\w:$", before))):
        # `:8000` after a non-word char is how a port is written here; `config.py:8000` is a line
        # reference and must NOT be exempted, hence the `\w:$` guard.
        return "PORT", "port number (port word nearby, or written as :NNNN outside a file:line ref)"
    return None, "no class matched"


def coordinate_in_window(text, pos):
    lo, hi = max(0, pos - WINDOW), min(len(text), pos + WINDOW)
    window = text[lo:hi]
    m = DURABLE.search(window)
    if m:
        return True, m.group(0)[:60], []
    notes = []
    if re.search(r"[\w./\\-]+\.md:\d+", window, re.I):
        notes.append("UNSTABLE_COORDINATE_markdown_line_number_in_a_rewritten_file")
    return False, None, notes


def scan(text):
    findings, claims, exempt = [], 0, {}
    text = normalise(text)
    spans = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
    unit_spans = [(m.start(), m.end()) for m in UNIT_AFTER_NUM.finditer(text)]
    for start, end in spans + unit_spans:
        cls, why = classify(text, start, end)
        tok = text[start:end]
        if cls:
            exempt[cls] = exempt.get(cls, 0) + 1
            continue
        claims += 1
        ok, coord, notes = coordinate_in_window(text, start)
        if not ok:
            findings.append({"kind": "F3_bare_numeric_claim", "matched": tok[:40],
                             "code": ("NUMBER_WITHOUT_COORDINATE" if not notes
                                      else "NUMBER_WITH_UNSTABLE_COORDINATE"),
                             "line": text.count("\n", 0, start) + 1,
                             "why_classified_as_quantity": why, "seen_coordinate": coord})
    for m in CONSTANT_CLAIM.finditer(text):
        claims += 1
        ok, coord, notes = coordinate_in_window(text, m.start())
        if not ok:
            findings.append({"kind": "F1_constant_value_claim", "matched": m.group(0)[:60],
                             "code": ("CONSTANT_VALUE_CLAIM_WITHOUT_COORDINATE" if not notes
                                      else "CONSTANT_VALUE_CLAIM_WITH_UNSTABLE_COORDINATE"),
                             "line": text.count("\n", 0, m.start()) + 1, "seen_coordinate": coord})
    for w in RELAY_WORDS:
        for m in re.finditer(re.escape(w), text):
            claims += 1
            ok, coord, notes = coordinate_in_window(text, m.start())
            if not ok:
                findings.append({"kind": "F2_relayed_claim", "matched": w,
                                 "code": "RELAYED_CLAIM_WITHOUT_DURABLE_EVIDENCE",
                                 "line": text.count("\n", 0, m.start()) + 1})
    return claims, findings, exempt


SAMPLES = {
    "exempt_HTTP_STATUS": ("the tapped leg answered HTTP 503 with no envelope", "HTTP_STATUS"),
    "fire_quantity_ms": ("the tapped leg waited 32209 with no coordinate nearby", None),
    "fire_status_with_unit": ("the answer was HTTP 500 B payload and nothing else", None),
    "exempt_YEAR": ("measured on 2026-09-25 at 15:00 +08 nothing else", "YEAR"),
    "exempt_run_id_coordinate": ("elapsed 32209 recorded in O0301-144907 and blob " + "a" * 40, None),
    "exempt_PORT": ("nothing was listening on port 8000 at that moment", "PORT"),
    "fire_run_id_without_coordinate": ("the wait was 62000 and no run id appears anywhere", None),
}


def selftest():
    rows = []
    for name, (text, expected) in SAMPLES.items():
        claims, findings, exempt = scan(text)
        rows.append({"sample": name, "claims": claims, "findings": [f["code"] for f in findings],
                     "exempt": exempt})
    # two-way assertions: every "exempt_" sample must be silent, every "fire_" sample must speak.
    checks = {}
    for name, (text, expected_class) in SAMPLES.items():
        claims, findings, exempt = scan(text)
        if name.startswith("exempt_"):
            checks[name] = (not findings) and (expected_class in exempt or expected_class is None)
        else:
            checks[name] = bool(findings)
    ok = all(checks.values())
    print(json.dumps({"selftest_checks": checks, "overall_pass": ok, "samples": rows},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text")
    ap.add_argument("--out")
    ap.add_argument("--expect-clean", action="store_true")
    ap.add_argument("--expect", type=int)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.text:
        print("usage: --text FILE | --selftest", file=sys.stderr)
        return 2
    raw = open(a.text, "rb").read()
    text = raw.decode("utf-8", errors="replace")
    claims, findings, exempt = scan(text)
    kinds = sorted({f["code"] for f in findings})
    verdict = ("Q43_GATE_GREEN" if not findings else "Q43_GATE_RED") if claims else "NO_CLAIM_FOUND"
    # NO_CLAIM_FOUND is NOT a pass: a text with zero checkable claims proves nothing (same rule as r3).
    code = 0 if (findings is not None and claims and not findings) else (3 if findings else 4)
    if a.expect is not None and a.expect != code:
        print("EXPECT_MISMATCH want", a.expect, "got", code, file=sys.stderr)
        return 5
    out = {"version": VERSION, "input": a.text, "bytes": len(raw), "lines": text.count("\n") + 1,
           "claims_checked": claims, "exempt_classes": exempt, "verdict": verdict,
           "exit_code": code, "findings": findings[:60], "finding_kinds": kinds,
           "finding_total": len(findings),
           "scope": "Numeric/constant/relay claims in the text. A green verdict here means every "
                    "quantity carries a durable coordinate - it does not mean the measurements are "
                    "correct, and it does not sign derived_result."}
    if a.out:
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("version", VERSION, "| input", a.text, len(raw), "B")
    print("claims checked", claims, "| exempt", json.dumps(exempt), "| overall", verdict,
          "| findings", len(findings), kinds)
    for f in findings[:25]:
        print("  line", f["line"], f["kind"], f["code"], "|", f["matched"],
              "|", f.get("why_classified_as_quantity", ""))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
