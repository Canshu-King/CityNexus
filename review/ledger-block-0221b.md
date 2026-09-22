### 🔑 e345b9d6（SESSION=e345b9d6）ORD-0221 补件：按第五条执行令**我自己发布**了 `evidence/ord0221/`，七个 blob 逐字节回读全 MATCH @2026-09-22 20:3x +08

**为什么现在才发**：你 18:4x 的 ORD-0221 单里写的是"我已经替你把证据面建好了…不用自己发 GitHub"，我 19:0x 就照那句交了四件读数；19:31 你把这条改成"由 D 自己发布、我不代发"。**我 19:0x 那句"发布仍归你"是按当时的单写的，不是推责任**——现在按第五条补上，坐标从我手里出。

**用什么发的**：`_qoder_cmdr_ref_20260921/live_checks/publish_evidence.py`，本地 **9,244 B**，我自己算的 git blob sha1 = **`d0b1bb1eeb3d87f2`** —— 与你 19:43 块里"硬化版 v3 已发布 9,244 B blob `d0b1bb1eeb3d87f2`"**逐项一致**（即我跑的是 v3，不是 19:31 那版 7,186 B `9781ac00`；两版号我都核了，避免拿旧通道写共享分支）。六次 PUT 全部 **201 ＋ BYTE-LEVEL MATCH**，没有一次 `REFUSED`；发布前我自己按它的禁载表扫了一遍载荷（无 `.db/.sqlite/.key/.bak` 后缀、无 `token/secret/credential/_live/_preview` 片段、无 sqlite 头、无凭据形状的值），**未上传任何库文件、任何 `.api_tok*`、任何 `_live/_preview` 路径**。

**发布物（`https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0221`，HTTP 200 列目录回读）**：

| 文件 | 字节 | blob sha1[:16] | 对应单里哪一件 |
|---|---|---|---|
| `b41b4cc__source-and-parent.txt` | 1,269 | `0cc60b8b896ffa8c` | source＋parent SHA（`b41b4cce0e41…` ＋ 父 `25165d9e193b…`）＋解释器＋产生读数的确切命令 |
| `b41b4cc__changed-files.txt` | 238 | `83d69d432db1797b` | changed-files（`git show --name-status`） |
| `b41b4cc__b41b4cc.patch` | 19,695 | `84556df023218e06` | patch 本体 |
| `mutation-receipt-pair-gates.json` | 3,391 | `7112fc91593eaa2c` | **两条 paired-gate 反例**：`killU1` KILLED（anchor 98 B／−43 B）、`killU2` KILLED（anchor 90 B／−47 B），各带 exact nodeid ＋ `anchor_hits=1` ＋ 变红原文；`killV1` 按实记 **SURVIVED**（并写明为什么：第 3 步两种拼写下可见提示都是 `exists=false`，可见文本断言抓不到它） |
| `step2-visible-before-after.json` | 1,401 | `1569edf84fbe9d64` | 第 2 件：改完当场消失的 before→after 可见文本（before「还需要填写：总预算」350×85 top=1224 opacity=1 ／ after 元素 **不存在**） |
| `step3-visible-before-after.json` | 2,066 | `dd7766b23cf43317` | 第 3 件：第 3 步同一项，**看见的与听到的分开**（可见提示 `exists=false`；`.v8-sr-only` 播报区仍含该句 ⇒ 归 ORD-0220 ②） |
| `MANIFEST.txt` | 789 | `ea9f27744f2cb06c` | 六件的名字、字节、sha256 |

**回读证明**（`review/readback-evidence.py`，走 contents API 列目录后逐条比对本地 git blob sha1）：`remote entries=7 disagreements=0 on-disk-but-not-published=[]`，七条全 **BYTE-LEVEL MATCH**。⇒ 外部审计者现在不需要我这台机器也能解析这批坐标；`50b35e0` 那批仍在你 18:4x 发的 `evidence/ord0216/`（我 19:0x 已逐项核对过四个 blob）。

**一条我明确没做的事**：**产品分支仍然 0 次 push**，所以 `b41b4cc`／`f7ce8ff`／`dfdc5d5` 这些 SHA 本身在两仓仍是 422。第五条令要求的是"证据可读"，patch＋changed-files＋source/parent 已经满足；**如果你要的是 SHA 本身可解析**，那是一次真正的分支 push（会动 `commander/control` 之外的共享 ref），你说一声我就做，不自己扩。

**现场**：未碰 `:4781/:4782/:8693` 与 `_live.db`；`demo/reset` 0 次；provider 出网 0 次；本轮 GitHub 调用＝7 次 PUT ＋ 2 次只读 GET（列目录与 blob 核对）；账本只追加本块。

status: ORD-0221 **补件 DONE@2026-09-22T20:3x+08 by e345b9d6**——四件读数已发布为可解析 blob（7/7 BYTE-LEVEL MATCH），发布器为 v3 `d0b1bb1e`。
evidence: `review/evidence/ord0221/`（七个文件，与远端逐字节相同）、`review/build-ord0221-payload.py`（载荷由已落盘的读数装配，不手抄）、`review/readback-evidence.py`（回读比对）、`review/verify-ord0221-evidence-surface.py`（19:0x 那次对 `evidence/ord0216` 的四 blob 核对）。
