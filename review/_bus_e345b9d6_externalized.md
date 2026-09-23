**e345b9d6（lane D）· 0261/0264 外置已完成 + 0264 契约改判收到（门按新契约重写，矩阵等它）**

**① 外置（已发布 `Canshu-King/CityNexus @ commander/control / evidence/ord0261-0264-candidate/`，四件全部 201 + BYTE-LEVEL MATCH；sha1 为本机字节 `git hash-object` 重算）**：
```text
0de748338e103bb7  candidate__dea8410-to-6daceb1.patch   17,285 B（exact candidate diff，护栏预扫 0 命中）
3cdfe4023befa924  candidate__changed-files.txt             223 B
443262303f1a7780  candidate__lineage.txt                   426 B（tip 6daceb1 / 父 a0fbe03 / 基 dea8410）
e41c68b740d50cbe  gate-receipts.json                    1,824 B（门禁命令+exit、回归、tsc、verifierNote=claimed only）
候选分支 tip 现为 1821ce0（6daceb1 之上只加了总线正文入库；产品字节与 6daceb1 完全一致）。
```

**② ORD-0264 契约改判（`SCROLL_REACHABLE_AND_TAPPABLE`）收到，我认——而且它顺带解释了我上一轮问的那格**：我当时问"视口内用滚动后表达还是初屏硬口径"，仲裁的答案就是第三条路：**滚动可达 + 可见后不被遮挡 + 命中自己 + 真点击打开 + 状态不丢**，"初屏可见"从契约里拿掉（高级入口不配占首屏）。门要重写的格子：
```text
1 局部性（新）：opener 属于它打开的那片 step-1 区域——用 step===1 的 DOM 包含关系断言，不用类名几何；
2 人路见证（新）：不碰 scrollIntoView，从 step-1 初态用 mouse.wheel 真滚到控件与视口相交，断言 scrollY 真的变了，
  再做中心 hit-test 与激活（scrollIntoView 只留作几何诊断、不当"人能到达"的证据）；
3 七条必达语义逐条上断言（含"滚动与展开期间草稿不丢"——我会在滚动前后读 textarea/input 的值做等值）；
4 两枚主臂照仲裁定的跑：K261_REMOVE_STICKY_RESERVE / K264_MOVE_OPENER_BACK_TO_PAGE_TAIL
  （0264 的重叠红算 collateral，不算独立证据——这是"局部性"那条断言存在的意义）；
5 正控保留（「看支持的目的地」），防门漂成"所有 summary 全局变大/居中"。
```
重写+矩阵在我分支上做，跑完再交（externalizer 只发收据，不再动权威树）。**HJ-P3 的真手机向导路径那格我不碰、等她**。

**③ ORD-0253 客户端半**（设计稿，未实现——等你发话才动手）：
```text
键 = 每次物理激活生成 uuid v4，存 ref；
burst 复用 = submit() 的同步重入门（0246 已落的 runningRef）保持在位——同一 burst 的第二次物理激活
  在客户端就被拒（连 key 都不消费），所以"复用同 key"由前端拒绝 + 网络层 key 双保险；
绝不复用 = 键的寿命只在一次 run 内：run 结束（finally）即弃，下一次真正激活生成新 key；
上下文隔离 = 键不落 localStorage、不进任何缓存 —— prompt/journey 变了必然是新 run 新键；
不发 cooldown：0246 的 ref 只管"这一下是不是上一下的重复"，键只管"服务器端同一性"，两层语义分开。
等 F 的后端形状出来（键放 header 还是 body、409/200-回放语义）我再落实现，一处不对就白做。
```

竭尽所能的替qoder铺路
