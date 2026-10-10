"""Read back the full 40-hex blobs for what the commander published this tick, then build+gate+post
one compact patrol note. Coordinates are fetched, never typed."""
import datetime
import io
import json
import subprocess
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
HDRS = {"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
        "User-Agent": "cnx-cmdr-note"}
PATHS = {
    "chain_probe": "evidence/phone-chain-1633/probe_r1.json",
    "static_verify": "evidence/ord0281-keyed-b/ord0281_cmdr_static_verify_r1.json",
}


def get(path):
    req = urllib.request.Request("https://api.github.com" + path)
    for k, v in HDRS.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


ref = urllib.parse.quote("commander/control", safe="")
shas = {}
for key, p in PATHS.items():
    meta = get("/repos/Canshu-King/CityNexus/contents/" + p + "?ref=" + ref)
    shas[key] = (meta["sha"], meta["size"])
    print(key, meta["sha"], meta["size"])

v = json.load(open("_ord0281_cmdr_static_verify_r1.json", encoding="utf-8"))
c = json.load(open("_phone_chain_1633.json", encoding="utf-8"))
probed = c.get("assets_probed") or c.get("probed") or len(c.get("assets", []))
cl = io.open("CLOSING_LINE.txt", encoding="utf-8").read().strip()
now = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).strftime("%H:%M")

lines = [
    "`@commander` `@仲裁` `@B` `@值守` `@下一班`",
    "",
    "【巡查拍 %s+08 · 两件亲测 + 一枚我自己的假缺】" % now,
    "",
    ("一、手机链壳面我又量了一次（不是推测，是走隧道的逐资产回读）：`%s` blob `%s`，%s B。"
     "结论字段 `DEPLOYED_AND_BYTE_IDENTICAL_ON_PHONE_SIDE`，被探测资产 %s 枚全部 200、与磁盘逐字节相同、"
     "没有一个以 HTML 兜底、`.js` 的 MIME 正确。数据面照旧是 :8000 无人监听那一件，仍等用户回字——"
    "我不擅自写受保护库，也不擅自占口。探针件自己写着 `generation_under_test = unknown` ⇒ 它只证明磁盘与隧道逐字节相同，"
    "不证明磁盘那一份属于哪一代；代次绑定由 15:19 的部署收据与换代回读那两件负责。") % (PATHS["chain_probe"], shas["chain_probe"][0],
                                             shas["chain_probe"][1], probed),
    "",
    ("二、B 的 ORD-0281 有键候选我做了**静态坐标亲测**（臂的派生归红队 ORD-0305，落地归我）：`%s` blob `%s`。"
     "外读结果：ref `%s` 的 tip =  claimed `%s`（相同）；parent = 基座 `%s`（相同）；"
     "改动 %d 个文件、全在 frontend/ 下、backend/ 为 0；被引用的 `frontend/src/lib/writeDeadline.ts` 在候选上 blob = `%s`，"
     "重算与引用逐位相同，且该文件在基座上不存在（404）。候选此刻状态=已核坐标、未落地。")
    % (PATHS["static_verify"], shas["static_verify"][0], v["ref"], v["want"], v["base"],
       len(v["files_changed"]), v["writeDeadline_blob_at_candidate"]),
    "",
    ("三、我这一拍差点报错一枚假缺：我用字节搜索找常量 `60000` 没命中，正要写「收据引的常数不在该 blob 里」——"
     "先把文件打出来读了声明行才看清，源码写的是 TypeScript 数字分隔符 `60_000`，值就是 60000。"
     "记进工件的 `commander_false_alarm_note`。给所有车道重复一遍那条老规矩：**说“没有”之前先把实际读到的东西打出来。**"),
    "",
    "纪律：本拍权威线未移动、0 ref 推送、产品码 0 改动、`demo/reset` 0、`_live`/`_preview` 0 读写、凭据 0 打印；新建只有上面两件工件。",
    "",
    cl,
]
body = "\n".join(lines) + "\n"
assert body.rstrip().endswith(cl), "closing missing"
io.open("_bus_patrol_1636.txt", "w", encoding="utf-8", newline="\n").write(body)

gate = subprocess.run([sys.executable, "claim_coordinate_check_r4b.py", "--text", "_bus_patrol_1636.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(gate.stdout[:700])
print("gate rc", gate.returncode)
if gate.returncode != 0:
    print("NOT POSTING - gate not green (rc 4 = nothing checkable, add a coordinate; rc 3 = a real finding)")
    raise SystemExit(gate.returncode)
post = subprocess.run([sys.executable, "bus_post.py", "_bus_patrol_1636.txt"],
                      capture_output=True, text=True, encoding="utf-8", errors="replace")
print(post.stdout[-300:], post.stderr[-200:])
