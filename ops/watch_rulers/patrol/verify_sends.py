"""Did each outbound message actually reach the target conversation's transcript?

For every (session, marker) pair, search all of that session's JSONL files for a USER record containing the
marker (markers are chosen from text unique to this shift's sends - a path, a filename, or a block name),
then compare the stored message's last line against the 83-byte closing line byte-for-byte.

A 'NOT-FOUND' here means the send was accepted by the API but is not in the transcript yet - which is a
different fact from 'the lane has not answered me'.
"""
import glob
import hashlib
import io
import json
import os
import time

BASE = r"C:\Users\仓鼠王\.qoder\projects\D--moodle"
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
CLOSING = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read().decode("utf-8").strip()

CHECKS = [
    ("1d64acf5", "S4", "→ S4（会话 1d64acf5）"),
    ("e4f3490f", "道0370", "→ 道0370（会话 e4f3490f）"),
    ("a68b0631", "rel", "→ rel（会话 a68b0631）"),
    ("49fe0d7b", "N3", "→ N3（会话 49fe0d7b）"),
    ("4033270f", "道0383", "→ 道0383（会话 4033270f）"),
    ("8e5245f0", "道0369", "→ 道0369（会话 8e5245f0）"),
    ("bac10f40", "AI", "→ 车道 ai（会话 bac10f40）"),
]


def texts(p):
    with io.open(p, "r", encoding="utf-8", errors="replace") as f:
        for rec in f:
            rec = rec.strip()
            if not rec:
                continue
            try:
                d = json.loads(rec)
            except Exception:
                continue
            m = d.get("message") or {}
            if m.get("role") != "user":
                continue
            c = m.get("content")
            t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
                 if isinstance(c, list) else (c or ""))
            if t.strip():
                yield d.get("timestamp") or "", t


def main():
    now = time.time()
    print("closing %d B sha1=%s" % (len(CLOSING.encode("utf-8")),
                                    hashlib.sha1(CLOSING.encode("utf-8")).hexdigest()))
    # 只认今天 02:29+08（=18:29Z）之后的记录：昨夜与今晨也往同一批车道敲过门，按文本匹配会读到上一轮。
    SINCE = "2026-09-28T18:29"
    for id8, nm, marker in CHECKS:
        g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")))
        hit = None
        for p in g:
            for ts, t in texts(p):
                if marker in t and ts[:19] >= SINCE:
                    cand = (ts, t, os.path.basename(p))
                    # prefer the record that IS my send (ends with the closing line); a later compaction
                    # summary also quotes the marker, and judging the tail on that one would say "not delivered".
                    if hit is None or ((CLOSING in t) > (CLOSING in hit[1])) or (
                            (CLOSING in t) == (CLOSING in hit[1]) and ts > hit[0]):
                        hit = cand
        if not hit:
            older = 0
            for p in g:
                for ts, t in texts(p):
                    if marker in t:
                        older += 1
            print("  %-9s %-9s NOT-IN-TRANSCRIPT-SINCE-%s marker=%r  (同名 marker 在更早记录里出现 %d 次)"
                  % (nm, id8, SINCE[11:16], marker, older))
            continue
        ts, body, src = hit
        tail = body.strip().splitlines()[-1].strip()
        age = (now - time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - 8 * 3600) / 60.0
        print("  %-9s %-9s stored@%s age=%5.1fmin chars=%5d tail_exact=%s closing_anywhere=%s via=%s" % (
            nm, id8, ts[:19], age, len(body), tail == CLOSING, CLOSING in body, src[:14]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
