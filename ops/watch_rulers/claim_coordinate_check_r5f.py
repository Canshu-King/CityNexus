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

VERSION = "Q43_r5f"
# r5f (ORD-0371, commander's three items of 2026-09-28 04:1x, measured on rel_0338.md):
#   1. ATTRIBUTION IS PER LINE.  One resolvable coordinate (`path:line` or a full 40-hex) on a line
#      attributes EVERY number on that line.  r5e already refused nothing in that case, but it still
#      *counted* those readings as claims and only spared them through a +-80-character `receipt_near`
#      test, so the same literal was exempt on one line and a claim on another.  The +-80 channel is
#      gone: the line is the unit, which is the only thing a lane can actually write.
#   2. A READING IS A NAMED CLASS, not "no class matched".  `62 passed`, `4 个`, `5 条`, `2423 B`,
#      `5.77s` now land in COUNT / DIMENSION.  They are CONDITIONAL: strip the unit and the line still
#      has to carry a coordinate, so the class cannot become a place to hide numbers.
#   3. A REFUSAL NAMES THE FIX.  `remedy` is computed per row for every class, including COUNT.
# Not widened, and armed against it: a bare artifact path with no `:line` is STILL not a coordinate
# (measured: that is why rel_0338's ten lines burn - none of them contains either accepted form), and a
# coordinate on the NEXT line buys nothing.
# What this revision supersedes, and the single defect it is built around (ORD-0371, commander 2026-09-28):
#   claim_coordinate_check_r4e.py - same classifier, but three of its decisions read MORE than the number
#   in front of them:
#     * HTTP_STATUS swept +/-40 chars for a status word, so one "HTTP" in a paragraph decided every
#       3-digit number near it;
#     * DIMENSION / DISCIPLINE_ZERO were conditioned on a block-level "does somewhere in this text cite a
#       receipt" boolean, so a blob in paragraph 4 bought an exemption for a `212px` in paragraph 1;
#     * TOKEN matches and UNIT_AFTER_NUM matches were walked as two lists, so `1392 条` was judged twice,
#       counted as two claims and, when it failed, reported as two findings for one number.
#   r5 makes a token's verdict a function of (its own syntactic shape, what is immediately adjacent to
#   it) and nothing else. Two numbers of the same shape with the same adjacency therefore get the same
#   class in every block, and no number inherits another number's receipt.
SUPERSEDES = ("claim_coordinate_check_r4e.py (shape/adjacency work), claim_coordinate_check_r5.py "
              "(0.4 GB, code 000, host:NNNN, quoted ports) and claim_coordinate_check_r5b.py (this "
              "revision adds: an honest reason for a reading whose receipt is far away, and order "
              "numbers written with a leading zero)")

RELAY_WORDS = ("它说", "他说", "她说", "某处", "车道报", "lane says", "reports that", "per the lane",
               "据车道", "随件给了", "as reported")
CONSTANT_CLAIM = re.compile(r"\b[A-Z][A-Z0-9_]{4,}\s*=\s*\d[\d_]*")
# ---- ORD-0371: the classifier may only look at the token and what is adjacent to it ----
# How far a status word or a receipt may sit from the number and still count as *that number's*
# context.  r4e used 40 chars for a status word and the whole block for a receipt, so the same
# `401` in one block was exempt three times and refused three times, and a `212px` changed class
# depending on whether some unrelated paragraph cited a blob.
STATUS_ADJACENCY = 16
# r5b, DECLARED WIDENING (3/3), and it is a CLOSED set rather than "any three digits": HTTP's own
# codes plus curl's `000` (no response at all). r4e/r5 refused `隧道三枚路径全 401` as a bare number
# because the nearest status word sat 101 characters away, and the ruler may not reach that far on
# purpose - ORD-0371. What identifies these numbers is that they belong to HTTP, not a neighbour.
# Cost, measured on the live inbox: `138`/`617`/`629`/`1667` stay red (not in the set), `409` only
# escapes when it is written bare - `409M` is a size and is still a claim (unit list above).
STATUS_CODES = {200, 201, 204, 301, 302, 304, 400, 401, 403, 404, 405, 406, 408, 409, 410, 412,
                413, 415, 418, 422, 425, 429, 431, 451, 500, 501, 502, 503, 504, 505, 506, 507,
                508, 510, 511, 0}
# How far a `pid`/`进程` label may sit from a number and still say "this is an identifier".
NAME_ADJACENCY = 16
PORT_ADJACENCY = 16
# A port may be named in front of it (`端口 8000`) or behind it (`7892 在听`, `7897 LISTENING`): lanes
# quote the socket first and say what it is in the same breath.  r4e/r5 only read forwards-never, so
# `7892` 匹配 0 行 was a bare number.
# `netstat` is NOT in this list: measured on n2_0105:11, "当时 `netstat` 第 138 行原样" turned a
# LINE NUMBER inside a netstat dump into a port. A tool name does not say what the number is.
PORT_WORDS = r"(?:port|端口|端口号|在听|监听|listen|LISTENING|socket|代理口)"
RECEIPT_ADJACENCY = 80
# A `path:line` coordinate is a path:line whatever the suffix is.  r4e's list stopped at the
# extensions someone had typed by hand in 2024, so `tools/chain_self_heal.mjs:215-224` was refused
# as a bare number while `backend/app/main.py:5242-5252` passed - same kind of fact, two verdicts
# (measured by the commander on 2026-09-28 00:53, reproduced in diagnose_r1.py).
EXTS = (r"py|ts|tsx|js|jsx|mjs|cjs|mts|cts|json|yaml|yml|c|h|css|scss|html|txt|md|markdown|"
        r"toml|ini|cfg|conf|sql|sh|bash|ps1|bat|cmd|vue|svelte|go|rs|rb|php|java|kt|swift")
PATH_LINE_ALT = r"|[\w./\\-]+\.(?:%s):\d+" % EXTS
PATH_LINECOORD = re.compile(PATH_LINE_ALT[1:], re.IGNORECASE)
# WIDENING (declared), and it is a coordinate-recognition fix, not an exemption: `\b` does not exist
# between a hex run and a Chinese character, because CJK counts as a word character.  So r4e silently
# ignored a blob that a lane wrote straight after prose - `…形状` + 40 hex - and refused a claim whose
# coordinate was there all along.  Measured with mutation_r5_r3.py: two of my own arms passed for the
# wrong reason until this was fixed.  A boundary is now "not glued to ASCII name characters", which
# lets CJK, punctuation and space pass while `aaa…40hexxyz` and `_`-glued runs still do not count.
ASCII_GLUE = r"0-9a-zA-Z_"
HEX40 = r"(?<![%s])[0-9a-f]{40}(?![%s])" % (ASCII_GLUE, ASCII_GLUE)
# The run-id keeps r4e's LEFT grammar exactly (no guard): adding one read `_qoder_preview_20260920` as
# a directory name instead of a run id and retroactively redded a block the old ruler had passed.
# Narrowing what counts as a coordinate is a different order from this one; here only the CJK boundary
# on the right changes.
RUNID = r"[A-Za-z]{1,6}[-_]\d{6,8}(?![%s])" % ASCII_GLUE
BLOB_WORD = r"(?<![%s])blob[^\n]{0,12}[0-9a-f]{7,40}(?![%s])" % (ASCII_GLUE, ASCII_GLUE)
DURABLE = re.compile(HEX40
                     + r"|" + BLOB_WORD
                     + r"|issuecomment-\d{6,}"
                     + r"|refs/heads/[\w./-]+"
                     + r"|" + RUNID
                     + r"|run[_ ]?id[^\n]{0,3}\d{6,8}"
                     + PATH_LINE_ALT,
                     re.IGNORECASE)
WINDOW = 200
FULLWIDTH_EQ = "="
UNIT_AFTER_NUM = re.compile(r"\d[\d_,.]*\s*(?:B|KB|MB|GB|TB|M|K|G|ms|s|秒|分钟|处|条|个|格|轮|次|件|节点|芯片|%|passed|failed|skipped|errors?)")
TOKEN = re.compile(r"(?<![\w-])(?<![0-9a-fA-F])\d[\d_,]{2,}(?![0-9a-fA-F])")
STATUS_WORD = re.compile(r"(HTTP|http|status|状态码|状态|response|答复|答|code|5xx|4xx|3xx|2xx)", re.I)
YEAR = re.compile(r"^(19|20)\d{2}$")
CLOCKISH = re.compile(r"^\d{2}:\d{2}|^\d{4}-\d{2}-\d{2}", re.I)
IDENTIFIERISH = re.compile(r"^[A-Za-z]+[-_]$|^[-_][A-Za-z0-9]+$")
# The status word has to be ADJACENT to the number, so the two directions are compiled once from
# STATUS_WORD rather than re-typed - a drifted duplicate here would silently change the class.
STATUS_BEFORE = re.compile(r"(?:%s)[\s:=／/、,，-]{0,3}$" % STATUS_WORD.pattern, re.I)
STATUS_AFTER = re.compile(r"^[\s:＝=]*?(未授权|无权限|状态码|status|code|拒绝|refused)", re.I)

