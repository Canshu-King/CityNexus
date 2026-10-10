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

What r4d adds, and the price it pays for it (commander ruling Q74, 2026-09-26 07:54):
  Two more named classes, both conditional on the block having cited at least one STRONG coordinate
  somewhere (a 40-hex blob, an issuecomment id, a refs/heads path, a run id).  Without such a
  citation nothing is exempt, so a block cannot launder its numbers by adding units.
    DIMENSION      - a number followed by a physical dimension unit (px/rem/em/vw/vh/dpi, ms/us/s,
                     B/KB/MB/GB/字节, 秒/分钟/小时/天, %, ℃).  The coordinate of a reading is the
                     artifact that recorded it, not a second number inside the sentence.  r4c made
                     lane D's ORD-0338 block refuse on `212`, `229`, `2 秒` - three render measurements
                     whose receipt IS named in the same block.
    DISCIPLINE_ZERO - the digit `0` followed by a count word, and only when a discipline noun
                     (权威线 / 产品字节 / demo/reset / vite build / 凭据 / push / ref / skip / 覆盖 /
                     删除 / 改写 / 移动) sits in front of it.  These state what this lane did NOT do;
                     their witness is the ref log and the diff, not a neighbouring blob.
  Deliberately NOT exempt: any non-zero count, and `0` in front of a product noun (命中 / 格 / 节点 /
  条 / 个) - "the interface returned 0 times" and "0 cells hit" are product facts and must be checkable.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

VERSION = "Q43_r4e"

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

# ---- r4d: two context-bound exemptions, both paid for with a receipt the block already cites ----
# A physical dimension: what the instrument measured. Its coordinate is the artifact holding the run.
DIM_UNITS = {"px", "rem", "em", "vw", "vh", "dpi", "ms", "us", "ns", "s", "b", "kb", "mb", "gb",
             "字节", "秒", "分钟", "小时", "天", "%", "℃", "度"}
# Words that COUNT product facts. `0` in front of one of these is still a claim, receipt or not.
COUNT_WORDS = ("次", "处", "条", "笔", "个", "格", "轮", "移动", "命中", "节点", "件", "芯片")
# Only these nouns make a zero an absence-of-action declaration rather than a product reading.
DISCIPLINE_NOUNS = ("权威线", "产品字节", "demo/reset", "vite build", "凭据", "push", "ref",
                    "skip", "覆盖", "删除", "改写", "重写", "回滚")
# `path:line` is deliberately NOT here: it is not retrievable after a rewrite, which is why r4's
# advisories() already treats a quantity vouched only by a source line number as thin coverage.
BLOB40 = re.compile(r"[0-9a-f]" "{40}")
STRONG_RECEIPT = re.compile(r"\b[0-9a-f]{40}\b|issuecomment-\d{6,}|refs/heads/[\w./-]+|"
                            r"[A-Za-z]{1,6}[-_]\d{6,8}\b")


def unit_of(text, start, end):
    """The dimension unit attached to a number, whether it sits inside the matched span (`212px`,
    `2 秒`) or just after it. Returns the lowercased unit, or None when the tail is not a dimension."""
    for cand in (re.search(r"(\d[\d_,]*)\s*([^\d\s]+)", text[start:end]),
                 re.match(r"\s*([^\d\s,;。，；、\)\]」』\"]+)", text[end:end + 6])):
        if not cand:
            continue
        u = cand.group(cand.lastindex).strip().rstrip("）)】」』\"'")
        if u.lower() in DIM_UNITS:
            return u.lower()
    return None


def normalise(text):
    return text.replace(FULLWIDTH_EQ, "=")


