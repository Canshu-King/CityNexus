"""Append ledger section 14.4 -- the remaining 28 sorted by cause, with the counts read off the run."""
import io
import subprocess
import sys

PATH = r"D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_GO_FROM_BLANK_REPORT.md"
PY = r"D:/moodle/CityNexus/.venv/Scripts/python.exe"
text = io.open(PATH, encoding="utf-8", newline="").read()
nl = "\r\n" if "\r\n" in text else "\n"
if "### 14.3" not in text:
    sys.exit("ABORT section 14.3 must be in the report before 14.4 follows it")
if "### 14.4" in text:
    sys.exit("ABORT section 14.4 already exists")

done = subprocess.run([PY, "-m", "pytest", "-q", "tests/test_r64_member_side_quest.py",
                       "--tb=line", "-p", "no:warnings"],
                      cwd=r"D:/moodle/_cmdr_rescue_v3_1022/backend", capture_output=True,
                      text=True, encoding="utf-8", errors="replace")
out = done.stdout
counts = {}
for label, needle in (("CHECK end_at > start_at", "CHECK constraint failed: end_at > start_at"),
                      ("CONFLICT RENDEZVOUS_TIME_PASSED", "LIVE_MOMENT_SCOUT_RENDEZVOUS_TIME_PASSED"),
                      ("time_state PAST", "'PAST' == 'AVAILABLE'"),
                      ("KeyError active_plan", "KeyError: 'active_plan'")):
    counts[label] = sum(1 for l in out.splitlines() if needle in l)
summary = [l for l in out.splitlines() if " failed" in l and "passed" in l]
total = summary[-1] if summary else "NO_SUMMARY rc=%d" % done.returncode
if sum(counts.values()) != 28:
    sys.exit("ABORT the classes add to %d, not 28: %s" % (sum(counts.values()), counts))

lines = [
    "",
    "### 14.4 剩下 28 枚按成因分类（分类数从同一条命令现读，四类相加正好 28）",
    "",
    "`pytest -q tests/test_r64_member_side_quest.py --tb=line -p no:warnings` 的末行：`%s`。按原因归类：" % total,
    "",
] + ["- %s：%d 枚" % (k, v) for k, v in counts.items()] + [
    "",
    "第一类最深：栈里的绑定参数是 `('2026-10-28T20:48:24.223560+00:00', '22222222-2222-4222-8222-222222222222')`",
    "—— 被写的是一枚已经过去的「现在」，而 journey id 是 demo 重置发的那枚固定 id。也就是说种子里那趟行程的",
    "`end_at` 与夹具此刻写进去的 `start_at` 谁该跟着谁，没有定过口径：墙钟一过，`CHECK end_at > start_at`",
    "就把臂拦在断言之前。第二类（4 枚 `LIVE_MOMENT_SCOUT_RENDEZVOUS_TIME_PASSED`）与第三类（1 枚 `'PAST'`）",
    "是同一件事的接口侧表现 —— 约定时刻已过，产品按规则拒绝，拒得对，是夹具的时间没跟着现在走。",
    "",
    "所以这 26 枚属刀三那族「过期断言」，不是鉴权、也不是产品缺陷；**但把它们改绿要定一条口径**：",
    "demo 种子的行程时刻应该由 `execution_clock.now()` 派生（跟着现在走），还是由夹具显式覆写。",
    "这一格我不自取 —— 它动的是 demo 重置的种子形状，会影响所有共用它的臂。",
    "",
    "剩下 2 枚是另一类：`KeyError: 'active_plan'`（夹具在响应里取一个现在不存在的键）。",
    "它到底是契约改名还是产品少发一个键，我没挖 —— 挖之前先记在这里，不当结论。",
    "",
]
io.open(PATH, "w", encoding="utf-8", newline="").write(text + nl.join(lines) + nl)
after = io.open(PATH, encoding="utf-8", newline="").read()
print("COUNTS", counts, "TOTAL", total)
print("BYTES_AFTER", len(after.encode("utf-8")), "SECTION_144", after.count("### 14.4"))
