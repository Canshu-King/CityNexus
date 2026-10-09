"""Emit this lane's inbox block.  Anchors come from anchors.json, which verify_anchors_r1.py
produced by reading the git objects -- no remembered line numbers here."""
import io
import json
import re
import subprocess

DATA = json.load(io.open("D:/moodle/_dwg_ctl10/anchors.json", encoding="utf-8"))
A = DATA["anchors"]
TIP, MY, BASE = DATA["TIP_NOW"], DATA["MYTIP"], DATA["BASE"]
CHANG, SAFE, LINK, CLOSING = DATA["CHANG"], DATA["SAFE"], DATA["LINK"], DATA["closing"]

PANEL = "frontend/src/features/discovery/RealCityDiscoveryPanel.tsx"
FMT = "frontend/src/lib/formatWhen.ts"
DICT = "frontend/src/i18n/LocaleContext.tsx"
V8 = "frontend/src/app/V8Experience.tsx"
SCHEMA = "backend/app/schemas.py"
Q4 = "frontend/e2e/qoder-ord0435-poi-batch-multiselect.spec.ts"
ARM = "review/duanwagong/datefmt_0553_discovery_arm_r1.py"
INST = "frontend/e2e/qoder-duanwagong-0553-batch-row-instant-r1.spec.ts"
STUB = "frontend/e2e/qoder-duanwagong-0553-batch-row-stub-r1.spec.ts"
EVZH = "review/duanwagong/readouts/dwg0553__Tzh.json"
EVEN = "review/duanwagong/readouts/dwg0553__Ten.json"
EVSZH = "review/duanwagong/readouts/dwg0553stub__Szh.json"
EVSEN = "review/duanwagong/readouts/dwg0553stub__Sen.json"
SHOT_ZH = "review/duanwagong/readouts/dwg0553_Tzh_dwg0553d.png"
SHOT_EN = "review/duanwagong/readouts/dwg0553_Ten_dwg0553d.png"
PROBE = "frontend/tools/cnx_0553_shape_probe_r1.cjs"
DOOR = "_qoder_cmdr_ref_20260921/live_checks/ledger_inbox_apply_r1.py"
HERMES = "backend/tests/test_v18_hermes_r20_transport_reliability_probe.py"
CTRL = "D:/moodle/CITYNEXUS_AGENT_CONTROL.md"
RULER = "_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"

pytest_tail = ""
try:
    raw = io.open("/tmp/pytest_dwg.txt", encoding="utf-8", errors="replace").read()
    percent = re.findall(r"\[\s*(\d+)%\]", raw)
    rc = re.findall(r"PYTEST_RC=(\d+)", raw)
    summary = re.findall(r"=+ .(\d+ failed.*|\d+ passed.*) =+", raw)
    pytest_tail = json.dumps({"percent_seen": percent[-1] if percent else None,
                              "rc": rc[-1] if rc else None,
                              "final_line": summary[-1][:300] if summary else None},
                             ensure_ascii=False)
except Exception as exc:
    pytest_tail = "log unreadable: %s" % str(exc)[:80]

