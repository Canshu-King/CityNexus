import io, os, time

LIVE = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
STAMP = time.strftime("%H%M")
OUT = os.path.join(r"D:\moodle\_qoder_ledger_inbox", "6efab655_" + STAMP + ".md")

TIP = "aac1142e1d25aab0a5bb4fbaa204f3a90668bd0f"
PICK = "2ea7284c8731538bd53aa822b7e0eb501e4280f3"
SELF = "7c49bb733bda982a0eaa0a642b62104f565f73af"
ARMSRC = "cd9883da1cce5fceec725f63cf9e1c2bc1d98362"
OLDPICK = "0c4208d88a05a9ead2cc1b34e85f893a68af3485"

body = u"""### 6efab655 · 号令者实例 A · 裁一条我自己那把尺：它判红的是个项目决定保留的形状，所以不进门；进门的换成"后端写得出的名字必须有词表行"这把覆盖臂

**〇、接班现场（应用重启之后全部现读）**

- 尖未动：`refs/heads/mirror/integration-frontend-apple-pass1` = `@@TIP@@`（我 01:36 那一笔 ORD-0572 之后没人再落）。
- 收件框待插零枚、拒零枚；盘余量九点六 GB；监听在听的五枚：`:4783`（手机链静态口，我 01:30 起复的那扇）、`:4799`（BB 机）、`:4820`（工地板）、我这台的 `:8813` 与 `:49813`。
- 车道动态：8ac89982 已 ack ORD-0572 与 ORD-0573 两单并说 C2b 判据沿用了；82f55d8a 已 ack ORD-0576，正在算"导入期抛错的枚数与默认配置能收到的条数之间那笔差"。

**一、为什么我不把闭合查找尺接进落地门（改判，具名理由）**

- 我那把 `cmdr_pick_closed_lookup_r1.py`（旧发布件 blob `@@OLDPICK@@`）对现尖判 RED：它认定 `pick()` 未命中支 `return rawChannel(value, zh);` 是"把调用方的入参回吐"。
- 我按常设先打印了目标实有内容再判：那枚 `rawChannel` 不是裸回吐，它把值包进一句人话——`frontend/src/lib/displayVocabulary.ts:178` 起的那段，中文写「这台服务器写的：…」，英文写 "as this server wrote it: …"。而 ORD-0551 的裁语本来就是**补覆盖**（后端写得出的每条名字都给它一行词表），不是拆掉这层兜底；我那枝"闭合查找"的候选当时按「证据件归档、产品字节以线上版为准」处理，没落。
- 结论：把这把尺当门臂，会让此后每一次落地都红在项目**决定保留**的形状上——这正是我拒绝别人的那种假红（两个互相抵消的错谓词比一个更危险）。所以它降级为 advisory：谁想看兜底支的形状可以跑，但门不认它的红。判红读数已发布：blob `@@PICK@@`（2368 字节，含三臂与现尖逐枚 return 行）。

**二、换进门的臂：词表覆盖臂（后端可写名 ⊆ 词表键）**

- 新臂 `cmdr_gate_vocab_covered_arm_r1.py`，源码已发布：blob `@@ARMSRC@@`（4986 字节）。它管的族两枚：`RUNTIME_IDENTITY`（后端 `backend/app/agent/runtime_identity.py:15` 起那四条）与 `MOBILITY_FACT_QUALITY`（后端 `backend/app/replanning/provider_snapshots.py:13` 起那三条）。
- 对现尖跑：判 PASS——两族分别是后端可写四条对词表四行、后端可写三条对词表三行，缺行零枚、词表多出行也零枚。
- 该红的那一次：把 `RUNTIME_IDENTITY` 的 `NOT_CONFIGURED` 一行从词表里摘掉再评同一枚尖，臂判 FAIL 并点名 `RUNTIME_IDENTITY/NOT_CONFIGURED`；`arm_discriminates: true`，整件自测输出已发布：blob `@@SELF@@`（789 字节）。
- 三条形状性约束写死在臂里，防它单向致盲：后端读不到、后端一枚名字都提不出、词表解析成空——任一种都判 ABORT 而不是 PASS（空分母不算通过）。

**三、我名下那格的改判**

- 原来挂着的那格写的是「闭合查找尺未接进落地门 `NOT_IN_GATE_YET_BY_CMDR`」。按第一节它**不该**进门，所以那格按新形状收口：进门的是覆盖臂，且从下一次落地起我在落地后立刻跑它，红就不算收口、绿要在块里带 blob。本格判 CLOSED（换了判据，不是原样做完——这句话要说在前面）。
- 顺带一条给两扇号令者的常设：落地后跑 `python cmdr_gate_vocab_covered_arm_r1.py --rev <刚落地的尖>`，退出码零才算这一手干净；退出码非零要在块里具名哪一族缺哪一行。

**四、没改善的部分（具名）**

- 本轮权威线未动、零枚候选落地（新交付只有 0afdb49b 的 `review/0afdb49b-copy-coverage-r1` 一枚新枝，是读数件不是产品字节；45d25bfb 的 ORD-0553 r12 我也还没复算）。
- ORD-0573、ORD-0574、ORD-0575、ORD-0576、ORD-0577 五单等车道交件；用户此刻在屏上看不见任何新变化（底栏选中态那笔已在尖上，但手机仍停 day33 那一代）。
- 花费面那句在真屏仍 `NOT_REACHED_BY_CMDR`；机词普查白名单仍缺 `JSON` 一枚；我本轮依旧零用例执行（只收集）。
"""

for k, v in (("@@TIP@@", TIP), ("@@PICK@@", PICK), ("@@SELF@@", SELF), ("@@ARMSRC@@", ARMSRC),
             ("@@OLDPICK@@", OLDPICK)):
    body = body.replace(k, v)
assert "@@" not in body
closing = io.open(os.path.join(LIVE, "CLOSING_LINE.txt"), encoding="utf-8", newline="").read().strip()
text = body.rstrip() + "\n\n" + closing + "\n"
io.open(OUT, "w", encoding="utf-8", newline="").write(text)
print("wrote", OUT, len(text.encode("utf-8")), "B")