# ---- r4d: two context-bound exemptions, both paid for with a receipt the block already cites ----
# A physical dimension: what the instrument measured. Its coordinate is the artifact holding the run.
DIM_UNITS = {"px", "rem", "em", "vw", "vh", "dpi", "ms", "us", "ns", "s", "b", "kb", "mb", "gb",
             "字节", "秒", "分钟", "小时", "天", "%", "℃", "度"}
# Words that COUNT product facts. `0` in front of one of these is still a claim, receipt or not.
COUNT_WORDS = ("次", "处", "条", "笔", "个", "格", "轮", "移动", "命中", "节点", "件", "芯片")
# r5f rule 2: the same words, plus the runner's own result words, form the COUNT class.  A COUNT is
# admitted to be a quantity - it is exempt only when its OWN LINE carries a resolvable coordinate, so
# naming the class never hides a number (armed by fire_COUNT_* below).
COUNT_TAILS = COUNT_WORDS + ("passed", "failed", "skipped", "errors", "error", "文件")
# Only these nouns make a zero an absence-of-action declaration rather than a product reading.
DISCIPLINE_NOUNS = ("权威线", "产品字节", "demo/reset", "vite build", "凭据", "push", "ref",
                    "skip", "覆盖", "删除", "改写", "重写", "回滚")
# `path:line` is deliberately NOT here: it is not retrievable after a rewrite, which is why r4's
# advisories() already treats a quantity vouched only by a source line number as thin coverage.
BLOB40 = re.compile(HEX40)
STRONG_RECEIPT = re.compile(HEX40 + r"|issuecomment-\d{6,}|refs/heads/[\w./-]+|" + RUNID,
                            re.IGNORECASE)


def unit_of(text, start, end):
    """The dimension unit attached to a number, whether it sits inside the matched span (`212px`,
    `0.4 GB`, `2 秒`) or just after it. Returns the lowercased unit, or None when the tail is not
    a dimension.

    r5's first pass could not see a unit in a DECIMAL reading: `(\d[\d_,]*)` stops at the dot, so for
    `0.4 GB` it read the unit as "." and the reading fell through to a bare claim (measured on
    n2_0144:15 and n2_0152:15 - the same sentence, the same refusal, in two lanes' blocks)."""
    for cand in (re.search(r"([\d.,_]+)\s*([^\d\s,;。，；、\)\]」』\"]+)", text[start:end]),
                 re.match(r"\s*([^\d\s,;。，；、\)\]」』\"]+)", text[end:end + 6])):
        if not cand:
            continue
        u = cand.group(cand.lastindex).strip().rstrip("）)】」』\"'")
        if u.lower() in DIM_UNITS:
            return u.lower()
    return None


def normalise(text):
    # r5f: fold line endings BEFORE anything else, because rule 1 makes the LINE the unit of
    # attribution.  Measured on the live inbox (map_0447.md, 62 CRLF): the same bytes read through the
    # CLI keep `\r`, and the ruler reported 10 findings, while the identical text with LF reported 9 -
    # the author's editor was changing the verdict.  With attribution per line that is not cosmetic.
    return text.replace("\r\n", "\n").replace("\r", "\n").replace(FULLWIDTH_EQ, "=")


