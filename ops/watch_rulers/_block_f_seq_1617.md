## commander 执行令（第二条）@2026-09-22T16:1x+08 —— 仲裁刚把 **F 的先后顺序**钉死了，防的是"等 C 修完才动手"的死锁：`0210 先机制 → 把红收据交给 C → 立刻做 0214 → C 修完再回来签 0210 CLOSED`

来源＝总线 `5773209274`（16:10:05，第六十次敲门回执）。**冻结顺序照录，不改一个词：**

```text
F:
1. ORD-0210 mechanism first
   - clean/fresh DB receipt path
   - independent-process runner
   - per-run exit + resolved absolute DB path + row counts
   - FLIP_WITHOUT_SHARED_STATE classification
   - acceptance-streak logic wired
   => mechanism can be ACCEPTED even while target g3 is still RED/FLIPPING

2. hand current failing receipt to C / ORD-0213
   => C owns product/concurrency root-cause repair

3. F immediately proceeds ORD-0214
   => harden §8 against well-shaped fabricated attribution

4. after C lands ORD-0213 fix
   => F returns to ORD-0210 target and runs the 10-process closure streak + reverse mutation
```

仲裁的理由原文：**"0210 是别人读数的地基，所以量具必须先落；但 g3 的产品根因现在归 C，不能让 F 因等 C 修完而整条线闲着。"** 结论一句：**"0210 先机制，0214 后施工，0210 最终 CLOSED 等 0213 修复后再签。不开新单。"**

### 给两条车道的具体含义（我把话翻成动作，不改裁定）

- **F `8ccd71d8`**：你现在手上那道"干净库/脏库同判定"的门，**交的时候 g3 是红的也可以签 `ACCEPTED(mechanism)`**——判据是量具形状（每进程独立、捕 `resolved=` 绝对路径、跑前跑后行数、两库同路径就判无效、`FLIP_WITHOUT_SHARED_STATE` 命名接上）。量具我 16:1x 已经做成 `live_checks/gate_streak.py` 并两向自检过（红靶 `STREAK_NOT_MET(0/2)`、绿靶 `STREAK_MET(2/2)`、`duplicate_db_paths=[]`），**直接用它或告诉我它缺什么**，别另写一份。做完第 1 步就把那份红收据贴进账本，然后**立刻**去 ORD-0214。
- **C `8c66aa92`**：`- id: ORD-0213` 的归属被仲裁再次确认（"C owns product/concurrency root-cause repair"），并且**F 的红收据会寄给你**当作起点。你的交付验收按 `GATE_ACCEPTANCE_STREAK` 八条，外加仲裁 15:58 那条反向要求：**破坏并发保护点必须能重新出 RED 或打断 streak**，否则你只能签 `STREAK_GREEN`，不许宣称根因门咬住了回归。

现场：working tip `56d20ec`（16:15 复查两棵树同 SHA，15:22 后主线 **0 新提交**）；reference tip `c0d7e3d`；`P7=false`；`56d20ec` 上 B 那四条红 0 恢复（见前一块，分母 1178）；用户库 3/19/3、护栏 403、匿名 401、`demo/reset` 从未触发、0 次出网、0 次写 `_live.db`；那把 key 仍未轮换。
