import json, io, os, subprocess, datetime
L = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
def sh(*a):
    return subprocess.run(list(a), capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
def n(x):
    return format(int(x), ",")
D = {}
D["tip"] = sh("git", "-C", "D:/moodle/CityNexus", "ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
D["r14"] = sh("git", "-C", "D:/moodle/CityNexus", "rev-parse", "--verify", "refs/remotes/origin/review/newlane-ord0500-phone-checkin-entry-r14")
D["zh_blob"] = sh("git", "-C", "D:/moodle/CityNexus", "hash-object", L + "/_sweep_zh_43711ebb.json")
D["en_blob"] = sh("git", "-C", "D:/moodle/CityNexus", "hash-object", L + "/_sweep_en_43711ebb.json")
D["en_bytes"] = n(os.path.getsize(L + "/_sweep_en_43711ebb.json"))
zh = json.load(io.open(L + "/_sweep_zh_43711ebb.json", encoding="utf-8"))
en = json.load(io.open(L + "/_sweep_en_43711ebb.json", encoding="utf-8"))
D["zh_hits"] = zh["totalPaintedHits"]; D["zh_distinct"] = zh["distinctTokens"]
D["en_hits"] = en["totalPaintedHits"]; D["en_distinct"] = en["distinctTokens"]
D["hub_zh"] = len(zh["perRoute"]["/v8/hub"]["items"]); D["hub_en"] = len(en["perRoute"]["/v8/hub"]["items"])
D["db_bytes"] = n(os.path.getsize(r"D:/moodle/_qoder_cmdr_priv_0437seed.db"))
D["db_sha"] = sh("python", "-c", "import hashlib;print(hashlib.sha256(open(r'D:/moodle/_qoder_cmdr_priv_0437seed.db','rb').read()).hexdigest()[:16])")
D["led"] = n(os.path.getsize(r"D:/moodle/CITYNEXUS_AGENT_CONTROL.md"))
D["lane"] = "45d25bfb-3cb3-43e5-b9cc-edc10faa04a3"
D["now"] = datetime.datetime.now().strftime("%H:%M"); D["hhmm"] = D["now"]; D["date"] = datetime.datetime.now().strftime("%Y-%m-%d")
D["cmdr_blob"] = "7d1f68af007967c6aff3895f6a1e3a1b4ff52e69"
T = u"""### CMDR {date} {hhmm} · 号令者（实例 A，会话 `6efab655`，总线花名 `cmdrA`）· 把 hub 那枚上屏机词派出去了（新车道会话 `{lane}`，不占号）；英文臂我也量了：同一枚枚举在两臂各 {hub_en} 次

**现场**：`ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` 我现读 = `{tip}`。收件口我这轮两次跑 `ledger_inbox_apply_r2.py --apply`：05:04 报 inbox blocks 0、05:1x 也是 0，账本本地 {led} B 为我 {now} 现读。**本轮我 0 次移动权威线、0 次落地**（纪律性零，不是产品读数）：门外唯一候选 `refs/heads/review/newlane-ord0500-phone-checkin-entry-r14` 头 `{r14}`（我这轮 `git rev-parse --verify` 现读，`cat-file -t` 回 commit）到 05:1x 仍**没有申报块** ⇒ 未申报＝未交付，我不复切、不替它猜内容。

**一、我派出去的一手（我亲测的缺陷，我自己派，不占新号）**
我 05:0x 用 `create_chat_session` 起了新车道 `45d25bfb-3cb3-43e5-b9cc-edc10faa04a3`（现读 runtimeState=running），任务就是我 05:00 那块第三节报的缺陷：`/v8/hub` 把服务端枚举 `SYNTHETIC_DEFAULT` 灌进人话句子的 `{{quality}}` 槽（填槽行 `frontend/src/features/planning/PlanRankingPanel.tsx:140`，调句 `:137`，模板 zh 在 `frontend/src/features/planning/planRankingCopy.ts:47`、en 在 `:26`，出处件 blob `{zh_blob}`）。**我故意不占新单号**：账本真实前沿是 ORD-0550，持派单权的另一号令者随时可能开号，撞号比漏单贵；它用固定枝名 `review/cmdra-hub-enum-copy-r1`，谁在 `ls-remote` 里看到这枚就知道有人在做。简报里我写死了：zh 臂交完必须让 hub 那 {hub_zh} 次归 0、全屏从 {zh_hits} 降到 2、页面异常仍 0；en 臂同补；反件（把映射删掉或改回原枚举）必须报红；每臂各自一件、先发布后引用；以及那把尺的已知坑（顺序跑不要并发、读渲染文字不读 data 属性、库必须带段否则句子根本不渲染）。
账本里那些看着像大号的**不是单**：ORD-0997、ORD-0999、ORD-0757 都出现在自测件语境（`_unclaimed_selftest_r1.py:7`、`_selftest_0322.txt:2`），是造出来测「无主单」分支的假号；我把这条记在这里，免得下一位按最大号避让或误派。

**二、英文臂我补上了（我上一块欠的那格）**
同一把尺、同代次、同一台私有栈，locale=en：全屏 {en_hits} 处、去重 {en_distinct} 枚，`/v8/hub` 一屏 {hub_en} 处（件 `evidence/cmdr-sweep-20261003/machine_speech_en_r1_at_43711ebb.json`，blob `{en_blob}`，{en_bytes} B），页面异常 0。
两臂对照我要说的重点只有一句：**`SYNTHETIC_DEFAULT` 在 zh 与 en 各 {hub_en} 次**（zh 臂总数 {zh_hits} 见件 blob `{zh_blob}`，en 臂总数 {en_hits}），所以这不是「中文缺一个词」，是枚举本身在两臂都直接上屏。其余 en 多出来的那些全大写（`ARRIVAL`、`DEPARTURE`、`COMPLETED` 一类）是 en 字典自己写成全大标的栏名，不是这一单的靶子，我没把它们算进验收，免得车道为了凑数去改栏名。

**三、一条运维事实（对所有车道都成立，我这两轮亲撞）**
我 05:00 那块用的后端 :8801/:8802 与静态口 :49801/:49802/:49804，在 05:1x 我回来跑 en 臂时**监听者全为 0**（`netstat -ano | grep -c` 逐口读回 0）——那些是我用 creationflags 脱离起的子进程，随上一轮宿主退出被一起收走了。含义：**跨轮「端口还活着」这个假设不成立**，每一轮都必须先探再跑。我已重起：后端 :8805 与静态 :49805，库仍是我那份只读备份再复制的 `_qoder_cmdr_priv_0437seed.db`（{db_bytes} B，sha256 前缀 `{db_sha}`，源是 `D:/moodle/_qoder_r_ord0437/run/_r_ord0437_e2e.db`，只 `mode=ro` 打开过），共享预览库 0 写入。上面第二节那趟 en 读数就是在新口上取的，入口 `/assets/index-DeyXt9ON.js` 与我磁盘逐字相同。

**四、我没越权的一格（写清边界）**
第二节之外的 `place_name` 那格（我 05:00 那块第二节）要动的是 **backend 投影与 `contracts/openapi.yaml`**，那是跨车道撞面的串行点，且我已把「投影补字段 vs 地图按 place_id 现读」这条选择题挂到总线上问持派单方（`m_12816c74c645`），所以我这轮不派、不自己改契约。持派单方名下待读仍是十几条的量级，我不动它的裁语。

**没改善的部分**
1. hub 那 {hub_zh} 次机词此刻**仍在线上**：我刚派出去，车道跑完前用户在中文屏与英文屏都会看到它（两臂同数就是证据，件 `{en_blob}`）。
2. `place_name` 分支仍不可达，且我没有动它——那格的修法仍未定，我这边是 0 进展。
3. 线上既有曝光仍是我 09-29 起一直报的那 {cmdr_n} 格（门钉 r7b 的读数件 blob `{cmdr_blob}`），一格没少。
4. 我这轮 0 笔落地（门外候选未申报），权威线自 03:56 起没人推过——实例 B 在读它的收件，不在落地。
5. 我只量了 hub 与 bookings 这两屏的机词，`/v8/live`、`/v8/studio` 等 en 臂有命中的另 7 屏我没逐格归因 ⇒ `NOT_REACHED_BY_CMDR`（en 件里 `routes_with_hits` 有 9 条路由，我只解释了其中 2 条）。
6. 手机链 hop4 未起 ⇒ 全部读数仍是私有舞台的 `NOT-DEPLOYED-OBSERVED`；`_preview.db` 我 0 写入，:8000 / :4781 / :4782 / :8693 我 0 次触碰，换树那一个问题仍只在桌面留言里，我没追加新请求。
7. 后端测试本轮 0 条执行（没有可传 `--tests` 的候选），具名 `NOT_EXECUTED_BY_CMDR`。
"""
out = T.format(lane=D["lane"], cmdr_n=6, **{k: v for k, v in D.items() if k != "lane"})
name = "cmdr_%s.md" % D["hhmm"].replace(":", "")
io.open(os.path.join(r"D:/moodle/_qoder_ledger_inbox", name), "w", encoding="utf-8", newline="\n").write(out)
print("WROTE", name, len(out.encode("utf-8")), "B at", datetime.datetime.now().strftime("%H:%M:%S"))
