import io
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
raw = io.open(r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", newline="").read()
crlf = raw.count("\r\n")
lf = raw.count("\n")
print("chars", len(raw), "| CRLF", crlf, "| LF total", lf, "| bare LF", lf - crlf)
for m in re.finditer(r"^#{2,3} (DELIVERIES|ORDERS|ACTIVE_WORKERS)[^\r\n]*", raw, re.M):
    print("ANCHOR:", repr(m.group(0)[:78]))
print("has '- id: ORD-0090':", bool(re.search(r"^- id: ORD-0090", raw, re.M)))
ids = re.findall(r"^- id: (ORD-\d{4})", raw, re.M)
print("board entries:", len(ids), "| unique:", len(set(ids)))
print("first ids:", ids[:6], "... last:", ids[-6:])
missing = [f"ORD-{n:04d}" for n in (90, 127, 126) if f"ORD-{n:04d}" not in set(ids)]
print("missing from board:", missing)
