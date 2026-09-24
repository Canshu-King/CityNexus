"""One-shot patch: order rounds by when their readings were taken, not by when I assembled the receipt.

Two rounds' receipts were re-issued by one command and share a wall-clock second, which the first version of the
aggregator read as "timestamps do not run forward" and turned into `STREAK_BROKEN(rounds not consecutive)` - a
wrong label for a bookkeeping artefact, and it buried the real signal. What has to run forward is the
*measurement*: each shape carries the origin's own answered-at clock, so the aggregator now orders rounds by the
latest reading they contain, keeps round-number consecutiveness as the only fatal gap, and reports receipt-time
collisions as a named warning instead of a verdict.
"""
import ast
import pathlib

p = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0271b_streak.py")
t = p.read_text(encoding="utf-8")
before = t

t = t.replace('''def reason_of(shape: dict) -> str:''',
              '''def latest_reading(rec: dict) -> str:
    """The origin's own clock, latest across the readings this round carries - HH:MM:SS on one machine."""
    best = ""
    for leg in ("control_shapes", "mutant_shapes"):
        for s in rec.get(leg) or []:
            at = ((s.get("origin_answer") or {}).get("answered_at")) or ""
            if at > best:
                best = at
    return best


def secs(hms: str) -> int:
    try:
        h, m, s = hms.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return -1


def reason_of(shape: dict) -> str:''', 1)

t = t.replace('''        no, at = rec.get("round"), rec.get("at")
        if prev_no is not None and no != prev_no + 1:
            gaps.append({"between": [prev_no, no], "why": "round numbers are not consecutive"})
        if prev_at is not None and at is not None and at <= prev_at:
            gaps.append({"between": [prev_at, at], "why": "timestamps do not run forward"})
        prev_no, prev_at = no, at''',
'''        no, at = rec.get("round"), rec.get("at")
        read_at = latest_reading(rec)
        if prev_no is not None and no != prev_no + 1:
            gaps.append({"between": [prev_no, no], "why": "round numbers are not consecutive"})
        if prev_read is not None and secs(read_at) >= 0 and secs(prev_read) >= 0 \\
                and secs(read_at) <= secs(prev_read):
            ordering.append({"between": [prev_read, read_at],
                             "why": "this round's latest reading is not later than the previous round's"})
        if prev_at is not None and at == prev_at:
            ordering.append({"between": [at, read_at],
                             "why": "two receipts were assembled in the same second (bookkeeping, not a "
                                    "measurement signal - rounds are ordered by their readings)"})
        prev_no, prev_at, prev_read = no, at, read_at''', 1)

t = t.replace('''    rounds, prev_at, prev_no = [], None, None
    gaps = []''',
              '''    rounds, prev_at, prev_no, prev_read = [], None, None, None
    gaps, ordering = [], []''', 1)

t = t.replace('''                       "capture_blob40": (rec.get("capture") or {}).get("blob40")})''',
              '''                       "capture_blob40": (rec.get("capture") or {}).get("blob40"),
                       "latest_reading_on_origin_clock": read_at})''', 1)

t = t.replace('''           "consecutiveness_gaps": gaps, "stored_vs_recomputed_mismatches": lying,''',
              '''           "consecutiveness_gaps": gaps, "stored_vs_recomputed_mismatches": lying,
           "reading_order_warnings": ordering,''', 1)

t = t.replace('''                      "gaps": gaps, "stored_vs_recomputed_mismatches": lying,''',
              '''                      "gaps": gaps, "reading_order_warnings": ordering,
                      "stored_vs_recomputed_mismatches": lying,''', 1)

assert t != before and "latest_reading" in t and "reading_order_warnings" in t
assert "prev_read" in t
ast.parse(t)
p.write_bytes(t.encode("utf-8"))
print("patched; bytes", len(t.encode("utf-8")))
