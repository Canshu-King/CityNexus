# ORD-0561 · 承重墙·第一格：颜色令牌清单一枚（**代码现读生成，不许手抄**）

这一件是号令者派给 2d2d7428 的「第二栋楼」的第一格：项目里所有会被屏上渲染的颜色与命名，都要能回答「它叫什么、从哪来、它在亮色与暗色两套形态下各自是什么」。清单由 `token_inventory_r1.py` 现读生成（尖 `2e2ddbaf72eed9565fd8b18ea9b8216061269f57`，读了 23 枚样式表、141 条声明），生成器随件入库以便重跑。

## 〇、这枚清单答什么、不答什么

- **答**：令牌叫什么、在哪一行定义、被谁引用（逐条给出文件与行）、在两套主题下各自写的是什么、以及一处漏掉会怎样漂。
- **不答**：对比度够不够（下一格用浏览器实测补）、`var()` 链最终解析成什么值（本清单按原文记录，不假装解析）。这两件事本件明确留空，不糊。

## 一、规模

| 项 | 数 |
|---|---|
| 样式表 | 23 枚 |
| 声明条数 | 141 条 |
| 认到的令牌 | 112 枚 |
| 其中带色值的 | 49 枚 |
| 内联兜底色（写死在 `var(x, 颜色)` 里的第二来源） | 29 处 |

## 二、六类洞（漏掉一处就是将来会漂的一处）

| 洞 | 枚数 | 含义 |
|---|---|---|
| 引用但无定义（带本地兜底） | 6 | 令牌不存在，但每个调用点自带兜底值——兜底就是第二个没被命名的颜色来源 |
| 引用但无定义（无兜底） | 0 | 浏览器把它解析成空：这类才是真正会「读到 absent」的那一种 |
| 有定义却被内联兜底遮住 | 11 | 令牌在，但调用点又写了一遍兜底；将来令牌一被删/改名，兜底静默顶上，屏照画 |
| 定义了但没人引用 | 9 | 死令牌（要么该删，要么该有调用点） |
| 亮暗两套写法相同却没进 always 家族 | 0 | 令牌文件自己把这个判为红（该进 `--cn-always-*`） |
| always 令牌又被写进暗色块 | 0 | 令牌文件自己把这个判为矛盾 |
| 只在暗色块有定义（亮色读它） | 0 | 亮色形态下这枚令牌读不到 |

其中最要紧的一类：**引用但无定义（带本地兜底）** 6 枚——--cn-font-mono、--cn-yield-left、--cn-yield-top、--v8-bg、--vv-height、--vv-offset。这六个的兜底值逐条在第二节之后列出，每一处都是一个「令牌没了还有颜色」的静默退路。

## 三、那六枚带兜底的令牌：兜底值与位置（逐条）

| 令牌 | 内联兜底值 | 位置 |
|---|---|---|
| `--cn-font-mono` | （无色值兜底） | features/checklist/pretripChecklist.css:30；features/checklist/pretripChecklist.css:34 |
| `--cn-yield-left` | （无色值兜底） | design-tokens.css:1039 |
| `--cn-yield-top` | （无色值兜底） | design-tokens.css:1040 |
| `--v8-bg` | #f4f6f2 | v10.css:50 |
| `--vv-height` | （无色值兜底） | design-tokens.css:1127；styles.css:796 |
| `--vv-offset` | （无色值兜底） | styles.css:796 |

## 四、内联兜底色（写死在调用点的第二来源）

共 29 处。它们都是真会画到屏上的颜色，但没有任何一行清单能说清它「叫什么」——这是这面墙要补的第一类洞。逐条：

| 兜底令牌 | 兜底值 | 位置 |
|---|---|---|
| `--cn-hairline` | `rgba(0, 0, 0, 0.16)` | features/simulation/SimulationPanel.css:38 |
| `--cn-hairline` | `rgba(0, 0, 0, 0.16)` | features/simulation/SimulationPanel.css:85 |
| `--cn-hairline` | `rgba(0, 0, 0, 0.16)` | features/simulation/SimulationPanel.css:142 |
| `--v8-ink` | `#1d2531` | features/planning/planRanking.css:5 |
| `--v8-ink` | `#1d2531` | features/planning/planRanking.css:6 |
| `--v8-accent` | `#0f766e` | styles.css:517 |
| `--v8-accent` | `#0f766e` | styles.css:518 |
| `--v8-accent` | `#0f766e` | styles.css:523 |
| `--v8-accent` | `#0f766e` | styles.css:524 |
| `--v8-accent` | `#0f766e` | styles.css:587 |
| `--v8-accent` | `#0f766e` | styles.css:588 |
| `--v8-accent` | `#0f766e` | styles.css:642 |
| `--v8-accent` | `#0f766e` | styles.css:698 |
| `--v8-accent` | `#0f766e` | styles.css:700 |
| `--v8-accent` | `#0f766e` | styles.css:1179 |
| `--v8-accent` | `#0f766e` | styles.css:1180 |
| `--v8-accent` | `#0f766e` | styles.css:1204 |
| `--v8-accent` | `#0f766e` | styles.css:1248 |
| `--v8-accent` | `#0f766e` | styles.css:1366 |
| `--v8-accent` | `#0f766e` | styles.css:1497 |
| `--v8-accent` | `#0f766e` | styles.css:1498 |
| `--v8-muted` | `#5b6675` | features/planning/planRanking.css:9 |
| `--v8-muted` | `#8994a3` | styles.css:675 |
| `--v8-muted` | `#607174` | v10.css:55 |
| `--v8-line` | `#e3e7ef` | features/planning/planRanking.css:3 |
| `--v8-line` | `#e3e7ef` | features/planning/planRanking.css:7 |
| `--v8-surface` | `#fff` | styles.css:1281 |
| `--v8-surface` | `#fff` | styles.css:1378 |
| `--v8-bg` | `#f4f6f2` | v10.css:50 |

## 五、清单怎么重跑

```
cd D:/moodle/_qoder_q_ord0422_20261001 && TIP=<40 hex> D:/moodle/CityNexus/.venv/Scripts/python.exe token_inventory_r1.py
```

生成器只读 `frontend/src` 下的样式表，逐行记下每个 `--token: value` 的定义块与每个 `var(--token)` 的调用点；暗色归属按**块的花括号配对**判定（不是「第一个暗色选择器之后都算暗色」——那种线性边界会把令牌文件下面第二个顶层 `:root {}`（底栏几何、触控下限）误判成暗色）。行号按**原文**计数（注释只抹白不删除），所以每个坐标都能在文件里逐枚打开回读。

## 六、没做的，具名

- 本格只交清单（现读生成、零产品字节）。**对比度是下一格**：用浏览器现读两套主题下每个令牌的真实解析值与背景，算 WCAG 比值，并配「该红的那一次」。
- `var()` 链的最终解析值本件按原文记录、未解析（下一格实测时由浏览器给真值）。
- 产品字节 0 枚改动、契约 0 枚；前端 e2e 整套没跑（`NOT_EXECUTED_BY_CMDR`）；权威尖我没移动过、已发布 ref 覆盖 0 次（force-push 没用过）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
