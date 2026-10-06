import io, os, time

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

TIP = "b2fccfdf2728bbb025c3c09db36ce5ed9401ee4c"
RB = "b7cd3ea847fbd513df85028ec08281c21faede1c"
D34 = "0293e5c1cf9be4ea4e7d14005e14c508cb3f528b"
R8 = "d107131c6f6e65d9f207f6bf1b563d1cc8877f89"
B66 = "b66e38a4a01fc66eef4b8c8981b84954e911fec8"

body = u"""### 6efab655 · 号令者实例 A · SYNTHETIC_DEFAULT 那格在现尖上再钉一次（带词表行与渲染点）；给 1ba48dbf 一枚可粘贴的改法；我方导出件清掉十二枚

**一、督办点的这一格：现尖上它仍然是修好的，不是待办**

- 词表行现读 `frontend/src/lib/displayVocabulary.ts:165`，那一枚枚举配的是中文「合成默认值，不是供应商给的」与英文 "a synthetic default, not a provider reading"，同段紧邻就是那张表的收尾括号。
- 屏侧走 `frontend/src/features/planning/PlanRankingPanel.tsx:144` 那行的 `mobilityFactQualityLabel(row.evidence.worstQuality, locale)`，也就是它只能经词表出字，没有 labelled-raw 那一支。
- 判语出处不是我此刻的记忆：账本里我那块闭单块（块头「四、SYNTHETIC_DEFAULT 那格再钉一次」，现读在 `D:/moodle/CITYNEXUS_AGENT_CONTROL.md:20751`）与插入回执 `_processed/6efab655_1925.md.inserted_*` 同指一事。
- 派单侧请办一件事：下次把这格派给我之前，先在账本里数一次我的闭单块枚数（`grep -c` 那一句的读数写进派单行）。这格我本轮零改动，因为无字节可改。

**二、车道 1ba48dbf 两连拒：具名指引（可整行粘贴，我不改它的字）**

- 现场：门在 16:58 与 17:39 两次拒它两块，退出码九，拒的都是同一形——把**入口 JS 的磁盘字节指纹**当成四十位坐标写进行文（第一块写的是 sha1 三f开头那枚，第二块写的是 sha1 一三五七c开头那枚）。四十位逐字出现时门必须能 `git cat-file` 取回，而文件指纹永远取不回，所以这不是门苛刻，是那一行没有可回读坐标。
- 请把它那一行整行换成下面这枚（我已发布过同一代次的指纹件，直接可引）：
  - `- 现读权威线 refs/heads/mirror/integration-frontend-apple-pass1 = @@TIP@@；两臂两趟跑的是同一份产物：入口 index-DLbc3Q3N.js = 1624131 字节，与号令者发布件里的代次指纹逐字相同（件 blob @@RB@@ 的 generation_proof 段，同段还带 sha256 头十六位 0ad6efd8853b974d）`
- 常设口径（对所有车道）：要断言"我读的就是这一代产物"，两条合法写法——① 同行给一枚可 `git cat-file` 的四十位（发布过的证据件 blob 最省事）；② 同行给 `path:line`。只报磁盘 sha1/sha256 而没有任何一枚可取回坐标，门必拒；先把指纹落成件再发布、再引它的 blob，比改判语便宜。

**三、我方派生件清扫账（只删自己的、非在服务的）**

- 一把新尺 `cmdr_build_sweep_r2.py`：保留名单不靠记忆，从**在跑进程的命令行**里读 `--dist` 参数得出；本轮据此留下五枚在服务或一小时内的导出树，退役十二枚旧的。盘余量从九点九 GB 回到十一 GB。
- 每一枚退役树的 `*_info.json` 全部留下，逐枚可一键重出（`cmdr_build_bundle_r1.py --sha <那枚四十位>`）。三枚点名给回：手机链上一代候选 `_build_day34` 的源是 `@@D34@@`、`_build_cmdra_0553_r8` 的源是 `@@R8@@`、`_build_b66e38a` 的源是 `@@B66@@`；谁要用哪一枚，报一声我或自己重跑那一条命令即可，字节形状不变。
- 反件先咬了我自己一次：第一遍跑在卸载 junction 那一步 ABORT（rc=3，`cmd /c rmdir` 被我多套了一层引号，报"文件名、目录名或卷标语法不正确"），**零枚删除、零枚损坏**；去掉引号才是第二遍，跑完候选数归零（幂等）。junction 的处置按常设：先普通 `rmdir` 解链，解完仍见反解析点就整棵不删。
- 别人名下的树、worktree、缓存、回收站：本轮零枚触碰。

**四、本轮权威线与落地**

- 权威线本轮未动，仍是 `@@TIP@@`（我 16:58 那次落地之后没有第二笔可落：表里其余待落枝我按「做完一件交一件」留着，逐枚要先过我的只读复算）。
- 收件框本轮读数：两枚待插、两枚被门拒（就是第二节那两枚），插入了零枚；镜像在 16:58 那次是 BYTE_LEVEL_CONFIRMED。

**五、没改善的部分（具名）**

- ORD-0575（被正文盖住的那枚提交键）仍零字节落地；ORD-0572、ORD-0573、ORD-0574 三单车道未交件。
- 花费面那句在真屏上仍 `NOT_REACHED_BY_CMDR`（分母缺，判据见上一块第二节）。
- 闭合查找尺接进落地门仍 `NOT_IN_GATE_YET_BY_CMDR`；机词普查白名单仍缺 `JSON` 一枚。
- 手机链仍是 day33 那一代，本轮两笔落地对用户手机不可见；换代是人类的决定，我没在留言口追加新请求。
"""

for k, v in (("@@TIP@@", TIP), ("@@RB@@", RB), ("@@D34@@", D34), ("@@R8@@", R8), ("@@B66@@", B66)):
    body = body.replace(k, v)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
