# ORD-0287 · 第 0 条：`test_G9` 原样摘到 `45b0a5e2` 跑不跑得起

lane F `8ccd71d8` · run `O287S0-250638-07baa0` · 2026-09-25T06:38:52+08:00

**答案：跑不起。** 拦路的是产品符号，不是我那格写得偏。按判据 0 我就停在这里——没建分支、没改断言、没 skip、产品字节 0 改动。

## 具名 + blob + 报错原文

```text
缺的符号            _fill_plan_generation_receipts
落地代 45b0a5e2 的 backend/app/main.py  blob 416ea4f210e967130710a900cdecd20e7a1b5eca   该符号命中 0 次
候选 7c806fab5 的 backend/app/main.py  blob ad13f4395e3405ce722ae8660836f3c2aaa29df2   该符号命中 2 次（一处定义、一处调用）
两代门文件本身也差：落地代 efa783397e6105ca8f15be9a5701e60e5ace0296（22 个 def，8 格）vs 候选代 799fbd2fe9d28433405408ddec1d7405b2d1c9d9（23 个 def，9 格）
外取对表（GET /repos/Canshu-King/CityNexus/contents/<path>?ref=<sha>）与本机重算逐位一致 ⇒ True

v1 原样追加（一个字不改，47 行 / 3,233 B）⇒ rc=1｜1 failed, 2 warnings in 2.11s
  报错原文：
    E   ImportError: cannot import name '_fill_plan_generation_receipts' from 'app.main' (D:\moodle\_qoder_f_run\e_0287_step0\Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7\backend\app\main.py)
v2 只补一行测试文件自己的 import（from datetime import datetime, timedelta, timezone；断言 0 改、产品 0 改）⇒ rc=1｜1 failed, 2 warnings in 1.39s
  报错原文（同一句）：
    E   ImportError: cannot import name '_fill_plan_generation_receipts' from 'app.main' (D:\moodle\_qoder_f_run\e_0287_step0\Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7\backend\app\main.py)
正控 同一棵拷贝树/同一形制的一次性库/同一解释器，跑权威线本来就有的 G1 ⇒ rc=0｜1 passed, 2 warnings in 1.51s
```

## 三条读数怎么读

```text
1) 红是**特异的**：同一棵拷贝树里 G1 绿、G9 红 ⇒ 不是库、不是舞台、不是解释器；
2) v1 与 v2 是**同一句 ImportError** ⇒ 我原先猜的『补 import 才露出真拦路石』没发生：G9 函数体第一句就是那句 import，所以 datetime 那处缺口在它后面，这一代量不到它单独的作用；
3) 那处 datetime 缺口只作**静态事实**记：落地代那道门文件里没有 `from datetime` 这一行（实测 False），而 G9 函数体用到 datetime/timezone/timedelta 共 5 处，候选代那份文件顶部是带着这行 import 的。
```

## 下一步（等你点名，我不自己拍）

```text
甲：先把 7c806fab5 那笔（缝 + G9）落进权威线，G9 就原样可跑——这是把『同代同名格』补齐的唯一路；
乙：我在权威线上写一枚不引 _fill_plan_generation_receipts 的载体（两半互控：别人已填不许动 + 我占的 NULL 必须填上），对着落地代内联那一处 UPDATE 测，两态可跑（权威树 GREEN、拆掉守卫 RED）；
两条都不碰断言换绿、都不碰产品字节。判据 3 的『两态可跑』我预判乙更省事，甲更彻底——你选。
```

```text
纪律：断言改动 0 处；产品字节改动 0；skip 0；分支/权威线写 False；demo/reset 0 次；凭据打印 0。
源导出只读复用（True），跑完回验主文件 blob 未动：True；实验都在拷贝树 D:\moodle\_qoder_f_run\e_0287_step0\Canshu-King-CityNexus-45b0a5e281cae9c37715173afd3ac5778f309ca7
读数与仪器：本件 + ord0287_step0_portability.json + o287_step0_portability.py（三件同目录）
```

