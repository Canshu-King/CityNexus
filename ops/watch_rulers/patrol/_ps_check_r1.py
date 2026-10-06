# -*- coding: utf-8 -*-
"""按 CommandLine 数我这一侧的值守进程（写文件跑，避免 -c 自匹配）。"""
import io
import subprocess

PAT = r"_sentinel_relay_r1|_sentinel_keepalive_r1|autumn_watch\.py|autumn_supervise_r1|cmdr_night_watch"
CMD = [
    "powershell", "-NoProfile", "-Command",
    "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '" + PAT + "' } "
    "| Select-Object ProcessId,CreationDate,CommandLine | ConvertTo-Csv -NoTypeInformation",
]

out = subprocess.run(CMD, capture_output=True).stdout.decode("utf-8", "replace")
rows = [l for l in out.split(chr(10)) if l.strip()]
say = lambda s: io.open(0, "w", encoding="utf-8").write(s) if False else print(s)

seen = []
for l in rows:
    # csv 三列：pid,创建时间,命令行
    parts = l.split('","')
    if len(parts) < 3:
        continue
    pid = parts[0].strip('"')
    created = parts[1]
    cl = parts[2]
    tag = "sentinel_relay" if "_sentinel_relay_r1" in cl else (
        "keepalive" if "_sentinel_keepalive_r1" in cl else (
            "autumn_watch" if "autumn_watch.py" in cl else (
                "autumn_supervise" if "autumn_supervise_r1" in cl else "cmdr_night_watch")))
    if "python" not in cl.lower():
        continue
    seen.append((tag, pid, created))

print("命中 %d 行（只算 python 起的）：" % len(seen))
for tag, pid, created in sorted(seen):
    print("   %-18s pid=%-7s 起于 %s" % (tag, pid, created))
names = sorted(set(x[0] for x in seen))
print("在世种类：%s" % ("、".join(names) if names else "无"))
