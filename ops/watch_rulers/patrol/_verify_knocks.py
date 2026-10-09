"""Read back the four lane knocks from their own session logs.

For each target: find the user record whose text starts with the knock's headline, then assert the LAST line of
that stored message equals the 83-byte closing line byte-for-byte. A send that was accepted but truncated or
mangled in storage is reported as NOT-DELIVERED - which is a different fact from "the lane hasn't answered yet".
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
KNOCKS = {
    "3b65af59": "map", "1d64acf5": "S4", "904a042d": "Q", "e4f3490f": "道0370",
}
targets = []
kdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knock")
for f in sorted(glob.glob(os.path.join(kdir, "*.txt"))):
    id8 = os.path.basename(f)[:8]
    if id8 in KNOCKS:
        targets.append((id8, KNOCKS[id8], f, io.open(f, encoding="utf-8").read()))

print("closing line: %d B sha1=%s" % (len(CLOSING.encode("utf-8")),
                                      hashlib.sha1(CLOSING.encode("utf-8")).hexdigest()))
now = time.time()
for id8, nm, path, txt in targets:
    g = sorted(glob.glob(os.path.join(BASE, id8 + "*.jsonl")))
    if not g:
        print("  %-9s %-6s NO LOG FILE for %s" % (nm, id8, id8))
        continue
    found = None
    user_msgs = 0
    src = None
    for p in g:
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
                if not t.strip() or "[Request interrupted" in t:
                    continue
                user_msgs += 1
                head = txt.splitlines()[0][:40]
                if head and head in t:
                    found = (d.get("timestamp"), t)
                    src = os.path.basename(p)
    if not found:
        # second channel: any user turn in the last 8 minutes that carries this lane's headline marker
        marker = "→ %s（会话 %s）" % (nm, id8)
        for p in g:
            with io.open(p, "r", encoding="utf-8", errors="replace") as f:
                for rec in f:
                    if marker not in rec:
                        continue
                    try:
                        d = json.loads(rec.strip())
                    except Exception:
                        continue
                    m = d.get("message") or {}
                    if m.get("role") != "user":
                        continue
                    c = m.get("content")
                    t = (" ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("text"))
                         if isinstance(c, list) else (c or ""))
                    if t.strip():
                        found = (d.get("timestamp"), t)
                        src = os.path.basename(p) + "(marker)"
                        break
            if found:
                break
    if not found:
        print("  %-9s %-9s NOT-FOUND in log (%d user msgs; files=%s; newest mtime %s)" % (
            nm, id8, user_msgs, [os.path.basename(x)[:8] for x in g],
            time.strftime("%H:%M:%S", time.localtime(max(os.path.getmtime(x) for x in g)))))
        continue
    ts, body = found
    tail = body.strip().splitlines()[-1].strip()
    ok = (tail == CLOSING)
    age = (now - time.mktime(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S")) - 8 * 3600) / 60.0
    print("  %-9s %-9s stored@%s age=%.1fmin  body=%d chars  tail_exact=%s via=%s (sha1 %s vs %s)" % (
        nm, id8, ts[:19], age, len(body), ok, src,
        hashlib.sha1(tail.encode("utf-8")).hexdigest()[:10],
        hashlib.sha1(CLOSING.encode("utf-8")).hexdigest()[:10]))
