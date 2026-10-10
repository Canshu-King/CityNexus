# -*- coding: utf-8 -*-
u"""交接稿补两节：五·五十一（末条形态只认对话节点）、五·五十二（长跑循环要挂进值守栈）。

为什么必须写进交接稿：这两条都是 19:3x 当场踩的坑，而且**都伪装成好消息**——
一条把三扇在跑的读成"活的假象"，另一条把"起过了"读成"活着"。下一班不读这段就会重踩。

写进去前先验：五·五十一的三条数字取自 19:33 现读；五·五十二的取自 19:14–19:31 实测。
另：这两节的编号必须接着现有最大编号（现读最大＝五·五十），不许跳号。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC51 = u"""## 五·五十一、判「谁在不在动」只认**对话节点**：脚手架节点每分钟都刷新

19:28:51 哨兵 J 档判红，红因列了四扇；19:33 我逐扇打开 jsonl 核实，**三条已被现读推翻**：

| 车道 | 哨兵 19:28 的报法 | 19:33 现读 | 判定 |
| --- | --- | --- | --- |
| 89f2e2d6 木工·小孙 | 断在半路（尾条是没回音的 tool_use） | 末三条＝assistant text → tool_use:Bash → user tool_result，0 分前 | 假 |
| 2d2d7428 玻璃工·小陈 | 交 1686 分／静 34 分 | idle 0.1 分，正在写 | 假（时间差） |
| 6a773af1 电焊工·老王 | 交 1542 分／静 38 分 | idle 0.8 分，正在写 | 假（时间差） |
| 45d25bfb 脚手架·老秦 | 交 965 分／静 31 分 | 末条 assistant text，36 分前，板上 idle 36.4 | **真** |

第一版核实脚本栽在**两个坑**上，两个都要传给下一班：

1. **只认有 role 或 content 的对话节点**。jsonl 末尾三条常常是 `active-leaf`／`runtime-config`／
   `file-history-snapshot` 这类脚手架节点——它们**每分钟被工具刷新**，看着像"这扇一直在动"。
   我第一版取到"0 分前 tool_result"，差点把三扇在跑的判成活的假象。
2. **timestamp 是 epoch 毫秒**（实测 `1791286362177`），当秒用 `fromtimestamp` 直接 OverflowError。

工具：`patrol/_verify_sentinel_red_r1.py`（可重跑，数字现取）。
勘误已追加进 `patrol/_sentinel_relay_HIT.txt`（备份 `.bak_1934`），**没改哨兵代码**——
它报的是 19:28 那一刻的读数，那时候三扇确实静，这是时间差不是它判错。

归属：45d25bfb 是「交完活等验收」，按 LANE_PROTOCOL 归号令者点验收，不归敲门那一格。
我 0 发送、0 上总线。

## 五·五十二、长跑循环要挂进**值守栈**，自己用工具手起只会活一拍

巡检跑批 `_patrol_loop_r1.py`（每 12 分钟自己跑一次巡逻并存档，19:1x 落的）起法试了两次：

| 怎么起的 | 结果 |
| --- | --- |
| Bash 后台 `&`（pid 4676） | 19:09:04 跑完第一拍，19:21 的第二拍**没落盘** |
| 工具 Popen + `DETACHED_PROCESS`（pid 11300） | 19:15:01 跑完第一拍，之后 tasklist 三连查皆无；stdout 空、无异常栈 |
| 挂进 `_watch_stack_r1.py` 的 COMPONENTS（pid 35364） | 19:18:48 第一拍、**19:31:22 第二拍都落了**，进程仍在 |

前两种与栈腿**同形制**却活不过一拍 ⇒ 不是形制问题，是它落在**工具进程树的清理范围**里。
栈腿由 `_watch_stack_r1.py` 起、归属不同，所以能整夜活着。

⇒ 结论：**新的长跑循环一律加进 COMPONENTS**，这样机器重启后 `--check`／起复就能把它带回来。
两个配套要点：

- 条目必须**四元**。栈把 `entry[4]` 当**档点**塞 `NVR_AT=` argv，跑批不认那个变量。
  间隔走 env：`PATROL_LOOP_MIN`（栈的 `start()` 会把 `os.environ` 传下去）。
- 档名**带 pid**（`round_<日期>_<pid>_<n>.txt`）。两枚跑批同时跑时档名都是 `_001` ⇒ 互相覆盖，
  这正是 19:0x 那次的原样重演。叠上跑批自带的单实例锁 `claim()` 才双重保险。

待看档（新增）：`patrol/rounds/_needs_eyes.log`。每拍把结论判红写进去，**只在状态翻转时写**
（红写两行、由红转绿写一行），所以我不用每 12 分钟跑整条巡检去 diff 也能看见"谁停了"。
判据 `judge()`：结论行不是「全队都在动」，或 ①未接 BB 机／②该敲／③不该敲／⑥值守栈／⑩推广 任一非零。
自测 `patrol/_patrol_loop_needseyes_selftest_r1.py` 六臂：真档绿｜结论变红｜该敲非零红｜栈塌红｜空文本红｜去重。

**踩出来的一个副产物**：判红第一版有假红（每拍都红）。两个错——① ` 0 扇` 的空格是我凭空想的，
实际是 `）0 扇`；② 我以为 ⑥ 是 U+2466，实际 ⑥ 是 U+2465（圈号是连续码位 0x2460＋n-1）。
改法：圈号**按序号推码位**、判据**抽数字再比 0**，不靠空格也不靠 WATCH_CELLS 兜。
**不咬人的报警等于没有报警**——新的报警腿一律要有"该红的那一次"。
"""

ANCHOR = u"## 五·五十、覆盖核对"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十一" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    # 现读最大编号（中文数词反解，只为确认不跳号）
    def cn(n):
        if n < 10:
            return CN[n]
        if n < 20:
            return u"十" + (CN[n % 10] if n % 10 else u"")
        return CN[n // 10] + u"十" + (CN[n % 10] if n % 10 else u"")

    vals = set()
    for w in re.findall(r"^## 五·([一二三四五六七八九十百]+)、", t, re.M):
        try:
            vals.add(int(cn_re(w)))
        except Exception:
            pass
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十锚")
        return 1
    j = t.find(u"\n## ", i)
    if j < 0:
        j = len(t)
    new = t[:j] + u"\n\n" + SEC51 + t[j:]
    if u"五·五十一" in new and u"## 五·五十一" not in new:
        print(u"REFUSE：节标题没成形")
        return 1
    # 写盘前体检：标题不成粘连、不重号
    heads = re.findall(r"^## .+$", new, re.M)
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连")
        return 1
    bak = HAND + u".bak_51_52_1935"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已写：新小节 %s（现读最大 中文序号见下）" % u"、".join(
        re.findall(r"^## (五·五[十二]+)、", new, re.M)))
    print(u"全文行数 %d → %d" % (t.count(u"\n"), new.count(u"\n")))
    return 0


def cn_re(w):
    u = {u"零": 0, u"一": 1, u"二": 2, u"三": 3, u"四": 4, u"五": 5,
         u"六": 6, u"七": 7, u"八": 8, u"九": 9}
    total, cur = 0, 0
    for ch in w:
        if ch == u"十":
            total += (cur or 1) * 10
            cur = 0
        elif ch in u:
            cur = u[ch]
    return total + cur


if __name__ == "__main__":
    sys.exit(main())