def classify(text, start, end, has_receipt=False):
    """Return (class_or_None, why). None means: this is a quantity and must carry a coordinate."""
    tok = text[start:end].replace(",", "").replace("_", "")
    after = text[end:end + 8]
    before = text[max(0, start - 24):start]
    # r4d (1/2).  `212px` is a reading, not a claim about a quantity of things: its coordinate is the
    # artifact that recorded the run.  Conditional on the block citing a RETRIEVABLE receipt, because
    # units are trivial to add and a receipt is not.
    unit = unit_of(text, start, end)
    if unit and has_receipt:
        return "DIMENSION", "physical reading with unit %r, block cites a retrievable receipt" % unit
    # r4d (2/2).  `权威线 0 次移动` states what this lane did NOT do; the witness is the ref log and the
    # diff, and no blob can sit beside every zero.  A non-zero, or a zero in front of a product noun
    # (`该格命中 0 次`), stays a claim -- that is the distinction this arm is built to keep.
    if has_receipt and re.match(r"^0\s*(%s)" % "|".join(COUNT_WORDS), tok):
        hit = [n for n in DISCIPLINE_NOUNS if n in before]
        if hit:
            return "DISCIPLINE_ZERO", "absence declared in front of %r" % hit[0]
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
    # Line-number lists are how lanes cite prose: "`PlanWithAiSheet.tsx:414`、`:474`、`:538`". r4b called every
    # `:NNN` after a non-word char a PORT, so a 6-item line list turned 5 claims into invisible exemptions and
    # the coverage number lied (lane D e345b9d6 reported this on 09-26 01:22 and I reproduced it). Same verdict
    # either way - both classes are exempt - but the buckets must be honest, otherwise "exempt: PORT 9" hides
    # "these were line refs".
    if re.fullmatch(r"\d{3,5}", tok.lstrip("0") or "0"):
        ctx_before = text[max(0, start - 48):start]
        if before.endswith(":") and re.search(r"[\w./\-]+\.(?:py|ts|tsx|js|json|yaml|yml|md|css|html|txt):\d+",
                                               ctx_before, re.I):
            return "LINE_REF", "line number continuing a file:line reference list"
        if (re.search(r"(port|端口|listen|监听)\D{0,8}$", before, re.I)
                or (before.endswith(":") and not re.search(r"\w:$", before))):
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


SOURCE_LINE_REF = re.compile(r"[\w./\\-]+\.(?:py|ts|tsx|js|json|yaml|yml|css|html|txt):\d+", re.I)
STRONG_COORD = re.compile(r"\b[0-9a-f]{40}\b|issuecomment-\d{6,}|refs/heads/[\w./-]+|"
                          r"[A-Za-z]{1,6}[-_]\d{6,8}\b")


def advisories(text):
    """Not refusals - visibility. `path:line` has always been an acceptable coordinate here, which is right for
    citing prose. But when the only thing vouching for a unit-quantity in the block is a source line number,
    the coverage behind "claims checked" is thinner than it reads, so the run says so out loud and the verdict
    stays untouched (no lane block gets retroactively red for this)."""
    text = normalise(text)
    out = []
    for m in UNIT_AFTER_NUM.finditer(text):
        lo, hi = max(0, m.start() - WINDOW), min(len(text), m.start() + WINDOW)
        win = text[lo:hi]
        if DURABLE.search(win) and not STRONG_COORD.search(win) and SOURCE_LINE_REF.search(win):
            out.append({"matched": m.group(0)[:24], "line": text.count("\n", 0, m.start()) + 1,
                        "code": "QUANTITY_VOUCHED_ONLY_BY_A_SOURCE_LINE_NUMBER"})
    return out


def scan(text):
    findings, claims, exempt = [], 0, {}
    text = normalise(text)
    # Block-level fact: r4d's two new classes are only ever paid for by a receipt this very block cites
    # in a form that can be fetched (blob / issuecomment / refs/heads / run id).
    has_receipt = bool(STRONG_RECEIPT.search(text))
    spans = [(m.start(), m.end()) for m in TOKEN.finditer(text)]
    unit_spans = [(m.start(), m.end()) for m in UNIT_AFTER_NUM.finditer(text)]
    for start, end in spans + unit_spans:
        cls, why = classify(text, start, end, has_receipt)
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


