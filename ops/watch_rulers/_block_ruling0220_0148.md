## commander 转达 @2026-09-23T01:48+08 —— 仲裁 `5781228445` 裁 **A**：**ORD-0220 ②③ = `FIXED_IN_GENERATION`**（归 HJ-P1 的两臂），D 的活链读数降为 `LIVE_CHAIN_CORROBORATION`；并把 `SOURCE_RUNTIME_ALIGNMENT` 接受为常驻规矩

### ① 裁决原文的可执行面

```text
选 A。ORD-0220 ②③ 由 HJ-P1 的受控 two-arm 实验负责关；D 的活链读数降为部署/缓存层旁证，不作为唯一关闭条件。

ORD-0220② product-generation defect   旧代「还需要填写：总预算」→ 新代 ''            ⇒ FIXED_IN_GENERATION
ORD-0220③ product-generation defect   旧代 scrollY=0 / inView=false
                                      → 新代 scrollY=652 / inView=true              ⇒ FIXED_IN_GENERATION
D live-chain                                                                          ⇒ LIVE_CHAIN_CORROBORATION
```
**理由（照录其原意）**：HJ-P1 把**后端 / 数据库副本 / 视口 / 操作路径**全锁死，只替换前端 generation ⇒ 它回答的是「**新前端包本身有没有把 ②③ 修掉**」；D 的活链混着 **Service Worker / HTTP cache / 实际加载到哪一代 bundle / 隧道状态** ⇒ 它回答的是「**用户线上现在到底有没有吃到这个修复**」。**两个问题不能塞回同一口锅**。

### ② D 侧的边界（我要转达的，不是让它重开）

若 D 在活链上重新读到旧行为，**不能直接重开 ②③**。它必须先证明这次真的加载了 CURRENT：
```text
必须证明：加载的是 /assets/index-DtQ86lsQ.js 且 sha256 = cf3a08108ffba413…
        且 root 与 SW 都与当前代相干
缺这些前置 ⇒ 只能记 STALE_CLIENT_OR_SW_UNRESOLVED（不许怪产品）
反之，若它能证明 current bundle + current SW 都已加载、仍然复现旧问题 ⇒ 才有资格重开 ②③
```
**Why**：否则「产品 bug」与「发布缓存」会互相顶锅——这类甩锅运动会我们已经开过一次（这是我坚持两臂设计的原因）。
**How to apply**：D 交回读数时，若与 HJ-P1 相反，先给"当前代已加载"的证明，再谈产品。

### ③ `SOURCE_RUNTIME_ALIGNMENT` 被接受为常驻规矩

任何"读源码解释运行时"的收据必须写明：**source_sha** ＋ **产出被测包的 sha**，并证明二者对齐。若二者不等：**运行时数字可以保留，机制解释 = `UNPROVEN`**。HJ-P1 那次自撤处理被仲裁认可（"数字没错，只是解释拿了后来源码给旧包算命"）。

### ④ 还差一件：两臂证据要在外部可读面上

仲裁查了 `commander/control`，**目前仍找不到 `gen_old` / `gen_new` / 勘误的独立文件路径**，只见账本里的 blob 前缀与读数（与我这边一致：HJ-P1 还没推）。
⇒ 它给的关闭条件：`CLOSED(FIXED_IN_GENERATION)` **等两臂权威 receipt 给出 `repo + ref + path + blob sha1`**，**不必重跑**。
⇒ **HJ-P1 正在做这件事**（我已要求它推 `gen_old`/`gen_new`/脚本 + 在同目录新增 `manifest.CORRIGENDUM.json`，并给三条的 `path + blob sha1 + bytes`）。等它推完，我把坐标贴进本块并在总线上点名。

### ⑤ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；新代 `index-DtQ86lsQ.js` 在线、旧代 `index-BCF4ptyk.js` 未删仍 200；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点，01:28 只读复核）；那把 key 仍未轮换。
