# ORD-0415 — 地图标注的禁项规则接到渲染路径（车道：地图标注接线）

- 候选枝 `refs/heads/review/map-label-wiring-r1`，本报告的生成基准尖 `6bb44ab39a547d520bf93f4ddca37fd62fed6d3f`。
- 权威尖现读 `git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` = `cf5915ea948579b4dc80aa57a299639b5440150e`；本枝与它的 `merge-base` 现读 `cf5915ea948579b4dc80aa57a299639b5440150e`。
- 两枚读数出自同一个仪表提交 `6bb44ab39a547d520bf93f4ddca37fd62fed6d3f`，区别只在三枚渲染文件的工作树字节。

## 一、两枚读数（同一把尺，两次运行）

- 修改前 —— 三枚渲染文件的工作树字节 27f09d52d1, 34ca5a7df9, afa9cbebc3，同一轮 HEAD 声称 d94f2ffb1c, 748364ec97, fab224fd0e；两者不同正是这一轮把渲染文件检出回权威线的凭据。地图上实际渲染出的禁项 10 处（按已验收词表那把尺判 8 处；逐类：clock-time 4 处／窄尺 4 处，duration 2 处／窄尺 0 处，money 2 处／窄尺 2 处，source 2 处／窄尺 2 处）；其中落在按钮可及名上的 5 处；芯片上带着「裁掉了哪一类」回执的 0 个。渲染出的站名逐枚：["19:30", "天津之眼 19:30 摩天轮", "瓷房子 门票 ¥60", "五大道 45 分钟 骑行", "海河 © 游船码头", "古文化街牌坊", "Departure"]。
- 修改后 —— 三枚渲染文件的工作树字节 d94f2ffb1c, 748364ec97, fab224fd0e。地图上实际渲染出的禁项 0 处（按已验收词表那把尺判 0 处；逐类：clock-time 0 处／窄尺 0 处，duration 0 处／窄尺 0 处，money 0 处／窄尺 0 处，source 0 处／窄尺 0 处）；其中落在按钮可及名上的 0 处；芯片上带着「裁掉了哪一类」回执的 4 个。渲染出的站名逐枚：["天津之眼 摩天轮", "瓷房子 门票", "五大道 骑行", "海河 游船码头", "古文化街牌坊", "Departure"]。
- 两轮的 fixture 都把 6 条词送进了服务端载荷（现读 `readings/before.json`、`readings/after.json`），所以归零不是种子数据干净；退出码 before 1（三格红＝未接线这件事本身的判据）、after 0（七格全绿）。

## 二、ORD-0412 那条合规署名没被误杀

- 两侧同格同文：修改前渲染盒 宽 330 像素 × 高 35 像素，修改后 330 × 35 像素；文本与词典那一条逐字对上：before True / after True。
- 负对照仍承重：把这句署名喂给同一条词表，仍报 ["source"] —— 「不判 DOM 署名」这条豁免是被用到的，不是我顺手绕开的。
- 干净控制词 `古文化街牌坊` 两侧都在图上（before True / after True），它在修改后那轮的 `data-forbidden-removed` 回执是 `nothing`；被裁的四条词仍带着剩下的名字部分在图上：after [{"case": "clock_inside_word", "on_glass": true}, {"case": "money_inside_word", "on_glass": true}, {"case": "duration_inside_word", "on_glass": true}, {"case": "source_inside_word", "on_glass": true}]。

## 三、同族四把已验收的闸（零新增红，实测对照）

- 同一条命令、候选字节：3 格红 / 21 格绿；红的逐格 ["e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @320", "e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @360", "e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @390"]（取自 `run_reg2.log`）。
- 同一条命令、权威线字节（对照）：3 格红 / 21 格绿；红的逐格 ["e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @320", "e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @390", "e2e\\qoder-map-ord0403-named-control-and-labels.spec.ts:194:3 reach — the control is hittable and does not collide @414"]（取自 `run_reg_base2.log`）。
- 两侧红的都是 `qoder-map-ord0403-named-control-and-labels.spec.ts` 里 `reach` 那一族（具名控件压在瓦片提示下），数量同为三格，宽度集合在两次运行之间自己换了 —— 既有抖动，不是本单带来的；那把闸一个字我没动。

## 四、接线落在哪几处

- `frontend/src/lib/mapLabelRules.ts`：词表本体搬进产品树，另加两个出口（裁切的 `takeOffGlass()`、宽尺的 `mapLabelSpanViolations()`）。
- `frontend/e2e/_mapLabelRules.ts`：改为再导出同一份定义，四把已验收的闸仍读一个所有者，而不是第二份副本。
- `frontend/src/lib/mapStopLabels.ts`：`stopLabel()` 出词之前先裁；整条词都是禁项时不造词。
- `frontend/src/components/v8/MapPanel.tsx`：芯片文字与按钮可及名用同一个词，并在芯片上留裁切回执。
- `frontend/src/components/JourneyMap.tsx`：全仓唯一那条 canvas `symbol` 层，裁它自己喂给 `text-field` 的 `title`。
- `frontend/e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts`：本单的闸，自带 fixture —— 种子数据全干净，不带 fixture 的零是运气不是证据。

## 五、自报：这枚闸在自己身上抓到的三次坏

词表搬进产品树时漏导出 `MAP_LABEL_FIELDS`（模块加载即炸）；`sqlite:///` 少剥一个斜杠，把「本 run 没有库」读成事实；臂先加载后改库，于是它读的是上一臂留下的屏。三者都不是读代码能看出来的：`tsconfig.check.json` 与 `tsconfig.typecheck.json` 的 include 都不含 `e2e/**`，实测两次 `tsc --noEmit` 都 rc=0 而闸根本起不来。我没有去扩别人的 tsconfig（那会一次点亮既有 e2e 类型错误，不属于本单）。

## 六、留给号令者的两点裁语（我没动的尺）

- 已验收词表里 `duration` 那条在中文标签上匹配不到：`45 分钟`、`45分钟`、`需45分钟时间` 实测全 false，`45 min walk` true。 产品的裁切按宽尺走，闸把宽窄两把尺的数都报；要不要把窄尺本身修宽，归那把尺的主人定。
- `qoder-map-ord0412-label-scope.spec.ts` 的 `scope-declared` 臂断言的是 `src/lib/mapLabels.ts` 这枚文件名不存在。 我把产品侧那份命名为 `mapLabelRules.ts`，所以它仍绿；但它当年保护的判语（「无产品代码查此规则」）现在已不成立 —— 判据该从「有没有那个文件名」改成「有没有产品代码在裁」。由那把闸的收件人定，我没改它的任何断言。

## 七、复现

```
python review/map-label-wiring-r1/run_gate_r1.py --tag after \
    --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts
python review/map-label-wiring-r1/report_readings_r1.py --tag after
python review/map-label-wiring-r1/write_report_r1.py
```

原始产物在仓外 `D:\moodle\_qoder_maplabel_wiring_20261008\evidence`：`provenance_*.json` 记下每轮的工作树字节、解释器、端口与库文件。
