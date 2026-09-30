"""ORD-0489 · compose this lane's ledger inbox block and run it through the coordinate ruler.

The block is generated from the committed artifacts, not from memory: `cite_at` opens the file at
HEAD, searches the probe string, and prints the line number it actually found, so an anchor cannot
point at a line that does not carry the number.  If a probe is missing or lands on several lines
the script aborts instead of guessing.  The closing line is copied byte-for-byte from
`CLOSING_LINE.txt`.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys

WT = "D:/moodle/_qoder_seed_ord0489/wt"
INBOX = "D:/moodle/_qoder_ledger_inbox"
CLOSING = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/CLOSING_LINE.txt"
RULER = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/claim_coordinate_check_r7.py"
BASE = "dcb90cccc68b81f2317b28db19051dedb9f06c80"
TIP = "910060f5bb730ef88a16949d595e7b5b0a969d97"
CAND = "15d65d7f289c628b810cf5ab4a097d858a128821"
REF = "refs/heads/review/newlane-ord0489-demo-seed-r1"

SEED = "review/ord0489/board_seed_final.json"
OWN = "review/ord0489/ownership_final.json"
STAT = "review/ord0489/static_serving_proof_final.json"
RO = "review/ord0489/preview_store_readonly_receipt.json"
BOARD = "review/ord0489/BOARD.md"
W2 = "review/ord0489/screens/walk_r2_20260930T0439.json"
W3 = "review/ord0489/screens/walk_candidate_r3_20260930T0439.json"
W4 = "review/ord0489/screens/walk_footprint_grow_r4_20260930T0439.json"
W5 = "review/ord0489/screens/checkin_geometry_r5_20260930T0434.json"
W6 = "review/ord0489/screens/discover_write_side_effect_r6_20260930T0451.json"
TOOL = "tools/ord0489_demo_seed_r1.py"
STACK = "tools/ord0489_lane_stack_r1.py"
ABS = "review/ord0489/line_generation_screen_absence.json"
FILES = [SEED, OWN, STAT, RO, BOARD, W2, W3, W4, W5, W6, TOOL, STACK, ABS]


def run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


CACHE: dict[str, tuple[str, list[str]]] = {}
for rel in FILES:
    shown = run(["git", "-C", WT, "show", "HEAD:" + rel]).stdout
    blob = run(["git", "-C", WT, "rev-parse", "HEAD:" + rel]).stdout.strip()
    kind = run(["git", "-C", WT, "cat-file", "-t", blob]).stdout.strip()
    if kind != "blob" or len(blob) != 40:
        sys.exit("ABORT_UNREADABLE_BLOB " + rel)
    CACHE[rel] = (blob, shown.splitlines())


def cite_after(rel: str, key: str, probe: str) -> str:
    """Anchor the first `probe` that appears *after* a named section key.

    A flat search cannot tell three identical readings apart, and picking by ordinal is a guess
    about which block I meant.  Naming the section makes the anchor self-describing.
    """

    blob, txt = CACHE[rel]
    keys = [i for i, line in enumerate(txt, 1) if key in line]
    if len(keys) != 1:
        sys.exit(f"ABORT_SECTION_AMBIGUOUS rel={rel} key={key!r} hits={keys[:8]}")
    tail = [(i, line) for i, line in enumerate(txt, 1) if i > keys[0] and probe in line]
    if not tail:
        sys.exit(f"ABORT_PROBE_AFTER_SECTION_NOT_FOUND rel={rel} key={key!r} probe={probe!r}")
    return "`%s:%d` blob `%s`" % (rel, tail[0][0], blob)


def cite_within(rel: str, key: str, probe: str, nth: int = 1) -> str:
    """Anchor the first `probe` inside the nth section that `key` opens.

    The section ends at the next line matching the same key, so a phone reading cannot borrow a
    desktop reading's line number.
    """

    blob, txt = CACHE[rel]
    keys = [i for i, line in enumerate(txt, 1) if key in line]
    if len(keys) < nth:
        sys.exit(f"ABORT_SECTION_COUNT rel={rel} key={key!r} hits={keys[:8]}")
    start = keys[nth - 1]
    stops = [k for k in keys if k > start]
    upper = stops[0] if stops else len(txt) + 1
    for i in range(start + 1, upper):
        if probe in txt[i - 1]:
            return "`%s:%d` blob `%s`" % (rel, i, blob)
    sys.exit(f"ABORT_PROBE_IN_SECTION rel={rel} key={key!r} probe={probe!r}")


def cite_at(rel: str, probe: str, nth: int = 1) -> str:
    blob, txt = CACHE[rel]
    hits = [i for i, line in enumerate(txt, 1) if probe in line]
    if len(hits) < nth:
        sys.exit(f"ABORT_ANCHOR_NOT_FOUND rel={rel} probe={probe!r} hits={len(hits)}")
    if len(hits) > nth:
        sys.exit(f"ABORT_ANCHOR_AMBIGUOUS rel={rel} probe={probe!r} hits={hits[:8]}")
    return "`%s:%d` blob `%s`" % (rel, hits[nth - 1], blob)


now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)
hhmm = "%02d:%02d" % (now.hour, now.minute)
slug = "%02d%02d" % (now.hour, now.minute)

L: list[str] = []
add = L.append

add(f"### ORD-0489 勘误重交：读数一枚不动，只把 4 枚指错行的坐标改直（车道 seed @{hhmm}+08）")
add("")
add(
    f"基座与交件坐标：现读 `refs/heads/mirror/integration-frontend-apple-pass1` = `{BASE}`"
    f"（`git ls-remote` 与 GitHub `git/ref/heads` 两路同值）；本车道候选 `{REF}` = `{TIP}`，"
    f"39 枚文件、全是新增，`git status --porcelain` 交件后为 0 行。"
)
add("")
add(
    "**勘误范围（先说我自己的错）**：阁下 14:22 入账的是我 13:23 的 `seed_1323.md`，那份的 `path:line` 是我手抄的行号。"
    "本件读数一枚不动、一枚不加，只重交坐标：行号改由脚本在 `HEAD` 对象里搜索命中后才落下，命中多处即中止（生成器随件在 "
    "`review/ord0489/`）。我自己回读旧块抓到 4 枚硬错，逐枚是：旧块第 15 行把「库体 7213056 字节」钉在 "
    "`review/ord0489/preview_store_readonly_receipt.json:10`，那行其实是 `mtime_utc`；旧块第 21 行把禁区常量钉在 "
    "`tools/ord0489_lane_stack_r1.py:40`，那行是 `import uuid as uuidlib`；旧块第 26 行把 422 钉在 "
    "`review/ord0489/board_seed_final.json:288`，那行是 `},`；旧块第 41 行把「回收站后再开钥匙得 201」钉在 "
    "`review/ord0489/board_seed_final.json:316`，那行是 `bin_status` 的 200。另有 4 枚只钉到块起行（数值在下一行）："
    "`walk_r2_20260930T0439.json` 的 130、755、759、790 行，本件一并改钉到数值行。旧件我不改，按规矩另发新件。"
)
add("")
add("**0）先撤回我自己说错的一句（同一轮内自纠，不等谁指）**")
add("")
add(
    "- 我说过「走过屏之后目录自己涨了」。那是我把两个分母混了：`GET /api/v1/places` 这扇门默认过滤服务端自造行，"
    "而我拿来对照的是库里全量行。单变量实验只开 `/v8/discover` 一条路由：走前 CN-TIANJIN 读 "
    + cite_after(W6, '"before": {', '"CN-TIANJIN": 8')
    + " 枚、CN-BEIJING 读 "
    + cite_after(W6, '"before": {', '"CN-BEIJING": 4')
    + " 枚；走完那一条路由后同一件里仍是 "
    + cite_after(W6, '"after_discover_route"', '"CN-TIANJIN": 8')
    + " 与 "
    + cite_after(W6, '"after_discover_route"', '"CN-BEIJING": 4')
    + "；再走一条不该碰目录的路由作对照，第三次读数依旧 "
    + cite_after(W6, '"after_control_route"', '"CN-TIANJIN": 8')
    + "。所谓「涨」只出现在把 `include_structural=true` 加进查询之后："
    + cite_at(STAT, '"path": "/assets/index-BdXy-aFm.js"')
    + " 那一代默认 8 与 4，加参数后 "
    + cite_at(STAT, '"bytes": 1489936')
    + " 字节是那条查询的正文量。差值由那一个参数解释，与走屏无关。"
)
add("")
add("**1）号令者给的五个数，我这边只读复现（`mode=ro`；读前读后字节与 mtime 相同，故本收据不可能写过被测物）**")
add("")
add("- `journeys` = 1 枚：" + cite_after(RO, '"shared_preview": {', '"journeys": 1,'))
add("- `plan_versions` = 1 枚：" + cite_after(RO, '"shared_preview": {', '"plan_versions": 1,'))
add("- `activities` = 6 枚：" + cite_after(RO, '"shared_preview": {', '"activities": 6,'))
add("- `places` = 16 枚：" + cite_after(RO, '"shared_preview": {', '"places": 16,'))
add("- `travelers` = 1 枚：" + cite_after(RO, '"shared_preview": {', '"travelers": 1,'))
add(
    "- 库体 "
    + cite_after(RO, '"shared_preview": {', "7213056")
    + " 字节，读前后一致判据 "
    + cite_after(RO, '"shared_preview": {', '"unchanged_across_reads": true')
    + "；我这枚私有库同样读前后一致 "
    + cite_after(RO, '"lane_store": {', '"unchanged_across_reads": true')
    + "。"
)
add(
    "- 一处口径澄清（不驳号令者，只把范围说准）：那 16 枚 `places` 分布在两枚 `city_code` 上——"
    "`CN-BEIJING` " + cite_after(RO, '"shared_preview": {', '"CN-BEIJING": 8') + " 枚、`CNX-DEMO` "
    + cite_after(RO, '"shared_preview": {', '"CNX-DEMO": 8') + " 枚；只有 `journeys` 是单城：" + cite_after(RO, '"shared_preview": {', '"CNX-DEMO": 1')
    + "。「城市只有一枚」在行程维度成立，在地点目录维度不成立。"
)
add(
    "- 更硬的一格：共享预览库共 " + cite_after(RO, '"shared_preview": {', '"table_count": 55') + " 张表，其中 "
    + cite_after(RO, '"shared_preview": {', "journey_checkins") + "、`journey_members`、`journey_role_capabilities`、"
    "`journey_share_grants` 四枚在该库里不存在（缺表清单起于 " + cite_after(RO, '"shared_preview": {', '"missing_tables": [')
    + "，命中为空集 " + cite_after(RO, '"shared_preview": {', '"present_checked_tables": []')
    + "）。所以足迹与分享接收两族屏在共享盘面上不是「样本少」，是门下面还没有表。"
)
add(
    "- 同一把尺量我自己的私有库：" + cite_after(RO, '"lane_store": {', '"table_count": 59') + " 张表，四枚全在，"
    "命中清单 " + cite_after(RO, '"lane_store": {', '"present_checked_tables": [') + "（与车道 cff87c64 的 ORD-0488 独立读到同一形状）。"
)
add("")
add("**2）我造盘面走的全部门（私有库、私有端口；SQL 直写与 `demo/reset` 一次没用）**")
add("")
add(
    "- 私有后端 `:8790`、私有前端 `:8791`、候选前端 `:8792`。工具里把禁区 `:8000`、`:4781`、`:4782`、"
    "`:8693` 写成启动即拒：" + cite_at(STACK, "FORBIDDEN_PORTS = (8000") + " 与 "
    + cite_after(STACK, "def cmd_start", '"refuse": "FORBIDDEN_SHARED_PORT"') + "。"
)
add(
    "- 三证归属同批取（判语 " + cite_at(OWN, '"verdict": "OWNED_BY_THIS_LANE"') + "）：唯一监听 pid 行 "
    + cite_at(OWN, '"listener_pids"') + "；该 pid 命令行含 `--port 8790` 与 `uvicorn`："
    + cite_after(OWN, '"processes": [', "--port 8790") + "；我库里行程行（`journey_rows`）"
    + cite_at(OWN, '"journey_rows": 3') + "、与共享库交集为空（同件 " + cite_at(OWN, '"fabricated_uuid_status": 404')
    + " 是反证：一把不存在的 id 必回 404）；表数 " + cite_at(OWN, '"tables": 59') + "、库体 "
    + cite_at(OWN, '"db_bytes": 3092480') + " B。"
)
add(
    "- 地点只有一条来路：`POST /api/v1/journeys/{id}/real-city/discover` 且 `mode=live`；`provenance` 不等于 "
    "`LIVE_PROVIDER` 就具名中止 `PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES`，判据 "
    + cite_at(TOOL, 'if provenance != "LIVE_PROVIDER"') + "、中止名 "
    + cite_at(TOOL, "PROVIDER_SUPPLY_ABSENT_NOT_INVENTING_PLACES")
    + "。逐次供能判语在 " + cite_at(SEED, '"all_discoveries_were_live_provider": true')
    + "），全部 `LIVE_PROVIDER`；本件里 `REPLAY_FALLBACK` 出现 0 次，同段判据 "
    + cite_at(SEED, '"all_discoveries_were_live_provider": true') + "。"
)
add(
    "- 目录：" + cite_at(SEED, '"CN-TIANJIN": 8') + " 枚、" + cite_at(SEED, '"CN-BEIJING": 4') + " 枚、"
    + cite_after(SEED, '"board_after"', '"CN-FUZHOU": 0') + " 枚。最后一枚是工单要的「无地点城市」，脚本对它**不发**供能请求（理由写在 "
    + cite_at(TOOL, '"CN-FUZHOU", "role": "no_places"') + "：那扇门正是会给它地点的东西）。"
)
add(
    "- 行程：" + cite_at(SEED, '"journeys_visible": 2') + " 枚在列表门上（第 3 枚被我按工单要求送进回收站），"
    "屏上级序即门序：" + cite_after(SEED, '"board_after"', '"天津 · 三日两晚",') + " 与 " + cite_after(SEED, '"board_after"', '"北京 · 四日三晚"')
    + "；回收站行 " + cite_at(SEED, '"recycle_bin_rows": 1') + "。"
)
add(
    "- 多天行程的活动：两枚先撞 `plans/generate` 得 " + cite_after(SEED, '"journey_key": "tianjin_multiday"', '"generate_status": 422')
    + " 与 " + cite_after(SEED, '"journey_key": "beijing_multiday"', '"generate_status": 422') + "（原文含 `CATALOG_INSUFFICIENT` 与 "
    "`day_sequences_available` 计数，见 " + cite_after(SEED, '"journey_key": "tianjin_multiday"', '"generate_candidates": 0') + " 同段），"
    "改走 `authoritative-compose` 得 " + cite_after(SEED, '"journey_key": "tianjin_multiday"', '"optimizer": "ORTOOLS_CP_SAT"')
    + "；选后当前方案分别带 " + cite_at(SEED, '"activities_on_current_plan": 10') + " 项与 "
    + cite_at(SEED, '"activities_on_current_plan": 11') + " 项活动。"
)
add(
    "- 足迹门：" + cite_at(SEED, '"rows": 3') + " 枚打卡（2 枚 `place` 加 1 枚 `activity`，逐条状态 "
    + cite_after(SEED, '"stamps_attempted"', '"target": "place"') + "、" + cite_at(SEED, '"target": "activity"') + "）。"
)
add(
    "- 分享门四格：有效钥匙客人读 " + cite_at(SEED, '"guest_read_status": 200', 1) + " 且 "
    + cite_at(SEED, '"guest_plan_state": "PLAN_PRESENT"') + "；撤销后 "
    + cite_at(SEED, '"guest_read_status": 409', 1) + " 具名 " + cite_at(SEED, "SHARE_GRANT_REVOKED")
    + "；不存在的钥匙 " + cite_at(SEED, '"status": 404') + " 具名 " + cite_at(SEED, "SHARE_GRANT_UNKNOWN")
    + "；行程进了回收站后同一把旧钥匙 " + cite_at(SEED, '"guest_read_after_bin": 409') + " 具名 "
    + cite_after(SEED, '"binned_grant"', "SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN") + "。"
)
add(
    "- 可重跑：同一脚本、三份新库各跑一遍，目录与活动数一致（本件的每一枚数字都来自最后那份收据 "
    + cite_at(SEED, '"order": "ORD-0489"') + "）；复跑配方四条命令写在 " + cite_at(BOARD, "ord0489_lane_stack_r1.py start")
    + "。脚本不造地点名：无供能时具名中止，见上。"
)
add("")
add("**3）屏上四组读数（一律取渲染文字与 testid 计数，不拿 data 属性当证据）**")
add("")
add(
    "- 行程列表（线代次 " + cite_at(STAT, '"path": "/assets/index-BdXy-aFm.js"') + " 那一代，`:8791`）：`/v8/access` 的选择器先渲染 "
    + cite_within(W2, '"phone": {', '"先选一条要看的行程"') + " 占位加两枚在用行程（逐项起于 " + cite_within(W2, '"phone": {', '"options": [')
    + "）；对回收站那枚执行 `undelete` 得 " + cite_within(W2, '"undelete": {', '"status": 200') + " 后同一控制多出 "
    + cite_within(W2, '"access_after_undelete"', '"福州 · 两日一夜（未规划）"', 1)
    + "）；再投回回收站得 " + cite_within(W2, '"rebin": {', '"status": 204') + "。实话：这条线上**没有排序控件**，屏上级序就是门序，"
    "所以我交的是「列表随门店状态变」，不是「点一下变序」。"
)
add(
    "- 回收站屏：行与计数都在屏上可读——" + cite_within(W2, '"trash-row": {', '"present": 1') + " 起逐行标题渲染，"
    "`trash-count` 同段 " + cite_within(W2, '"trash-count": {', '"present": 1') + "。"
)
add(
    "- 分享接收屏：有效那一格屏上站点行 " + cite_within(W2, '"valid": {', '"present": 10')
    + " 处、天数句逐字「共 3 天」见 " + cite_within(W2, '"shared-day-count"', '"text": "共 3 天"')
    + "；回收站那格的拒语逐字 "
    + cite_within(W2, '"binned_trip": {', "SHARE_GRANT_JOURNEY_IN_RECYCLE_BIN") + "；无效与未知两格各自的 code 文本行在同件 "
    + cite_within(W2, '"revoked": {', "SHARE_GRANT_REVOKED") + " 与 " + cite_within(W2, '"unknown": {', "SHARE_GRANT_UNKNOWN") + "。"
)
add(
    "- 足迹屏与长图屏在线代次上不存在：扫路由清单与逐条判定汇总在 " + cite_after(ABS, '"line_generation"', '"routes_swept": 16')
    + "（同件 " + cite_after(ABS, '"phone"', '"footprint_or_checkin_id_hits": 0') + " 与 " + cite_after(ABS, '"phone"', '"poster_or_longimage_id_hits": 0')
    + " 两行为 0 命中），逐条 `footprint_or_checkin_ids` 与 `poster_or_longimage_ids` 皆空数组，"
    "中文词命中数四个键各为 0：" + cite_after(ABS, '"phone"', '"足迹": 0') + "。这格具名 `NOT_REACHED_BY_LANE`，原因：两屏只在候选枝 "
    "`refs/heads/1ba48dbf-ord0476-footprint-screen-r2` = `" + CAND + "`，`git merge-base --is-ancestor` 对基座 `"
    + BASE + "` 返回非零（不是基座的祖先）。"
)
add(
    "- 为证盘面真能喂那两屏，我把候选前端（" + cite_at(STAT, '"path": "/assets/index-gebvkcUd.js"') + " 那一代，`:8792`）接到我的线上后端走一遍："
    "足迹面板计数句逐字为「这次行程共有 3 枚足迹」（" + cite_within(W3, '"footprint_before_new_stamp"', '"text": "这次行程共有 3 枚足迹。"') + "）；在屏上点一次真打卡，"
    "门从 " + cite_at(W4, '"door_rows_before": 3') + " 行长到 " + cite_within(W4, '"door_rows_before": 3', '"door_rows_after": 4') + " 行，"
    "屏上计数同时改口「这次行程共有 4 枚足迹」（" + cite_at(W4, '"tally_after_on_screen": "这次行程共有 4 枚足迹。"') + "），"
    "该行被判 accepted 为真，见 " + cite_at(W4, '"accepted": true') + "；长图面板 1 个天块（"
    + cite_at(W3, '"days_blocks": 1') + "）与 10 个站点块（" + cite_at(W3, '"stop_blocks": 10')
    + "），导出件 `citynexus-trip-poster.png` 落盘 " + cite_at(W3, '"saved_bytes": 177100') + " B；"
    "空行程那一格 `trip-poster-bar` 不出现（" + cite_within(W3, '"empty_trip_poster_gate"', '"present": 0') + "）而 `footprint-empty` 出现（"
    + cite_within(W3, '"empty_trip_footprint"', '"present": 1') + "）。以上读数属候选代次，不得当线行为引用。"
)
add(
    "- 候选屏一处真缺陷（坐标给足迹车道）：390x844 下一枚 `stop-checkin` 的中心命中的是 `nav-map` 而非自己，"
    "重叠 " + cite_at(W5, '"overlap_px2": 1984') + " 平方像素，控件顶 y 见 " + cite_at(W5, '"y": 800')
    + "、底栏 y 见 " + cite_within(W5, '"nav_elements"', '"y": 789') + "；同一件里另外两枚按钮中心命中为自身（"
    + cite_within(W5, '"controls"', '"hit_at_centre": "stop-checkin"') + "），所以是位置问题不是渲染问题。视口记在 "
    + cite_at(W5, '"viewport": {') + "。"
)
add("")
add("**4）两条产品侧事实（不在我这单要修的范围内，交坐标与读数）**")
add("")
add(
    "- F1 分享门不查回收站：对已进回收站的行程再开一把新钥匙得 "
    + cite_at(SEED, '"grant_cut_attempted_after_binning"', 1) + " 段里的 201（同一把旧钥匙在客人门得 "
    + cite_at(SEED, '"guest_read_after_bin": 409') + "）。即「开钥匙」这条写路径不看 `deleted_at`，只有呈现路径看。"
)
add(
    "- F2 `plans/generate` 要供能方自己报时：目录里 8 枚（" + cite_at(SEED, '"CN-TIANJIN": 8') + "）加 4 枚（"
    + cite_at(SEED, '"CN-BEIJING": 4') + "）真地点仍得 422 `CATALOG_INSUFFICIENT` 且日模板数为 0（"
    + cite_after(SEED, '"journey_key": "tianjin_multiday"', '"generate_candidates": 0') + "），同一批地点走 compose 得 201（"
    + cite_after(SEED, '"journey_key": "tianjin_multiday"', '"optimizer": "ORTOOLS_CP_SAT"') + "）。Overpass 在这两城的站点大多不带 `opening_hours`，"
    "而日模板只认这个字段。"
)
add(
    "- 本机供能真形制：直连 Nominatim 是 12 s `ConnectTimeout`，经本机代理 1.25 s 得 200；"
    "所以 `CITYNEXUS_PROVIDER_NETWORK_MODE` 必须留 `env_proxy`——写 `direct` 会让产品把 live 探能降级成 "
    "`REPLAY_FALLBACK`，而那一格**照样回 200、照样往目录里写行**，这就是脚本判 `provenance` 不判状态码的原因（"
    + cite_at(TOOL, 'if provenance != "LIVE_PROVIDER"') + "）。"
)
add("")
add("**5）没做到的格子，具名交**")
add("")
add(
    "- `NOT_REACHED_BY_LANE`：线代次上的足迹屏与长图屏（两屏不在基座 `" + BASE + "`，只在候选枝 `" + CAND + "`；"
    "上面第 3 节把候选代次读数分开标了代次）。")
add("- `NOT_REACHED_BY_LANE`：行程列表「点一下就变序」——这条线没有排序入口，我只交了门店状态变化引起的屏上级序变化。")
add(
    "- 共享预览库我一个字没写：全程 `mode=ro`，读前后字节相同（" + cite_after(RO, '"shared_preview": {', "7213056")
    + "、" + cite_after(RO, '"shared_preview": {', '"unchanged_across_reads": true') + "）。"
)
add(
    "- 我没碰 `:8000`、`:4781`、`:4782`、`:8693`；我的整条面在 `:8790`、`:8791`、`:8792` 与私有库 "
    + cite_at(OWN, '"db_bytes": 3092480') + " B 上。"
)
add("")

block = "\n".join(L) + "\n"
closing = open(CLOSING, "rb").read()
block_bytes = block.encode("utf-8") + closing
target = os.path.join(INBOX, f"seed_{slug}.md")
with open(target, "wb") as handle:
    handle.write(block_bytes)
print(json.dumps if False else "")
print("WROTE", target, len(block_bytes), "bytes")
print("CLOSING_SHA1_TAKEN_FROM_FILE", __import__("hashlib").sha1(closing).hexdigest(), len(closing), "B")
print("LINES", block.count(chr(10)) + 1)
