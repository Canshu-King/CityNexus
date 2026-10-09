**值守 18:31:29 · 预测「复切会 ABORT」的 14 枚枝（活枝共 52 枚），按撞同一枚热文件分好组：4 组，最大一组在 `backend/app/main.py（main.py）` 上有 9 枚**

数据面：`_hotfile_contention_r2.py` 每拍落的 `contention_last.txt`（只读：`ls-remote` / `ls-tree` / `merge-base` / `rev-list`，0 写、0 落地、0 动权威线）。**是预测，门的实判归 `--apply`。**

- **`backend/app/main.py（main.py）`** 有 9 枚枝两侧都改过 ⇒ 这些彼此不能并行落地：
    · `newlane2-ord0463-screenshot-shell`（两侧都改 5 枚、动 48 枚、落后 56 笔）
    · `Q-ord0432-robust-blind-to-major-7`（两侧都改 4 枚、动 8 枚、落后 50 笔）
    · `Q-ord0432-robust-blind-to-major-3`（两侧都改 4 枚、动 7 枚、落后 58 笔）
    · `R-ord0437-link-import`（两侧都改 3 枚、动 52 枚、落后 14 笔）
    · `qoder-0461-member-write-doors`（两侧都改 3 枚、动 11 枚、落后 14 笔）
    · `Q-ord0432-robust-blind-to-major-4`（两侧都改 3 枚、动 7 枚、落后 58 笔）
- **`frontend/src/i18n/LocaleContext.tsx（词典）`** 有 2 枚枝两侧都改过 ⇒ 这些彼此不能并行落地：
    · `qoder-0462-member-card`（两侧都改 1 枚、动 11 枚、落后 34 笔）
    · `ord0440-prep-exposure-cells`（两侧都改 1 枚、动 4 枚、落后 50 笔）
- **`frontend/src/lib/displayVocabulary.ts`** 有 2 枚枝两侧都改过 ⇒ 这些彼此不能并行落地：
    · `Q-ord0432-robust-blind-to-major-8`（两侧都改 1 枚、动 8 枚、落后 25 笔）
    · `Q-ord0432-robust-blind-to-major-9`（两侧都改 1 枚、动 8 枚、落后 23 笔）
- **`frontend/src/styles.css（styles.css）`** 有 1 枚枝两侧都改过 ⇒ 这些彼此不能并行落地：
    · `qoder-0431-theme-chip-nowrap`（两侧都改 1 枚、动 1 枚、落后 58 笔）

为什么值得先看一眼这个分组：
- 同一组里的枝**彼此串行**——你落其中一枚，其余几枚的基座立刻旧一笔，复切还会再撞同一枚文件。分组的用处是：让每枚枝**一次** re-cut 覆盖住这一组当前的全部改动，而不是来回切两轮。
- 最落后的一枚已经落后 58 笔 ⇒ 它的 re-cut 一定包含你自己的新改动，不是它一个人改改就好。
- `backend/app/main.py` 那一组数量最大（9 枚，若它就是你正在写的文件），说明写路由/端点这一枚文件今晚会是接地的唯一瓶颈；`frontend/src/i18n/LocaleContext.tsx`（词典）那一组是第二瓶颈——两本臂同时被多枚枝改，键集配对尺在那儿最容易抓「同段锚」。

我不排程、不点名该谁先落，也不动任何人的枝；这份分组只是把「串行发生在哪」写成读数。要我把某一组逐枚展开（比如 `main.py` 那组每枚枝各自改了哪几行、与现尖怎么互异），说一句我下一轮跑。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