BLOCK = u"""### 短瓦工 · ORD-0553 交件 · 逐字认领 discovery 批量回读那一枚整文件 · 甲案落了，两 locale 的屏上读数各拿到手

花名「短瓦工」（id `qoder:` 见本车道流水）。本块走收件口，账本零直写。
文件名写作 `duanwagong_{HHMM}.md`：代插门的文件名闸只收 `[A-Za-z0-9._-]+_[0-9]{{4}}\\.md` 这一形制（闸源码 {DOOR}:81），汉字花名当场被拒，所以文件名用罗马字、块内一律写「短瓦工」——这是门的形制，不是我的选择，请号令者别把它读成我没守命名规矩。

**认领与基**

- 认领单号 ORD-0553，按 `{CTRL}`:{order_claim_rule} 那行写的「一枚文件一扇车道，先到先得」。
- 认领前跑占面尺 `_qoder_cmdr_ref_20260921/live_checks/patrol/_live_orders_reader_r1.py`：号头去重三十二枚、逐字认领面十二枚文件，`{PANEL}` 那枚文件不在面里；现数远端 `review/` 枝名里带 0553 的四枚当时都只碰 `frontend/src/lib/displayVocabulary.ts` 与字典，没碰本件。
- 建枝时现取权威尖 {BASE}（`ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` 现读逐字同值）。中途线从 259ed27d14b62224eb1a23b244c281288a012fc5 换代一次，我在**首推之前** rebase 上去；推过之后不动已发布枝。
- 交枝 `refs/heads/review/短瓦工-0553-r1`，枝尖 {MINE}（`git ls-remote --refs` 现读同值）。落地腿已把我这五笔取上线：现尖 {TIP}，`merge-base --is-ancestor` 现测我枝尖是它的祖先。本块零枚权威线直写。

**撞车自报（请号令者点一枚，我不删他家枝）**

- `refs/heads/review/长瓦工-0553-r1`（尖 {CHANG}）改了同一枚文件的同一格，且**那一行代码与我逐字相同**——都是 `{PANEL}`:{panel_after} 那一句；差别只在上面那段注释：他那段引 ORD-0423，我这段写明「面板 props 只有 journeyId 与 cityCode，拿不到行程时区」。**代码内容两枚等价，落哪一枚屏上结果都一样**。
- 时序现读：我那笔 {BASE} 之后第一笔提交是零〇三六五一分，他那笔是零〇三八五〇分；我建枝前跑的占面尺与远端枝名里都没有它。这是「看板只记逐字声明、不看枝名」那个老缺口的又一次实证（缺口本身已由别的车道在册面上报过）。
- 我那侧多带三件东西：静态臂一枚（{ARM}:{arm_a1}）、只读屏腿两枚（{INST} 与 {STUB}）、两 locale 屏上读数与截图（{EVZH} 等）。若号令者点他那枚落地，本块的屏读与臂仍可直接接过去用。

**一、改了哪一格（改前与改后都现读）**

| 内容 | 现读坐标 |
| --- | --- |
| 改前：把服务器串前十六位拼上屏 | `{PANEL}`:{panel_before} |
| 改后：调用现成封装 | `{PANEL}`:{panel_after} |
| 新增的那行 import | `{PANEL}`:{panel_import} |
| 时区口径写在调用处 | `{PANEL}`:{panel_zone} |
| 现成封装本体 | `{FMT}`:{fmt_export} |
| 封装输出的形状（月＋日＋时:分） | `{FMT}`:{fmt_shape} |

**二、时区口径（甲案要的那句「显式」）**

设备钟。这台机现读 `Asia/Shanghai`，读数落在 `{EVZH}` 与 `{EVSZH}` 里那格 `device_zone`。为什么不写行程时区：这枚面板的 props 只有 journeyId 与 cityCode，行程时区不在作用域里，要穿进来就是跨文件改动、与「一枚文件一扇车道」冲突——这一点我按 `{CTRL}`:{order_claim_rule} 的边界收在调用处注释里（`{PANEL}`:{panel_zone}），没有偷偷换个说法。

**三、零新键（复用一枚现成键，并申报命名空间跨了）**

- 封装要求 `pending` 参数。我**没有新建任何键**，复用了 `inbox.timePending`，两臂现读：英侧 `{DICT}`:{dict_en}，中侧 `{DICT}`:{dict_zh}。
- 跨命名空间复用在这枚文件里本就有先例：它现在就读别家键 `{PANEL}`:{panel_recovery_key}（`recovery.technicalDetail`）。若号令者要求 `discovery.` 名下另立键，那是提案表的活，我按规矩不自造，等你点。
- 屏上会读到 `pending` 那一支的前提是 `start_at` 为空串，而契约把 `start_at` 定为必填，所以那一支实测未触发——写在这里免得被当成已验证路径。

**四、屏上读数（两 locale 各一条，真流程落到了方案）**

写腿（`{INST}`，权威模式、库新建、AI 关、前端端口 :5511、后端端口 :5512）：旅客自己点「完成」，compose 真写了方案，臂走的是第二次 GET 的对拍。

| locale | 服务器串的瞬时 | 屏上那格读到 | 改前那一版会读 |
| --- | --- | --- | --- |
| zh-CN | `2026-10-09T19:05:00+08:00` | 十月九日 十九:〇五 | 年-月-日 时分那种裸 ISO |
| en | `2026-10-09T19:05:00+08:00` | `9 Oct, 19:05` | `2026-10-09 19:05` |

逐字读数与复算对拍都在现读文件里：zh 那格 `{EVZH}`:{ev_zh_cell}，它记的改前会排 `{EVZH}`:{ev_zh_old}，en 那格 `{EVEN}`:{ev_en_cell}；截图 `{SHOT_ZH}` 与 `{SHOT_EN}`。臂走 LAND 那一支的坐标 `{INST}`:{inst_land}。

桩腿（`{STUB}`）补的是写腿补不到的一件事：**同一格里偏移被切掉就是六小时的错**。它把两枚瞬时并排交给同一枚行，网络腿在路由边界作答、未写库：

| 持有的瞬时 | 改前那版排 | 改后屏上（zh / en） |
| --- | --- | --- |
| `2026-10-10T15:30:00+08:00` | `2026-10-10 15:30` | 十月十日 十五:三〇 / `10 Oct, 15:30` |
| `2026-10-10T02:00:00+00:00` | `2026-10-10 02:00` | 十月十日 十:〇〇 / `10 Oct, 10:00` |

坐标：持有的那枚 UTC 瞬时 `{STUB}`:{stub_utc}，zh 读数 `{EVSZH}`:{ev_szh_cells}，en 读数 `{EVSEN}`:{ev_sen_cells}。

**五、屏上文本确实变了，这属单子里那条豁免——证据摊开**

单子原文在 `{CTRL}`:{order_exception}：「不许改…除非你能贴出『原来那版本来就是错的』的证据行（例如原始 ISO 直接上过屏）」。本格正是那一枚：改前那行把 `2026-10-10T02:00:00+00:00` 切成 `2026-10-10 02:00` 上屏，而它真实的地方时刻是本设备的十:〇〇。仓里自己对这条缺陷写过话：`{V8}`:{v8_defect} 与它下一句「永远按行程时区排瞬时」`{V8}`:{v8_rule}。

**六、对本单转达的一处更正（不是抱怨，是反例）**

- 已交件的 safebottom 那块（枝 `refs/heads/review/safebottom-0553-r1`，尖 {SAFE}）在账本 `{CTRL}`:39 写了本格「套上去必然改屏上文本」并把本件列进「甲案不成立」；形状探针 `{PROBE}`:{probe_site}（枝 `refs/heads/review/link-0553-r1`，尖 {LINK}）也把本件列进「七枚都不能换成 formatWhen」。
- 两处预测都在说形状会变——这一点我实测一致，不改口。它们没说的是：形状变正是单子第 {order_exception} 行那条豁免适用的情形。实测结果在本块第四节，两 locale 都拿到了屏上读数，屏上不再出现裸 ISO，且那一格从「错六小时」变「对」。所以本件不该继续记在「做不了」那一档；剩下几枚（V10 已交、V12 与 V8Experience 那两枚只排时:分或只有日期、JourneyInboxWorkbench 那两枚是 `<input type="datetime-local">` 的取值）我一枚没碰，它们的判据仍等号令者改那一行。

**七、闸**

| 闸 | 读数 |
| --- | --- |
| 类型（全树 include） | `npm run typecheck:all` 退出码零，在 rebase 后的新基上重跑一次仍是零 |
| 前端构建 | `npm run build` 退出码零，产物 dist 出到 |
| i18n 判据（把 ORD-0533 那条搬进尺） | 本文件所呼的每一枚键在两臂都存在，键数由文件现读、非手抄，坐标 `{ARM}`:{arm_a6} |
| 本车道静态臂 | 10 条判据全绿，坐标 `{ARM}`:{arm_a1}；同一把臂打到建枝基准的原始字节上 5 条转红（`{ARM}`:{arm_a2}），把调用指向一枚不存在的键时该判据点名转红（`{ARM}`:{arm_a6}），不是空判据 |
| 后端 pytest 全套 | **PARTIAL**：本车道未跑完，见末节；本笔零枚后端字节，改动文件面只有前端与本车道量具（对 {BASE} 现读 `git diff --name-only` 里 backend/ 命中零） |

**八、还欠的（不藏）**

1. 后端 pytest：跑到八成余时读数原样是 {pytest_tail} 这段（含 `F` 与 `E` 记号，都落在 `backend/tests/` 下、我没碰的文件里）。要一条完整红集合还得再跑一轮；复跑命令：`cd backend && D:/moodle/CityNexus/backend/.venv/Scripts/python.exe -m pytest -q --continue-on-collection-errors -p no:cacheprovider`。另报一件：现尖上有一枚测试文件在本机 venv 里连收集都过不去，缺 `mcp` 模块，坐标 `{HERMES}`:1，那是线自带的、与本单无关。
2. 本车道未做屏读的分支：`pending` 那一支（空串）没造出真触发，只做了静态断言。
3. 我没改任何他人量具与断言。既有 ORD-0435 那臂现线红的原因是它只勾一枚候选，而 compose 契约要求 place_ids 至少两枚（`{Q4}`:{q4_wait} 与 `{SCHEMA}`:{schema_min} 现读）——这是别人的闸与契约对不上，我只报坐标，不代它改断言。

**九、边界**

边界 A：产品字节一枚文件（`{PANEL}` 一句调用加一行 import，注释另计）；字典零枚改动、契约零枚、他人量具零枚改动、他人枝零枚改动；本车道名下新增静态臂一枚、e2e 只读腿两枚、读数与截图若干枚。
边界 B：权威线零枚直写（线由落地腿移动，我只是推自己名下 `refs/heads/review/短瓦工-0553-r1` 一枚）；force-push 零次；旧枝零枚删除。
边界 C：账本零直写（本块走收件口）；`demo/reset` 零次；共享预览库零次写；本轮 e2e 用三枚自有的 `_e2e_*.db` 一次性库，跑完只删自己造的这两枚；本车道未留任何监听端口（两轮跑批的服务随进程退出）。

**十、复跑**

权威模式两轮，端口 :5511 与 :5512 现读空闲：`cd frontend && unset DEEPSEEK_API_KEY CITYNEXUS_AI_API_KEY; CITYNEXUS_E2E_AUTHORITATIVE=1 CITYNEXUS_AI_ENABLED=false CITYNEXUS_PYTHON=D:/moodle/CityNexus/backend/.venv/Scripts/python.exe CITYNEXUS_E2E_RUN_ID=<新id> CITYNEXUS_DATABASE_URL=sqlite:///<仓库内 _<新id>.db> npx playwright test qoder-duanwagong-0553-batch-row-instant-r1.spec.ts qoder-duanwagong-0553-batch-row-stub-r1.spec.ts`。静态臂：`python {ARM}`，同一把臂加 `--panel <原始字节副本>` 即复现第五节的红。尺自己的红我报过：Git Bash 的 `/tmp` 与 Windows Python 的 `/tmp` 不是同一处，第一次负对照我因此读到旧文件、差点把「臂没牙」当成「码不对」——现改用绝对路径，坐标 `{RULER}`:1。

{closing}
"""

text = BLOCK.format(
    HHMM="0110", PANEL=PANEL, FMT=FMT, DICT=DICT, V8=V8, SCHEMA=SCHEMA, Q4=Q4, ARM=ARM,
    INST=INST, STUB=STUB, EVZH=EVZH, EVEN=EVEN, EVSZH=EVSZH, EVSEN=EVSEN, SHOT_ZH=SHOT_ZH,
    SHOT_EN=SHOT_EN, PROBE=PROBE, DOOR=DOOR, HERMES=HERMES, CTRL=CTRL, RULER=RULER,
    BASE=BASE, MINE=MY, TIP=TIP, CHANG=CHANG, SAFE=SAFE, LINK=LINK, closing=CLOSING,
    pytest_tail=pytest_tail, **A)

out = "D:/moodle/_dwg_ctl10/block_%s.md" % "0110"
io.open(out, "w", encoding="utf-8", newline="\n").write(text)
print("wrote %s bytes=%d lines=%d" % (out, len(text.encode("utf-8")), text.count("\n") + 1))
print(text.split("\n")[0])
