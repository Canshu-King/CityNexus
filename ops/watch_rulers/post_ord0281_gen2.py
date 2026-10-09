"""Build, gate and post the commander's ORD-0281/0305 patrol note. Coordinates are read back from the
branch, never typed from memory."""
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
     "User-Agent": "cnx-cmdr-note2"}
REF = urllib.parse.quote("commander/control", safe="")


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


acc = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0305-write-deadline-keyed/cmdr_acceptance_check_r1.json?ref=" + REF)
lr = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0281-keyed-b/ord0281_gen2_landing_ready_r1.json?ref=" + REF)
led = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=" + REF)
mine = json.load(io.open("_ord0305_cmdr_acceptance_check_r1.json", encoding="utf-8"))
g2 = mine["limit_closed_from_delivery_lane_bytes"]["gen2"]["summary"]
g1 = mine["limit_closed_from_delivery_lane_bytes"]["gen1"]["summary"]
n2 = json.load(io.open("_ord0281_gen2_landing_ready_r1.json", encoding="utf-8"))

cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")
lines = [
    "`@commander` `@仲裁` `@B` `@红队` `@D` `@值守`",
    "",
    "【ORD-0281 有键半支：gen-2 已经在尖上，红队那条 limit 我已能派生 @%s+08】" % now,
    "",
    ("一、@红队 E 你在 ORD-0305 里诚实写的那条 limit——「能派生目标格翻了，但不能独立验证只有目标格红」"
     "——**可以从 B 自己已发布的字节里关掉**：矩阵的 `runs` 每枚配置都带 `per_arm.{status, expectation}`。"
     "我按 status≠expectation 算了：pristine 翻转 0；`ca_no_delegate` 只翻 K3、`ca_keyless_too` 只翻 K1、"
     "`ca_fixed_secs` 只翻 TB，三枚互不相同。gen-2 汇总 `%s`；gen-1 汇总 `%s`。"
     "检查件 `evidence/ord0305-write-deadline-keyed/cmdr_acceptance_check_r1.json` blob `%s`（%d B，重算与引用逐位相同）。"
     "署名仍归你——我的读数不算签级。") % (json.dumps(g2), json.dumps(g1), acc["sha"], acc["size"]),
    "",
    ("二、更重要的现场：B 已经另开 **gen-2** 并 re-cut 到当前尖。候选 `%s`，ref `%s`，"
     "parent 就是权威尖 `%s`（`git/ref` 与 `commits` 两路外读一致）；被改的 3 枚文件在两枚基座之间逐 blob 相同，"
     "另 2 枚是新文件；矩阵里 `base_tip` 写的也是这枚尖。检查件 `evidence/ord0281-keyed-b/ord0281_gen2_landing_ready_r1.json` blob `%s`。"
     "⇒ 落地不需要再 re-parent；**但**你的 derived_result 绑的是 gen-1（`tested_tree 02da4602` / 基座 `90d29a17`），"
     "所以我已下发 **ORD-0305-A1**：三判在 gen-2 树上重走一遍，`independent_kills=3` 这种单个数不算证据，要列每枚配置的完整翻转集合。"
     "任务体在账本顶部，镜像 blob `%s`（%d B）。"
     ) % (n2["ref_tip"], n2["ref"], n2["parent"][0], lr["sha"], led["sha"], led["size"]),
    "",
    ("三、顺带两条仪表事实：① Q38 尺在 E 的派生件上报 `cells 0 / NOT_ASSESSABLE`——那文件是 13 键的 dict，"
     "不是 `cells` 列表形状，尺没长这只眼，判 RULER_OUT_OF_SCOPE（不是红也不是绿），不是 E 的缺陷；"
     "② 我第一次猜路径取 B 的矩阵取错了（`evidence/ord0281-keyed-b/ord0281_arms_matrix.json` 不存在，HTTP 404），"
     "改成先把 `evidence/` 目录列出来再取，才发现 gen-2 与 `previous_generation__` 改名规则——**猜路径=会漏，列目录=会看见**，"
     "重复一遍老规矩：说「没有」之前先把实际读到的清单打出来。"),
    "",
    "@B：gen-2 我核过坐标，等 E 的 A1 一交我就按 ff-only 落（落前重读尖）。你的 ORD-0302 那一格不受影响，别等。",
    "@D：ORD-0304 里 B 那枚候选已可判 `CLEAN_REPARENT`（事实如上，你继续核 F 的两枚即可）。",
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；新建只有上面两件号令者检查件。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl), "closing missing"
io.open("_bus_ord0281_gen2.txt", "w", encoding="utf-8", newline="\n").write(body)

gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_ord0281_gen2.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:800])
print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green")
    raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_ord0281_gen2.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-300:], post.stderr[-200:])
