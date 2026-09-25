#!/usr/bin/env python3
"""ledger_state_board_r1.py - derive the current status of every ORD work order
mechanically from the shared agent-control ledger. Read-only.

Lane: S3-stateboard. Tool author: S3-stateboard.

HARD RULE: every emitted value is a literal token/substring lifted from the ledger
text itself. When nothing is found the value is the sentinel NOT_IN_LEDGER. The code
never invents a status, never defaults to "UNKNOWN", and never paraphrases prose.

CLI:
  python -X utf8 ledger_state_board_r1.py --ledger <local copy> --out <artifact.json>
  python -X utf8 ledger_state_board_r1.py --ledger <local copy> --selftest
Exit code is non-zero when --selftest fails (or when a normal run's self-test fails).
"""
import argparse
import datetime
import hashlib
import io
import json
import re
import sys

NOT = "NOT_IN_LEDGER"

# Self-reference guard: this board must never read its own documentation as data. Once a
# delivery of this tool is applied to the ledger, its prose lines literally contain strings
# like 'ORD-0032 ... REJECTED' and 'ORD-9999 -> NOT_IN_LEDGER'; those are DESCRIPTIONS of the
# ruler, not order verdicts. Any line carrying one of these markers is excluded from the board.
SELF_REF_MARKERS = [
    "ledger_state_board", "state_board", "state-board", "S3-stateboard",
    "状态板", "--selftest", "selftest", "self-test", "NOT_IN_LEDGER",
    "永真防档", "哨兵", "覆盖如实", "spot_check", "self_test",
]
_SELF_REF_RE = re.compile("|".join(re.escape(m) for m in SELF_REF_MARKERS), re.IGNORECASE)


def is_self_ref(line):
    return _SELF_REF_RE.search(line) is not None


# Order-lifecycle status words that actually appear in the ledger (reconnaissance-derived).
# Hyphen/underscore-connected ALL-CAPS runs are tokenised ATOMICALLY, so negated states such
# as "NOT-LANDED" and long forms such as "OPEN-FOR-CURRENT-TIP" are NOT misread as LANDED/OPEN.
# Measurement-arm verdicts (KILLED/PASS/FAIL/MET/SURVIVED/NOT_MEASURED/NOT_RUN) are deliberately
# excluded: they describe one arm, not the order.
ORDER_STATUS = {
    "CLOSED", "CLOSED-ON-GENERATION", "ACCEPTED", "ACCEPTED-CODE", "LANDED", "DELIVERED",
    "PARTIAL", "NOT_APPLICABLE", "BLOCKED", "REFUSED", "PARKED", "SUPERSEDED", "NOT_STARTED",
    "REJECTED", "IN_PROGRESS", "SHIPPED", "STALE",
}
# Words that name a blocker (used only to locate the verbatim blocking sentence).
BLOCK_CUES = ["阻塞", "卡在", "欠件", "仍欠", "欠", "待验", "待", "等 @", "等@", "未做", "未跑",
              "未开始", "暂缓", "按住", "不作数", "BLOCKED", "REFUSED", "PARKED", "SUPERSEDED"]

ORD_RE = re.compile(r"ORD-(\d{4})")
CAPS_RE = re.compile(r"[A-Z][A-Z0-9]*(?:[_-][A-Z0-9]+)*")
HEX40_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
HEX8_RE = re.compile(r"(?<![0-9a-f])[0-9a-f]{8}(?![0-9a-f])")
EV_RE = re.compile(r"evidence/[A-Za-z0-9._/\-]+")
FULL_DT_RE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(\+\d{2})?")
CMDR_RE = re.compile(r"CMDR-(\d{2})(\d{2})-(\d{2})(\d{2})")

# secret redaction for any free-text field we store (name kept, value dropped)
SECRET_RE = re.compile(
    r"([A-Za-z0-9_]*(?:KEY|SECRET|TOKEN|PASSWORD|PASSWD|APIKEY|ACCESS_KEY|CREDENTIAL)[A-Za-z0-9_]*)"
    r"\s*[:=]\s*([^\s,;`\"')]+)", re.IGNORECASE)


