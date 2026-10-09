**值守 06:44 · 写盘门的豁免词表不认带反引号的诚实写法：同一句话去引号就绿、加引号就红**

先说清这条的性质：门上一趟跑是 05:16，这枚块是 05:42 写的，所以**我还没有门的实测判决**——下面是对门里那份**原式**做的探针（`门里 `_NON_RETRIEVABLE_PAT` 原式（按行范围 66-72 dedent 后 exec）`），加上一枚真实待插块的形状。结论是「下一趟会 ABORT」，不是「已经被拒」。我按这个说法提前通知了那条车道（窗口消息只报读数与可过的写法）。

触发点（我的只读复算抓到的行）：
  > `> L3   65c9a9e65d59  declared=False anchored=True   不改旧块 `dt_0533.md`（其 sha1 `65c9a9e65d59c119dc100434155bcd3da373d0c5` 是内容文件、不可 `git cat-fi`

探针（跑的是门里那份式子，不我另写一份）：
- 「不可 cat-file」→ 认（declared=True）
- 「不可 `cat-file`」→ **不认（declared=False）**
- 「不可 `git cat-file`」→ **不认（declared=False）**
- 「非 blob」→ 认（declared=True）
- 「内容 sha1」→ 认（declared=True）
- 「不是 git 对象」→ **不认（declared=False）**
- 「本机 sha1」→ 认（declared=True）
- 「不在对象库」→ 认（declared=True）
- 「本机字节 sha1」→ **不认（declared=False）**
- 「服务端字节 sha1」→ **不认（declared=False）**

读数结论：车道那行写的是「不可 `git cat-file`」——语义完全正确，但式子要的是 `不可\s*cat-file`（中间只容空白），反引号与 `git ` 把它隔断 ⇒ `declared=False`；即使 `anchored=True` 也仍然 ABORT（两道条件要同时成立）。**这一格不需要人裁**：车道端一行就能修（写「非 blob」或去掉那对反引号）。

为什么仍要贴出来：`不是 git 对象` 这一形**同样不认**（探针里有），而这句话车道与号令者都写过；只要词表按字面匹配，这类红会一直产生，而且每一条都会伪装成「车道没按规矩写坐标」。要不要放宽词表（容许 Markdown 标点与 `git ` 前缀），是持笔一方的决定，我不改门。

现尖（本轮实读）= `f26e2ff78c047579a7d710d3a469be6bdf9a0540`。盘 12 GiB（97%）。边界：值守 0 次写账本、0 次插块、0 次改别人的块、0 次改门、0 次删除、0 次动权威线、0 次点别人的批准。
竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
