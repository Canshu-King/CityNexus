# -*- coding: utf-8 -*-
"""查清每枚值守进程的父子关系与命令行（判重、判是谁起的）。"""
import io
import subprocess

PAT = r"_sentinel_relay_r1|_sentinel_keepalive_r1|autumn_watch\.py|autumn_supervise_r1"
Q = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like '*python*' -and "
     "$_.CommandLine -match '" + PAT + "' } | "
     "Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine | ConvertTo-Csv -NoTypeInformation")
out = subprocess.run(["powershell", "-NoProfile", "-Command", Q],
                     capture_output=True).stdout.decode("utf-8", "replace")
rows = []
for l in out.split(chr(10)):
    if not l.strip():
        continue
    p = l.split('","')
    if len(p) < 4:
        continue
    pid, ppid, created, cl = p[0].strip('"'), p[1], p[2], p[3]
    if pid == "ProcessId":          # csv 表头不是进程；曾经被算成 autumn_supervise 的一枚
        continue
    tag = ("sentinel" if "_sentinel_relay_r1" in cl else
           "keepalive" if "_sentinel_keepalive_r1" in cl else
           "autumn_watch" if "autumn_watch.py" in cl else "autumn_supervise")
    env = [x for x in ("SENTINEL_TOTAL", "SENTINEL_STOP", "AUTUMN") if x in cl]
    rows.append((tag, pid, ppid, created))

print("python 起的值守进程 %d 枚（父子关系）：" % len(rows))
byid = {r[1]: r for r in rows}
for tag, pid, ppid, created in sorted(rows, key=lambda x: x[3]):
    parent = byid.get(ppid)
    print("   %-17s pid=%-6s 父=%-6s(%s) 起于 %s" % (
        tag, pid, ppid, (parent[0] if parent else "非值守/已退"), created))

kinds = {}
for r in rows:
    kinds[r[0]] = kinds.get(r[0], 0) + 1
print("计数：" + u"、".join(u"%s=%d" % (k, v) for k, v in sorted(kinds.items())))
