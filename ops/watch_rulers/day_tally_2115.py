"""Count what the commander's day actually looks like, using only numbers greppable in the ledger + git."""
import io
import re
import subprocess
from collections import Counter

LEDGER = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
REPO = r"D:\moodle\_qoder_integration_20260919"

t = io.open(LEDGER, encoding="utf-8", newline="").read()
print("ledger bytes:", len(t.encode("utf-8")), "lines:", t.count("\n"))

ids = re.findall(r"^- id: (ORD-\d+)", t, re.M)
print("board entries (ORD ids):", len(ids), "unique:", len(set(ids)))

st = re.findall(r"^  status: (\S[^\n]*)", t, re.M)
kinds = Counter()
for s in st:
    m = re.match(r"([A-Z\-]+(?:-[A-Z]+)*)", s.strip())
    if m:
        kinds[m.group(1).split("@")[0]] += 1
print("status kinds:", dict(kinds))
print("dispatched by commander:", sum(1 for s in st if "DISPATCHED" in s and "494abfd7" in s))
print("accepted by commander:", sum(1 for s in st if "ACCEPT" in s and "494abfd7" in s))
print("closed/void by commander:", sum(1 for s in st if re.search(r"CLOSED|VOID|SUPERSEDED|PARK", s) and "494abfd7" in s))

# per-hour activity of the ledger text (timestamps written by all lanes)
hours = Counter(re.findall(r"2026-09-21T(\d\d):", t))
print("2026-09-21 timestamps by hour:", dict(sorted(hours.items())))
cn = Counter(re.findall(r"2026-09-21 (\d\d):", t))
print("plus '2026-09-21 HH:' style:", dict(sorted(cn.items())))

authors = Counter(re.findall(r"#### \(?(?:SESSION=)?([0-9a-f]{8}) ", t))
print("delivery blocks by session:", dict(authors.most_common()))
print("total '####' headers:", t.count("\n#### "))
print("total '### ' headers:", t.count("\n### "))

# commits today on the authoritative lineage
out = subprocess.run(
    ["git", "-C", REPO, "log", "--since=2026-09-21 00:00", "--format=%h|%ad|%s",
     "--date=format:%H:%M", "--all"],
    capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip().splitlines()
print("commits since 00:00 today (all refs):", len(out))
byh = Counter(l.split("|")[1][:2] for l in out)
print("  by hour:", dict(sorted(byh.items())))
mine = [l for l in out if any(k in l for k in ("commander", "ORD-0", "gate", "ledger"))]
print("  message mentions ORD/commander/ledger:", len(mine))
print("  first:", out[-1] if out else "-")
print("  last :", out[0] if out else "-")