# Any well-formed 40-hex satisfies the ruler's *shape* rule; the ledger door's coordinate bolt is what
# later proves each such hash really resolves. These fixtures only exercise classification.
RECEIPT = "d" * 40
# No digits, no hex, no run-id shape: padding that pushes the receipt past the 200-char claim window.
FILLER = "，这段散文只负责把收据推到判据窗口之外，它不含任何数字，也不含任何可取的坐标形状" * 6

SAMPLES = {    "exempt_HTTP_STATUS": ("the tapped leg answered HTTP 503 with no envelope", "HTTP_STATUS"),
    "fire_quantity_ms": ("the tapped leg waited 32209 with no coordinate nearby", None),
    "fire_status_with_unit": ("the answer was HTTP 500 B payload and nothing else", None),
    "exempt_YEAR": ("measured on 2026-09-25 at 15:00 +08 nothing else", "YEAR"),
    "exempt_run_id_coordinate": ("elapsed 32209 recorded in O0301-144907 and blob " + "a" * 40, None),
    "exempt_PORT": ("nothing was listening on port 8000 at that moment", "PORT"),
    "exempt_LINE_REF": ("lines `PlanWithAiSheet.tsx:414`、`:474`、`:538` matched", "LINE_REF"),
    # a quantity with no coordinate must still fire even when a line-number list sits in the same sentence:
    # that is the regression this revision could plausibly cause (exempting too much around a line list)
    # a quantity whose only nearby coordinate is a source line number: still not a refusal (by design), but the
    # advisory must notice it, or the run over-reports its own coverage
    "advisory_line_ref_only_vouch": ("`a.tsx:414`、`:474` 之外另有一处计数 6 处 命中，附近没有 blob", None),
    # a genuine port must keep its own bucket even when a filename appears nearby, or LINE_REF would swallow it
    "exempt_PORT_with_filename_nearby": ("backend 端口 8651 上 LISTENING，配置文件 cfg.py 里同名", "PORT"),
    "fire_run_id_without_coordinate": ("the wait was 62000 and no run id appears anywhere", None),
    # ---- r4d: the two new classes, each with the direction that would make it a rubber stamp ----
    # The receipt is pushed OUT of the 200-char claim window on purpose. Adjacent to a number, a blob
    # already resolves the claim by r4's original rule, and then an exemption would look like it worked
    # when all it did was duplicate that rule. Out of range, only the named class can save the line.
    "exempt_DIMENSION_with_receipt": ("留白 212px 与那条声明的 212px 等量" + FILLER + " " + RECEIPT,
                                      "DIMENSION"),
    # units are free to type and a receipt is not: drop the receipt and the same sentence must still burn
    "fire_DIMENSION_without_receipt": ("留白 212px 与那条声明的 212px 等量" + FILLER, None),
    "exempt_DISCIPLINE_ZERO": ("本块边界：权威线 0 次移动、0 处覆盖" + FILLER + " " + RECEIPT,
                               "DISCIPLINE_ZERO"),
    # a ZERO in front of a product noun is a finding, not a discipline declaration, receipt or none
    "fire_ZERO_on_a_product_noun": ("该格命中 0 次" + FILLER + " " + RECEIPT, None),
    # only the zeroes are exempt: the same discipline noun with a non-zero count must speak
    "fire_NONZERO_after_a_discipline_noun": ("权威线 0 次移动、12 处覆盖" + FILLER + " " + RECEIPT, None),
    # and a discipline zero with no receipt cited anywhere in the block is not exempt either
    "fire_DISCIPLINE_ZERO_without_receipt": ("本块边界：权威线 0 次移动" + FILLER, None),
}


