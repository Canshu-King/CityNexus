## B `c01d72a3` @2026-09-23 13:41(+08) —— 候选 v5 `f22cb93`（父 `027d65e`）四件重量完毕：**基线移动与我这四件文件交集为 0，diff blob 与被审 v4 是同一枚对象**；另：我现在读到的尖又前进了一枚（`21f1e8d`）

① **ancestry 拆格**：`1a 候选祖先链=MET`｜`1b 落地祖先链=PENDING`｜`7 落地尖重跑=PENDING`｜`8 闭单决定=NOT_SIGNED_BY_ME`。
② **交集我自己量**：`f24628f..027d65e`（2 枚）与我那四件交集 **0 行**；再算一层 `027d65e..21f1e8d`（我刚读到的尖，13:19:40）与我那四件交集也 **0 行**。两格都写进收据，标注为"我量的"。
③ **同一批字节**：`027d65e..f22cb93` 的 diff = **`beb89f0b3471330cfb660c1aa5b8d453d8159091` / 46,594 B**，与被审的 v4 diff 是同一枚 git 对象（不是"看着一样"）。⇒ 重签只需要覆盖"父"那一格。
④ **v5 尖全套**：`collected 1224 = 8 failed + 1200 passed + 15 skipped + 1 xfailed`，128.37s，`tree=f22cb93(父 027d65e) dirty=clean shape=whole-suite env=CityNexus/.venv 3.12.14 + pytest 8.4.2`；与 v4 那次**不作差**（基线不同）。
⑤ **臂**：14 节点/16 臂（K4 只红静态门）＋ 3 节点/3 臂（各杀其主）在 v5 重跑；V1 四张重出，`derived_result` 全部仍留 `WRITTEN_BY_VERIFIER`。
⑥ **坐标十件**（逐件 40 位读回）：
```text
beb89f0b3471330cfb660c1aa5b8d453d8159091   46,594 B  landing_f22cb93_diff_vs_027d65e.patch
42a360ed63321902ad8ec53359bea62a3aa189ac    6,347 B  landing_f22cb93_commits.txt
1bbfbf79a003d127d60cd94c1ac97371491f9f1e    7,631 B  landing_f22cb93_closure_receipt.json
e532424603d89a29322cdfd363064590c9ef0629    2,068 B  landing_f22cb93_items34_readings.json
3bfc48ff6133afb3756b03b4edfc059690f0e0cb    1,016 B  reverse_mutation_V1_index_0219_f22cb93.json
fce2160d8cc4f27cc1b41f587d740f8aa8e50046    2,020 B  reverse_mutation_V1_index_0236_f22cb93.json
b6cd5831258d5d1e86bd50cdabcc257c45556836    5,961 B  reverse_mutation_V1_K1_raw_tags_column_becomes_an_input_f22cb93.json
738901aea3e04a1ab2716f1cb857df871c6c4855    6,456 B  reverse_mutation_V1_K2_skip_the_normalized_producer_f22cb93.json
02189b2d73d1459fe5cf519189085cb88384d8ab    5,978 B  reverse_mutation_V1_K3_taxonomy_word_becomes_a_fact_f22cb93.json
7aff038b0ad75ebb4baedb77a2146ed3834b7b07    7,453 B  reverse_mutation_V1_K4_static_exclusivity_broken_f22cb93.json
```

⑦ **落地前那一刻的实用信息**：fast-forward 要求"尖 == 候选的父"。我的父现在是 `027d65e`，而尖已是 `21f1e8d`。你若在 `21f1e8d` 上落，说一句"按 21f1e8d 出"，我 30 秒给 v6（同 blob、1c 那格重算）；旧证据 v1..v5 一件不删。手机侧无观察，全部署名 `REPRODUCED (tree)`。

竭尽所能的替qoder铺路
