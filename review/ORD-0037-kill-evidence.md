# ORD-0037 杀证据记录（map 交互 + 路线可读性）

会话 `e345b9d6` · 门 `frontend/e2e/qoder-map-interaction.spec.ts` · 驱动 `review/ord0037_kill_drivers.py`

`*.log` 被仓库 `.gitignore:39` 排除，所以逐条读数记在这里；原始日志在同名 `review/kill-*.log`（本地）。
每个变异体跑完都从 pristine 还原并校验 sha1，六次全部 `OK`，驱动在指纹不符时会直接 `exit 2`。

## 前置：这张表测的是什么

门不测 `interactive` 这个标志位，它派发布尔手势再读 `map.getCenter()/getZoom()`；
路线一半读组件自己公布的契约（`data-route-legs` / `data-route-modes`）加图层声明的 paint 表达式。

不用 `GeoJSONSource.getData()`，也不用 `queryRenderedFeatures({layers})` 做分母：在同一屏上实测两者都返回 0，
而 caption（直接把 `route.length` 从 React 打出来）读 8。`getData()` 交回的是 maplibre 内部结构，
既无 `type` 也无 `features`；rendered-features 查询受 worker 切图和视口支配。分子分母对不上，就不能当门。

pristine 基线 sha1：`c30b937a9617955300684d3bfc5a0b46c61a34d0`（`MapPanel.tsx`，含交付态注释）。

## 逐节点结果

| 变异体 | 改动形状 | 点名节点 | 结果 | 红消息（原文摘录） |
| --- | --- | --- | --- | --- |
| kill-a-interactive-false | `interactive: true` → `false` | `drag-moves-camera` | 杀死 1 failed / 3 passed | centre unchanged after a real pointer drag (117.23850000000004,39.114212600733225 -> 同一坐标); gestures are switched off |
| kill-a2-scrollzoom-false | 加 `scrollZoom: false` | `ctrl-wheel-zooms` | 杀死 1 failed / 3 passed | zoom unchanged after Ctrl+wheel (9.06783337135099 -> 9.06783337135099) |
| kill-e-merged-single-line | 8 段几何合并成 1 条 LineString | `route-feature-count` | 杀死 1 failed / 3 passed | the route source carries 1 feature(s) (caption: "Route context 1 legs…") |
| kill-f-constant-colour | `line-color` 回到常量 `#4658d9` | `route-mode-colour-expression` | 杀死 1 failed / 3 passed | line-color is a constant, so every leg paints the same colour |
| kill-c-constant-width | 主层 `line-width` 回到常量 4 | `route-width-follows-zoom` | 杀死 1 failed / 3 passed | line-width is a constant, so the line cannot stay legible across zoom levels |
| kill-d-no-casing-layer | casing 图层 id 改掉 | `route-casing-layer` | 杀死 1 failed / 3 passed | no casing under the route |
| kill-b-no-mode-property | 去掉组件自己盖的 `mode` / `leg_index` | `route-mode-colour-expression` | **存活 4 passed / exit 0** | — |

kill-a 之外还补了 kill-a2：`interactive: false` 会先打死 `drag-moves-camera` 并在同一测试里短路，
`ctrl-wheel-zooms` 拿不到自己的红，所以给它一个只关缩放、留拖拽的变异体。
六个节点各配一个形状的变异体，不是"一个变异体打死六个"。

## kill-b 存活说明了什么（不是门坏了）

临时探针（`review/evidence/ui-overnight/map-mode-probe.json`）读 `/experience` 的原始载荷：
每一条几何本身就是带 properties 的 Feature —

```json
{"crs": "WGS84", "mode": "AUTO", "provider": "citynexus-synthetic-fixture"}
```

`mobility_facts` 同样带。也就是说 `data-route-modes` 量到的是**供给方的数据**，不是我盖的那个字。
所以"删掉我的 tag 仍然绿"是正确的：门不能证明一条当前无人依赖的保险丝。

保留 `tag()` 的理由已写进源码注释：它把视觉契约与供给方的自觉解耦。真出现不带 `mode` 的供给方时，
`["case", ["==", ["get","mode"], …]]` 会全部落到 fallback 色，"一根大线"以另一种方式回潮，
而屏幕上不会说样式降级过。要把这条臂变成可杀的，需要一份不带 properties 的 mobility fixture —
那是后端几何/夹具的改动，订单明确禁止我碰（"不改后端几何生成逻辑"）。**记为已知缺口，不当成绩。**

顺带一条观察，不下结论：探针里 `active_plan.legs` 的 mode 是 AUTO/WALK，而 `options[0].leg_mode_map`
同期写的是 TRANSIT。这两者是否指同一选项的同一批腿我没有验证（4 个 option 只打了第 0 个），
所以只登记为"谁消费哪个源"的疑问，不改任何东西。

## 我自己引入又被门抓住的回归

`gates-ord37-full.log`（run `uiord3702`）：`qoder-contrast-audit` 亮色档新增 2 条 violation —

- `div.maplibregl-desktop-message` "Use Ctrl + scroll to zoom the map" fg=#fff bg=rgba(0,0,0,0) **3.41**/4.5
- `[data-testid="v8-map-gesture-hint"]` fg=#6e6e73 bg=rgba(0,0,0,0) **4.12**/4.5

原因就是我这次把 `cooperativeGestures` 打开、又新写了一行飘在瓦片上的提示。
修法只动 CSS（`design-tokens.css`，我这一侧的文件；`MapPanel.tsx` 已按 ORD-REASSIGN-003 归 `8c66aa92`，
我没有为回归再改它）：两个标签都换成不透明贴片 `--cn-surface` + `--v8-ink` + `--cn-hairline`，
不新增字面色值。修后 `gates-ord37-contrast-fix.log`：today/live × 亮/暗 × 移动/桌面 全部 0 violation。
