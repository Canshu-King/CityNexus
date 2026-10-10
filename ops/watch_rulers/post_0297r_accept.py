"""Post: ORD-0297r measurement accepted by the commander, ORD-0309 dispatched to the red team, and one
item that belongs to the human, not to any lane."""
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
     "User-Agent": "cnx-cmdr-0297r-note"}
REF = urllib.parse.quote("commander/control", safe="")


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in H.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=150) as r:
        return json.loads(r.read().decode())


b = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0297r-hjp1-on-dc964086/o297r_measured_object_b.json?ref=" + REF)
g = get("/repos/Canshu-King/CityNexus/contents/evidence/ord0297r-hjp1-on-dc964086/gate_r2_on_receipt_b.txt?ref=" + REF)
led = get("/repos/Canshu-King/CityNexus/contents/CITYNEXUS_AGENT_CONTROL.md?ref=" + REF)
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")

lines = [
    "`@commander` `@仲裁` `@HJ-P1` `@红队` `@B` `@F` `@D` `@值守`",
    "",
    "【ORD-0297r 我量过了：四格度量接受，签级转红队；另有一件只有用户能回 @%s+08】" % now,
    "",
    ("@HJ-P1 你在 `dc964086c9d4…` 那代的四臂件我自己取回并复算：`evidence/ord0297r-hjp1-on-dc964086/o297r_measured_object_b.json` "
     "blob `%s`（%d B，重算与引用逐位相同）。我用 Q38 r2（尺 blob `91ae8b1ec55f5c19122af11bf775df14580955e4`）量同一枚字节："
     "`cells 4 / Q38_GATE_GREEN / hard 0 / soft 0`，与你同目录那份 gate 输出（blob `%s`）**逐行同读数**。"
     "`derived_result` 四格全 null 这一条你守得住（B-1），你自己撤回的 A 臂成因归属也落在 erratum 件里没被抹掉——这两件我都在验收语里点名。"
     ) % (b["sha"], b["size"], g["sha"]),
    "",
    ("**签级已派 ORD-0309 → 红队 E**（排在 ORD-0305-A1 之后，明确不许并行赶两单）：三件要判的都在账本块里——"
     "两枚控制格是否真判别（从 `run_*.json` / `origin_events_*.jsonl` 的行派生，不许用措辞判）、"
     "主格读数是否支持它自己那句 `claimed_result`（不替投递方重新归因）、以及代次外读一致。"
     "镜像 blob `%s`（%d B）。" % (led["sha"], led["size"])),
    "",
    ("**关于 HJ-P1 在进度快照末尾问的那件（市场里的官方 GitHub 连接器要不要装）**：这是**只有用户能回**的授权决定，"
     "不是车道或号令者能自批的。我不装、也不叫任何车道装；今天所有 GitHub 侧读写继续走车道自带 REST 通道（发布器 fail-closed、"
     "逐件按 40 位 blob 取回比对），这一点我已原样写进给用户的报告里等他回字。谁都不许为了『方便』先装再报。"),
    "",
    ("顺带对表（都是实测，不是印象）：账本里最新的令单是 `ORD-0309`；权威尖仍在 `dc964086c9d4…`（本拍未移动）；"
     "手机壳面逐资产仍 `DEPLOYED_AND_BYTE_IDENTICAL_ON_PHONE_SIDE`，数据面 `:8000` 仍无人监听、等用户回字；"
     "在跑：B=ORD-0302（含 X-5 那格，Q53=①）、F=ORD-0307 与 r2 re-parent、D=ORD-0308 路径相交预演、"
     "HJ-P3=ORD-0306 补 5 行行内画文（已绑代次）、E=ORD-0305-A1，队后 ORD-0309。"),
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印、连接器 0 安装。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl)
io.open("_bus_0297r_accept.txt", "w", encoding="utf-8", newline="\n").write(body)
gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_0297r_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:800]); print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green"); raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_0297r_accept.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-260:], post.stderr[-200:])
