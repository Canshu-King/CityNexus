## 亲测 @2026-09-25 07:0x+08 —— 落地次序这件事**我自己用 `git merge-tree` 量了**（只读，不动任何 ref）：D 的候选 × B 的候选在 `V8Experience.tsx` **确实冲突**；另收 ORD-0288 定形，点名 ORD-0291

### ① 落地次序：我读到的事实（不引任何车道的结论）
```text
merge-base(review/0278-0253-on-45b0a5e@06717045, review/0274-b2c-c@ef277b2) = 45b0a5e2…（两枚都直接坐在权威尖上）
git merge-tree --write-tree --name-only 06717045 ef277b2   ⇒ rc=1
   CONFLICT (content): Merge conflict in frontend/src/app/V8Experience.tsx   （预测树 ea24cf27d9b2…）
对照（D 自己量的是旧一代）：06717045 × 853c549 ⇒ 同一处冲突（rc=1，预测树 b1077bae0101…）
⇒ D 的警告成立，而且**在 B re-parent 之后依然成立**——它不是"某一代的巧合"，是同一片代码两个人都写。
```
**处置（我来排，不问车道）**：
1) **谁先落不看谁先交，看谁的 `derived_result` 先到**：0274 那枚归 @HJ-P1（ORD-0290，正在跑），0278/0253 那枚归 @红队（ORD-0286，它这一拍落到一半变 cold，我已重新点名）。
2) 第一枚 ff-only 落完，**第二枚必须 re-parent + 在新代重跑自己的门与反突变**才算可落——旧代读数一律不折算（Q24/Q25）。
3) **@D 不许现在开 ORD-0288 的产码**：0288 的射程落在 `PlanWithAiSheet.tsx`（B 正在 0280 上写同一文件），同文件双写者就是给明天留冲突。等 0280 落地我再点名，理由写在这里。

### ② ORD-0288 定形 = **ACCEPTED**（HJ-P3，总线 `5823596418`，shape `evidence/ord0288-shape-hjp3/…` blob `072077ced7bd27fe…`）
它这一拍的现场读数值得单独立一条，因为**它把"有凭条"这件事证伪了**：
```text
同一趟新行程、同一把 Idempotency-Key 连发三发 ⇒ journey_missions 0→3、agent_runs 0→3，
而 idempotency_keys **一行都没多**；7 次请求 = 7 个不同 mission id（零重放），响应也不回显这把键。
对照：plans/generate 带键一发就 +1 行回执（operation=plans.generate）⇒ 机器现成，是这一支没接。
路由侧：Header(alias="Idempotency-Key") 只在 main.py:4606/:7740/:9907/:11364，本单的 run_agent_command(:1057) 不在其中。
```
⇒ 第一条判据钉成 **"请求里有个头"不算凭条**：今天是**静默忽略**，比 409 更危险（客户端连"没被受理"都不知道）。
三格我照收：T-1（键过现成 `validate_idempotency_key`、落既有 7 列表、同键同体不增行、同键不同体走现成 409，比较先去 `trace_id`）；**T-2a/T-2b 拆开**（a 今天可验且必红；b 依赖 0281 的期限，标 `BLOCKED_BY-0281-T-b`，**不许拿 a 的绿冒充 b**）；T-3（库里**有**回执时屏上也不许报"没发生"，要同读库与读屏）。逐腿射程：在射程 1 条、**具名不在射程 12 条**，机理分列不互吞。

### ③ ORD-0291 · T-c 常量探针 · @HJ-P3（`aad2d1f2`，0288 已交、现 ready）
```text
把它自己在 0281 T-c 提的那枚探针做实，给 @B 产码后当验收工具（现在就有用，不等产码）：
 1) 只在**私有副本**里改常量，产品字节 0 改动；常量具名（哪个文件哪一行、改前/改后值）。
 2) 两档各跑一次：X 与 X/2，只看**触发时刻是否随常量移动**；按 Q25，这枚时长读数**不跨代继承**。
 3) 逐腿点名：在射程外的腿具名列出（它 0288 已经这么写，口径沿用）。
 4) 面：新端口 + 私有冻结 dist（它 06:2x 自己定的两条前置，现在反过来保护它自己）。
 5) 发布 evidence/ord0291-deadline-probe-hjp3/；账本块 + 总线一条；不签 derived_result。
```

### ④ 我把 0288 那句"这一支没接"**静态核了一遍**（在落地代导出树 `_qoder_wt_45b0a5e`，只读；main.py 11,417 行）
```text
Header(alias="Idempotency-Key") 出现行号 = [4606, 7740, 9907, 11364]   ← 与 HJ-P3 报的四枚逐位相同 ✓
def run_agent_command 在第 1058 行（它写 :1057，应是装饰器行）；其后 80 行内 Idempotency-Key alias = [] ⇒ **确实没接** ✓
validate_idempotency_key 是真符号：定义在 app/commerce/validators.py:109，main.py:100 import，
   调用点 main.py:4631 / 7769 / 10110 / 10160 ⇒ T-1 那句"过现成校验器"**有实体，不是自造名字** ✓
表也是现成的：app/db/models.py:663 class IdempotencyKey / __tablename__ = "idempotency_keys" ✓
```
⇒ **ORD-0288 定形 ACCEPTED**（判据引用的符号我逐枚查过存在性；只有 `:1057` vs `:1058` 一行偏移，记在这里不猜）。
它那条"静默忽略比 409 更危险"的判断我接受为**产品事实**，并已把它转成 ①-3 的排产理由（同文件双写者不给开）。

### ⑤ 现场（07:0x 实测 `runtimeState`，不是猜）
`c01d72a3` B running（0280 写窗口内）｜ `1a986a24` HJ-P1 running（0290 五臂派生）｜ `8ccd71d8` F running，**队列里压着我 3 条**（0287→0289 顺序已写在消息里，不再加）｜ `d2305848` 红队 **cold**（0286 没交，已重新点名）｜ `e345b9d6` D cold（无待办：等 0286；0288 产码被我按住，见 ①-3）｜ `aad2d1f2` HJ-P3 ready → 点名 ORD-0291。
**权威线未动**（`45b0a5e2…`）；`commander/control` 只有我的发布在推进；已发布路径 0 覆盖；用户库 0 读写；凭据 0 打印。
