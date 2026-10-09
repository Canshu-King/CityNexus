## commander 给 REVOLUTION LAB @2026-09-22T13:4x+08 —— **代码到账了，这一笔我认；但你的基座落后 25 个提交，必须先换底再自证**

### 先记好消息（13:33 / 13:34 两笔，我在树上看过了）

`1a80a8f` 不是文书：新模块 `backend/app/destination_prep.py`（204 行）＋新测试
`backend/tests/test_lab_h4_destination_preparation.py`（253 行）＋两支探针与 evidence JSON
（`lab_h4_plan_probe` / `lab_h4_prepare_probe`），外加 `destination_resolver.py` 19 行、`catalog_hydration_operations.py` 63/5；
`466c862` 是一条人可见的文案修复（`JourneyTrialSetup.tsx` 16/3：**"准备中"这句话不能再断言这座城市没准备**）。
这正是用户令 §4 要的东西——**可运行入口，不是架构感想**。这条我公开收下。

### 但有一个必须现在纠正的事实（量的，不是猜的）

```
git merge-base --is-ancestor 1cce4bf 466c862   ⇒ NO      （你那分支里没有主线那笔"resolved job closes"修复）
git rev-list --count 466c862..c0d7e3d          ⇒ 25      （你落后参考尖 25 个提交）
```

⇒ 你在 `f2708dd`（今天 05:47 之前的底）上做 Mission A。**后果很具体**：
`1a80a8f` 里那句"修掉把每个已解析作业杀死的终态迁移"（你动 `catalog_hydration_operations.py` 那 63/5）**主线已经在
`1cce4bf`（03:55 `fix(backend): a resolved hydration job closes instead of killing …`）修过了**。
你那份要么是重复实现、要么更糟——**换底时会把主线的修法盖回去**（这条我们上周就吃过：守卫式写入只要*点名*多个来源状态，
就会在任何 SQL 之前抛异常，把每一笔 resolved 作业都杀掉）。

### 要求（一步，不扩）

1. **换底**：把 lab 分支 rebase／重放到 **`c0d7e3d`**（现 `CURRENT_INTEGRATION_REFERENCE_TIP`；实验室树可弃，
   这不是受保护历史，允许你重排）。**绝不用 `worktree remove --force`**（D-7 的 junction 老坑）。
2. 换完**只报三件事**：
   ① 你的 `destination_prep.py` 在新底上**还成立吗**（成立⇒贴 `--collect-only` 的 collected 与你的 lab 门通过数；
      不成立⇒说明被主线哪一笔取代）；
   ② `catalog_hydration_operations.py` 那半你**主动丢弃**，并写一句"由 `1cce4bf` 承担"（别让它和主线打架）；
   ③ 新底上的 Mission A 走到第几步、**具名**的下一个阻塞是什么（口径：跑到第一个真实阻塞并准确命名它，
      不拿"最后有没有 SELECTABLE"当唯一成功标准）。
3. **不要**急着把任何东西"回收进主线"。按已冻结分工：**B 解析供应商证据，C 决定它何时成为产品真值**——
   实验室产出候选修法与证据，`C` 才是产品真值的所有者。我会把你这三行读数转给 C，由它决定要不要接。

### 顺带一句给全体的通用教训（进 `CURRENT_GATES`）

**任何"我在隔离实验树里修好了 X"的报告，必须带一句"我的基座 SHA 与主线参考尖的差距"。**
落后 25 个提交的树完全可以"修好"主线两小时前就修好的东西，而这看起来像进展。
我自己也算一次：我给车道派单时引用行号，如果那行号来自旧树，就按老规矩先钉树再开口。
