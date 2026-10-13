# ORD-0686 补漏：`_provider_collocated_edge` 这八行——装前一枚红、装后转绿、邻面与整树零变化

尖 `e1f352030e61b96bbda2c487c3386e8e93b76163`（`git ls-remote` 现读，`git cat-file -t` 回 commit）。出处 `0639d68b1efc5d08d7b12589a2f3a93cc001624f`（`git cat-file -t` 回 commit；它的 backend/app/stay_mobility.py 的 blob 是 `af15f8f8c4f1c7e2bb931e8f8311c65a985d9595`，`git cat-file -t` 回 blob）。

## 洞在哪（现尖，本拍现读）

| 读数 | 值 | 锚 |
|---|---|---|
| 那枚文件里 `def _provider_collocated_edge` | 零命中 | backend/app/stay_mobility.py:1 |
| 但它被调用 | 两处，第 2155 与 2207 行 | backend/app/stay_mobility.py:2155 |
| 出处那一代的定义 | 第 1684 到 1691 行，八行（含 docstring 与空行） | 0639d68b1efc5d08d7b12589a2f3a93cc001624f |

装法：只把那八行逐字追加在本文件模块级末尾，不重排、不改别人的行号；文件从 2227 行走成 2238 行，回车字节零（本仓 `.gitattributes` 把 `*.py` 钉成 `eol=lf`）。

## 闭包先过，再谈绿

按符号表逐枚查这八行读到的全局名，落在尖上那枚文件里的：全部解析（未解析清单为空）。这与今天那回「搬了 530 行函数体、拖出 recovery-epoch 整条 feature、邻面当场红三十一枚」是同一道闸——那次的成因就是没人查这一步。

## 两栏读数（一次跑批：解释器 `D:/moodle/CityNexus/.venv` 3.12.14，命令 `-X utf8 -m pytest -q -p no:cacheprovider`；一次性导出树，测试文件只放进去量、不进本枝）

| 量什么 | 装前 | 装后 | 锚 |
|---|---|---|---|
| 整枚 r77 文件（测试取自出处那一代，blob `19aba4700178`） | `13 failed, 21 passed, 2 warnings in 2.31s` | `12 failed, 22 passed, 2 warnings in 4.29s` | 0639d68b1efc5d08d7b12589a2f3a93cc001624f |
| 转绿的用例 | `test_selected_plan_projection_names_provider_collocated_zero_minute_edge` 一枚 | 同左 | backend/app/stay_mobility.py:2207 |
| 新增红 | — | 零枚 | backend/app/stay_mobility.py:1 |
| 邻面：尖上 import 这枚模块的测试文件 18 枚 | `5 failed, 165 passed, 2 warnings in 21.40s` | `5 failed, 165 passed, 2 warnings in 23.66s` | backend/app/stay_mobility.py:2155 |
| 整树收集 | `1992 tests collected`（rc=0） | `1992 tests collected`（rc=0） | refs/heads/mirror/integration-frontend-apple-pass1 |

一句口径：号令者 17:05 读到的基线是另一代尖、另一把尺（他那块写 18 passed 与 8 failed），本表两栏只出自本拍同一棵树的两个臂，不与那一枚数对照。

## 本枝里没有的

没有测试文件（CMDR-DELIVER-0683 丁.2：测试只由集枝人带一次）、没有 `backend/app/main.py`、`backend/app/schemas.py`、`backend/app/services.py`、`backend/app/fact_acquisition.py`、`contracts/openapi.yaml`、`frontend/src/i18n/LocaleContext.tsx`、对账表 tsv；没改任何断言、没 skip、没造夹具。

## 另一处同病的，留给领组的人（我没碰）

`backend/app/services.py` 的 `_place_metadata` 同样有调用无定义：定义零命中、调用在第 2184、2218、2238、2262、2306 行；出处那一代的正本两行（`0639d68b1efc5d08d7b12589a2f3a93cc001624f:600`）。它归 services，是热文件、且 CMDR-DELIVER-0685 丁已把那枚文件的 import 与 config 字段派给键盘工——所以我不动它，只把坐标留在这里。
