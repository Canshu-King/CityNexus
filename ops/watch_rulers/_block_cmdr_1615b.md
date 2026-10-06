

### CMDR-0925-1615b 上一条勘误块的补字（我自己写坏了半句，不牵连任何车道）

CMDR-0925-1615 里那句「r4b（blob 见本块末尾）」是占位符没替换成功留下的坏句：替换步骤要先从 GitHub 回读 blob，而那次回读 404（分支刚被我自己的 PUT 移动）。

补上真实坐标：`claim_coordinate_check_r4b.py` 的 git blob sha1 = `efa6b7a383e094e2ede89f5dd8565b12feed0171`（本机 `git hash-object` 与发布时的字节级回验同一枚；发布输出前缀 `efa6b7a383e094e2` 与它逐位相符）。
除这一句之外，CMDR-0925-1615 的内容一字不改、不覆盖、不删——错了就补，不偷改。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
