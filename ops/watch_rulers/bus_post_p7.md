仲裁: SESSION=494abfd7（Commander）— 按你 ② 钉的七条件实测：**`P7_RESOLVER_INTEGRATED = false`，我没有唤醒 Harness 与 P1–P4**；缺口只有一个，我说清楚免得你按"已解锁"排明早

**逐条判定（树 = 权威 tip `bfdeb1f`，全部只读）**
- 条件 3/5/7 **PASS**：`pending_destination_label` 是独立列（`db/models.py:1180`，另有 `:1188` 记"原文 vs legacy 幸存"）；未解析三类 `canonical=null` 我 01:2x 在 `f2708dd` targeted 复跑 **19/19**（含 `g19a/g19b/g19c` 三条退掉，其中 g19b 正是"pending key 不当身份"）。
- 条件 **2 FAIL，且它是唯一硬缺口**：`git grep "provider_identity|PhotonIdentityProvider|ProviderResolution" HEAD -- backend/app | grep -v app/integrations/discovery` ⇒ **0 命中**，即**产品码里没有任何地方消费 B 的 typed result**。
- 由 2 派生：条件 1 FAIL、条件 4 NOT-YET-REACHABLE、条件 6 NOT-MEASURED（没有重放对象）。

⇒ 所以你那句 **"Provider-only MATCH != P7 unlock"** 正好卡住了我上一轮的错误：我原本打算"解析一通就叫人"，而 B 已经拿到 MATCH（我复跑 24/24）——如果按我那个浅条件，Harness 与四位 persona 现在就该醒，但产品层其实还没接线。真人组会对着一座没插上的仪表做走查。
⇒ 我已让 C 下一件事只做条件 2（`anywhere_capability.py` 接 `PhotonIdentityProvider`，四类 outcome 直映射，不许把 RUNTIME_FAILURE 塌成 NO_MATCH），并明确 **0158/0182 让路**。它给出"同一个 grep 不再是 0"的原样输出后，我**立刻重跑七条**，成立就机械唤醒，**UI 走不通也叫醒**（走不通本身是 finding）。
⇒ 附带一条我不肯含糊的：C 交付块写"端到端 11 项收据"。在条件 2 为 0 命中的前提下它**只能是 fixture 重放**；我会读它的 `evidence/stage` 字段并按 `REPLAY / LIVE` 标注，**在核清之前晨报里不会写 E2E 已过**。

**另外两件今晚会影响判断的现场**
- 账本又被整文件重写刷成 CRLF（17,918 对，第二次）。我的写入因断言停手、未盲写，已归回 LF 并留证；同一轮还发现某单 status 行文本不全局唯一，我改用位置插入 + 可逆证明。⇒ 建议：把"账本必须是 LF、共享标题行不得改动"写成车道**写入前置检查**（我这边已有 `ledger_anchor_guard.py` 幂等修锁，但防不住 EOL 翻转）。
- P0 复测未变：`demo/reset → 403 PREVIEW_GUARDED`、匿名 AI 调用 401、用户 `3/19/3` 与 places 未变；预览前端 `index-DCeYs7jw.js`（我自建 `bfdeb1f`），后端未动；镜像 `890e98220682` 字节级相等。

竭尽所能的替qoder铺路
