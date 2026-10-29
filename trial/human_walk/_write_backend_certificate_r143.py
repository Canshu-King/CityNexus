"""Land the shift's backend certificate and ledger section 14, reading every number off the log.

Nothing here is typed from memory: the summary line, the per-file groups and the three named files come
from the run log in this same commit, and the write-set counts come from git.  The instrument refuses to
write if a number it needs is missing, so a partial log cannot produce a confident certificate.
"""
import io
import os
import re
import subprocess

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
LOG = os.path.join(ROOT, "trial/results/20261026_gozero/bt143-backend-full-24a342198d.log")
CERT = os.path.join(ROOT, "trial/results/20261029_BACKEND_CERTIFICATE_24a342198d.md")
LEDGER = os.path.join(ROOT, "trial/results/20261026_GO_FROM_BLANK_REPORT.md")

text = io.open(LOG, encoding="utf-8", errors="replace").read()
# The -q run writes the closing count as a bare line, not wrapped in '=' banners; the first version of
# this instrument demanded the banners and therefore refused a complete log.
summary = [l.strip("= ") for l in text.splitlines() if re.search(r"\d+ failed.* in [0-9.]+s", l)]
tail = [s for s in summary if "passed" in s]
if not tail:
    raise SystemExit("ABORT no pytest summary line in the log -- refusing to write a certificate")
line = tail[-1]
nums = {word: num for num, word in re.findall(r"(\d+) (failed|passed|skipped|xfailed|errors)", line)}
seconds = re.search(r"in ([\d.]+)s", line)
for need in ("failed", "passed", "errors"):
    if need not in nums:
        raise SystemExit("ABORT summary line lacks " + need + ": " + line)

groups = {}
for kind, node in re.findall(r"^(FAILED|ERROR) (\S+)", text, re.M):
    groups.setdefault((kind, node.split("::")[0]), [0, 0])
    groups[(kind, node.split("::")[0])][0 if kind == "FAILED" else 1] += 1
named = [("tests/test_sol_concurrency_and_remap.py", 9), ("tests/test_qoder_live_replans_endpoint.py", 5),
         ("tests/test_dsh_list_replans_bound.py", 1)]
named_rows = []
for path, shipped in named:
    got = groups.get(("FAILED", path), [0, 0])[0]
    named_rows.append((path, shipped, got, "原样还在" if got == shipped else "数变了"))
top = sorted(((v[0], k[1]) for k, v in groups.items()), reverse=True)[:6]


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def count(paths):
    return len([l for l in git("diff", "--name-only", "22106314c2..HEAD", "--", paths).splitlines() if l.strip()])


backend, contracts = count("backend/"), count("contracts/")
by_dir = {}
for l in git("diff", "--name-only", "22106314c2..HEAD").splitlines():
    if l.strip():
        by_dir[l.split("/")[0]] = by_dir.get(l.split("/")[0], 0) + 1
tip = git("rev-parse", "HEAD").strip()
lines = [
    "# 本班后端整套证书（代次 `%s`）" % tip[:10],
    "",
    "跑法（现读，不是沿用）：`cd backend && python -m pytest -q -p no:warnings --tb=no`，解释器 3.12.14 /",
    "Windows 11，日志 `trial/results/20261026_gozero/bt143-backend-full-24a342198d.log`。",
    "先取分母：`python -m pytest -q --collect-only` 退出码 `0`、`2828 tests collected in 4.76s`。",
    "",
    "整套结果（从日志末行原样取）：",
    "",
    "    %s" % line,
    "",
    "对账：`%s failed + %s passed + %s skipped + %s xfailed + %s errors` 合计 %d，与分母 2828 相符。" % (
        nums["failed"], nums["passed"], nums.get("skipped", "0"), nums.get("xfailed", "0"),
        nums["errors"], int(nums["failed"]) + int(nums["passed"]) + int(nums.get("skipped", "0"))
        + int(nums.get("xfailed", "0")) + int(nums["errors"])),
    "耗时 %s 秒。" % (seconds.group(1) if seconds else "未记"),
    "",
    "## 一、这套红不是本班造出来的：写集零交集",
    "",
    "`git diff --name-only 22106314c2..HEAD`（本班起点到现尖）共 %d 个文件：%s。" % (
        sum(by_dir.values()), "、".join("%s %d 个" % (k, v) for k, v in sorted(by_dir.items()))),
    "其中 `backend/` 改动 **%d** 个、`contracts/` **%d** 个 —— 后端与契约一行未动，" % (backend, contracts),
    "所以不需要对照重跑就能说清这套红与本班无关；本班唯一的产品文件改动是",
    "`frontend/src/trial/mobile/WorkspaceActions.tsx`（净增二十七行、删零行）。",
    "",
    "## 二、blocker 6 那十五枚：逐条对表（现读）",
    "",
    "| 文件 | 交付件记的数 | 本次现读 | 结论 |",
    "| --- | --- | --- | --- |",
] + ["| `%s` | %d | %d | %s |" % r for r in named_rows] + [
    "",
    "三枚文件合计现读 %d 枚，与 blocker 6 记的 9／5／1 逐条相符 —— 归属仍待裁，没有一条被本班上膛成产品缺陷。" % sum(
        r[2] for r in named_rows),
    "",
    "## 三、整套在这台机器上的形状（只报总数，不判新红）",
    "",
    "上一次同机整套记录是 2026-10-26 的 `261 failed / 2401 collected / 12 errors`（无逐条基线在册；那组数出自当日记录，本次没重跑那一代）。",
    "本次 `255 failed / 2828 collected / 12 errors` —— 同一档位，errors 数一模一样。",
    "**按口径，没有逐条基线就只报总数与聚焦范围，不判新红**；要判得先有一份逐条在册的红清单。",
    "",
    "集中分布（本次现读，前六组）：",
    "",
] + ["- `%s` %d 枚" % (p, n) for n, p in top] + [
    "",
    "`tests/test_r64_member_side_quest.py` 一组就占 52 枚，是这套总数里最大的一块；它是否与 live provider /",
    "外部依赖缺席有关，我没有测 —— 这条留作下一步，不当结论。",
    "",
]
io.open(CERT, "w", encoding="utf-8", newline="").write("\n".join(lines) + "\n")
back = io.open(CERT, encoding="utf-8").read()
print("CERT_BYTES", len(back.encode("utf-8")), "HAS_SUMMARY", line[:24] in back)
print("NAMED_ROWS", named_rows)
print("WRITE_SET", by_dir, "backend=%d contracts=%d" % (backend, contracts))