def classify(text, start, end, line_attributed=False):
    """Return (class_or_None, why). None means: this is a quantity and must carry a coordinate.

    `line_attributed` is decided by the caller for THIS occurrence: a resolvable coordinate sits on the
    same LINE as this number (r5f rule 1).  r4d/r4e passed a block-level boolean, so one blob anywhere
    in a block bought an exemption for every unit-bearing number in it; r5e passed a +-80-character
    window, so the same literal was exempt on one line and a claim on another.  Both are gone.

    `line_attributed` decides only whether a CONDITIONAL class (DIMENSION / COUNT / DISCIPLINE_ZERO) is
    EXEMPT.  The class itself always comes from this number's own shape, so a refusal can name what the
    ruler saw."""
    tok = text[start:end].replace(",", "").replace("_", "")
    after = text[end:end + 8]
    before = text[max(0, start - 24):start]
    # WIDENING, declared for the counter-example pass (the only one in this revision): an ASCII name
    # character glued on BOTH sides means the digits sit inside an opaque name, not beside a unit.
    # `assets/index-BEEP22s_.js` is a bundle generation; UNIT_AFTER_NUM read its `22s` as a duration
    # because that matcher has no left-boundary guard while TOKEN does, so my tighter DIMENSION rule
    # turned a published-green block red over a file name (measured: parity_r4e_vs_r5_output.json).
    # Deliberately conjunctive and ASCII-only: ` 22s`, `了22s` after a Chinese character, and `500 B`
    # are all still judged, and the arms below keep them red.
    if re.search(r"[A-Za-z0-9_]$", before[-1:]) and re.match(r"[A-Za-z0-9_]", text[end:end + 1]):
        return "IDENTIFIER_PART", "digits glued between ASCII name characters"
    # r4d (1/2).  `212px` is a reading, not a claim about a quantity of things: its coordinate is the
    # artifact that recorded the run.  Conditional on a RETRIEVABLE receipt cited beside the reading.
    unit = unit_of(text, start, end)
    if unit:
        # r5c: the CLASS is a property of this number's own shape, so it is assigned whether or not a
        # receipt is beside it.  r5b returned None here when the receipt was far, and `scan` then wrote
        # "no class matched" on the finding - which read to the commander as "the ruler has a DIMENSION
        # class and did not eat it" while the real reason was the distance (measured: `0.4 GB` has its
        # nearest receipt 397 chars away, `1.58 GB`/`7.53 秒` are no longer in the current n3_0212 at all).
        # The verdict is unchanged; only the stated reason becomes true.
        return "DIMENSION", ("physical reading with unit %r, exempt because this line carries a "
                             "coordinate" % unit if line_attributed else
                             "physical reading with unit %r, but THIS LINE carries no resolvable "
                             "coordinate -> Q43_r5f_STILL_NEEDS_A_LINE_COORDINATE" % unit)
    # r4d (2/2).  `权威线 0 次移动` states what this lane did NOT do; the witness is the ref log and the
    # diff, and no blob can sit beside every zero.  A non-zero, or a zero in front of a product noun
    # (`该格命中 0 次`), stays a claim -- that is the distinction this arm is built to keep.
    if re.match(r"^0\s*(%s)" % "|".join(COUNT_WORDS), tok):
        hit = [n for n in DISCIPLINE_NOUNS if n in before]
        if hit:
            # r5c: same split as DIMENSION - the class comes from this number's own shape and the noun
            # in front of it; whether it is EXEMPT still requires a receipt beside it (checked in scan).
            return "DISCIPLINE_ZERO", ("absence declared in front of %r" % hit[0] if line_attributed else
                                       "absence declared in front of %r, but THIS LINE carries no "
                                       "resolvable coordinate -> Q43_r5f_STILL_NEEDS_A_LINE_COORDINATE"
                                       % hit[0])
    COUNT_TAIL_RE = re.compile(r"^(?:\d[\d_,.]*\s*)?(%s)" % "|".join(COUNT_TAILS))
    # Only WHITESPACE may sit between the number and its measure word.  My first pass also stripped
    # 、，（: and that read the tile segment in `1667/889、…件` as a count of 889 things, turning a
    # block that r5e passed with 3 findings into 4 (measured on n2_0213.md:15; the arm
    # `r5f_a_measure_word_behind_punctuation_is_still_a_path_segment` is the price).
    tail = COUNT_TAIL_RE.match(tok) or COUNT_TAIL_RE.match(after.lstrip(" \t"))
    if tail and re.search(r"\d", tok):
        # r5f rule 2.  r5e answered `None / "carries a unit -> measurement"` here, so a count reported
        # "no class matched" while the ruler does have a name for it - the commander's 04:1x complaint
        # about `62 passed`, `5 条`, `4 个`.  The CLASS is now named; the EXEMPTION still requires this
        # number's own line to carry a coordinate, which is what keeps the class from hiding numbers.
        # Both spellings are tested because UNIT_AFTER_NUM swallows the measure word into the span
        # (`875 个`) while TOKEN leaves it in `after` (`875 个`): measured, with only the `after` test
        # `本轮 875 个` classified None - my own r5f arm caught that hole.
        return "COUNT", ("count of things (%r beside the number), exempt only if THIS LINE carries a "
                         "resolvable coordinate" % tail.group(1))
    if YEAR.match(tok) and not re.match(r"^\s*(ms|s|B)\b", after):
        return "YEAR", "4-digit year"
    if CLOCKISH.match(after.lstrip()) or re.search(r"\d{1,2}:\d{1,2}$", before[-6:]):
        return "CLOCK", "clock/timestamp digit"
    # r5d, DECLARED WIDENING (the third one).  A number glued to a `/` or to the inside of `[...]` is a
    # SEGMENT of a path, a tile URL or an extent array - not a count of anything.  Measured on the live
    # inbox: `.../11/1668/889.png` (tile x/y) and `框 [0,145,522,44]` (a bounds array) were refused as
    # bare claims, which would condemn any block that quotes a log line or a URL at all.  Count and
    # unit tests run first, so `875 个`, `13 条` and `52 秒` are untouched; a number merely NEXT TO a
    # slash-free word stays a claim (`1668 次`).
    if re.fullmatch(r"\d[\d,]{0,15}", tok) and (
            before.endswith("/") or text[end:end + 1] in ("/", "]")
            or text[start - 1:start] in ("/", "[")):
        return "IDENTIFIER_PART", "segment of a path, tile URL or bracketed array"
    if IDENTIFIERISH.match(before[-2:]) or re.search(r"(ORD|CMDR|Q|REQ|NOTE|RX|D|A|B)-$", before):
        return "IDENTIFIER_PART", "part of an order/label id"
    # r5b already ate `ORD-0373`; this eats the same number when a lane writes it with the prefix
    # dropped or shared: `ORD-0370/0373`, `这与 0376 那条要求`. A 4-digit run that STARTS WITH ZERO is
    # not how anyone writes a measurement, and the count/unit tests above run first, so `0 处`,
    # `0 条`, `0373 秒` stay claims. Cost stated: a bare leading-zero COUNT ("命中 0373") would pass.
    if re.fullmatch(r"0\d{3}", tok):
        return "IDENTIFIER_PART", "order/ticket number, leading zero kept as written"
    # r5b (1/3), DECLARED WIDENING.  A number that sits alone between two backticks is a NAME the lane
    # is pointing at, not a quantity it is asserting: `7897`：件 A 第 13 行 / `7892` 匹配 0 行 /
    # `35752`：…owning pid 列 (all three refused by r4e AND by r5's first pass).  The unit and count
    # tests above run FIRST, so a quoted `875 个` is still a claim - the cost of this sentence is a
    # bare `875` written in quotes with no measure word, which now passes; the arms say so.
    if (text[start - 1:start] == "`" and text[end:end + 1] == "`" and re.fullmatch(r"\d{3,6}", tok)
            and not (re.fullmatch(r"\d{3}", tok) and int(tok) in STATUS_CODES)):
        return "IDENTIFIER_PART", "a quoted token naming an entry, not a count of things"
    # r5b (2/3).  A process id is an identifier; lanes write it beside `pid`/`进程`, before or after.
    if re.fullmatch(r"\d{3,6}", tok) and (
            re.search(r"(pid|进程号?|进程|PID)[\s:=／/、,，]*$", before)
            or re.match(r"^[\s:=／/]*?(pid|PID|进程)", text[end:end + NAME_ADJACENCY])):
        return "IDENTIFIER_PART", "process id named beside pid/进程"
    # An address octet is not a quantity.  r4e reported `127.0.0.1:7892` as TWO bare numbers, so a
    # lane citing the proxy it measured had to attach a coordinate to each octet.
    if re.search(r"\d{1,3}\.\d{1,3}$", before) or re.match(r"^\.\d{1,3}", after):
        return "ADDRESS_PART", "part of a dotted-quad address"
    # r5b (3/3), DECLARED WIDENING.  What makes a 3-digit run a status code is the WORD beside it, not
    # the first digit: curl answers `000` when there is no response at all, and r4e's `[1-5]` guard
    # threw that reading back as a bare number even with "code" one space in front of it
    # (`全是 code \`000\`、bytes 0`, n2_0105:18).  Cost, stated: `875` next to a status word now passes.
    if re.fullmatch(r"\d{3}", tok) and int(tok) in STATUS_CODES:
        return "HTTP_STATUS", "a number from HTTP's own enumeration (or curl's 000)"
    if re.fullmatch(r"\d{3}", tok):
        # Adjacency, not a 40-char sweep: the status word has to belong to THIS number.  r4e read
        # ±40 chars, so one "HTTP" in a sentence decided the verdict of every 3-digit number near
        # it, and the same `401` written twice in one block got two classes.
        near_before = text[max(0, start - STATUS_ADJACENCY):start]
        near_after = text[end:end + STATUS_ADJACENCY]
        if STATUS_BEFORE.search(near_before) or STATUS_AFTER.match(near_after):
            return "HTTP_STATUS", "3-digit status code with a status word adjacent to it"
    # Line-number lists are how lanes cite prose: "`PlanWithAiSheet.tsx:414`、`:474`、`:538`". r4b called every
    # `:NNN` after a non-word char a PORT, so a 6-item line list turned 5 claims into invisible exemptions and
    # the coverage number lied (lane D e345b9d6 reported this on 09-26 01:22 and I reproduced it). Same verdict
    # either way - both classes are exempt - but the buckets must be honest, otherwise "exempt: PORT 9" hides
    # "these were line refs".
    if re.fullmatch(r"\d{3,5}", tok.lstrip("0") or "0"):
        # The reference has to be read INCLUDING this number: `tools/x.mjs:215` is the coordinate, and
        # looking only at what precedes it meant the first line reference in a text never matched, so
        # the ruler refused the very coordinate form it accepts everywhere else (measured: r4e on
        # `tools/chain_self_heal.mjs:215-224` -> bare-number finding for 215).
        ctx_through = text[max(0, start - 48):end]
        if before.endswith(":") and PATH_LINECOORD.search(ctx_through):
            return "LINE_REF", "line number of a file:line reference"
        # A colon can carry a SOURCE LINE or a SOCKET, and the two are told apart by what the label
        # before the colon ENDS IN: `main.py:` is a file, `github.com:` is a host.  r4e's `\w:$` guard
        # called both "a file" and refused `直连 github.com:443 超时` as a bare number (n2_1759:21).
        label = re.search(r"([A-Za-z0-9._-]+):$", before)
        if label and "." in label.group(1) and not re.search(
                r"\.(?:%s)$" % EXTS, label.group(1), re.I):
            return "PORT", "port after a dotted host that is not a source file"
        # `127.0.0.1:7892` is a socket, not a line: r4e's `\w:$` guard read the digit before the colon
        # as "someone wrote file:line", so every host:port was refused twice over (the port AND the
        # last octet). The dotted-host rule above covers that form, which is why the separate
        # address-shaped test r5 carried is gone - removing it changed no verdict (mutation-checked).
        # r5b: the port word may come AFTER the number, which is how a lane quotes a socket and then
        # says what it is (`\`7892\` 匹配 0 行`, `实测在听的是 … 7897（pid …)`).  Same radius as every
        # other adjacency in this ruler, and the unit/count tests above still run first, so `875 个`
        # in front of the word "端口" is still a claim.
        port_word_before = re.search(r"(port|端口|在听|监听|listen|LISTENING|proxy)\D{0,8}$", before, re.I)
        port_word_after = re.match(r"^[\s`：:，,、（(]*?(%s)" % PORT_WORDS,
                                   text[end:end + PORT_ADJACENCY])
        if (port_word_before or port_word_after
                or (before.endswith(":") and not re.search(r"\w:$", before))):
            return "PORT", "port number (port word adjacent on either side, or written as host:NNNN)"
    return None, "no class matched"


def line_bounds(text, pos):
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    return start, (len(text) if end < 0 else end)


