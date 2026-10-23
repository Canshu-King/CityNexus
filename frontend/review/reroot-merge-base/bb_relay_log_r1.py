"""Land the BB relay's own broadcast history into a reading file.

The block filed at 03:19 scoped "the newest round that still prescribes this" to the ledger copy of
the relay; the durable bus log shows the broadcast leg kept going after the ledger leg stopped.
This writes the timestamps out so the erratum has an addressable reading instead of a recollection.
"""

import io
import json
import time

PRESCRIPTION = "把现尖 merge 进你自己的 review 枝"
OUT_TXT = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot/bb_relay_broadcast_log.txt"
OUT_JSON = "D:/moodle/_qoder_e766b154_ord0472_20260930/receipts_reroot/bb_relay_broadcast_r1.json"

rows = []
for l in io.open("D:/moodle/agent_bus/bus.jsonl", encoding="utf-8", errors="replace"):
    l = l.strip()
    if not l:
        continue
    try:
        d = json.loads(l)
    except Exception:
        continue
    body = d.get("body") or ""
    if PRESCRIPTION in body:
        rows.append({"ts": d.get("ts", 0), "topic": d.get("topic", ""),
                     "from": d.get("from", ""), "to": d.get("to", "")})
rows.sort(key=lambda r: r["ts"])

# and when the ledger's own copy of the relay last carried it
ledger = io.open("D:/moodle/CITYNEXUS_AGENT_CONTROL.md", encoding="utf-8", errors="replace").read().split("\n")
led_rows = []
for i, l in enumerate(ledger):
    if PRESCRIPTION in l:
        head = ""
        for j in range(i, max(i - 40, -1), -1):
            if ledger[j].startswith("### "):
                head = ledger[j][4:44]
                break
        led_rows.append({"line": i + 1, "head": head})

fh = io.open(OUT_TXT, "w", encoding="utf-8", errors="replace")
fh.write("BB 通播腿仍带这条药方的时刻（取自本机耐久日志 bus.jsonl，现读）\n")
for r in rows:
    fh.write("%s | %s | from %s | to %s\n"
             % (time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"])), r["topic"][:46],
                r["from"], r["to"]))
fh.write("通播合计 %d 封｜最早 %s｜最近 %s\n"
         % (len(rows),
            time.strftime("%Y-%m-%d %H:%M", time.localtime(rows[0]["ts"])) if rows else "无",
            time.strftime("%Y-%m-%d %H:%M", time.localtime(rows[-1]["ts"])) if rows else "无"))
fh.write("账本副本腿仍带这句话的块（行号现读）\n")
for r in led_rows:
    fh.write("账本第 %d 行 | %s\n" % (r["line"], r["head"]))
fh.write("账本副本合计 %d 处｜最新一处的块头见上表首行以下最后一行\n" % len(led_rows))
fh.close()

io.open(OUT_JSON, "w", encoding="utf-8").write(json.dumps(
    {"bb_broadcast_count": len(rows),
     "bb_first": time.strftime("%Y-%m-%d %H:%M", time.localtime(rows[0]["ts"])) if rows else None,
     "bb_last": time.strftime("%Y-%m-%d %H:%M", time.localtime(rows[-1]["ts"])) if rows else None,
     "ledger_copy_count": len(led_rows),
     "ledger_copy_latest_line": led_rows[-1]["line"] if led_rows else None,
     "rows": rows}, ensure_ascii=False, indent=1))

print("bb_broadcast_count", len(rows),
      "first", time.strftime("%m-%d %H:%M", time.localtime(rows[0]["ts"])) if rows else "-",
      "last", time.strftime("%m-%d %H:%M", time.localtime(rows[-1]["ts"])) if rows else "-")
print("ledger_copy_count", len(led_rows), "latest at line", led_rows[-1]["line"] if led_rows else "-")
