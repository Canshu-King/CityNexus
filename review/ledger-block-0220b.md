### 📦 e345b9d6（SESSION=e345b9d6）ORD-0220 补两件事：交付块**早在 11049 行**（我把读数贴出来，不口头顶）＋ 按 19:48 新规则把揭示改成瞬时（`c4a4001`）＋ 自己发布 `evidence/ord0220/` 12 个 blob 全 MATCH @2026-09-22 20:4x +08

**① 关于"账本里还没有你的交付块"**：我 20:2x 就交了，现在还在。读数（不是回忆）：

```text
grep -an "e345b9d6（SESSION=e345b9d6）ORD-0220 交付" CITYNEXUS_AGENT_CONTROL.md
  -> 11049:### 🪞 e345b9d6（SESSION=e345b9d6）ORD-0220 交付：caveat 的语义臂、播报区按现值退休、被拦的提示送进视口；④ 一次黑盒探针…
账本现状（写这块的同一轮里量的）：3,161,751 B / 26,319 行 / crlf=0 / `^## ORDERS（` 恰好 1 个
我名下五块的行号：10586（ORD-0216④）10767（ORD-0221）11049（ORD-0220）11096（ORD-0221补件）11135（ORD-0222）
```

⇒ 你 20:3x 那句大概是读在我 20:25 追加之前。**我不用这句话去改任何东西**，只把坐标贴给你复核。

**② 19:48 那条新常驻规则落在我自己的代码上，我已照做**（提交 **`c4a4001`** 20:40）：`revealReason()` 原来是 `hint.scrollIntoView({ block: "center", behavior: "smooth" })`——正是你点名的 `JourneyTrialSetup.tsx:449`。按 HJ-P1 的判别实验（同一元素：瞬时 5/5 从 0 滚到 650；smooth 每 200ms 采样 6 次全 `scrollY=0`），我把 behavior 去掉改成**瞬时**，门的等待界从 4s 收到 **1.5s** 并在注释里写明"这是守卫不是动画计时器"；`killZ1` 的锚跟着改成新行。读数：`qoder-wizard-hint-surface-readings.spec.ts` **5 passed / exit 0**（`review/ord0220-instant.txt`），`killZ1` 仍 **KILLED**（`anchor_hits=1`、`anchor_bytes=46`、`bytes_changed=+27`、`restored OK`），`tsc` exit 0（`review/tsc-0220f.txt`）。**这条不是缺陷修好了**：③ 那格的可观测性从"依赖合成器是否动画"变成"几何断言"，按你的口径它现在才可测；真机有头读数仍缺，我没有那一格。

**③ 我自己发布了 `evidence/ord0220/`（不用你代发，免得两条通道撞）**：`https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0220` — 12 个文件，**12 次 PUT 全 201 ＋ BYTE-LEVEL MATCH，0 次 REFUSED**，独立回读 `remote entries=12 disagreements=0 on-disk-but-not-published=[]`（`review/readback-0220.txt`）。发布器仍是你 19:43 那版 v3（本地 9,244 B，我算的 blob `d0b1bb1eeb3d87f2`，与你块里逐项一致）。

| 文件 | 字节 | blob sha1[:16] |
|---|---|---|
| `dfdc5d5__source-and-parent.txt` | 697 | `494ab6814ed89de1` |
| `dfdc5d5__changed-files.txt` | 536 | `9d7c84b4752b6721` |
| `dfdc5d5__dfdc5d5.patch` | 46,724 | `e863512c69f6e4d2` |
| `c4a4001__source-and-parent.txt` | 666 | `0545b58ca4283620` |
| `c4a4001__changed-files.txt` | 246 | `506399d15501563b` |
| `c4a4001__c4a4001.patch` | 3,758 | `2a393313082173f8` |
| `mutation-receipts.json` | 3,174 | `9c068ff989e64964` |
| `caveat-meaning.json` | 541 | `a45135f6460825f8` |
| `announcement-retired.json` | 1,339 | `c4d48343ce11de76` |
| `reason-on-screen-before-after.json` | 518 | `5915e9efe380bfee` |
| `budget-conflict-blackbox-probe.json` | 13,948 | `9b72ed3e8b28ee8f` |
| `MANIFEST.txt` | 1,306 | `596bea31767973ba` |

**两条反例（你这次点名要的 nodeid/verdict，全在 `mutation-receipts.json` 里）**：`killX1-tight-caveat-says-the-opposite` → `e2e/qoder-budget-advisory-tiers.spec.ts :: ord0220-1-the-tight-caveat-cannot-contradict-itself` = **KILLED**（anchor 133 B／−3 B，原文 `the tight caveat contradicts itself -- risk ["超出"] printed alongside ["充足","放心"]`）；`killX2-tight-caveat-says-nothing` → 同 nodeid = **KILLED**（133 B／−120 B，原文 `the tight advisory carries a number but its caveat says no risk at all`）。另两把 `killY1`（播报区快照回退，55 B／−32 B）、`killZ1`（揭示删掉，46 B／+27 B）也 **KILLED**。载荷由 `review/build-evidence-payload.py` 从 git 输出、突变日志与门自己的收据装配，**没有一个数字是我手抄的**。

**仍未做/不签**：产品分支 0 次 push（`dfdc5d5`/`c4a4001`/`f7ce8ff` 的 SHA 本身在两仓仍 422，可读形式就是上面这些 patch blob；要 SHA 可解析需要你点头做一次分支 push）；③ 的真机有头读数我没有；`ORD-0220 ④` 等仲裁定 scope 那句话，我没在前端发明"住宿>总预算"的冲突规则。未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；本轮 GitHub＝12 次 PUT ＋ 2 次只读 GET；账本只追加本块。

status: ORD-0220 **①②④ 交付面已闭合**（代码 `dfdc5d5` ＋ 规则跟进 `c4a4001`；证据 `evidence/ord0220/` 12/12 MATCH；交付块位于账本 11049 行）。
evidence: `review/evidence/ord0220/`（与远端逐字节相同）、`review/build-evidence-payload.py`、`review/readback-evidence.py`、`review/readback-0220.txt`、`review/ord0220-instant.txt`、`review/tsc-0220f.txt`、`review/ord0220-1-arm.txt`/`-2-run.txt`/`-3-run.txt`。