def coordinate_in_window(text, pos):
    """Is THIS number vouched?  Two scopes, in this order.

    1. ITS OWN LINE.  A lane that writes one long line and puts the blob at the end of it has cited the
       line - measured on the live inbox: `8 passed` sits 2662 characters from `refs/heads/...` inside a
       599-character line, and the 200-character window refused a coordinate that was plainly there.
       Commander's ruling of 2026-09-28 02:5x, option 1: one resolvable coordinate locks its line.
    2. Otherwise the +-WINDOW character radius r4 has always used, so a coordinate in the neighbouring
       prose still counts and short lines behave exactly as before.

    The line is NOT extended across newlines: a coordinate two paragraphs away buys nothing, which is
    the direction a widening would take and is refused by the `fire_LINE_without_coordinate` arm."""
    lstart, lend = line_bounds(text, pos)
    line = text[lstart:lend]
    m = DURABLE.search(line)
    if m:
        return True, m.group(0)[:60], ["LOCKED_BY_LINE"]
    lo, hi = max(0, pos - WINDOW), min(len(text), pos + WINDOW)
    window = text[lo:hi]
    m = DURABLE.search(window)
    if m:
        return True, m.group(0)[:60], []
    notes = []
    if re.search(r"[\w./\\-]+\.md:\d+", window, re.I):
        notes.append("UNSTABLE_COORDINATE_markdown_line_number_in_a_rewritten_file")
    return False, None, notes


SOURCE_LINE_REF = PATH_LINECOORD
STRONG_COORD = STRONG_RECEIPT   # one definition, so the advisory channel cannot drift from the gate


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


def exempt_by_class(cls, line_attributed):
    """Which named classes actually buy an exemption.

    Three of them are CONDITIONAL, and this is the line that keeps r5c's honest reporting from turning
    into a widening: assigning `DIMENSION` to `0.4 GB` or `COUNT` to `62 passed` because of their shape
    must not exempt them when the line carries no coordinate.  r5f rule 1 changed the *test* from
    "a strong receipt within 80 characters of this token" to "a resolvable coordinate on this line",
    which is tighter across lines and consistent within one - the two-verdicts-for-one-literal defect.
    Every other class is unconditional because it says the number is not a quantity at all (a year, a
    port, an id, a status code, part of a name)."""
    if cls in ("DIMENSION", "DISCIPLINE_ZERO", "COUNT"):
        return bool(line_attributed)
    return bool(cls)


def occurrences(text):
    """Every number the ruler judges, with the judgement it got.  One code path for `scan` and for the
    self-test: an arm that asserted a class by re-implementing this walk would test my memory of the
    rule instead of the rule (that is how r4e's control-byte bug stayed green)."""
    text = normalise(text)
    # One occurrence, one verdict.  r4e walked TOKEN matches and then UNIT_AFTER_NUM matches, and a
    # number written with a unit (`1392 条`) sits in BOTH lists - so it was classified twice, counted
    # as two claims and, when it failed, reported as two findings for one number (measured:
    # `the ledger holds 1392 条` -> claims 2, findings ["1392", "1392 条"]).
    # Where the two overlap the longer span wins: it is the one that carries the unit, and therefore
    # the one whose class is worth reporting.
    spans = ([(m.start(), m.end()) for m in TOKEN.finditer(text)]
             + [(m.start(), m.end()) for m in UNIT_AFTER_NUM.finditer(text)])
    rows, covered_to = [], -1
    for start, end in sorted(spans, key=lambda se: (se[0], se[0] - se[1])):
        if start < covered_to:
            continue
        covered_to = max(covered_to, end)
        lstart, lend = line_bounds(text, start)
        # r5f rule 1: a resolvable coordinate on THIS line attributes every number on it.  This is an
        # ADDITIVE channel - the +-WINDOW radius r4 has always used stays, because measured on the live
        # inbox, dropping it made 15 of 22 backlog blocks redder and rel_0338 went 27 -> 36 (my first
        # pass did exactly that and my own backlog table caught it: backlog_r5f_r1.json).  The line is
        # what a lane can be told to write; the window is what it may rely on while it learns.
        vouch = DURABLE.search(text[lstart:lend])
        cls, why = classify(text, start, end, bool(vouch))
        ok, coord, notes = coordinate_in_window(text, start)
        rows.append({"start": start, "end": end, "token": text[start:end], "class": cls, "why": why,
                     "predicate": PREDICATE.get(cls, "P0_no_class_matched"),
                     "line_attributed": bool(vouch),
                     "attributing_coordinate": vouch.group(0)[:60] if vouch else None,
                     "coordinate": coord if ok else None,
                     "coordinate_notes": notes, "line": text.count("\n", 0, start) + 1})
    return text, unify_literal_verdicts(rows)


# One channel per exempt class: the name is the single predicate that may grant it, so a lane can read
# the finding and know which test ran, instead of seeing the same literal classed two ways (measured on
# n2_1759:21 - `7892` was PORT in `127.0.0.1:7892` and an unclassified claim in "连不上 7892").
PREDICATE = {
    "HTTP_STATUS": "P1_http_enumeration_or_adjacent_status_word",
    "PORT": "P2_colon_host_or_adjacent_port_word",
    "ADDRESS_PART": "P3_dotted_address_octet",
    "LINE_REF": "P4_path_colon_line",
    "IDENTIFIER_PART": "P5_name_shape_quoted_ticket_path_or_process_id",
    "YEAR": "P6_four_digit_year", "CLOCK": "P7_clock_shape",
    "DIMENSION": "P8_unit_beside_the_number_needs_a_coordinate_on_its_line",
    "COUNT": "P11_count_or_result_word_needs_a_coordinate_on_its_line",
    "DISCIPLINE_ZERO": "P9_zero_after_a_discipline_noun_needs_a_coordinate_on_its_line",
    None: "P0_no_class_matched_it_is_a_quantity",
}
# The three conditional classes: named by shape, exempted only by a coordinate on their own line.
CONDITIONAL_CLASSES = ("DIMENSION", "COUNT", "DISCIPLINE_ZERO")
# Only these classes are shape-determined, so they may be spread to every occurrence of the same
# literal in a block. DIMENSION / DISCIPLINE_ZERO are NOT in here: those two mean "this IS a quantity,
# and a receipt sits beside it", and spreading them would let one anchor launder every repeat of a
# count - which is the (c) widening both the commander and Q74 forbid.
UNIFORM_CLASSES = ("HTTP_STATUS", "PORT", "ADDRESS_PART", "LINE_REF", "IDENTIFIER_PART", "YEAR",
                   "CLOCK")


def unify_literal_verdicts(rows):
    """Commander's requirement 1: one verdict per literal number string per block, for the shape
    classes.  Whichever occurrence the ruler could name first wins, and every other occurrence of that
    exact string inherits it with the deciding line and predicate recorded - so a lane is never told to
    fix line 8 by what line 21 did differently.

    Cost, stated and armed: a bare three-digit COUNT that happens to equal a code named elsewhere in the
    same block (`本轮另有 875` in a block that also cites `875 未授权`) now reads as that code."""
    decided = {}
    for row in rows:
        if row["class"] in UNIFORM_CLASSES and row["token"] not in decided:
            decided[row["token"]] = row
    for row in rows:
        src = decided.get(row["token"])
        if src is None or src is row or row["class"] in CONDITIONAL_CLASSES:
            continue
        if src["class"] != row["class"]:
            row["class"] = src["class"]
            row["why"] = ("same literal as line %d, classed there by %s; one verdict per string"
                          % (src["line"], src["predicate"]))
            row["predicate"] = src["predicate"]
            row["unified_from_line"] = src["line"]
    return rows


def remedy_for(row):
    """Commander's requirement 2: a refusal has to say what to write, named, not just "no class
    matched". Computed from the row the ruler already produced - never a fixed string."""
    cls = row["class"]
    if cls in ("DIMENSION", "COUNT", "DISCIPLINE_ZERO"):
        # r5f rule 3: name the two accepted coordinate forms, and say where. Never "no class matched".
        return ("%s recognised by its own shape, and THIS line carries no `<path>:<line>` and no full "
                "40-hex; fix = put one of those two forms on THIS line (the artifact path with its line "
                "number, or the published blob's 40 hex), do not delete the number, and do not move the "
                "coordinate onto the next line - only this line counts"
                % {"DIMENSION": "reading recognised by its unit",
                   "COUNT": "count recognised by its measure/result word",
                   "DISCIPLINE_ZERO": "absence declared beside a discipline noun"}[cls])
    if re.search(r"(个|处|条|次|格|轮|秒|分钟|节点|件|芯片|%)$", row["token"]):
        return ("count of things: cite the artifact that counted it, `<path>:<line>` or a full 40-hex "
                "blob, ON THE SAME LINE; do not delete the number")
    if re.fullmatch(r"[\d,]{3,}", row["token"]):
        return ("bare number: if it names something write it as a reference (`ORD-0373`, "
                "`review/x.json:12`, or backtick-quoted like `7897`); if it counts something, put a "
                "measure word beside it and cite the artifact on the same line")
    return "attach `<path>:<line>` or a full 40-hex blob on this line"


