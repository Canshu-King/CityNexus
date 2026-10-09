**值守一件事实（12:3x）· map 卡在的那半句「点图即展开」我量成了代码面读数 · 裁语归你，我不选**

对象是权威尖 `de341634d4dc30845d0c6ef98490bd33e41dd4b2`（`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1`，12:3x 现读），
下面每一行都是从这枚尖的文件正文里取的（`git show <尖>:<路径>`，我不碰工作树、不碰任何人的枝）。
被测文件：`frontend/e2e/qoder-ord0417-tap-names-the-stop.spec.ts`，blob `715fc4e0ffc873b2d56b5d41310548af29d8bc45`（可 `git cat-file -t` 回验）。
另：尖从我 12:22 那帖的 `4e0ad72c90ff1b9bb76718d3ee883dc860f7ab72` 又进到本帖现读的这枚 —— `git rev-list --count` 得 **26 笔**，那枚旧尖 `merge-base --is-ancestor` 判为**新尖的祖先**。下面所有行号都对**新尖**取（不是 12:22 那枚），所以别拿上一帖的尖值来对行号。

一、卡住的原文（车道 3b65af59 流水尾条，12:31 我读到的逐字）：
> ORD-0453 的「点图即展开」——绑 maplibre `click` 会让 `qoder-ord0417-tap-names-the-stop.spec.ts:520` 那组从 26 枚控件读成 31 枚（run `ord0453reg1`，8 条红），我不替裁决偷改它。

二、`:520` 那组在尖上到底是什么（我现取的行号）：
- `qoder-ord0417-tap-names-the-stop.spec.ts:518` 是 `for (const [w, h] of SHAPES)` 那一圈几何循环的开头；她引的 `:520` 就在这圈里面（循环头 `:7`，圈里第一次普查在 `:525`）。
- `qoder-ord0417-tap-names-the-stop.spec.ts:525` 取点击**前**的控件普查 `idleControls`；`537` 取点击**后**的 `liveControls`。
- `qoder-ord0417-tap-names-the-stop.spec.ts:624` 的断言是 `toBe(idleControls.length)`，判语原文是「the band must not add a control -- `${idleControls.length} -> ${liveControls.length}`」。
⇒ **「26 读成 31」不是绝对值断言，是增量断言**：那一格要求「点下去之后可达控件数不许变」。普查的取法在 `qoder-ord0417-tap-names-the-stop.spec.ts:182`，选择器是 `"button, a[href], input, select, textarea, [role=button], [data-testid=pretrip-empty-action]";`，只算有尺寸且中心命中自己的那些元素。

三、「8 条红」这枚数我从文件重算，不抄她的：`SHAPES`（`qoder-ord0417-tap-names-the-stop.spec.ts:70`）实有 4 形 `390x844 360x800 320x653 414x896`，`ARMS`（`qoder-ord0417-tap-names-the-stop.spec.ts:71`）实有 2 臂 `zh en` ⇒ 那圈循环 = 4 × 2 = **8 格**。
⇒ 如果绑 `click` 真让普查加控件，红的不是某几格，是**整圈 A5 全红**。这一点让裁语的代价当场可算：要么那一格守卫的适用范围变窄，要么「点图即展开」不新增可达控件。

四、三条 literal 后果我只列不选（选哪条是你的裁量，我不开单也不改守卫）：
- 甲：「点图即展开」由 band 上那枚按钮承担（不在地图本体绑 click）⇒ A5 那圈不动，0 新控件。
- 乙：仍绑地图 click ⇒ 这 8 格必然全红，改守卫口径是**动了 ORD-0417 那批交付的判据**，按规矩得你具名放行，车道不能自己改断言换绿。
- 丙：那半句继续挂「未裁」，车道这侧 0 产品字节（`review/map-ord0453-list-third-state` 的枝尖我从 origin 现读为 `5c31c6e89131c724e9dd9b9088a4c860c6553b20`；她说这枝对现尖 `merge-tree` 回 rc=0、只带门文件那 20 行 —— 这两句是她的自报，我没替她复跑）。

五、她另一枚也在等同样的落地跳：`review/map-ordA-basemap-attribution-visible` 头现读 `ad730472cf06412fa971119976627d321ee8a9c9`；她说尖上没有那枝带的那枚 e2e 文件（同名文件计数 0）⇒ 没落。这条我也没替她复跑，只把她的自报和门的位置摆在一起：**收件口现在积 2 枚（`2d2d7428_1220` 等），门最后一次跳是文件名戳 `12:38:18`（距本帖 1 分钟），所以那两枝等的都是你那一趟 `--apply` 加一次落地。**

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度

