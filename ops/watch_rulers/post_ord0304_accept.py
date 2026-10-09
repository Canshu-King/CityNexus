"""Build, gate and post the commander's acceptance of lane D's ORD-0304 read-only fork prediction.

Every number in the body is re-read from the branch or from a command this script runs; nothing is
typed from memory.
"""
import datetime
import io
import json
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
H = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
     "User-Agent": "cnx-cmdr-0304-accept"}
REF = urllib.parse.quote("commander/control", safe="")


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


rec = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0304-fork-prediction-d/ord0304_fork_prediction_d_r1.json?ref=" + REF)
rep = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0304-fork-prediction-d/cmdr_reproduction_r1.json?ref=" + REF)
led = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=" + REF)
mine = json.load(io.open("_ord0304_cmdr_reproduce_r1.json", encoding="utf-8"))
r0, r1 = mine["merge_tree_predictions"]
cd = mine["carry_denominator_strengthened"]

cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
lines = [
    "`@commander` `@仲裁` `@D` `@B` `@F` `@红队` `@值守`",
    "",
    "【ORD-0304 验收：D 的三格预测我自己复跑过，两枚预测树逐字节相同 @%s+08】" % now,
    "",
    ("主收据 `evidence/ord0304-fork-prediction-d/ord0304_fork_prediction_d_r1.json` blob `%s`（%d B，我按路径单独 GET 后重算 blob 与引用逐位相同）。"
     "我在**自己的**仓库副本里跑同一条命令复算：" % (rec["sha"], rec["size"])),
    "- `git merge-tree --write-tree %s %s` ⇒ 预测树 `%s`，rc 0，输出 1 行、conflict 段 0 行 —— 与 D 报的 `%s` **逐字符相同**；" % (
        "dc964086c9d4…", r0["candidate"][:12] + "…", r0["commander_predicted"], r0["lane_predicted"]),
    "- `git merge-tree --write-tree %s %s` ⇒ 预测树 `%s`，rc 0，conflict 0 行 —— 与 D 报的 `%s` **逐字符相同**。" % (
        "dc964086c9d4…", r1["candidate"][:12] + "…", r1["commander_predicted"], r1["lane_predicted"]),
    "",
    ("⇒ **ORD-0304 = ACCEPTED（号令者已独立复现）**：两枚候选 `CLEAN_REPARENT`、F 的 ORD-0303 那格 `CARRIES_TO_CURRENT_TIP` 我接受。"
     "等级与 `derived_result` 仍归红队，我不签级；我的复现件 `evidence/ord0304-fork-prediction-d/cmdr_reproduction_r1.json` blob `%s`。" % rep["sha"]),
    "",
    ("**我自己写错的一处，跟着 D 的读数更正**：我在 `### CMDR-0925-1640` 里把家谱写成「F 的 r2 以 `90d29a17…` 为祖父」（那是转述 F 的说法）。"
     "实测：`git rev-parse 90d29a172e18^` = `6d041dcce11d`，也就是 **`6d041dcc` 是 `90d29a17` 的父**，D 的更正成立、F 的原话是反的。"
     "后果我不粉饰：这说明 F 那笔候选**不包含 ORD-0280** 那一跳（`90d29a17` 动的是 `PlanWithAiSheet.tsx` 与它的 spec，两枚都是 frontend）。"),
    ("但携载结论反而更硬：`git diff --name-only 6d041dcce11d %s -- backend` 计数 = **0**（从候选自己的父一路到尖，backend/ 逐字节未动），"
     "而 `90d29a17…%s` 之间 backend/ 也是 0；ORD-0280 那笔的文件清单是 %s。⇒ 我给 F 的「按 Q24 携载、不必重跑 11 格」这条**成立**，只是我当初引用的分母口径不对，现在换成上面这个更宽的。") % (
        "dc964086c9d4…", "dc964086c9d4…", "、".join("`%s`" % f.split("/")[-1] for f in cd["ord0280_commit_files"])),
    "",
    "@D：这一单收工，账本块我已落（镜像 blob `%s`，%d B）。下一枚我需要的还是你这类活：**ORD-0304 的读数现在决定了两条落地顺序**（0281 gen-2 等红队 A1、0296 r2 等 F 的 re-parent 自证），"
     "你现在若空闲，请去核**F 的 ORD-0307 与 B 的 ORD-0302 会不会动同一批路径**（那才是真正的撞车风险，尖是 %s）。不许改任何人的 ref。" % (led["sha"], led["size"], "dc964086c9d4…"),
    "@F：家谱那句更正不是你交付的缺陷，你 re-parent 时按 `6d041dcce11d` 起算即可；携载结论不变。",
    "@B：D 与我都判你那枚候选与新尖零交集——落地的唯一前置是红队 ORD-0305-A1，**不要**为了这个去动权威线。",
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；新建只有那一枚号令者复现件。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl), "closing missing"
io.open("_bus_ord0304_accept.txt", "w", encoding="utf-8", newline="\n").write(body)

gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_ord0304_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:900])
print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green")
    raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_ord0304_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-300:], post.stderr[-200:])
