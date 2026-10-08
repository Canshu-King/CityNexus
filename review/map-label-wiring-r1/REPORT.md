# ORD-0415 — the map label forbidden rule wired to the render path (lane 地图标注接线)

- 候选枝 `refs/heads/review/map-label-wiring-r1`，本报告的生成基准尖 `c796547c1dc2e1e463f7e7c1e14f8945e6937b7a`（`git cat-file -t` 回读为 `commit`）。
- 权威尖（现读，只读不推）：`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` = `8d74fa55761c5c7ed3d8c45860e3513a8bd2b221`，本车道起枝的那枚尖等于它（`merge-base HEAD <tip>` 现读等于该尖）。
- 两轮的仪表同一个提交 `c796547c1dc2e1e463f7e7c1e14f8945e6937b7a`；两轮的区别只有三枚渲染文件的工作树字节（下表逐枚给 blob 前缀）。

## 两枚读数（同一把尺，两次运行）

- **修改前**（三枚渲染文件是权威线字节 `d94f2ffb1c, 1d5ef0efbd, fab224fd0e`）：渲染出的禁项命中 10 处（按已验收词表那把尺 8 处），逐类 宽尺／窄尺：clock-time 4／4, duration 2／0, money 2／2, source 2／2；按钮可及名里带禁项 5 枚；词表被真正触发的芯片 0 枚；署名 `v8-map-attribution` 渲染盒 {"w": 330, "h": 35}，文本与词典那一条对上：True。
- **修改后**（候选字节 `d94f2ffb1c, 1d5ef0efbd, fab224fd0e`）：渲染出的禁项命中 0 处（按已验收词表那把尺 0 处），逐类 宽尺／窄尺：clock-time 0／0, duration 0／0, money 0／0, source 0／0；按钮可及名里带禁项 0 枚；词表被真正触发的芯片 4 枚；署名渲染盒 {"w": 330, "h": 35}，文本与词典那一条对上：True，把这句喂给同一条词表仍报 `source`（['source']），说明豁免是承重的、不是我顺手绕过的。

- 两轮的 fixture 都把同样 6 枚词送进了服务端载荷（`readings/*.json` 的 `offender_classes` 逐枚留底），所以“归零”不是种子数据干净：修改前渲染的芯片是 ["19:30", "天津之眼 19:30 摩天轮", "瓷房子 门票 ¥60", "五大道 45 分钟 骑行", "海河 © 游船码头", "古文化街牌坊", "Departure"]，修改后是 ["天津之眼 摩天轮", "瓷房子 门票", "五大道 骑行", "海河 游船码头", "古文化街牌坊", "Departure"]。
- 合规署名没被误杀：干净控制词 `古文化街牌坊` 两侧都在图上（before True / after True），且它在修改后的 `data-forbidden-removed` 是 `nothing`；被裁的四个词仍带着剩下的名字部分在图上（after [{"case": "clock_inside_word", "on_glass": true}, {"case": "money_inside_word", "on_glass": true}, {"case": "duration_inside_word", "on_glass": true}, {"case": "source_inside_word", "on_glass": true}]）。
- 退出码：before 1（三格红正是未接线的判据），after 0（七格全绿）。

## 接线落在哪四处（现读行号见交付块）

1. `frontend/src/lib/mapLabelRules.ts` — 词表本体搬进产品树，加 `takeOffGlass()` 与 `mapLabelSpanViolations()`。
2. `frontend/e2e/_mapLabelRules.ts` — 改为再导出，四把已验收的闸仍读同一份定义（不是第二份副本）。
3. `frontend/src/lib/mapStopLabels.ts` — `stopLabel()` 出词之前先裁，整词都是禁项时不造词。
4. `frontend/src/components/v8/MapPanel.tsx` 与 `frontend/src/components/JourneyMap.tsx` — 芯片与按钮可及名用同一个词；legacy 的 canvas `symbol` 层裁它自己喂给 `text-field` 的 `title`。

## 一处自报（仪表的毛病，不是产品的）

这枚闸在自己身上抓到三次“只有真跑才咬得到”的错：词表搬进产品树时漏导出 `MAP_LABEL_FIELDS`；`sqlite:///` 少剥一个斜杠把“本 run 没有库”读成事实；臂先加载后改库，于是它读的是上一臂留下的屏。根因相同：`tsconfig.check.json` 与 `tsconfig.typecheck.json` 的 include 都不含 `e2e/**`，所以 `npm run typecheck` 与 `typecheck:all` 全绿时没看过这些文件一眼（实测两次 rc=0）。我没有去扩别人的 tsconfig（那会把既有的 e2e 类型错误一次点亮，不属于本单）。

## 一处留给号令者的裁定点（我没动的尺）

- 已验收词表里 `duration` 那条 `\d+\s*(?:分钟|min)\b` 在中文标签上匹配不到：`45 分钟`／`45分钟`／`需45分钟时间` 实测全 false，`45 min walk` true。  产品的裁切按宽尺走（不改窄尺，因为四把闸拿它做断言），闸把两把尺的数都报。要不要把窄尺本身修宽，归尺的主人次定。
- `qoder-map-ord0412-label-scope.spec.ts` 的 `scope-declared` 臂断言的是 `src/lib/mapLabels.ts` 这枚文件名不存在；我把产品侧那份命名为 `mapLabelRules.ts`，  所以它仍绿。但它当年保护的判语（“无产品代码查此规则”）现在已经不成立，该怎么改写由那把闸的收件人次定；我没有改它的任何断言。

## 复现

```
python review/map-label-wiring-r1/run_gate_r1.py --tag after \
    --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts
python review/map-label-wiring-r1/report_readings_r1.py --tag after
```

原始产物在仓外：`D:\moodle\_qoder_maplabel_wiring_20261008\wt\..\evidence`（`provenance_*.json` 记了两轮各自的工作树字节、解释器与端口）。
