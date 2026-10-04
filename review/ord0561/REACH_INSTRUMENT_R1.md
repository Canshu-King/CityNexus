# ORD-0561 校准 · 我这把路由仪表收尾：六类可达性判据装进去了，并且逐枚反控证明它们能咬

代次：读数在 `f3ba478caaecdbdf7254786b2bf0d03d323897d0` 上取（`git ls-remote --refs origin refs/heads/mirror/integration-frontend-apple-pass1` 现读），同代 `vite build` 产物入口 `http://127.0.0.1:4892/assets/index-BcQ9VAso.js`（1622092 字节，服务字节 sha1 与磁盘字节 sha1 相同 `1ca92fee8fc18a4b6b17031970149b5976eb352c`），私有栈 api pid 44860 / static pid 39736，库 `_r5_rch2.db`，静态口代理 CITYNEXUS_BACKEND_PORT=4891。写件这趟现读线尖 `0293e5c1cf9be4ea4e7d14005e14c508cb3f528b`。

## 一、题面与它的来源

号令者点的是：按 `1ba48dbf` 今天的 ORD-0561 读数件把那 6 类装进我这把仪表。那族的坐标是枝 `refs/heads/review/1ba48dbf-ord0561-screens-r1` 的头 `d9424847a51a04b0a0d8e6fb731a0476606b6137`，件 `review/ord0561-screens/shape_r1.json`（服务端 blob `79763ddbb86274196e970290ea32b446efbdaa6a`，本机取到 11756 字节，它的仪表源码在同一枝的 `review/ord0561-screens/shape_probe_r1.cjs.txt`）。它那件里 `errors` 是空数组 ⇒ 它的两臂五屏全部读到了东西，我拿它当校准面是站得住的。

## 二、我这把仪表现在装了什么

| 类 | 判据（装进仪表的那一句） | 与它那把的关系 |
| --- | --- | --- |
| C1 一句完整的话被压成 1 px | 叶子元素 `scrollWidth > clientWidth + 1` 且渲染宽 `clientWidth <= 4 px` | 同判据，我另加了一条渲染宽上限，专门收「整句还在、画面只剩一条竖线」那种 |
| C2 无名/只有字母的控件 | `aria-label`、`title`、`textContent` 三者全空；或 `aria-label` 缺失而可见文字只剩两三个字母（顶栏头像 `v8-avatar` 那一族） | 它那把没测这一类，只把它当截断报出来；这是我这轮新增的第二格 |
| C3 按钮中心被正文盖住 | 中心在视口内的按钮，`elementFromPoint(中心)` 命中的不是它自己/它的子孙/它的祖先 | 与它那把同判据，我另外记下命中方与被盖方各自在不在底栏里 |
| C4 行内动作落在固定底栏里 | 中心 y 越过 `768 px` 那条账本冻住的上沿（`ORD-0401`），或中心被底栏 `.v8-mobile-nav` 接走；**底栏自己的控件不算**（那 5 枚本就该在那条带里），排除的枚数单独记 | 它那把只报「被盖住」，我这一条把「在底栏之下」单独拆出来了 |
| C5 Copilot 屏的入口键被压 | C3/C4 里落在 `/v8/agent` 的那些 | 同一判据在它那点名那一屏上的取集 |
| C6 以省略号收尾的触键 | 可见 `button` 的渲染文字以 `…` 或 `...` 收尾 | 同判据，我只收按钮（它把 span 也一并收了） |

跑法（一条命令跑两臂两形，仪表是 `sweep_ink_r1.cjs`）：

```
MAP=<ink map> LOCALES=zh-CN,en TIERS=light SHAPES=390x844,1280x900 \
  node sweep_ink_r1.cjs <label> sweep_<label>.json <journeyId> <shareToken>
LBL=<label> python sum_reach_r1.py        # 校准与分类
LBL_BASE=<base> LBL_MUT=<mut> python diff_mutant_reach_r1.py   # 六类逐枚反控
```

仪表字节：`sweep_ink_r1.cjs` 14411 字节 B、`sum_reach_r1.py` 8690 字节 B、`diff_mutant_reach_r1.py` 4033 字节 B、`mutant_reach_r1.js` 2433 字节 B、`chain_reach2.sh` 1486 字节 B、`parse_check_literals_r1.cjs` 1276 字节 B（逐枚本机字节 sha1 在 `二·补` 一节）。

二·补 逐枚本机字节 sha1（这几枚是本机文件重算的 sha，未入 git、不是 blob，故意不可取回；要跑就用上面那条命令，别从这几枚 sha 取件）：

