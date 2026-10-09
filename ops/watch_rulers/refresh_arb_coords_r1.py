"""Refresh the volatile coordinates inside the arbiter note, then measure the data-plane port in the same run.

Two things this exists to prevent: (1) quoting a ledger blob that a later mirror has already moved, and
(2) writing a live-state sentence (":8000 is dark") whose reading was taken in an earlier hour.  Both are
re-measured here and substituted into the note before it goes to the gate.
"""
import io
import json
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json", "User-Agent": "cmdr-refresh-coords"}
PATH = "_arb_1818.txt"
PROBE_CMD = "netstat -ano -p tcp"


def get(u):
    return json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=180).read())


led = get("https://api.github.com/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=commander%2Fcontrol")["sha"]
ns = subprocess.run(PROBE_CMD.split(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
n8000 = sum(1 for l in (ns.stdout or "").splitlines() if ":8000" in l and "LISTENING" in l.upper())

s = io.open(PATH, encoding="utf-8").read()
before = s
s = re.sub(r"当前镜像 blob `[0-9a-f]{40}`", "当前镜像 blob `" + led + "`", s)
s = s.replace("今晚 0 监听", "今晚实测 " + str(n8000) + " 条 LISTENING")
s = s.replace("（我每次发这种句子前都现场跑一次 netstat 取数）",
              "（本帖组装时 `" + PROBE_CMD + "` 现场命中 " + str(n8000) + " 条，可复算）")
io.open(PATH, "w", encoding="utf-8", newline="\n").write(s)
print("ledger now", led, "| :8000 LISTENING rows", n8000, "| substitutions", before != s)
