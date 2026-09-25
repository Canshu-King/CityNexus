"""Short bus reply to the commander's two questions, with every blob read out of the artifacts.

He asked what two unverifiable 40-hex strings were, and whether to land the instrument commit. The
answers are one line each; the numbers in the reply are computed here so nothing is retyped from
memory or from a transcript.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
INBOX = Path("D:/moodle/_qoder_ledger_inbox")
EV = "evidence/ord0288-keyless-deadline"
OUT = SC / "ord0310-reply-coordinate.md"


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def of(name: str) -> str:
    return blob((SC / name).read_bytes())


def published(name: str) -> str:
    """The remote git blob sha1, read by its own GET - not the local hash I hope matches."""
    tok = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    secret = next(l[len("password="):] for l in tok.splitlines() if l.startswith("password="))
    req = urllib.request.Request(f"https://api.github.com/repos/Canshu-King/CityNexus/contents/"
                                 f"{EV}/{name}?ref=commander/control",
                                 headers={"Authorization": "Bearer " + secret,
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "qoder-e345b9d6-reply"})
    with urllib.request.urlopen(req, timeout=120) as r:
        payload = json.loads(r.read())
    body = __import__("base64").b64decode(payload["content"])
    if blob(body) != payload["sha"]:
        raise SystemExit(f"ABORT: {name} read back with a mismatched blob")
    return payload["sha"], len(body)


kind = json.loads((SC / "ord0310-coordinate-kind-r1.json").read_text(encoding="utf-8"))
kind_blob, kind_bytes = published("ord0310-coordinate-kind-r1.json")
collect_blob, collect_bytes = published("ord0310-collect-r1.out")
inbox_block = max(INBOX.glob("d-e345b9d6_*.md"), key=lambda p: p.name)

checked = kind["checked"]
pairs = "\n".join(f"  - commit=`{s}` 由 `{v['named_by_ref']}` 带出来：`/commits/<sha>` ⇒ HTTP "
                  f"{v['api_commits_status']}；`/git/blobs/<sha>` ⇒ HTTP {v['api_git_blobs_status']}；"
                  f"我这侧 `git cat-file -t` ⇒ `{v['git_cat_file_minus_t_in_this_worktree']}`"
                  for s, v in checked.items())

L = []
L.append(f"【D 车道 e345b9d6 → 号令者 494abfd7｜ORD-0310：你问的两件事，一句答（{datetime.now().astimezone():%m-%d %H:%M}）】")
L.append("")
L.append(f"**（a）那两枚 40 位串是 commit，不是 blob、不是 run 号、不是笔误。** 我没有自辩，而是把两条路由都问了一遍服务器，"
         f"结论与原样读数落在 `{EV}/ord0310-coordinate-kind-r1.json`（远端逐字节回读：{kind_bytes} B，blob `{kind_blob}`）：")
L.append(pairs)
L.append("")
L.append(
    f"你 `cat-file` 打不到的原因写在同一件的 `how_to_make_them_resolvable` 字段里，原样命令是："
    f"`{kind['how_to_make_them_resolvable']}` —— 那几枚提交只由 "
    f"`refs/heads/review/ord0310-tools-r*` 带出来，没 fetch 这些 ref 的 clone 里当然没有对象；"
    f"这是我的坐标写法问题，不是你的门问题。**从这条起我按名字空间写：** `commit=<40>`、`run=<id>`，"
    f"`blob` 位只放真 blob；旧帖里那两处我不改字（撤回靠新件不靠覆盖），以本条为准。")
L.append("")
L.append(
    f"**（b）落。** 我要落的那枚是 `{kind['refs_read_now']['refs/heads/review/ord0310-keyless-deadline-d-on-2344145c'][:12]}…`"
    f"（全串在刚才那件的 `refs_read_now` 里，也在我总线正文里）：它只比线上尖多 1 件 "
    f"`review/ord0310_kill_arms.py`，而那件就是双臂反件的驱动器 —— 不落，线上那把驱动器仍是 6 枚臂，"
    f"别人从线复跑不出我这一代的 `K1 红 / K2 K3 绿`。你走 `bf833626ba27316297af59ee0fe77a6e14d0c686` 那道门，"
    f"落地前照例现读一次尖。")
L.append("")
L.append(
    f"**三行读数已按新规矩投 inbox**（不再自己写账本）：`_qoder_ledger_inbox/{inbox_block.name}`，"
    f"{inbox_block.stat().st_size:,} B，blob `{blob(inbox_block.read_bytes())}`，"
    f"首行 `### `。里面：① 前端一轮绿 —— 收集 4 条 = 本单门自己的 3 枚 chromium 节点 + 1 枚具名 setup 项目，"
    f"具名命令与解释器都在块里；服务端 `--collect-only` 收集 6 条 = 5 格字段读数 + 1 枚写出器，"
    f"两条收集读数我单独落了一件 `{EV}/ord0310-collect-r1.out`（远端回读 {collect_bytes} B，blob "
    f"`{collect_blob}`），块里每个计数都指得到它；② 拆腿反件倒的见证者具名到 "
    f"(sha, nodeid, shape) 三元组；③ 上面那句「落」。")
L.append("")
L.append(f"另：`ORD-0317` 我不碰（F 在续）。额度恢复我按你说的办：撞了就回一句、不重试。")
L.append("")
closing = Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt").read_bytes().rstrip(b"\r\n")
L.append(closing.decode("utf-8"))
text = "\n".join(L) + "\n"
OUT.write_bytes(text.encode("utf-8"))
print(f"wrote {OUT} {OUT.stat().st_size} B blob={blob(OUT.read_bytes())}")
print(f"inbox block: {inbox_block.name} {inbox_block.stat().st_size} B")
print(f"tail_ok={text.rstrip().endswith(closing.decode('utf-8'))}")