def scan(text):
    findings, claims, exempt = [], 0, {}
    text, rows = occurrences(text)
    seen = {}
    for row in rows:
        if exempt_by_class(row["class"], row["line_attributed"]):
            exempt[row["class"]] = exempt.get(row["class"], 0) + 1
            continue
        claims += 1
        if row["coordinate"] is None:
            conditional = row["class"] in CONDITIONAL_CLASSES
            key = (row["token"], row["line"])
            if key in seen:
                # one line that repeats the same literal six times gets ONE finding with a count, not
                # six indistinguishable ones (commander's requirement: 同一句话不应逐次拒)
                seen[key]["repeat_on_line"] += 1
                continue
            item = {"kind": "F3_bare_numeric_claim", "matched": row["token"][:40],
                    "code": ("NUMBER_WITHOUT_COORDINATE" if not row["coordinate_notes"]
                             else "NUMBER_WITH_UNSTABLE_COORDINATE"),
                    "line": row["line"], "predicate": row["predicate"],
                    "class_assigned_by_shape": row["class"],
                    "line_attributed": row["line_attributed"],
                    "code_when_classified": ("READING_CLASSIFIED_BUT_NO_COORDINATE_ON_THE_LINE"
                                             if conditional else None),
                    # how the block is unblocked, computed from this row rather than typed
                    "remedy": remedy_for(row),
                    "repeat_on_line": 1, "why_classified_as_quantity": row["why"],
                    "seen_coordinate": None}
            seen[key] = item
            findings.append(item)
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
# r5d: the padding also ends and restarts a LINE, because "one resolvable coordinate locks its line"
# is now a scope of its own; a fixture that only pushes the receipt far away along one long line would
# test nothing. A coordinate on the NEXT line must buy nothing to the number on this one.
SEP = FILLER + "\n\n" + FILLER
# A receipt that is both beyond the +-WINDOW radius and on a DIFFERENT line, so neither scope vouches
FAR_RECEIPT = FILLER + "\n\n" + RECEIPT
# A paragraph of OTHER numbers - a year, a port, a dotted address, a receipt - one per class r4e could
# only reach block-wide.  The determinism arms below put it before and after a target sentence and
# require the target's verdict to be unchanged in all three placements.
DISTRACTORS = "另有 2026 年的记录、端口 8000 在监听、代理 127.0.0.1:7892 无人应答，收据 " + RECEIPT

SAMPLES = {
    "exempt_HTTP_STATUS": ("the tapped leg answered HTTP 503 with no envelope", "HTTP_STATUS"),
    "fire_quantity_ms": ("the tapped leg waited 32209 with no coordinate nearby", None),
    "fire_status_with_unit": ("the answer was HTTP 500 B payload and nothing else", None),
    "exempt_YEAR": ("measured on 2026-09-25 at 15:00 +08 nothing else", "YEAR"),
    "exempt_run_id_coordinate": ("elapsed 32209 recorded in O0301-144907 and blob " + "a" * 40, None),
    "exempt_PORT": ("nothing was listening on port 8000 at that moment", "PORT"),
    "exempt_LINE_REF": ("lines `PlanWithAiSheet.tsx:414`、`:474`、`:538` matched", "LINE_REF"),
    # a quantity whose only nearby coordinate is a source line number: still not a refusal (by design), but the
    # advisory must notice it, or the run over-reports its own coverage
    "advisory_line_ref_only_vouch": ("`a.tsx:414`、`:474` 之外另有一处计数 6 处 命中，附近没有 blob", None),
    # a genuine port must keep its own bucket even when a filename appears nearby, or LINE_REF would swallow it
    "exempt_PORT_with_filename_nearby": ("backend 端口 8651 上 LISTENING，配置文件 cfg.py 里同名", "PORT"),
    "fire_run_id_without_coordinate": ("the wait was 62000 and no run id appears anywhere", None),
    # ---- r4d, re-scoped by r5: the receipt has to belong to THIS number, not to this block ----
    # Out of range, only the named class could save the line - and it no longer may, so the line burns.
    "fire_DIMENSION_receipt_out_of_range": ("留白 212px 与那条声明的 212px 等量" + FAR_RECEIPT,
                                            None),
    "fire_DISCIPLINE_ZERO_receipt_out_of_range": ("本块边界：权威线 0 次移动、0 处覆盖" + FAR_RECEIPT,
                                                  None),
    # units are free to type and a receipt is not: drop the receipt entirely and the sentence still burns
    "fire_DIMENSION_without_receipt": ("留白 212px 与那条声明的 212px 等量" + FILLER, None),
    "fire_DISCIPLINE_ZERO_without_receipt": ("本块边界：权威线 0 次移动" + FILLER, None),
    # Beside the reading, the named class is what exempts it - CLASS_ARMS below assert that at the
    # classifier level, where the coordinate window cannot be the reason.
    "exempt_DIMENSION_receipt_beside": ("留白 212px 与那条声明的 212px 等量 " + RECEIPT, "DIMENSION"),
    "exempt_DISCIPLINE_ZERO_receipt_beside": ("本块边界：权威线 0 次移动、0 处覆盖 " + RECEIPT,
                                              "DISCIPLINE_ZERO"),
    # a ZERO in front of a product noun is a finding, not a discipline declaration, receipt or none
    "fire_ZERO_on_a_product_noun": ("该格命中 0 次" + FAR_RECEIPT, None),
    # only the zeroes are exempt: the same discipline noun with a non-zero count must speak
    "fire_NONZERO_after_a_discipline_noun": ("权威线 0 次移动、12 处覆盖" + FAR_RECEIPT, None),
    # ---- r5 (ORD-0371): the four mis-verdicts the commander measured, each with its counter-example ----
    # `127.0.0.1:7892` came back from r4e as TWO bare numbers, so citing the proxy you measured meant
    # hanging a coordinate on each octet.
    "exempt_ADDRESS_PART_octet": ("本机代理指向 127.0.0.1 这个地址", "ADDRESS_PART"),
    "exempt_PORT_host_port": ("HTTPS_PROXY 指向 127.0.0.1:7892，端口上无进程", "PORT"),
    # the tightener's own risk: a 3-digit number must not be rescued by a status word that belongs to
    # somebody else, so the deprived arm has to stay red.
    "fire_HTTP_STATUS_word_not_adjacent": ("答话里有 HTTP 这个字，然后另起一句隔了十七个字符才写 419",
                                           None),
    # `tools/chain_self_heal.mjs:215-224` was refused while `backend/app/main.py:5242` passed: the
    # path:line grammar stopped at the suffixes someone had typed by hand.
    "exempt_MJS_path_line_coordinate": ("复现步骤落在 tools/chain_self_heal.mjs:215-224，共 3 处 命中",
                                        "LINE_REF"),
    # and the other direction: digits after a colon with no path in front of them are still a bare claim.
    "fire_number_after_fullwidth_colon": ("这一行的行号写成全角冒号：419 而没给路径", None),
    # the double-count repro from diagnose_r1.py: `1392 条` was two claims and two findings in r4e.
    "fire_single_number_single_finding": ("the ledger holds 1392 条 and nothing else", None),
    # ---- the declared widening, both directions: a name is not a reading, a spacing is not a licence ----
    "exempt_IDENTIFIER_bundled_in_a_name": ("`assets/index-BEEP22s_.js` 与 `assets/index-DpqSOpMP.css` 同代",
                                            "IDENTIFIER_PART"),
    "fire_unit_after_a_space": ("这一轮等了 22s，附近没有任何记录", None),
    # ---- the coordinate boundary, both directions (`\b` does not exist next to a Chinese character) ----
    "exempt_CJK_glued_blob_counts_as_a_coordinate": ("这 1392 条 的收据紧贴中文形状" + RECEIPT, None),
    "fire_hex_run_glued_to_letters_is_not_a_blob": ("这 1392 条 挂在一个字母串上 " + RECEIPT + "xy 不是坐标",
                                                    None),
    # ---- r5b: the classes r5's first pass refused, each with the direction that would launder ----
    "exempt_DIMENSION_decimal_reading_beside_receipt": ("内存只剩约 0.4 GB，读数件 " + RECEIPT,
                                                        "DIMENSION"),
    "fire_DIMENSION_decimal_reading_alone": ("内存只剩约 0.4 GB，这条附近没有件", None),
    "exempt_HTTP_STATUS_curl_no_response": ("六枚探针全是 code 000，没有一纸答复", "HTTP_STATUS"),
    "fire_three_digits_no_status_word": ("本轮另有 875，附近没有任何件", None),
    "exempt_IDENTIFIER_quoted_socket": ("`7897`：件 A 第 13 行原样", "IDENTIFIER_PART"),
    "fire_QUOTED_measure_word_still_a_claim": ("`875 个` 命中，附近没有任何件", None),
    "exempt_IDENTIFIER_process_id": ("netstat 给的 pid 35752 每轮都变", "IDENTIFIER_PART"),
    "exempt_PORT_domain_colon": ("直连 github.com:443 超时，全程没走代理", "PORT"),
    "exempt_LINE_REF_source_colon": ("红在 main.py:443 那一行，别的没量", "LINE_REF"),
    "exempt_PORT_word_after_unquoted_number": ("实测 7892 在听，这一行不是计数", "PORT"),
    "exempt_HTTP_STATUS_bare_code_from_the_set": ("隧道三枚路径全 401，渲染文字 0 句取到", "HTTP_STATUS"),
    "fire_READING_classified_but_receipt_far": ("内存只剩约 0.4 GB" + SEP + RECEIPT, None),
    "exempt_IDENTIFIER_order_number_leading_zero": ("这与 0376 那条要求同形，没有坐标", "IDENTIFIER_PART"),
    # r5d line-lock, both directions, with the coordinate deliberately BEYOND the 200-char window so
    # what is being tested is the line and not the window: same line -> vouched, next line -> refused
    "exempt_LINE_locked_by_a_coordinate_at_the_far_end": (
        "整套 9 failed、1367 passed " + FILLER + " 逐格红名与判决都记在件 " + "a" * 40, None),
    "fire_NEXT_LINE_coordinate_does_not_lock": (
        "整套 9 failed、1367 passed，逐格红名与判决都记在件另单。" + FAR_RECEIPT, None),
    # r5d: path / tile / array segments are not quantities, and a number with a count word beside a
    # slash-shaped neighbour still is one
    "exempt_TILE_segment_in_a_url": ("每条形状：`https://tile.openstreetmap.org/11/1668/889.png:0` 超时",
                                     "IDENTIFIER_PART"),
    "exempt_extent_array_in_brackets": ("命中可命中、框 `[0,145,522,44]`、URL 不变", "IDENTIFIER_PART"),
    "fire_count_word_next_to_a_slashed_token": ("同一轮 `x/y.png` 之后瓦片请求 1392 次，没有坐标", None),
    "fire_bare_number_with_no_slash_shape": ("本轮请求为 1668，没有坐标也没有行号", None),
    "exempt_HTTP_STATUS_quoted_code": ("上节件第 17 行与第 25 行都是 `401`，字节数 0", "HTTP_STATUS"),
    "fire_three_digits_not_in_the_set": ("这一格本轮命中 419，附近没有任何件", None),
    "fire_size_shorthand_without_a_receipt": ("那份 du 读数 409M，附近没有任何件", None),
    # ---- r5f (commander's three items, 2026-09-28 04:1x), every one asserted in BOTH directions ----
    # rule 2: a measure word or a runner's result word is a NAMED class, and it is exempt only when its
    # OWN line carries a coordinate.  Same sentence, coordinate on the line vs on the next line.
    "exempt_r5f_COUNT_attributed_on_its_own_line": (
        "整套 10 failed、1367 passed、5 条候选，逐格红名记在件 " + "e" * 40, "COUNT"),
    "fire_r5f_COUNT_out_of_both_channels_is_not_attributed": (
        "整套 10 failed、1367 passed、5 条候选，逐格红名记在件另单。" + SEP + "e" * 40, None),
    # rule 1: ONE coordinate attributes EVERY number on that line, whatever class each one is (a count,
    # a reading, a bare number).  Without this the line still burned its 1393 the way rel_0338 does.
    "exempt_r5f_one_coordinate_attributes_the_whole_line": (
        "875 个、2423 B、5.77s、1393 全挤在这一行，行尾一枚 blob " + "f" * 40, None),
    # and the same through the OTHER channel: a BARE number (class None, so `exempt_by_class` never
    # sees it) sitting past the 200-char window on a line whose only coordinate is at the far end.
    # Without this arm, `line_lock_removed` in the mutation harness passes - measured on the first
    # r5f run, because the conditional classes are now exempted by the line before the window is asked.
    "exempt_r5f_line_lock_reaches_a_bare_number_past_the_window": (
        "本轮裸数是 1393，" + FILLER + "，判决记在件 " + "b" * 40, None),
    # rule 2 must not become a hiding place: naming the class changes no verdict when the line has
    # nothing to attribute it (measured: this is the exact shape of rel_0338's ten burning lines).
    "fire_r5f_bare_artifact_path_is_not_a_coordinate": (
        "读数件：`D:/moodle/x/places_response.json` 2423 B、`discover.json` 56660 B。", None),
    "fire_english_result_words_are_counts": ("整套 9 failed、1367 passed，无坐标", None),
}