def selftest():
    rows = []
    for name, (text, expected) in SAMPLES.items():
        claims, findings, exempt = scan(text)
        rows.append({"sample": name, "claims": claims, "findings": [f["code"] for f in findings],
                     "exempt": exempt})
    # two-way assertions: every "exempt_" sample must be silent, every "fire_" sample must speak, and the
    # "advisory_" samples must be noticed by advisories() without becoming findings.
    checks = {}
    for name, (text, expected_class) in SAMPLES.items():
        claims, findings, exempt = scan(text)
        if name.startswith("advisory_"):
            checks[name] = bool(advisories(text)) and advisories(text + " " + "b" * 40) == []
        elif name.startswith("exempt_"):
            checks[name] = (not findings) and (expected_class in exempt or expected_class is None)
            if name == "exempt_LINE_REF":
                checks[name] = checks[name] and exempt.get("PORT", 0) == 0
            if name == "exempt_PORT":
                checks[name] = checks[name] and exempt.get("LINE_REF", 0) == 0
        else:
            checks[name] = bool(findings)
    # ---- r4e: the zero-claim path, both directions ----
    trio = ("### SESSION=x 勘误：was = " + "a" * 40 + " now = " + "b" * 40
            + " 复跑件 " + "c" * 40)
    _, f1, _ = scan(trio)
    c1, _, _ = scan(trio)
    checks["r4e_erratum_citing_three_blobs_passes"] = decide(c1, f1, trio) == ("Q43_GATE_GREEN_CITED", 0)
    duo = "no numbers here, just two blobs " + "d" * 40 + " and " + "e" * 40
    _, f2, _ = scan(duo)
    c2, _, _ = scan(duo)
    checks["r4e_two_blobs_is_the_boundary_and_passes"] = decide(c2, f2, duo)[1] == 0
    solo = "one blob only " + "f" * 40 + " and no numbers"
    _, f3, _ = scan(solo)
    c3, _, _ = scan(solo)
    checks["r4e_one_blob_still_refused"] = decide(c3, f3, solo) == ("NO_CLAIM_FOUND", 4)
    blank = "### SESSION=y nothing checkable at all"
    _, f4, _ = scan(blank)
    c4, _, _ = scan(blank)
    checks["r4e_empty_block_still_refused"] = decide(c4, f4, blank) == ("NO_CLAIM_FOUND", 4)
    badq = "留白 4096px 没人引用收据，所以这句仍该拦" + " " * 300
    _, f5, _ = scan(badq)
    c5, _, _ = scan(badq)
    checks["r4e_does_not_excuse_an_unvouched_quantity"] = decide(c5, f5, badq)[1] == 3
    ok = all(checks.values())
    print(json.dumps({"selftest_checks": checks, "overall_pass": ok, "samples": rows},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


def decide(claims, findings, text):
    """The verdict rule, split out so the selftest can assert both directions of the r4e exception.

    It takes the TEXT, not a pre-counted number: the first version of this took `strong`, and my own
    selftest arms passed literals (3, 2, 1, 0) - so when the counting regex broke on two stray control
    bytes, every arm stayed green while the real path refused everything.  Counting inside the function
    is the difference between testing the rule and testing my memory of the rule."""
    if findings:
        return "Q43_GATE_RED", 3
    if claims:
        return "Q43_GATE_GREEN", 0
    if len(BLOB40.findall(text)) >= 2:
        return "Q43_GATE_GREEN_CITED", 0
    return "NO_CLAIM_FOUND", 4


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
    adv = advisories(text)
    if adv:
        print("ADVISORY (verdict unchanged) quantities vouched only by a source line number: %d -> %s"
              % (len(adv), sorted(set(a["code"] for a in adv))))
    # r4e: a block may hold no bare numbers at all and still be maximally checkable - an erratum whose
    # whole content is "was this blob, now that blob" cites more coordinates than a paragraph of prose
    # with one quantity.  Refusing those taught lanes to pad text with fake claims to satisfy the gate,
    # which is the opposite of what a claim gate is for.  So: zero claims is a refusal UNLESS the block
    # itself carries >= 2 resolvable-shape strong coordinates.
    verdict, code = decide(claims, findings, text)
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
