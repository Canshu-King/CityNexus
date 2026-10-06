import io, os, subprocess, sys, time

LIVE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
OUT = r"D:\moodle\_qoder_ledger_inbox\6efab655_%s.md" % time.strftime("%H%M")

TIP = "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
BUNDLE = "fa0276edc214c0534a963a61b92d2438daf40834"
INSTR = "2bb25d5ea434f6f8218449fb8dc48f330ae09f92"
CRUMB = "758a341ec3f0ba18089dc024e27569b7894787b5"

body = u"""### 6efab655 · 号令者实例 A · 打卡那格在真机上量到第二击的拒答句；顶栏那手五屏两臂亲测；另把 C2 名单开成两单

**〇、栈与代次（三证齐，全部现读）**

- 权威尖现读 `@@TIP@@`（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1`，同一分钟回读）。
- 被服务的字节就是磁盘的字节：入口件 `index-BW2_ds1t.js` 两侧同为 1623134 字节、sha256 头十六位 `780bdef73784a61d`（件 `@@BUNDLE@@` 的 `entry_asset` 段，blob 见本块第一节末）。
- 私有口两枚：接口 `127.0.0.1:8811`、静态 `127.0.0.1:49811`；`netstat -ano -p TCP` 里这两行 LISTENING 的 PID 父链各指向我自己起的子进程（同一件 `stack` 段）。
- 库：`D:/moodle/_qoder_cmdr_priv_0437seed.db` 以 `mode=ro` 打开再 `src.backup(dst)` 复制成 `D:/moodle/_qoder_cmdr_stack_d107131/cmdr_stack_copy.db`；共享预览库一字未动。
- 分母：那枚库 142 程、其中 45 程有排程（`select count(*) from journeys` 与带 `journey_legs` 的子查询，件 `@@BUNDLE@@` 的 `stack` 段）；本轮读的是其中 24 段那一程。
- **自报一件我自己的仪器错**：第一版快照只 `git archive` 了 `backend`，漏了 `data/`，于是 `GET /api/v1/journeys/{id}/experience` 回 http_status=500、五屏全量成空分母（`backend/app/stay_mobility.py:160` 那行读 `data/v9/city_operations.json`）。这不是产品缺陷，是起栈件的缺件。已在 `cmdr_stack_launch_r2.py` 上加了前置闸（缺那枚 json 就 ABORT），并拿一枚只改快照路径的反件验过它真的红（反件 rc=1，判语点名缺的文件）。

**一、顶栏那手（我落的 breadcrumb r2）在屏上验收**

- 中文臂五屏逐字全中、英文臂五屏逐字全中，空分母零屏、页面异常零次；读数件 blob `@@BUNDLE@@`（47862 字节，`readings` 段里 `_crumb_zh_d107131_r2.json` 与 `_crumb_en_d107131_r2.json` 两份）。
- 源码侧同代次对读：路由白名单在 `frontend/src/app/V8Experience.tsx:1938`，四枚键 `nav.trash`、`nav.access`、`nav.import`、`nav.footprints` 在 `frontend/src/i18n/LocaleContext.tsx` 里各两份（中文与英文），所以 `t()` 不会退成键名。

**二、我名下那格：打卡入口定位 + 第二击拒答（销账）**

- 入口在 `/v8/trips` 那一屏，中文臂三枚「打卡」按钮（`/v8/hub`、`/v8/map`、`/v8/stay`、`/v8/live` 四屏零枚；逐枚几何在件 blob `@@BUNDLE@@` 的 `readings/_chk_zh_d107131.json`）。
- 三枚的纵坐标都在 844 像素高的视口之外（读数里是 860、1017、1174 像素），所以我上一版尺按原坐标点击得到的「点了没反应」是仪器错、不是产品读数；这一版先 `scrollIntoView({block:'center'})`、再证中心命中自枚为真（`centre_hit_self: true`，cy=422 像素）才点。
- 连点两下：两次 POST 的正文是同一枚 activity（id 在件内），第一回 http_status=201、第二回 http_status=409；两臂各一次同形（件 blob `@@BUNDLE@@`，`_dbl_zh_d107131.json` 与 `_dbl_en_d107131.json`）。
- 屏上画出来的那句（中文臂逐字）：这一站已经打过卡了（服务器记的是 10月5日 15:35），这次没有再盖一枚，行程里还是原来那一枚。
- 英文臂同形逐字：This stop is already stamped (5 Oct, 15:31); nothing new was written — the trip keeps the stamp it had.
- 载体不是裸文字：`p.cn-stop-checkin__notice`，带 `role="status"`，渲染尺寸 272 × 51 像素 ⇒ 读屏听得见，不是只画给眼睛看（件 blob `@@BUNDLE@@`，`_refusal_announce_zh_d107131_r3.json` 的 `probe.ancestor_chain`）。
- 文案出处：`frontend/src/features/checkin/checkinCopy.ts:43` 那支带 `{moment}` 的中文句，本轮第一次在真屏上量到它带着服务器时刻画出来。
- 具名仪器缺口（别当成已完备）：第二击我没记 `elementFromPoint` 落在哪个元素，所以「同一枚 activity 被点两次」是从两次 POST 正文相同推出来的，不是从命中点推出来的。

**三、三块新到的件，我的裁**

- 车道 82f55d8a 的 `refs/heads/review/82f55d8a-breadcrumb-fix-r1` = `@@CRUMB@@`：**同一格线上已有**（第一节那四行就是我落的 breadcrumb r2），它这轮十次读数我当验收证据收下，不再落第二遍；本格判 CLOSED。
- 车道 8ac89982 的 C2 名单（零产品字节、只出名单）→ 开两单，判据沿用它块里那两条：
  - **ORD-0572**：底栏四枚路由键 `nav-hub`、`nav-trips`、`nav-map`、`nav-me` 缺的是选中态；给命中路由那枚加 `aria-current="page"`，渲染形制在 `frontend/src/app/V8Experience.tsx:2112`。验收要正对照：未命中那三枚必须仍然没有 `aria-current`，且四枚可见文字一字不变。
  - **ORD-0573**：trips 四枚 tab 的两件事——内联双语字面要换成词表键（`frontend/src/app/V8Experience.tsx:2237` 那行数组里的 `{zh ? item.zh : item.en}`），以及 `role="tab"` / `aria-selected` / 面板侧 `role="tabpanel"` 三样都缺（容器 `frontend/src/app/V8Experience.tsx:2317` 已有 `aria-label`）。验收要屏上读数：切换 tab 后 `aria-selected="true"` 必须只在一枚上。
- 车道 1d64acf5 报的「两侧都没有内容也判绿」那一形：判它是**仪器债、不是产品缺陷**，点它单——先补一枚该红的那一次（把两侧都清空的夹具喂进它自己那把尺，看它是否仍然判绿），再谈改判语。

**四、没改善的部分（具名到格子）**

- ORD-0520 屏侧那格本轮仍未做：`NOT_REACHED_BY_CMDR`（本轮时间花在起栈与两格真机读数上）。
- 闭合查找尺还没接进落地门：`NOT_IN_GATE_YET_BY_CMDR`。
- 我的机词普查白名单仍缺 `JSON` 一枚，所以那族读数偏高（偏保守，不会漏判）。
- 新开的 ORD-0572、ORD-0573 还没有字节落地，用户此刻在屏上看不见任何新变化；本轮我只销掉了自己名下那格，并把一格的验收证据换成真屏读数。

**五、件与坐标**

- 读数件：`evidence/cmdr-checkin-refusal-20261005/readings_bundle_r1.json`，blob `@@BUNDLE@@`，47862 字节，`BYTE-LEVEL MATCH`。
- 仪器件（四把尺与起栈件合订）：`evidence/cmdr-checkin-refusal-20261005/instruments_r1.txt`，blob `@@INSTR@@`，29306 字节，`BYTE-LEVEL MATCH`。
- 现尖 `@@TIP@@` 上本轮零产品字节改动、零 ref 移动（只 `git ls-remote` 读、`git archive` 只读导出）。
"""
for _k, _v in (("@@TIP@@", TIP), ("@@BUNDLE@@", BUNDLE), ("@@INSTR@@", INSTR), ("@@CRUMB@@", CRUMB)):
    body = body.replace(_k, _v)
assert "@@" not in body, "unfilled token left in the block"

closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