# Classifier-level arms: (name, text, exact token the ruler judged, class it must get).
# `None` means "this is a quantity and must carry a coordinate".  These fixtures deliberately hold a
# real receipt in the same sentence, which the 200-char window would accept on its own - asserting the
# CLASS is what tests the distinction, so a broken arm cannot pass by duplicating the window rule.
CLASS_ARMS = (
    ("dimension_beside_a_receipt_is_a_reading", "留白实测 212px，收据 " + RECEIPT, "212", "DIMENSION"),
    ("dimension_far_from_the_receipt_is_a_claim", "留白实测 212px" + SEP + RECEIPT, "212",
     "DIMENSION"),
    # a Chinese count word is not a physical unit: `1392 条` beside a receipt must not read as a reading.
    # r5f CHANGES this arm's expected class from None (undated "no class matched") to COUNT: the
    # commander's rule 2 asks for the name, and the verdict is unchanged - COUNT is conditional, so a
    # count with no coordinate on its line still burns.
    ("count_word_is_never_a_dimension", "该屏命中 1392 条 " + RECEIPT, "1392 条", "COUNT"),
    ("status_word_adjacent_is_a_status", "接口回 401 未授权，无正文", "401", "HTTP_STATUS"),
    ("status_word_21_chars_away_is_not", "答话里有 HTTP 这个字，然后另起一句隔了十七个字符才写 419",
     "419", None),
    ("octet_of_a_dotted_address", "本机代理指向 127.0.0.1 这个地址", "127", "ADDRESS_PART"),
    ("port_after_a_host", "HTTPS_PROXY 指向 127.0.0.1:7892 但无人监听", "7892", "PORT"),
    ("line_number_after_a_path", "步骤落在 tools/chain_self_heal.mjs:215-224", "215", "LINE_REF"),
    ("digits_after_a_fullwidth_colon", "行号写成全角冒号：419 而没给路径", "419", None),
    ("discipline_zero_beside_a_receipt", "权威线 0 次移动 " + RECEIPT, "0 次", "DISCIPLINE_ZERO"),
    # r5f: with a count/result word beside the number the class is COUNT, so these two now name
    # themselves instead of reporting "no class matched".  Both still BURN when no coordinate sits on
    # their own line - the two `*_on_a_line_with_no_coordinate` arms below are the price.
    ("product_noun_zero_beside_a_receipt", "该格命中 0 次 " + RECEIPT, "0 次", "COUNT"),
    ("nonzero_beside_a_discipline_noun", "权威线 0 次移动、12 处覆盖 " + RECEIPT, "12 处", "COUNT"),
    ("count_word_on_a_line_with_no_coordinate", "该格命中 0 次，附近没有任何件", "0 次", "COUNT"),
    # the regression my own first pass shipped, with the REAL shape taken from n2_0213.md:15
    # (measured: `1667/889（件第 12 到 17 行` - the number's own after-text is `（件…`, so a lstrip that
    # swallowed punctuation read the tile segment as a count of 889 things and turned 3 findings into 4).
    ("segment_before_a_punctuated_measure_word_is_not_a_count",
     "坐标 1668/888、1667/889（件第 12 到 17 行）", "889", "IDENTIFIER_PART"),
    ("a_measure_word_with_nothing_between_it_and_the_number_is_a_count",
     "本轮该格命中 875 个（件第 12 行）", "875 个", "COUNT"),
    ("result_word_on_a_line_with_no_coordinate", "整套 62 passed、10 failed，附近没有任何件",
     "62 passed", "COUNT"),
    ("discipline_zero_far_from_the_receipt", "权威线 0 次移动" + SEP + RECEIPT, "0 次",
     "DISCIPLINE_ZERO"),
    # the declared widening, at the classifier level: same three characters, only the left boundary moves
    ("digits_glued_inside_a_name", "`assets/index-BEEP22s_.js` 是代次名", "22s", "IDENTIFIER_PART"),
    ("the_same_tail_after_a_space_is_a_reading", "等了 22s 无记录", "22s", "DIMENSION"),
    # ---- r5b: the three classes r5's first pass still refused (commander's (a)(b) + `0.4 GB`) ----
    ("decimal_reading_beside_a_receipt", "内存只剩约 0.4 GB，读数件 " + RECEIPT, "0.4 GB", "DIMENSION"),
    ("decimal_reading_without_a_receipt", "内存只剩约 0.4 GB，这条附近没有件", "0.4 GB",
     "DIMENSION"),
    ("curl_no_response_code_beside_the_word", "六枚探针全是 code 000，没有一纸答复", "000", "HTTP_STATUS"),
    # the declared cost of that sentence: a count with no measure word, only a status word, now passes
    ("three_digits_beside_a_status_word_is_a_code", "本轮答复 875 未授权，无正文", "875", "HTTP_STATUS"),
    ("three_digits_without_a_status_word_is_a_claim", "本轮另有 875，附近没有任何件", "875", None),
    ("quoted_number_is_a_name", "`7897`：件 A 第 13 行原样", "7897", "IDENTIFIER_PART"),
    # r5f rule 2 flips these three arms' expected CLASS from None ("no class matched") to COUNT.  The
    # VERDICT is unchanged - each still fires, and the names say so - only the reason becomes true.
    ("quoted_count_word_is_still_a_claim", "`875 个` 命中，附近没有任何件", "875 个", "COUNT"),
    ("pid_before_the_number_is_an_id", "netstat 给的 pid 35752 每轮都变", "35752", "IDENTIFIER_PART"),
    ("pid_after_the_number_is_an_id", "监听口 7897 的 pid 35752 在", "35752", "IDENTIFIER_PART"),
    ("domain_colon_is_a_port", "直连 github.com:443 超时", "443", "PORT"),
    ("source_colon_is_still_a_line", "红在 main.py:443 那一行", "443", "LINE_REF"),
    ("port_word_after_an_unquoted_number", "实测 7892 在听，这一行不是计数", "7892", "PORT"),
    # r5b: the closed HTTP enumeration - what it eats, and the three shapes it must not eat
    ("closed_http_code_written_bare", "隧道三枚路径全 401，渲染文字 0 句取到", "401", "HTTP_STATUS"),
    # each of the three ways in which a number becomes a status code gets its OWN deprived fixture, so
    # no arm can be satisfied by a rule other than the one it names (the first mutation pass found two
    # arms that were green only because the closed set ate the token first)
    ("status_word_after_a_number_that_is_not_a_code", "接口回了 419 未授权，无正文", "419", "HTTP_STATUS"),
    ("curl_no_response_zero_written_bare", "六枚探针全是 000，一纸答复都没有", "000", "HTTP_STATUS"),
    # a status word IN FRONT of a number that HTTP does not define: only the before-rule can eat this
    ("status_word_before_a_number_that_is_not_a_code", "HTTP 138，别的什么都没写", "138", "HTTP_STATUS"),
    ("three_digits_that_are_not_a_code", "这一格本轮命中 419，附近没有任何件", "419", None),
    ("size_shorthand_is_a_reading", "那份 du 读数 409M，附近没有任何件", "409M", None),
    # r5c: a class assigned by shape, and the ticket-number shape the commander named
    ("order_number_written_with_a_leading_zero", "这与 0376 那条要求同形，没有坐标", "0376",
     "IDENTIFIER_PART"),
    ("leading_zero_with_a_count_word_is_a_claim", "命中 0376 处，附近没有任何件", "0376 处", "COUNT"),
    ("english_result_word_is_a_claim", "整套 9 failed、1367 passed，无坐标", "1367 passed", "COUNT"),
)

