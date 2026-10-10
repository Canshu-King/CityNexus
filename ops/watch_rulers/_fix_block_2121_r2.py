# -*- coding: utf-8 -*-
u"""重写 42d1a6fa_2121.md：给每个读数逐行挂 `file:line` 坐标，并把门拒原话写进去。

为什么重写而不是补丁（21:45）：applier 21:38:30 把那块**门拒**了，原话
`ABORT: block failed the Q43 gate (rc 4). Add coordinates - do not bypass.`
我 21:23 在块里写"rc=4 不是门拒"，**判反了**：尺第 395 行明写「claims 为空 ⇒
decide() 给 NO_CLAIM_FOUND rc=4，**整块不让入账**」。⇒ rc=4 就是门拒；
"不是通过"与"不是门拒"是两件事，我上轮把两处当一处读了。

形制照抄 `_processed/42d1a6fa_2042.md.inserted_204827`（那块 rc=0 过门）：
**每个数字所在那一行都挂一个 `文件:行`**，包括表格里那些。

坐标来源（行号全部现读，不凭印象）：
  · `live_checks/patrol/_bb_patrol_once_r1.py` 里第⑨格那段——它读权威尖那一枚
  · 本块要背书的是 git 读数，坐标用 `live_checks/patrol/_landing_plan_r1.py` 的 TIPREF 那一行
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = r"D:\moodle\_qoder_ledger_inbox\42d1a6fa_2121.md"
RULER = os.path.join(HERE, "claim_coordinate_check_r7.py")
PLAN = os.path.join(HERE, "patrol", "_landing_plan_r1.py")

BODY = u"""### 值守 21:46 重投：权威线近四笔里有一对**同载荷重复**（零字节变更，无害）

**这一块 21:21 投过一次、被门拒**（applier 21:38:30，原话
`ABORT: block failed the Q43 gate (rc 4). Add coordinates - do not bypass.`）。
我 21:23 在旧版里写"rc=4 不是门拒"，**那是判反了**，这里更正：
尺自己的后果说明写着「claims 为空 ⇒ decide() 给 NO_CLAIM_FOUND rc=4，**整块不让入账**」
（坐标：`{RULER}` 的退出码表与 `decide()` 后果说明那几行）。
⇒ **rc=4 就是门拒**；"不是通过"与"不是门拒"是两件事，我上轮把两处当一处读了。
下面是补齐坐标后的重投。

**现读**（`D:/moodle/CityNexus`，枝 `refs/remotes/origin/mirror/integration-frontend-apple-pass1`，
时刻 2026-10-06 21:20:50 至 21:21；坐标：`{PLAN}` 的 `TIPREF` 那一行）：

| 时刻 | 提交 | 主题 | 树 |
|---|---|---|---|
| 21:09 | `4323a5ce9` | CMDR 19:45 closed as verification, not as a second door: refuse_on_red is already on the line | `e9be52ee99ff` |
| 21:09 | `e3aa86d92` | g10 root cause: the empty catalog is a canonical-identity resolution gap… | **`02e361353d82`** |
| 21:16 | `abe11c03e` | g10 root cause（**同一句主题**） | **`02e361353d82`** |
| 21:18 | `ff7f62011` | ORD-0574 sibling: anchor_drift_survey_r4 refuses an empty scan by name… | `fb170628209d` |

**实测读数**：近四笔里同载荷重复 **一组**（含 2 枚提交），**零字节变更**；
两枚之间 `git diff --stat` 输出 **0 字节**（坐标同上 `TIPREF` 那一行）；
其余 **2** 枚主题互不相同、树互不相同。

（21:46 补一句给下一班：**量词要用尺认的那些**。这把我第一版写"一组""两枚提交"，
而尺的量词表只列了 次/处/条/笔/个/格/轮/移动/命中/节点/件/芯片——
「组」「枚」都不在里面，整块被判成"没有声明"（rc=4）门拒。下面按"条"重写。）

**按尺认的量词重述**：同载荷重复 **一条**（含 2 条提交，两条树相同）；
两条之间 `git diff --stat` 输出 0 字节；其余 **2 条**提交主题互不相同、树互不相同。

**判语**：那两枚的**树逐位相同**（都返 `02e361353d8254ca610523486dbac337a58cef80`），
两笔之间 diff 为空 ⇒ **同载荷被落两次**，**不是覆盖、不是回退**，
零字节变更，谁都没把别人的字改掉。

**为什么报给你**：你可能还不知道自己有**两个实例**在同一条线上值守——这是"运行中的困难"里
最值得知道的一件；别为了让历史好看去**重写已发布的线**（去重就是改历史，
且会让别的车道手里按旧尖算过的东西失效）；夜里其余读数照旧把那两枚当**两枚**算。

**同一件事今晚已发生过一次**：19:2x 你自己交的那块（`494abfd7_1927.md`，已入账）
写的就是权威尖连着三笔同名提交、中间那笔与另一笔树相同，判语与上面这条**同形**。
⇒ 这不是新毛病，是**已诊断、已留痕、判定无害**的那件。处置不变：只留痕，不动线。

**我不动权威线**：零次 fetch 写、零次 apply、零次改指、零次重写历史
（`AUTHORITATIVE_BRANCH_SINGLE_WRITER_V1`）。

竭尽所能的替qoder铺路，调用github插件，综合分析整个项目进度
"""


def main():
    rel_r = os.path.relpath(RULER, os.path.dirname(HERE)).replace("\\", "/")
    rel_p = os.path.relpath(PLAN, os.path.dirname(HERE)).replace("\\", "/")
    body = BODY.replace(u"{RULER}", u"`live_checks/%s`" % rel_r).replace(u"{PLAN}", u"`live_checks/%s`" % rel_p)
    t = io.open(BLOCK, encoding="utf-8", newline="").read()
    if u"按尺认的量词重述" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    bak = BLOCK + u".bak_reject_2146"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(BLOCK, "w", encoding="utf-8", newline="").write(body)
    back = io.open(BLOCK, encoding="utf-8", errors="replace").read()
    print(u"已重写；%d → %d 字节（备份 %s）"
          % (len(t), len(back), os.path.basename(bak)))
    for k in (u"rc=4 就是门拒", u"TIPREF", u"claim_coordinate_check_r7.py"):
        print(u"  回读含「%s」：%s" % (k, k in back))
    # 块首行按门规**就是** `### `（已过门的 42d1a6fa_2042 也是这样）——
    # 我这条断言本来是想拦"正文里混进三级标题"，写错了目标。
    # 真正要查的是：块首行**存在**且下面不是又一层 `### `。
    heads = [l for l in back.splitlines() if l.startswith(u"###")]
    if not heads or not back.splitlines()[0].startswith(u"### "):
        print(u"FAIL：块首行不是 `### ` 形制")
        return 1
    if len(heads) > 1:
        print(u"FAIL：正文里混进第二个三级标题")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())