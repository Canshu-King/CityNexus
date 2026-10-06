## commander 记账 @2026-09-22T18:56+08 —— HARNESS 第二次自抓仪表错（**它主动声明 digest 换值**）；ORD-0210 源审计包已就位待仲裁比对

### ① HARNESS 18:53 那条自纠，我按"主动换值 + 给出比对禁令"记账

它交了三块（措辞分母 64×8 与 promotion 杀测各 10 连、从 `66cad62` 搬到 `522c414` 重测 13 族一格没动），**但头条是它自己的错**：

```text
错   harness_promotion_killtest.py 打两段报告（AS-IS / SIMULATED naive），两段用同一批案例标签；
     它的驱动把两段塞进同一个扁平字典 ⇒ naive 臂静默覆盖 as-is 臂
症状 破坏对照返回 reacts=False —— 不是门聋，是它翻的那一案在合并后的字典里本来就是 VIOLATION
修法 按 === 标题 === 分节、键成 section::label，并加两条结构断言（AS-IS 必须全静默、SIMULATED 必须恰好 3 案 fire）
后果 杀测 digest 从 b9cbecb3…（合并错版）→ 29901f493dc73230（分臂版）；它明写"别拿两分钟前的那个数比对"
```

**我为什么记这条**：它没有悄悄改数，而是**把换值写进交付块并给出比对禁令**——这正是我们冻结的"证据要能自证其版本"。
它另外自曝修了一处**坐标自漂**（004 收 `--head` 却硬编码 import 旧导出 ⇒ 现在 `--export` 跟随 head 并打印所用导出），我按"同族第二次"记（第一次是 8/9/10 条那块里"同尖两跑共用库并覆盖 JSON"）。
**边界它自己写明**：十连证**复跑纪律**，不证产品应当如此（第 8 条）。我照此记账，**不替它升级成产品结论**。

### ② ORD-0210 源审计包（我 18:53 发布，等仲裁比对）

```text
https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0210
  50b35e0__9514eb7.patch                    74,692 B  blob a20a989f847bf99a
  50b35e0__9514eb7.files.txt                   131 B  blob c96b5855a6e5d9e0
  _qoder_streak_receipt.py                  22,125 B  blob d3297d44bd60d26c
  test_qoder_db_isolation_same_verdict.py   45,402 B  blob d1d466ce5819525e
  gate-acceptance-streak.yaml                5,140 B  blob 0b8947799280ff6c
live_checks/publish_evidence.py              3,372 B  blob 1006c995fb6a526f   ← 发布器自己也发了（他抓的讽刺）
```
他签的两条：`ORD-0210 RUNTIME RECEIPT = ACCEPTED-EVIDENCE` / `IMPLEMENTATION MECHANISM = PENDING-SOURCE-AUDIT`。**我不动，等他的源审计结论。**

### ③ 一条我给全体车道的追加口径（从 HARNESS 这条错里提炼，不是新规则、是它的推论）

**凡"破坏对照返回 False/True"的读数，必须先证明两臂没有共用键空间。**
HARNESS 这次正是"两臂同名标签被扁平合并"造成假 `reacts=False`；同族还有它自己 16:1x 的"同尖两跑共用库并覆盖 JSON"。
⇒ 我把它写进唤醒模板的尾巴：**任何 digest/对照读数，交付时要么分节命名空间、要么证明两臂键不相交**。

### ④ 现场

working tip `25165d9`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。
车道 18:55 读数：D / B / HJ-P2 / HJ-P3 / C / HERMES 在跑；HARNESS / 红队 / HJ-P1 / F / LAB 我已逐个推（各自带着新规）。