- `sweep_ink_r1.cjs`：本机字节 sha1 4f20f9f3bdf4aed68370c7e405a2963e61257380
- `sum_reach_r1.py`：本机字节 sha1 f1723026d259a1c1599d8050c685144494f939f5
- `diff_mutant_reach_r1.py`：本机字节 sha1 5511b4796557d24b3b2b0c0e514e08c9f684592b
- `mutant_reach_r1.js`：本机字节 sha1 62651b886ebc7f5ceefacbe2ff12ae0a57801c19
- `chain_reach2.sh`：本机字节 sha1 e6e72eea52aaf0aca914a571b5e669e32648944f
- `parse_check_literals_r1.cjs`：本机字节 sha1 ffca8fa2ec0ef7b051140969b75eb0bd61d04640

## 三、校准：在它那张网格上逐类对数

网格 = 它的五屏（`/v8/hub`、`/v8/trips`、`/v8/map`、`/v8/agent`、`/v8/me`）× 390 宽 × 每臂一趟；我这把在同一网格上每臂也读到 5 屏，`not_mounted` 为 0 趟。

| 臂 | 它那把 covered | 我这把 covered | 我这把扣掉底栏自身 | 它那把 clipped | 我这把 clipped | 它那把 ellipsis | 我这把 ellipsis | 我这把 no_name | 我这把两字母无 aria | 我这把越过 768 那条线 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| zh-CN | 6 | 19 | 19 | 7 | 7 | 6 | 6 | 0 | 30 | 10 |
| en | 3 | 18 | 18 | 7 | 7 | 6 | 6 | 0 | 15 | 11 |

对得上的：`clipped` 与 `ellipsis` 两臂逐类相等（见上表）。对不上的是 `covered`——我这把比它多，原因我量出来而不是猜：① 我的选择器面是 `button, a[href], [role=button]`，它那把只有 `button`；② 它按底栏 `nav-<key>` 点击进入（每屏都滚过、面板状态与我的直达 URL 不同），我按路由直达；③ 我把中心越过 `768 px` 那条带的命中也算进 covered（它只算视口内被他人接走的）。这三条差异里只有 ① 与 ② 会让数变大，③ 是分类口径不同——所以我不判它的数错，也不判我的数错，两把的网格与判据都摆在上面。

## 四、六类在我这张面上（17 条路由 × 2 臂 × 2 形 = 68 趟）

| 类 | 命中枚数 | 中文臂 | 英文臂 |
| --- | --- | --- | --- |
| C1 | 16 | 8 | 8 |
| C2 | 285 | 200 | 85 |
| C3 | 2 | 1 | 1 |
| C4 | 109 | 55 | 54 |
| C5 | 4 | 3 | 1 |
| C6 | 4 | 2 | 2 |

底栏自己的控件被排除出 C4 的枚数：0 枚（排除是有数的，不是默默丢掉）。演示门：`demo/reset` http_status=200、`prepare-scenario` http_status=200、`demo/scene` http_status=200，站点 6 段、无坐标 0 段，错 token 的重置回 http_status=403，分享授权回 http_status=201。

## 五、六类逐枚反控（这才顶「仪表能咬」）

反控臂在同代产物上往屏里注入每类一枚缺陷（每枚带 `data-testid=cn-mut-…` 自己的记号），干净臂必须 0 枚记号——现读干净臂记号 0 枚、反控臂记号命中 6 格；两臂入口资产同名 `index-BcQ9VAso.js`。

- `C4 动作落在底栏之下` → below_floor:c4 命中 6 枚
- `C1 一句被压成 1 px 的话` → clipped:c1 命中 6 枚
- `C3 中心被正文盖住` → covered:c3 命中 6 枚
- `C6 省略号收尾的触键` → ellipsis:c6 命中 6 枚
- `C2 头像族只有两个字母` → glyph_name:c2b 命中 6 枚
- `C2 无名控件` → no_name:c2 命中 6 枚

## 六、我这一手没做的

产品字节 0 枚改动：这手只把仪表收尾，没修屏上任何一枚缺陷。前端 e2e 整套没跑（`NOT_EXECUTED_BY_CMDR`，本件结论不依赖测试计数）；没量实体手机；瓦片底图在这台机器仍不加载，`/v8/map` 走的是 `domcontentloaded` 这条导航策略，没有一个结论依赖瓦片像素。上几手挂着的仍未闭并具名：共享预览口还在服务落地前的产物字节（换代要号令者动那枚口），「乙」那三行没带档位前缀那格仍等裁，墨色普查里 34 枚没上过屏的选择器要带状态驱动才量得到。

