# ORD-0384 -- 门条件不真：`trip.stay_budget.declared` 在两套栈上不是同一个值

结论：这是**门的条件不真**，不是产品缺陷。号令者已确认归入门的整改，不记本单账。

## 两侧实测（数字都从收据里数出来，不是回忆）

| 侧 | 读数 | 坐标 |
| --- | --- | --- |
| 手机链 :4781（广州两日，03:55 已被 demo/reset 抹掉） | `declared` = `null` | `live_experience.json@1121` |
| authoritative e2e（扫 42 份 X1/Y1 收据，其中 16 份真的记了这个字段） | `declared` = `false` 共 16 份；`null` 共 0 份；另有 26 份是本单改写后的 Y1，它不再记这个字段，所以不计入分母 | `review/evidence/ord0384/declared_shape_r1.json` |

e2e 侧没有一份收据出现过 `null`。也就是说：写成 `declared === null` 的规则在链上会亮，在门里永远不亮。

## 为什么它不是产品缺陷

面板与推导模块对「响应说什么」是一致的（Y1 双向共现在两套栈上都绿）。不一致的是两套栈对同一个字段说了不同的话，
所以门从未跑过屏幕上真实会出现的那个状态。

## 重定范围之后的现状

`stay_budget_undeclared` 已经不是条目了：`stay_budget` 在生成式契约里只出现 1 次，位置是 `JourneyCreate/properties/stay_budget`，即**请求体那一侧**；两份契约都没有把它写在响应上。
所以这个形状差异现在不再影响屏上内容。但 fixture 仍答 `false` 而链答 `null` 这件事没有修，
任何将来锚在这个字段上的规则都会继承同一个盲区。

补一条给门的线索：三态出口的代码在本树里是存在的（`backend/app/stay_mobility.py:1619` 会答 `STAY_BUDGET_NOT_DECLARED`），所以 `null` 不是缺能力，是 seed 与出口两条路没被同一格覆盖。

## 建议给门的整改

1. 让 e2e 的 seed 能造出 `declared: null` 与 `declared: false` 两种状态，并各配一格；
2. 门的每条断言把「我造的是哪个状态」写进收据（本单 Y2 已按这个写法：三轮分别记 `constructed_open` / `cleared` / `constructed_open_again`）。
