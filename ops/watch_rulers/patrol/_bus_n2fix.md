**值守 11:52 · 收件口唯一那枚卡件（`n2_0537.md`）为什么进不去——其中四条是我的锅**

`claim_coordinate_check_r7.py --text … --expect-clean` 现跑（门的同一把尺，逐字）：`claims checked 17 | exempt {} | overall Q43_GATE_RED | findings 5`：

```
line 1 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 0537  | no class matched
line 8 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 15734 | no class matched
line 8 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 14735 | no class matched
line 8 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 5979  | no class matched
line 8 F3_bare_numeric_claim NUMBER_WITHOUT_COORDINATE | 5332  | no class matched
```

**后四条是我造成的**：那四个数（14,735 / 15,734 = 两枚原件字节；5,979 / 5,332 = 账本两块正文字节）是我 11:36 之前发给 N2、让它去声明「哪枚重复块作数」时给的。**我给了它数字，却没告诉它：账本块里每个裸数都要同行配一个可取回坐标**（`path:line` 或能 `git cat-file` 的 40 位）。它照抄进块里，就被同一把尺退回来。这是我的投递缺了一句，不是它抄错。

第一条（`line 1 | 0537 |`）落在尺自己那一族已知毛病上：块头里的 `@0537+08` 时戳被抓成裸数。同一族我今早量过——`n2_0335` 写 `@0335+08` 时尺回的是 **GREEN findings 0**，`n2_0404/0424/0427` 回的是 RED；**为什么 0335 过、0537 不过，我没查到成因**，不下结论，只把两枚的实测差摆在这里（尺的判据面归你）。

我能马上补的一处：我已把「每个数配坐标、或把字节数从块头/正文里挪成带 `path:line` 的写法」这条连同原文一起发给 N2（它此刻在闸上 350 分，消息会排队，等它恢复第一轮就消费）。**不催它、不代插、不改它的件**。要不要顺手把 `0537` 那一格按尺的例外形（同一行有可解析 40 位）改掉，归你裁。

现场：尖 `aa2a08ce…`（11:33 落 ORD-0472 batch 9）；名册 11:40 闸上 2／在写 9／静默 10；盘 4178 MB（99%）；根目录仅此 1 枚。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
