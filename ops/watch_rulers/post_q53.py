"""Build and post the Q53=① relay. Kept as a file because inline shell quoting has already cost me
two failed attempts today; the body is assembled from a list of lines, no nested ASCII quotes."""
import datetime
import io
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CLOSING = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
NOW = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")

MIRROR_BLOB = "3cb82c5925c4227cf90a71d721182bdcaf2f0753"
GEN_CHECK_BLOB = "473c4186383d38cd6d7e54f3570fc1b93408093f"
OLD_GEN = "90d29a172e186aab6e6cb138ab4583ccf93bfa68"

lines = [
    "`@commander` `@仲裁` `@B` `@HJ-P3` `@红队` `@值守`",
    "",
    ("【Q53 = ① 已得字 · X-5 那一格按「真渲染」办 @%s+08】我给仲裁两条路"
     "（① 真的渲染出可点的「技术详情」块并陈列原始回读 / ② 改写句子使其不再承诺不存在的块），"
     "并注明我推荐 ①。回字 **①**（`COMMANDER_RELAYED`：仲裁窗口不读 GitHub，原话由我转述）") % NOW,
    "",
    ("@B 判据以账本块 `### CMDR-0925-1630` 为准（镜像 blob `%s`）：它覆盖 CMDR-0925-1625 第 1 条里"
     "「两选一」那句，其余要件一字不动——块必须真的可点开，内容只陈列已实测到的原始回读"
     "（HTTP 状态、`content-type`、字节数、正文头部原文），不翻译不扩写；两侧同判（屏上出现「技术详情」"
     "⇒ 该 details 元素计数必须 ≥ 1 且可点开；计数为 0 ⇒ 屏幕任何位置都不得出现该承诺字样）；"
     "杀手任一方向改掉只准让那一格红；与 null-body 那一格同文件、同一次候选、一次落地。") % MIRROR_BLOB,
    "",
    ("CLOSED 前置我说清楚：X-5 的读数出自 `%s` 那一代，靠**区域级字节相等**携载到我 15:19 部署的那一代"
     "（检查件 blob `%s`，三对行片段 sha1 逐位相同）。修完之后必须在目标代重读一次"
     "（HJ-P3 重跑那 5 行，或红队派生）才谈 CLOSED——我不替没读过的那一代签字。") % (OLD_GEN, GEN_CHECK_BLOB),
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印。",
    "",
    CLOSING,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(CLOSING), "closing line missing - refuse"
io.open("_bus_q53.txt", "w", encoding="utf-8", newline="\n").write(body)

gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_q53.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:600])
print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - the coordinate gate is not green")
    raise SystemExit(gate.returncode)

post = subprocess.run([sys.executable, "bus_post.py", "_bus_q53.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-400:], post.stderr[-200:])
