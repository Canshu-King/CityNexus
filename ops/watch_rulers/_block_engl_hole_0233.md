## commander 验收 @2026-09-23T02:33+08 —— **红队打穿 D 刚闭的 E1：英文面是真洞**（门硬编码 `zh-CN`、产品英文句是内联字面量 ⇒ 英文用户看见自相矛盾句而门恒绿）；B 落第 12 条门并给出合流确认

### ① 红队 `d2305848`：E1 三靶，**靶 1 穿透（真洞）**

```text
突变：英文串接上  Don't worry, you have plenty.
门（中文场景）：绿
en-GB 探针实测屏上真渲染出：
  At this budget, … exceed the plan. … Don't worry, you have plenty.
  （budget-advisory-caveat 可见、htmlLang=en）
根因具名：门 :56 硬编码 zh-CN；产品 :2032 英文分支是内联字面量而非常量
        ⇒ 逐字相等只钉住了中文
⇒ 英文用户能看到自相矛盾句，而门永远绿
```
**靶 2（第二处渲染点）→ 没穿**：`advisory.hint` **全仓只有一处渲染点**（`V8Experience.tsx:2349`），同语义文本只有 `:1997`/`:1999` 两个 locale 分支；突变数字半加安抚词 ⇒ 门红（被门里保留的 risk/allay 断言覆盖）。
**靶 3（空白归一化）→ 没穿（两形状都红）**：全角空格 U+3000 ⇒ 红；零宽 U+200B ⇒ 红（归一化统一空白**形状**但不删空白；零宽不在 JS `\s` 类里），并给了可核依据：caveat 句中文标点后本无空白，要构造只能插入。
三臂 `anchor_hits=1/bytes_changed=True/restored_exact=True`；权威树 0 改动、未碰 `_live.db`。
**处置**：修法（英文也提常量 + 门加英文 locale 臂、同样不 import 产品常量）**已原样派回 D**，并要求：①英文串接安抚句 ⇒ 英文臂红、**中文臂仍绿作对照**；②英文句改一个标点 ⇒ 英文臂红（中文自测的对称版）；③**中英文各要自己的杀手**。**注意**：D 自己在本轮前已把这条写成"已知边界"，红队把它变成了"仍然开着的洞"——**这正是"把边界写下来"与"把它修上"的区别**。

### ② B `c01d72a3`：第 12 条门落地 + 合流确认

```text
dea1251d7bc493c80751bcba8a27808cf3adaba8   parent a96fabf   1 file +50
节点  test_two_hard_constraints_each_name_their_own_blocker
杀手  M11（婴儿车分支顺带报行李名）与 M12（反方向），各只让这一条红、其余 11 条全绿
连击  12 节点 × 10 进程 × 120 只不同库 全 STREAK_MET(10)；跑完删自己 120 只、释放 99.3 MB、复验剩 0
突变  累计 13 臂全 KILLED（11＋2 两份收据），nodes_without_a_killing_arm=[]
坐标  dea1251.patch 37d61baa6c26a7de ｜ 累积 patch 4a03305ef6f6def8(29,053 B)
      12 节点审计表 294d704ed8dbec4b ｜ 13 臂收据 e0fe7d2b0e5ec0f9 ｜ 连击读回 b436784a93843ad0
```
**合流点确认（它实测）**：主线 `8b9ea04` 导出两份，只在 `capabilities.py` 那两行上区分，各跑"它 12 条 + C 的写入端 9 条"：
```text
只留 `else None`（裁定形态） -> 21 passed
留着 `else "STRONG"`（现状） -> 21 passed
```
⇒ **删 C 那行不破任何门。** ⇒ 我裁定生效：**留 `else None`、删 `else "STRONG"`**；已挂成 **ORD-0234**（归拥有 `capabilities.py` 的车道，待它交完手上 ORD-0224 再接）。
**它自首一条**：第一次跑用 `git show HEAD:` 覆盖门文件，而第 12 条当时还没提交 ⇒ 两栏都成 20，**差 1 被它自己的加法定律（21 = 12＋9）拓红**；换工作树文件后才是上面的数。⇒ **"先写一个能自己发现错的定律"**，这条做法记入规矩。
**它转来的产品边界问题**：`_accessibility_metadata` 只读 `metadata_json`、不合并 `tags_json`（它独立复测：只把事实放 `tags_json` ⇒ 两把门都返回 `[]`；混放 ⇒ 只读到 `{'stroller_accessible': False}`）。**它没把它写成断言**（那等于把现状钉成规范）⇒ 我把问题原样转仲裁：**`tags_json` 该不该参与无障碍求值**；在仲裁回话前它不为它写任何门。

### ③ 现场

链三条端口在听（`:4781` 56212 / `:4782` 20364 / `:8693` 55960）；三代包同挂（`DtQ86lsQ` / `BCF4ptyk` / `CnfHH2K_` 全 200）；清理闸门仍关（0 删除，等用户真机刷新）；`P7=false`；reference tip `c0d7e3d`；P0 未动（3 行程 / 19 计划版本 / 3 出行人 / 16 地点）；那把 key 仍未轮换。
