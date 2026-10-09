import json, io, os, subprocess, datetime
L = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
def run(*a, inp=None):
    r = subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", errors="replace", input=inp)
    if r.returncode: print("ERR", a[-1][:40], r.stderr[:140])
    return r.stdout.strip()
D = {}
D["tip"] = run("git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
D["ctrl"] = run("git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin", "refs/heads/commander/control").split()[0]
led = r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
raw = open(led, "rb").read()
D["led_blob"] = run("git", "-C", "D:/moodle/CityNexus", "hash-object", "-w", led)
D["led_bytes"] = format(len(raw), ",")
en = json.load(io.open(L + "/_sweep_en_43711ebb.json", encoding="utf-8"))
zh = json.load(io.open(L + "/_sweep_zh_43711ebb.json", encoding="utf-8"))
D["en_hits"] = en["totalPaintedHits"]; D["en_distinct"] = en["distinctTokens"]
D["en_blob"] = run("git", "-C", "D:/moodle/CityNexus", "hash-object", "-w", L + "/_sweep_en_43711ebb.json")
D["zh_hits"] = zh["totalPaintedHits"]; D["zh_blob"] = run("git", "-C", "D:/moodle/CityNexus", "hash-object", "-w", L + "/_sweep_zh_43711ebb.json")
D["hub_tok"] = sum(1 for x in en["perRoute"]["/v8/hub"]["items"] if x["token"] == "SYNTHETIC_DEFAULT")
D["inc_blob"] = run("git", "-C", "D:/moodle/CityNexus", "hash-object", "-w", L + "/_mirror_incident_r1.json")
D["inc_bytes"] = format(os.path.getsize(L + "/_mirror_incident_r1.json"), ",")
D["now"] = datetime.datetime.now().strftime("%H:%M")
D["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
T = u"""### CMDR {date} {now} · 号令者（实例 A，会话 `6efab655`，总线花名 `cmdrA`）· 英文臂补上了：同一枚枚举在两臂各 {hub_tok} 次；另记一次账本镜像 401（已恢复，我没抢推）

**现场**：权威尖现读 `{tip}`（这半小时没动）；账本枝 `refs/heads/commander/control` 现读 `{ctrl}`，本地 {led_bytes} B 对我 {now} 现读、git blob id `{led_blob}`。**本轮我 0 次移动权威线、0 次落地。**

**一、账本镜像一度 401，我没用 git 抢推（这条要写清，免得别人以为我绕过了闸）**
05:23 代插把我的 05:20 块与值守会话那块写进本地账本后，镜像那步报 `PUT -> 401 Bad credentials`（rc 3）。我把范围量清楚了才住手：同一分钟内 REST 的 **GET 正常**（`publish_evidence_gated_r1.py` 对已发布路径回 SKIP_IDENTICAL 并逐字节读回），一次 1,118 B 的小体量 PUT **成功**（那件就是事故收据 `evidence/cmdr-incident-20261003/ledger_mirror_401_r1.json`，blob `{inc_blob}`，{inc_bytes} B），只有约 12.5 MB 整发的 contents PUT 连拒两次 ⇒ 不是 token 全死、也不是线被撤销。我建了两枚 git 传输的候选提交想按同一内容投同一枝，两次都被非强制推**正确拒绝**（枝在此期间被 publish 与别人推进：`1136db09` → `f4112f2d`），于是我**停手不抢道**，改等通道本身。05:5x 我重跑 `mirror_with_guard_r2.py` 成功：它先流式读回远端并自校 git blob sha1（`complete=True`、attempts 1），回读 BYTE_LEVEL_CONFIRMED。**我那两块现在远端可读**（我用 `git show <枝>:CITYNEXUS_AGENT_CONTROL.md` 现数过 `### CMDR 2026-10-03 05:20` 命中 1）。护栏前提我也核过：那一刻远端有而本地没有的行为 0。

**二、英文臂我量了（我 05:20 那块欠的第二格）**
同一把尺 `cmdr_machine_speech_sweep_r1.js`、同代次产物、同一台私有栈，locale=en：全屏 {en_hits} 处、去重 {en_distinct} 枚 token，件 `evidence/cmdr-sweep-20261003/machine_speech_en_r1_at_43711ebb.json`，blob `{en_blob}`，页面异常 0。关键对照：**`SYNTHETIC_DEFAULT` 在 en 臂也画了 {hub_tok} 次，与 zh 臂的 {zh_hits} 处同一枚枚举**（zh 件 blob `{zh_blob}`）。⇒ 这不是「中文少一个词」，是那枚枚举在两臂都直接进人话句子；我已把这手派给车道会话 `45d25bfb-3cb3-43e5-b9cc-edc10faa04a3`（05:2x 起，现读 runtimeState=running，枝名 `review/cmdra-hub-enum-copy-r1`，**不占新单号**，账本真实前沿仍是 ORD-0550）。其余 en 多出来的全大写（`ARRIVAL`、`DEPARTURE`、`COMPLETED` 等）是 en 字典自己写成全大标的栏名，我没算进这一单的靶子。

**三、一处我要更正的时序**
05:58 我对车道 6a150e1e 那块跑出 `Q43_GATE_RED`（`line 39 | 0210 | no class matched`）并据此想发具名指引；等我 06:0x 去读那行时文件已经不在收件口——`_processed/6a150e1e_0559.md.inserted_055937` 显示它在 05:59:37 **已被入账**（入账者是另一位号令者的代插跑次）。所以「指引由我发出」这句不成立：实际是车道自己把那行改了、由另一跑次通过。我把这条写在这里，不占别人的手。另记一条实测：尺报的 `0210` 在当时的文件正文里字面搜不到（我对 `0210` 做过 ASCII 与 NFKC 归一化两次搜索），这与既有那条「块名里的数字会被算成裸数」同形，留给尺的主人。

**四、跨轮的进程事实（对所有车道都成立）**
我 05:00 那块用的后端 :8801/:8802 与静态 :49801/:49802/:49804，05:1x 回来时 `netstat` 逐口读到监听者 0——脱离进程随上一轮宿主退出被收走。已重起：后端 :8805 与静态 :49805（库仍是同一份只读备份再复制的 `D:/moodle/_qoder_cmdr_priv_0437seed.db`，17,330,176 B，源 `D:/moodle/_qoder_r_ord0437/run/_r_ord0437_e2e.db` 只 `mode=ro` 打开）。第二节那趟 en 读数就在新口上取，入口 `/assets/index-DeyXt9ON.js` 与磁盘逐字相同。**含义：每一轮先探端口再跑仪表，别继承上一轮的「它还活着」。**

**没改善的部分**
1. hub 那 {hub_tok} 次机词此刻仍在线上（两臂都在），车道 45d25bfb 尚未推出枝（`ls-remote` 现读 `refs/heads/review/cmdra*` 为空）。
2. `place_name` 那格仍未定：我把选择题挂在总线 `m_12816c74c645` 上等持派单方，我这边 0 进展；总线回件我这轮读到 count 0。
3. 我本轮 0 笔落地；门外候选 r14 在 05:5x 已由车道自交 r2 形（`b10743eceaad865756a50d173907ee8c3f2bda36`）并随那块入账，但**那笔我没复切、没落**（归读得到它的那位号令者）。
4. en 臂我只解释了 hub 与 bookings 两屏，另 7 屏有命中的未逐格归因 ⇒ `NOT_REACHED_BY_CMDR`。
5. 镜像 401 的成因我没钉死（只钉到「大体量 contents PUT 被拒、GET 与小体量 PUT 同刻可用」这一层）；下一次再撞，别人仍可能误判成 token 失效。
6. 手机链 hop4 未起 ⇒ 本轮读数仍是私有舞台 `NOT-DEPLOYED-OBSERVED`；`_preview.db` 我 0 写入，:8000 / :4781 / :4782 / :8693 我全程未发请求也未重启；桌面留言里仍是换树那一个问题，我没追加。
7. 后端测试本轮没有任何一条被执行（我没有可传 `--tests` 的对象），具名 `NOT_EXECUTED_BY_CMDR`。
"""
name = D["now"].replace(":", "")
out_txt = T.format(**D)
open("D:/moodle/_qoder_ledger_inbox/cmdr_" + name + ".md", "wb").write(out_txt.encode("utf-8"))
D["name"] = name
print("WROTE cmdr_" + D["name"] + ".md")
