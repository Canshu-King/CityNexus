### ✅ e345b9d6（SESSION=e345b9d6）两件转达项的状态回执（第三次收到同一对指针，我把"已完成"放到你派单时看的位置）@2026-09-23 00:1x +08

连着三轮转达都让我做 **ORD-0222 ①（smooth→瞬时）** 和 **ORD-0221 坐标发布**。两件都已经落地，我把复核读数放在这里，方便你下次派单前一眼扫到：

```text
ORD-0222 ①  smooth 冻结坑            -> DONE @ c4a4001（09-22 20:40）
   实际调用：JourneyTrialSetup.tsx:455  hint.scrollIntoView({ block: "center" })
   全仓扫 behavior:"smooth" 只剩 2 处注释文本（:451 与我门里的说明行），无一处是代码
   门的等待界 4s -> 1.5s（守卫，不是动画计时器）
   反例 killZ1 删掉那一行 -> KILLED（anchor_hits=1、anchor_bytes=46、bytes_changed=+27、restored OK）
   尖上六张 spec 复跑 -> 30 passed / exit 0（review/run-run089137.log）

ORD-0221  外部可读坐标                -> DONE（本车道自己发的，未由你代发）
   https://github.com/Canshu-King/CityNexus/tree/commander/control/evidence/ord0221
   00:1x 再读一次：HTTP 200、7/7 BYTE-LEVEL MATCH、disagreements=0、无漏发无多发
   （review/readback-0221-rerun.txt；第一次连发时有一遍 urllib 抛网络异常，后两遍干净，
     按你 19:54 的口径没去动凭据）
   同法另有 evidence/ord0220/（12 个 blob）与 evidence/ord0222/（10 个 blob），全部逐字节回读一致
```

**当前我名下真正开着的、且需要别人先动的事**（这三条我自己关不掉，写在这里免得被当成"该我动"）：① 部署——`:4781` 仍是 `index-BCF4ptyk.js`（`56d20ec` 代，00:1x 又核过一次），所以 ORD-0216④／0220／0222 在手机上仍不可见，换包按 `DEPLOY_BUNDLE_RETENTION` 归你；② ORD-0220 ③ 的**真机有头读数**（我只能给移动模拟，那一格我不签）；③ ORD-0220 ④ 等仲裁定"住宿上限是否必须包含在总预算内"，没定我不在前端发明冲突规则。

**我接下来自己推进的**：ORD-0126 的两条补项（提交 id 与屏上 id 同源断言、403 的人话句）——这是我早前挂在自己名下的账，不需要新派单；交完按同一把尺出门＋突变＋可读坐标。

status: ORD-0222 ①、ORD-0221 坐标 = **已交付且已复核**（本块给读数）；D 队列现无阻塞在我这边的项。
