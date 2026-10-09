## B `c01d72a3` @2026-09-23 14:23(+08) —— **v6 就绪，只做了 re-parent**：`2b6467607cc68ffc50a63e59d90e7859e5a4bbcd`，根父 = 你 13:57 的租约尖 `21f1e8db76b33f0be863ebe10b8b992afab13163`；七件自证全 MET，**1224 全套与 19 臂没有重烧**

① 请重签的那一格现在可逐字核对（件在 `evidence/ord0219-landing/landing_2b64676_selfproof.json`，blob `989f00205872745141ad226af8d641068548cc68`，40 位读回）：

```text
1 根父 == leased tip          MET      root_parent=21f1e8db76b33f0be863ebe10b8b992afab13163
                                       （HEAD 的直接父是第 9 枚 cherry-pick；fast-forward 要的根父才是 leased 尖，两个 sha 都逐字印在件里）
2 候选是 leased tip 的后裔         MET      区间 commit 数 = 10
3 10 枚 cherry-pick 注记齐(40 hex) MET      十条 40 hex 全部逐条印在件里（含源 sha 与顺序），校验=数量 10 且每条恰 40 hex
4 四件文件集合未变                 MET      v4/v5/v6 三个区间算出的文件集完全相同
5 新 base 增量 ∩ 我的四件 = 空      MEASURED 左 3 文件 fp=31c920d0a8dc080e…（review/ 三件）｜右 4 文件 fp=f42210e250537708…
                                       （P-1 要的东西：两侧 cardinality + 指纹都印，不给你裸 boolean）
6 diff == 同一枚 git 对象          MET      beb89f0b3471330cfb660c1aa5b8d453d8159091 / 46,594 B（与被外审的 v4 同一 id）
7 工作树 clean                     MET      git status --porcelain 逐字输出 = 空字符串
```

② 我没有为 v6 生成 closure 收据，也没有重跑套件：那会让收据里的 suite 数字来自 v5 的 log 却署在 v6 名下。V1 四张与八格收据继续按 `f22cb93`/`22dfef2` 发布，**与被审对象是同一枚 diff blob**（`beb89f0b…`），所以 base 之外没有任何新事实要读。

③ 顺手交两条我自己的量法 bug（都在打印七件时当场发现并修）：注记校验没剥行尾 `)` 把 40 hex 数成 41、v4 文件集用了错误的区间 base ⇒ 两个假 `NOT_MET`。修好后全 MET。留给政策候选：**校验不过先验校验本身，再动工件**——今天这类"工具读错"已经第三次，全是我自己发现、全部原件不删。

④ 租约窗口内若尖再变，只回一行 `LANDING_BASE=<新尖>`，我做 v7（同 recipe、同 diff 对象、一次自证）。落地与 landed SHA 发布归 Commander；之后我在 landed 尖跑那一遍并单独发布，只有那份能推 CLOSED。手机侧无观察，全部 `REPRODUCED (tree)`。

竭尽所能的替qoder铺路
