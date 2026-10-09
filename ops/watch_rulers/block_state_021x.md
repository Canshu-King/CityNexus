### SESSION=494abfd7 · 02:1x 记账三件：ORD-0192 的里程碑**我暂时只能记 SELF_REPORTED**（仓库里找不到它的提交）、我自己的 ORD-0135 签收注记被车道重写冲掉后已补回、我写的 amend 工具存在**静默跳过**缺陷（已修）@02:1x

`STATUS: THREE-LEDGER-FACTS | 树 `git log` 实读 tip `306f153`（02:13）| 全部可复放 |`

#### ① ORD-0192（贡山链）报到了仲裁指定的那个落点——但**我核不到证据，就不升档**
B 的 status 写：13 步收口在 step 13，具名 `MOBILITY_EVIDENCE_NOT_HARD_ELIGIBLE`；解析真、目录真（6 条 live provider 行），但每个 used edge 只能落 `SYNTHETIC_DEFAULT` ⇒ **不造 SELECTABLE**；云和第二例更早卡在 answered-zero→Nominatim 兜底。
⇒ 形状**完全符合仲裁 A 的达标定义**（跑到第一个真实阻塞并准确命名）。
⇒ **但**：我在权威仓 `git log` 里**搜不到 ORD-0192 的提交**（`git log --format='%H %s' | grep ORD-0192` 为空），receipt 的 14 项字段也就无处可验；车道未 push 属正常，但**没有可 checkout 的坐标 = 我不能签**。
⇒ 处理：已回一句给它——**给我 exact SHA（+ 分支/worktree 路径 + `git log -1 --stat` 原样）**，我在 `git archive <SHA>` 上重跑它的 mobility 收据与那条"answered-zero 不得落 Nominatim 兜底"，才升 REPRODUCED。**在此之前晨报该项 = `SELF_REPORTED`。**

#### ② 我自己的签收注记被吞了（第三次控制面写入污染的新证据）
02:1x 复查发现 ORD-0135 的 `ACCEPTED / REPRODUCED@01:4x` 注记**在文件里 0 命中**，status 退回 `QUEUED@19:0x` ⇒ 车道整文件重写不只吞过标题行、也吞过**别人写的行**。已按同一份证据重贴（并在注记里写明"被冲掉后补"）。
⇒ 结论：**账本条目级"只追加"不够**，还得有**周期对账**：我以后每轮用 `git rev-list`/镜像 sha 与本地 diff，检查我签过的注记是否还在（本轮就是这么做发现的）。

#### ③ 我的工具缺陷（这次是自己的写入器），已修
`ledger_write.py --amend` 的"是否已贴过"检查用 `note[:20] in 全文` ⇒ 两条都以 `ACCEPTED / REPRODUCED@` 开头的注记会互相顶掉，**静默跳过不报错**。
⇒ 改成**只在目标单自己的 region 内查重**，并在真跳过时打印 `[skip] <ID> already amended`。修好后 ORD-0193 / ORD-0135 两条注记都真的落进去了。
⇒ 这正是今晚反复出现的那一类：**观察/写入工具自己出错，却看起来像目标状态如此**。已并入晨报"工具类误差"清单。

#### ④ 顺带一条好消息
tip `306f153`（02:13）= F 的 `test(review): prove the four destination outcomes are separate, not just separately breakable` —— 就是**时间优先/交叉突变**那条按顺序重写后的版本。等我复跑六组再升档。

status: ORD-0192 暂记 SELF_REPORTED（无 SHA 可核，已索要）；ORD-0135 注记被车道重写吞掉后已补回并建立"注记周期对账"；我修的 amend 静默跳过缺陷已落地；F 的时间优先版已进 tip 待我复跑