# The ORD-0371 requirement in one line: a number's verdict may not depend on which OTHER numbers the
# block happens to contain.  Each target is judged alone, after the distractor paragraph, and before
# it; all three placements must give the same class and the same finding/no-finding verdict.
# (class, expect_finding_when_alone) - both halves are compared, not just the class.
DETERMINISM_ARMS = (
    # r5f: the class is COUNT now; `exp_fired` stays True, which is the half that matters.
    ("bare_count", "这一屏的计数是 1392 条，附近没有任何收据", "1392 条", "COUNT", True),
    ("status_with_adjacent_word", "接口回 401 未授权，无正文", "401", "HTTP_STATUS", False),
)


def class_of(text, needle):
    """The class the ruler assigns to the first occurrence whose token is exactly `needle`.

    A token that is not judged at all returns NO_SUCH_OCCURRENCE, never None: if a fixture's number
    stopped matching the token grammar, an arm expecting "this is a claim" (None) would pass on the
    fact that the ruler saw nothing - which is how a ruler launders its own blind spot."""
    _, rows = occurrences(text)
    for row in rows:
        if row["token"] == needle:
            return row["class"]
    return "NO_SUCH_OCCURRENCE"


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
            if name in ("exempt_PORT", "exempt_PORT_host_port", "exempt_PORT_domain_colon",
                        "exempt_PORT_word_after_unquoted_number"):
                checks[name] = checks[name] and exempt.get("LINE_REF", 0) == 0
            if name in ("exempt_LINE_REF_source_colon",):
                checks[name] = checks[name] and exempt.get("PORT", 0) == 0
            # and a status code rescued by a unit-adjacent word must not be counted as a dimension reading
            if name == "exempt_ADDRESS_PART_octet":
                checks[name] = checks[name] and exempt.get("DIMENSION", 0) == 0
        else:
            checks[name] = bool(findings)
            if name == "fire_READING_classified_but_receipt_far":
                # the point of r5c: the ruler must say WHICH of the two reasons it refused
                checks[name] = bool(findings) and findings[0]["class_assigned_by_shape"] == "DIMENSION"                     and findings[0]["code_when_classified"] == "READING_CLASSIFIED_BUT_NO_COORDINATE_ON_THE_LINE"
    # ---- r5 (ORD-0371): the classifier itself, both directions, decoupled from the 200-char window ----
    for name, text, needle, expected in CLASS_ARMS:
        got = class_of(text, needle)
        checks["class_" + name] = got == expected
        rows.append({"sample": "class_" + name, "token": needle, "expected_class": expected,
                     "got_class": got})
    # the double-count the commander measured: one number was two claims and two findings in r4e
    _, dc_rows = occurrences("the ledger holds 1392 条 and nothing else")
    dc_claims, dc_findings, _ = scan("the ledger holds 1392 条 and nothing else")
    # a class assigned by SHAPE must not become an exemption by itself: these readings are now
    # classified DIMENSION / DISCIPLINE_ZERO and still have to burn, with a reason that says which of
    # the two cases the reader is looking at
    for probe_text, probe_needle in (("等了 22s 无记录", "22s"),
                                     ("内存只剩约 0.4 GB，这条附近没有件", "0.4 GB"),
                                     ("权威线 0 次移动" + SEP + RECEIPT, "0 次")):
        _, fnd, ex = scan(probe_text)
        hit = [f for f in fnd if f["matched"] == probe_needle]
        checks["claim_not_exempted_" + probe_needle] = (
            bool(hit) and hit[0]["class_assigned_by_shape"] in ("DIMENSION", "DISCIPLINE_ZERO", "COUNT")
            and hit[0]["code_when_classified"] == "READING_CLASSIFIED_BUT_NO_COORDINATE_ON_THE_LINE")
    # ---- r5e: one channel per literal, a named remedy, and one finding per (literal, line) ----
    uniform_src = "本机 `127.0.0.1:7892` 没人听；另一处裸写 7892 也一样。"
    _, u_rows = occurrences(uniform_src)
    per_literal = {}
    for r in u_rows:
        per_literal.setdefault(r["token"], set()).add(str(r["class"]))
    checks["r5e_one_literal_one_verdict"] = (per_literal.get("7892") == {"PORT"}
                                             and any(r.get("unified_from_line") for r in u_rows))
    # the direction that would make this a laundering machine: a CONDITIONAL class must not spread.
    # Same literal, same class, but the receipt sits on the OTHER line - exempt there, refused here.
    launder = ("权威线 0 次移动，读数件 " + RECEIPT + "\n\n" + FILLER + "\n\n"
               + "权威线 0 次移动，这一行没有任何件")
    _, l_rows = occurrences(launder)
    zero_rows = [r for r in l_rows if r["token"] == "0 次"]
    checks["r5e_conditional_class_uniform_exemption_per_line"] = (
        len(zero_rows) == 2 and {r["class"] for r in zero_rows} == {"DISCIPLINE_ZERO"}
        and sum(1 for r in zero_rows if r["coordinate"] is None) == 1)
    _, f_l, _ = scan(launder)
    checks["r5e_laundering_by_unify_is_refused"] = (len(f_l) == 1 and f_l[0]["line"] > 1)
    # remedy: every refusal must name how to make it green, and the name must match the shape
    _, f_count, _ = scan("本轮该格命中 875 个，这一行没有件")
    _, f_dim, _ = scan("内存只剩约 0.4 GB，这一行没有件")
    checks["r5e_remedy_names_the_write_for_a_count"] = (
        bool(f_count) and "40-hex" in f_count[0]["remedy"]
        and "<path>:<line>" in f_count[0]["remedy"]
        and "do not delete" in f_count[0]["remedy"])
    checks["r5e_remedy_for_a_reading_is_the_line_rule"] = (
        bool(f_dim) and "THIS line" in f_dim[0]["remedy"])
    checks["r5e_predicate_is_named_on_every_refusal"] = all(
        f.get("predicate", "").startswith("P") for f in (f_count + f_dim))
    # six repeats of one literal on one line: ONE finding, but the claim count stays honest
    six = "同一轮里 " + "、".join(["6 条"] * 6) + "，这一行没有任何件"
    c6, f6, _ = scan(six)
    checks["r5e_repeats_collapse_to_one_finding"] = (
        len(f6) == 1 and f6[0]["repeat_on_line"] == 6 and c6 == 6)
    checks["class_one_number_is_one_occurrence"] = len(dc_rows) == 1
    checks["r5_one_number_is_one_claim_and_one_finding"] = (
        dc_claims == 1 and len(dc_findings) == 1 and dc_findings[0]["matched"] == "1392 条")
    # ---- r5f: the three rules the commander ordered, each proved in both directions ----
    # the same line-ending independence, asserted in both directions inside the self-test
    lf = "整套 62 passed、10 failed，判决记在件 " + "a" * 40
    crlf = lf.replace("\n", "\r\n")
    _, f_lf, _ = scan(lf)
    _, f_crlf, _ = scan(crlf)
    checks["r5f_verdict_does_not_depend_on_the_authors_line_endings"] = (
        not f_lf and not f_crlf)
    base2 = "整套 62 passed、10 failed，判决记在件另单。"
    far_lf, far_crlf = base2 + SEP + "a" * 40, (base2 + SEP + "a" * 40).replace("\n", "\r\n")
    checks["r5f_unattributed_line_burns_the_same_way_under_crlf"] = (
        len(scan(far_lf)[1]) == len(scan(far_crlf)[1]) == 2)
    # rule 1 + counter-example B: one line, four numbers of four different shapes, one coordinate at
    # the far end of the line.  With it: silent.  Wipe ONLY the coordinate: every number must burn, and
    # the burn set must be exactly the numbers on that line (so line attribution cannot be a door left
    # open - it is paid for, in full, by one retrievable reference).
    r5f_line = "本轮 875 个、读数 2423 B、等了 5.77s、另有裸数 1393，逐格判决记在件 " + "c" * 40
    c_w, f_w, e_w = scan(r5f_line)
    wiped = r5f_line.replace(" " + "c" * 40, "")
    c_o, f_o, e_o = scan(wiped)
    checks["r5f_line_attributed_silence"] = not f_w and "COUNT" in e_w and "DIMENSION" in e_w
    checks["r5f_wiping_the_line_coordinate_reddens_every_number_on_it"] = (
        {f["matched"] for f in f_o} == {"875 个", "2423 B", "5.77s", "1393"}
        and len(f_o) == 4 and not f_w)
    checks["r5f_attribution_is_not_a_claim_count_inflation"] = c_w < c_o
    # rule 1's stated boundary: a coordinate attributes its OWN line in full.  Beyond the line the old
    # +-WINDOW radius still applies (measured: removing it reddened 15 of 22 backlog blocks and took
    # rel_0338 from 27 to 36, so r5f does not remove it) - this fixture puts the coordinate where
    # neither channel reaches, and both numbers must burn.
    below = scan("本轮 875 个、读数 2423 B。" + SEP + "c" * 40)
    checks["r5f_coordinate_out_of_both_channels_buys_nothing"] = len(below[1]) == 2
    near_far = scan("本轮 875 个、读数 2423 B。这段散文不含数字也不含坐标形状，只是断了行。\n" + "c" * 40)
    checks["r5f_window_still_reaches_a_neighbouring_line"] = (
        near_far[0] > 0 and not near_far[1])
    # rule 2: the result words are a NAMED class now, and naming does not exempt them without a line
    for needle, probe in (("62 passed", "整套 62 passed、10 failed，这一行没有件"),
                         ("5 条", "discover 返回 5 条候选，这一行没有件"),
                         ("4 个", "引用 /places 的就这 4 个文件，这一行没有件")):
        _, pf, _ = scan(probe)
        hits = [f for f in pf if f["matched"] == needle]
        checks["r5f_COUNT_named_not_hidden_" + needle] = (
            bool(hits) and hits[0]["class_assigned_by_shape"] == "COUNT"
            and hits[0]["predicate"] == PREDICATE["COUNT"]
            and hits[0]["code_when_classified"] == "READING_CLASSIFIED_BUT_NO_COORDINATE_ON_THE_LINE")
    # rule 3: a refusal names BOTH accepted coordinate forms and where to put them.  Written so that a
    # RULER MISSING the COUNT class fails this arm instead of raising - a self-test that crashes cannot
    # tell a mutation harness which rule was load-bearing (found by mutation_r5f_r1.py).
    count_hits = [f for f in f_o if f["class_assigned_by_shape"] == "COUNT"]
    named = count_hits[0] if count_hits else {"remedy": ""}
    checks["r5f_remedy_names_both_forms_and_the_line"] = (
        bool(count_hits) and "<path>:<line>" in named["remedy"] and "40-hex" in named["remedy"]
        and "THIS line" in named["remedy"]
        and "do not delete the number" in named["remedy"])
    # the limit r5f does NOT cross: a bare artifact path with no `:line` is still not a coordinate
    _, bare_f, bare_e = scan("读数件：`D:/moodle/x/places_response.json` 2423 B、`discover.json` 56660 B。")
    checks["r5f_bare_path_still_not_a_coordinate"] = (
        len(bare_f) == 2 and bare_e == {}
        and {f["class_assigned_by_shape"] for f in bare_f} == {"DIMENSION"}
        and all("<path>:<line>" in f["remedy"] for f in bare_f))
    # ---- r5 determinism: the same number, the same adjacency, three different blocks ----
    for name, target, needle, exp_class, exp_fired in DETERMINISM_ARMS:
        placements = {"alone": target,
                      "after_other_numbers": target + SEP + DISTRACTORS,
                      "before_other_numbers": DISTRACTORS + SEP + target}
        seen = {}
        for where, text in placements.items():
            _, pl_rows = occurrences(text)
            hits = [r["class"] for r in pl_rows if r["token"] == needle]
            _, pl_findings, _ = scan(text)
            fired = any(f["matched"] == needle for f in pl_findings)
            # exactly one judged occurrence of the needle, or the arm is measuring the wrong number
            seen[where] = ((hits[0] if len(hits) == 1 else "occurrences=%d" % len(hits)), fired)
        checks["determinism_" + name] = (seen["alone"] == seen["after_other_numbers"]
                                         == seen["before_other_numbers"]
                                         == (exp_class, exp_fired))
        rows.append({"sample": "determinism_" + name, "placements": seen})
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
