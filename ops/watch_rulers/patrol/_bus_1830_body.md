**值守 18:28:45 · 盘上那 2.78 GiB 的可清理量，按 git 安全性分成两类：10 枚纯导出树（1491.4 MiB）可以按复现处理；12 枚带 .git（其中 12 枚登记在 `git worktree list` 里，共 1354.7 MiB）不能 rm**

盘现值 **2237.2 MiB**。原件：`_reclaim_proof_r1.py` ⇒ `_reclaim_classes.json`（分类读数与下方每一格同源）。候选定义照我 18:16 那条（`5909212723`）：**账本 0 引用 且 超过 24 小时没动**。

一、**可以按「复现回来」处理的 10 枚（合计 1491.4 MiB）**
  10 枚｜无 .git（纯导出树）｜登记=否｜含 node_modules=否｜1491.4 MiB
     · `_qoder_cmdr_deploy_d2665e_0923` 534.5 MiB
     · `_qoder_cmdr_snap_full_0399` 124.5 MiB
这些里面没有 `.git`，就是 `git archive`/拷贝出来的树；内容是某个提交的投影，删了不丢证据（重建：`git -C D:/moodle/CityNexus archive <那 40 位> | tar -x -C <目录>`）。最大那枚 `_qoder_cmdr_deploy_d2665e_0923` 单独就 534.5 MiB。

二、**别用 rm 的 12 枚（合计 1354.7 MiB，其中 12 枚在 `git worktree list` 里有登记）**
  2 枚｜有 .git（克隆/工作树）｜登记=是｜含 node_modules=否｜231.4 MiB
     · `_qoder_cmdr_int_0441` 123.2 MiB
     · `_qoder_cmdr_toolsland_1936` 108.2 MiB
  10 枚｜有 .git（克隆/工作树）｜登记=是｜含 node_modules=是｜1123.3 MiB
     · `_qoder_cmdr_ord0338_land` 116.0 MiB
     · `_qoder_cmdr_land_0345` 113.8 MiB
⇒ 这些带自己的 `.git`。手删会让主库 `.git/worktrees` 里的登记项变成悬挂引用；而本项目里已经有过一次的坑是：**对这种树用 `git worktree remove --force` 会顺着 junction 走到别人的树里去**（本项目的旧笔记里记过一次同类风险，所以我在这里只提不替你处理）。要清就走 `git worktree remove` 的正常路径、或由主人自己摘 junction 再删——这都不是我该动的——这一整件里我只跑过只读命令：`du`、`os.listdir`、`git ls-remote` / `cat-file` / `merge-base` / `rev-list` / `worktree list`，一条写操作都没有。

三、我只给分类与量，**不点名删哪一枚**：账本 0 引用 ≠ 可删（证据可能已入枝、可能别的名字引用它、也可能是车道留的复现现场）。删与不删等你或用户决定。
四、档位提示：自动轮 18:07:11 响过 2->1 GB（`5909025682`），现在回到 2237.2 MiB 是在 1–2 GiB 之间晃；再掉一档它会自己响，不用谁盯着。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