def redact(s):
    return SECRET_RE.sub(lambda m: m.group(1) + ":<redacted>", s)


def trunc(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    return s[:n] + "...(+%d)" % (len(s) - n)


def git_blob_sha1(path):
    data = io.open(path, "rb").read()
    h = hashlib.sha1()
    h.update(b"blob %d\x00" % len(data))
    h.update(data)
    return h.hexdigest()


def parse_block_time(header):
    """Return (tkey_tuple_or_None, as_of_raw_or_None). tkey is (Y,Mo,D,H,M) for ordering."""
    m = FULL_DT_RE.search(header)
    if m:
        y, mo, d, hh, mm, tz = m.groups()
        return (int(y), int(mo), int(d), int(hh), int(mm)), m.group(0)
    m = CMDR_RE.search(header)
    if m:
        mo, d, hh, mm = m.groups()
        return (2026, int(mo), int(d), int(hh), int(mm)), m.group(0)
    return None, None


def parse_owner_lane(header):
    """Lane identity from a block header: commander id, else the first 8-hex session id,
    optionally prefixed by a leading single-letter lane tag (B/D/E/F)."""
    h = header
    is_cmdr = ("### CMDR-" in h) or re.match(r"###\s+CMDR-\d", h) is not None
    if is_cmdr:
        m = HEX8_RE.search(h)
        return ("commander " + m.group(0)) if m else "commander"
    m = HEX8_RE.search(h)
    if not m:
        return NOT
    # a leading "### B <hex>" or "### D `hex`" letter tag, if present right at the start
    lead = re.match(r"###\s+([A-F])\s+`?[0-9a-f]{8}", h)
    if lead:
        return lead.group(1) + " " + m.group(0)
    return m.group(0)


def status_hits_in(line):
    out = []
    for m in CAPS_RE.finditer(line):
        if m.group(0) in ORDER_STATUS:
            out.append((m.start(), m.end(), m.group(0)))
    return out


def bind_status_on_line(line, ord_start, ord_end):
    """Bind an ORDER_STATUS token to THIS order occurrence on the same line.
    The ledger's grammar is 'ORD-x <connector> STATUS' (a status follows its order), so we bind
    ONLY to the nearest FOLLOWING status within a short window. A binding is refused when another
    order reference sits between this order and the status - either an explicit 'ORD-0xxx' or a
    bare 4-digit shorthand like '0302' - so a status that describes a DIFFERENT order mentioned
    in the same sentence is never mis-attributed (e.g. 'ORD-0312 ... blocks 0302 CLOSED' must not
    mark ORD-0312 CLOSED). No preceding-status fallback: 'STATUS ... ORD' is not this ledger's form."""
    s_hits = status_hits_in(line)
    o_spans = [(m.start(), m.end()) for m in ORD_RE.finditer(line)]
    bare = [(m.start(), m.end()) for m in re.finditer(r"(?<!\d)\d{4}(?!\d)", line)]
    FOLLOW_MAX = 30
    after = []
    for (ss, se, sw) in s_hits:
        if ord_end <= ss and (ss - ord_end) <= FOLLOW_MAX:
            between = o_spans + bare
            if not any(ord_end < t0 < ss for (t0, t1) in between):
                after.append((ss - ord_end, sw))
    if after:
        gap, w = min(after, key=lambda t: t[0])
        return w, gap
    return None


def pair_evidence_with_blobs(line):
    """For each evidence/ path on the line, attach the nearest 40-hex on the SAME line."""
    hexes = [(m.start(), m.group(0)) for m in HEX40_RE.finditer(line)]
    pairs = []
    for m in EV_RE.finditer(line):
        p_end = m.end()
        if hexes:
            near = min(hexes, key=lambda h: abs(h[0] - p_end))
            blob = near[1]
        else:
            blob = NOT
        pairs.append({"path": m.group(0), "blob": blob})
    return pairs


class Board:
    def __init__(self, lines):
        self.lines = lines
        self.blocks = self._split(lines)
        self.index = self._index()

    @staticmethod
    def _split(lines):
        hdr = [i for i, ln in enumerate(lines) if ln.startswith("### ")]
        blocks = []
        for n, s in enumerate(hdr):
            e = hdr[n + 1] if n + 1 < len(hdr) else len(lines)
            tkey, as_of = parse_block_time(lines[s])
            blocks.append({
                "idx": n, "start": s, "header": lines[s], "body": lines[s:e],
                "tkey": tkey, "as_of": as_of, "lane": parse_owner_lane(lines[s]),
            })
        return blocks

    def _recency(self, b):
        # sort(reverse=True) -> newest first: dated blocks outrank undated, then by tkey desc,
        # then by file position ascending (the ledger's active region is inserted newest-first).
        if b["tkey"] is not None:
            return (1, b["tkey"], -b["idx"])
        return (0, (0, 0, 0, 0, 0), -b["idx"])

    def _index(self):
        # per ORD id -> list of postings {block, line}
        # self-reference guard: a line that describes this board (contains a SELF_REF marker)
        # is meta-prose, not an order verdict -> it is excluded so the board never consumes its
        # own published text as data.
        idx = {}
        skipped = 0
        for b in self.blocks:
            for ln in b["body"]:
                if is_self_ref(ln):
                    skipped += 1
                    continue
                for oid in {m.group(0) for m in ORD_RE.finditer(ln)}:
                    idx.setdefault(oid, []).append({"b": b, "line": ln})
        self.self_ref_lines_skipped = skipped
        for oid in idx:
            idx[oid].sort(key=lambda p: self._recency(p["b"]), reverse=True)
        return idx

    def order_ids(self):
        return sorted(self.index.keys())

    def derive(self, oid):
        postings = self.index.get(oid, [])
        rec = {}
        if not postings:
            for k in ("latest_status", "owner_lane", "as_of", "generation", "blocking_phrase"):
                rec[k] = NOT
            rec["evidence_blobs"] = NOT
            rec["note"] = "no block mentions this order id"
            return rec

        latest_status = NOT
        status_src = NOT
        status_lane = NOT
        status_asof = NOT
        mention_head = postings[0]["b"]["header"]
        mention_lane = postings[0]["b"]["lane"]
        mention_asof = postings[0]["b"]["as_of"] or NOT
        generation = NOT
        generation_candidates = NOT
        gen_src = NOT
        gen_asof = NOT
        ev = NOT
        ev_src = NOT
        ev_asof = NOT
        blocking = NOT
        blk_src = NOT

        for p in postings:
            line = p["line"]
            # the posting only exists when this line mentions oid; bind/derive against THIS
            # order's own occurrences, never the first ORD on the line (which can be another order)
            oid_spans = [(m.start(), m.end()) for m in ORD_RE.finditer(line) if m.group(0) == oid]
            if not oid_spans:
                continue
            # status: first span of THIS order that binds a status on the same line
            if latest_status == NOT:
                for (s0, s1) in oid_spans:
                    hit = bind_status_on_line(line, s0, s1)
                    if hit:
                        latest_status = hit[0]
                        status_src = redact(trunc(line, 200))
                        status_lane = p["b"]["lane"]
                        status_asof = p["b"]["as_of"] or NOT
                        break
            # generation (newest line that mentions THIS order alongside a 40-hex)
            if generation == NOT:
                hx = [m.group(0) for m in HEX40_RE.finditer(line)]
                if hx:
                    generation = hx[-1]
                    generation_candidates = hx
                    gen_src = redact(trunc(line, 200))
                    gen_asof = p["b"]["as_of"] or NOT
            # evidence (newest line that mentions THIS order and an evidence/ path)
            if ev == NOT and EV_RE.search(line):
                pr = pair_evidence_with_blobs(line)
                if pr:
                    ev = pr
                    ev_src = redact(trunc(line, 200))
                    ev_asof = p["b"]["as_of"] or NOT
            # blocking phrase (newest line mentioning THIS order that carries a block cue)
            if blocking == NOT and any(cue in line for cue in BLOCK_CUES):
                blocking = redact(trunc(line, 200))
                blk_src = redact(trunc(line, 200))
            if latest_status != NOT and generation != NOT and ev != NOT and blocking != NOT:
                break

        rec["latest_status"] = latest_status
        rec["owner_lane"] = status_lane if status_lane != NOT else mention_lane
        rec["as_of"] = status_asof if status_asof != NOT else mention_asof
        rec["generation"] = generation
        rec["evidence_blobs"] = ev
        rec["blocking_phrase"] = blocking
        # transparency: exact provenance so any value is grep-verifiable against the ledger
        rec["_status_source_line"] = status_src
        rec["_generation_source_line"] = gen_src
        rec["_generation_candidates"] = generation_candidates
        rec["_evidence_source_line"] = ev_src
        rec["_blocking_source_line"] = blk_src
        rec["_latest_mention_as_of"] = mention_asof
        rec["_latest_mention_lane"] = mention_lane
        rec["_latest_mention_header"] = redact(trunc(mention_head, 140))
        return rec

    def build(self):
        ids = self.order_ids()
        return ids, {oid: self.derive(oid) for oid in ids}


def local_now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
def run_selftest(ledger_text):
    detail = {}
    ok = True

    lines0 = ledger_text.split("\n")
    board0 = Board(lines0)
    ids, per = board0.build()

    # ---- (a) verbatim match on a real order that HAS a status (validated on the RAW line) ----
    probe_a = next((o for o in ids if per[o]["latest_status"] != NOT
                    and per[o]["latest_status"] in ORDER_STATUS), None)
    if probe_a is None:
        detail["a"] = {"pass": False, "why": "no real order with a status token to test"}
        ok = False
    else:
        reported = per[probe_a]["latest_status"]
        # Do NOT compare the stored (redacted + truncated) field against the text - a >window
        # source line can never be a verbatim substring of itself. Instead re-find the RAW
        # posting line that binds this order to this token and assert THAT line is in the ledger.
        raw_line, raw_ok = None, False
        for p in board0.index.get(probe_a, []):
            ln = p["line"]
            if is_self_ref(ln):
                continue
            for m in ORD_RE.finditer(ln):
                if m.group(0) != probe_a:
                    continue
                hit = bind_status_on_line(ln, m.start(), m.end())
                if hit and hit[0] == reported:
                    raw_line, raw_ok = ln, (ln in ledger_text)
                    break
            if raw_ok:
                break
        again = Board(ledger_text.split("\n")).derive(probe_a)["latest_status"]
        passed_a = raw_ok and again == reported and reported in ORDER_STATUS
        detail["a"] = {"pass": passed_a, "order": probe_a, "reported_status": reported,
                       "found_raw_source_line": raw_line is not None,
                       "raw_source_line_verbatim_in_ledger": raw_ok,
                       "raw_line_length": (len(raw_line) if raw_line else 0),
                       "rederived_identical": again == reported}
        ok = ok and passed_a

    # ---- (b) time-derivation counterexample (not first-match / not position) ----
    probe_b = next((o for o in ids if per[o]["latest_status"] in ORDER_STATUS), None)
    if probe_b is None:
        detail["b"] = {"pass": False, "why": "no status order to mutate"}
        ok = False
    else:
        base_status = per[probe_b]["latest_status"]
        alt = next(s for s in ("ACCEPTED", "CLOSED", "PARTIAL", "BLOCKED", "LANDED", "PARKED")
                   if s != base_status)
        # NOTE: this synthetic header must NOT contain any SELF_REF marker, otherwise the
        # self-reference guard would (correctly) drop it and the counter-example would not test
        # what it is meant to test.
        synth = ("### SESSION=deadbeef @2099-01-01 00:00+08 —— "
                 "**%s = %s** (in-memory injected newest block)\n\n") % (probe_b, alt)
        text_b = synth + ledger_text
        per_b = Board(text_b.split("\n")).derive(probe_b)
        now_status = per_b["latest_status"]
        now_asof = per_b["as_of"]
        # control: without the injected block the tool still reports the real base status
        control = Board(ledger_text.split("\n")).derive(probe_b)["latest_status"]
        passed_b = (now_status == alt and base_status != alt
                    and "2099" in str(now_asof) and control == base_status)
        detail["b"] = {"pass": passed_b, "order": probe_b, "base_status": base_status,
                       "injected_status": alt, "reported_after_inject": now_status,
                       "reported_as_of": now_asof, "control_without_inject": control}
        ok = ok and passed_b

    # ---- (c) never a silent UNKNOWN; an order with no real verdict -> NOT_IN_LEDGER ----
    # The ghost id must be one that does NOT appear anywhere in the ledger. A hardcoded
    # 'ORD-9999' would collide with this board's own published prose (which mentions ORD-9999
    # in its description), so the absent id is chosen from the actual token set.
    present = {"ORD-" + m.group(1) for ln in lines0 for m in ORD_RE.finditer(ln)}
    ghost = None
    for i in range(9000, 9999):
        cand = "ORD-%04d" % i
        if cand not in present:
            ghost = cand
            break
    g = Board(lines0).derive(ghost)
    # scan the WHOLE board: no field may be "UNKNOWN"/"unknown"/empty; missing == NOT_IN_LEDGER
    bad_tokens = {"UNKNOWN", "unknown", "N/A", "na", "none", "", None}
    offenders = []
    for o, r in per.items():
        for k in ("latest_status", "owner_lane", "as_of", "generation", "blocking_phrase"):
            if r[k] in bad_tokens:
                offenders.append((o, k, r[k]))
    passed_c = (ghost is not None) and (g["latest_status"] == NOT) and (not offenders)
    detail["c"] = {"pass": passed_c, "ghost_order": ghost, "ghost_present_in_ledger": (ghost in present),
                   "ghost_result": g["latest_status"], "bad_sentinel_offenders": offenders[:5],
                   "offender_count": len(offenders)}
    ok = ok and passed_c

    # ---- invariant: per_order count == number of distinct orders (computed, never typed) ----
    detail["invariant"] = {"per_order_len": len(per), "orders_seen": len(ids),
                           "equal": len(per) == len(ids)}
    ok = ok and (len(per) == len(ids))

    detail["selftest_passed"] = bool(ok)
    return ok, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--out")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    text = io.open(a.ledger, "r", encoding="utf-8", newline="").read().replace("\r\n", "\n").replace("\r", "\n")

    if a.selftest:
        ok, detail = run_selftest(text)
        io.open("_selftest_detail.json", "w", encoding="utf-8").write(
            json.dumps(detail, ensure_ascii=False, indent=1))
        # ASCII-only stdout summary (console is GBK)
        print("SELFTEST", "PASS" if ok else "FAIL")
        for k in ("a", "b", "c", "invariant"):
            v = detail.get(k, {})
            print("  ", k, v.get("pass") if isinstance(v, dict) else v)
        print("   selftest_passed", detail.get("selftest_passed"))
        return 0 if ok else 1

    board = Board(text.split("\n"))
    ids, per = board.build()
    ok, detail = run_selftest(text)
    blob = git_blob_sha1(a.ledger)
    # three orders to hand to the commander for a grep spot-check: prefer ORD-03xx whose
    # status is carried directly in a block HEADER line ('### ... ORD-x = STATUS'), because
    # that is the single line a grep of 'ORD-x' will surface.
    def has_status(o):
        return per[o]["latest_status"] in ORDER_STATUS
    header_carried = [o for o in per if o >= "ORD-0300" and has_status(o)
                      and per[o]["_status_source_line"].startswith("### ")]
    any_status = [o for o in per if o >= "ORD-0300" and has_status(o)]
    seen = []
    for o in header_carried + any_status:
        if o not in seen:
            seen.append(o)
    spot = seen[:3]
    # honesty: count active orders whose status the ledger states only in Chinese verbs (they
    # carry a block but no CAPS order-status token bound to their own id) -> latest_status NOT.
    o3xx = [o for o in per if o >= "ORD-0300"]
    o3xx_not = [o for o in o3xx if per[o]["latest_status"] == NOT]
    art = {
        "tool": "ledger_state_board_r2.py",
        "supersedes": "ledger_state_board_r1.py",
        "lane": "S3-stateboard",
        "ledger_blob": blob,
        "at_local": local_now_iso(),
        "blocks_scanned": len(board.blocks),
        "orders_seen": len(per),
        "per_order": per,
        "selftest_passed": bool(ok),
        "selftest_detail": detail,
        "spot_check_orders": [
            {"order": o, "latest_status": per[o]["latest_status"], "as_of": per[o]["as_of"],
             "owner_lane": per[o]["owner_lane"],
             "grep": "grep '%s' -> the reported status word appears on the SAME line" % o,
             "source_line": per[o]["_status_source_line"]} for o in spot],
        "coverage_note": {
            "orders_with_latest_status": sum(1 for o in per if has_status(o)),
            "orders_without": sum(1 for o in per if per[o]["latest_status"] == NOT),
            "ORD-03xx_total": len(o3xx),
            "ORD-03xx_without_status": len(o3xx_not),
            "self_ref_lines_skipped": board.self_ref_lines_skipped,
            "why_not_ledger": ("many active orders state their result only in Chinese verbs "
                               "(交付/落地/勘误/在飞/已部署/等 verifier), which are NOT part of the "
                               "recognised CAPS order-status vocabulary; reporting NOT_IN_LEDGER for "
                               "those is the honest reading of the ledger, not a miss. The tool never "
                               "invents a status and never emits 'UNKNOWN'."),
        },
        "method": {
            "self_reference_guard": ("a line describing THIS board (containing any of "
                                     "ledger_state_board / state-board / 状态板 / selftest / "
                                     "NOT_IN_LEDGER / S3-stateboard / 覆盖如实 / spot_check ...) is "
                                     "treated as meta-prose, not data, and is excluded from every "
                                     "field's derivation. This fixes the r1 defect where, after r1's "
                                     "own delivery block was applied to the ledger, the board read "
                                     "'ORD-0032 ... REJECTED' and 'ORD-9999 -> NOT_IN_LEDGER' out of "
                                     "its own documentation."),
            "block_split": "a block = a line starting with '### ' up to the next such line",
            "recency_rule": ("the latest block for an order is chosen by the timestamp parsed from "
                             "the header (full 'YYYY-MM-DD HH:MM' or 'CMDR-MMDD-HHMM'); blocks with no "
                             "parseable full date are ranked after dated ones (recency is not asserted "
                             "when the ledger does not state it), ties broken by file position with "
                             "lower index treated as newer. File position alone is NOT used because the "
                             "ledger is inserted per-author, not strictly per-time."),
            "status_rule": ("latest_status = the ORDER_STATUS token bound to THIS order's own occurrence "
                            "ON THE SAME LINE in the newest block that carries such a binding. Binding is "
                            "following-only within 30 chars and is refused when another order reference "
                            "(an ORD-0xxx or a bare 4-digit shorthand like 0302) sits between the order "
                            "and the status. Hyphenated runs are atomic so 'NOT-LANDED'/'OPEN-FOR-CURRENT-TIP' "
                            "do not match LANDED/OPEN."),
            "order_status_vocabulary": sorted(ORDER_STATUS),
            "excluded_measurement_words": ["KILLED", "PASS", "FAIL", "MET", "SURVIVED",
                                            "NOT_MEASURED", "NOT_RUN"],
            "missing_value_sentinel": NOT,
            "secret_handling": ("free-text fields are run through redact(); a KEY/SECRET/TOKEN/... "
                                "assignment keeps the field NAME and replaces the VALUE with <redacted>"),
        },
        "recon": {
            "note": "reconnaissance performed before any conclusion; raw numbers measured from this ledger copy",
            "blocks_total": len(board.blocks),
            "distinct_orders": len(ids),
            "order_id_min": ids[0] if ids else None,
            "order_id_max": ids[-1] if ids else None,
        },
    }
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="\n").write(
            json.dumps(art, ensure_ascii=False, indent=1))
        print("WROTE", a.out, "orders", len(per), "blocks", len(board.blocks),
              "selftest", "PASS" if ok else "FAIL", "blob", blob)
    else:
        print(json.dumps({k: v for k, v in art.items() if k != "per_order"}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
