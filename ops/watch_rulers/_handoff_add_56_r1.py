# -*- coding: utf-8 -*-
u"""交接稿补一节：五·五十六——**活锁不是遗弃锁**，「超 N 分钟即遗弃」会误清它。

为什么必须写：21:06 车道 `1d64acf5` 交件报「共享仓库那把 `shallow.lock` 挡死了所有读线请求」。
我 21:11 现读：那把锁**已经不在**，`git fetch origin` rc=0 无错 ⇒ 警报自己解了。
但它暴露的真问题留给下一班：**那把锁是被持锁的 fetch 正常释放的，不是被"五分钟即遗弃"清掉的**；
车道当时判它是**活锁**（查得到持有者的 CommandLine），因此那条自动清锁的规矩**一旦套上去就会误清**。

为什么要紧：`shallow.lock` 挡的是**读线请求**，而权威尖取数、两把到点取数、落地闸全都要 fetch。
误清活锁 ⇒ 并发 fetch 同时写同一份索引 ⇒ 索引写坏，那比"卡住"更坏。

**判据（三条都要，缺一条就当活锁）**：
  ① 零字节 ＋ 龄超线（龄只是必要条件，不是充分）；
  ② **查得到持有者**：按 CommandLine 找 `git -C D:/moodle/CityNexus fetch …`；
  ③ 持有者还活着 ⇒ **活锁，不许清**。
  只有①②③都不成立（查不到持有者 ＋ 进程确已不在 ＋ 龄远超线）才当遗弃锁。
  反过来：**查不到持有者不等于没有持有者**——查法本身可能失败（WMI 超时、命令写错、名字在别处），
  查不到时按"不可判"处理，不当遗弃（这与我今晚在哨兵 instances() 上踩的是同一形）。

现读（21:11:37）：`D:/moodle/CityNexus/.git/shallow.lock` 不存在；`git fetch origin` rc=0、
stderr 空；锁仍不在。⇒ 那次挡线已自愈，无需人工干预。**本节只留判据，不动手清任何锁。**
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HAND = os.path.join(HERE, "HANDOFF_20261005_NIGHT.md")

SEC = u"""## 五·五十六、**活锁不是遗弃锁**：「超 N 分钟即遗弃」会误清它

21:06 车道 `1d64acf5` 交件报：共享仓库那把 `shallow.lock` 挡死了**所有读线请求**。
21:11 我现读：那把锁**已经不在**，`git fetch origin` rc=0、stderr 空 ⇒ 警报自己解了。
但真问题留给下一班：**那把锁是被持锁的 fetch 正常释放的**，车道当时判它是**活锁**
（查得到持有者的 CommandLine）。所以「超五分钟即遗弃」那条规矩**一旦套上去就会误清它**。

**为什么这事要紧**：`shallow.lock` 挡的是读线请求，而权威尖取数、两档到点取数、落地闸
全都要 fetch。误清活锁 ⇒ 两个 fetch 同时写同一份索引 ⇒ 索引写坏，那比"卡住"更坏。

**判据（三条都要，缺一条就当活锁）**：

| 条 | 内容 |
|---|---|
| ① 必要不充分 | 零字节 **且** 龄超线——龄只是第一道 |
| ② 持有者 | 按 CommandLine 找 `git -C D:/moodle/CityNexus fetch …` |
| ③ 活判 | 持有者还活着 ⇒ **活锁，不许清** |

只有 ①②③ 都不成立（查不到持有者 **且** 进程确已不在 **且** 龄远超线）才当遗弃锁。
**「查不到持有者」不等于「没有持有者」**：查法本身可能失败（WMI 超时、命令写错、
持有者以别的命令行出现）——查不到时按**不可判**处理，不当遗弃。
（同形：我今晚在哨兵 `instances()` 上踩过一次，CIM 全表枚举超时被读成"没哨兵"，
那次是**加盲分支**解决的，不是当它不存在。）

现读（21:11:37）：`D:/moodle/CityNexus/.git/shallow.lock` 不存在；`git fetch origin` rc=0、
stderr 空；锁仍不在。⇒ 那次挡线已自愈，无需人工干预。
**本节只留判据；我 0 次删除任何锁**（删锁是破坏性动作，破坏性与后果要同一扇门）。
"""
ANCHOR = u"## 五·五十五、"


def main():
    t = io.open(HAND, encoding="utf-8", newline="").read()
    if u"五·五十六" in t:
        print(u"已在 ⇒ 不重复补")
        return 0
    i = t.find(ANCHOR)
    if i < 0:
        print(u"REFUSE：找不到五·五十五锚")
        return 1
    new = t[:i] + SEC + u"\n" + t[i:]
    heads = re.findall(r"^## .+$", new, re.M)
    if any(h.startswith(u"## ##") for h in heads):
        print(u"REFUSE：标题粘连，未写盘")
        return 1
    if any(l.startswith(u"### ") for l in new.splitlines()):
        print(u"REFUSE：出现三级标题，未写盘")
        return 1
    dup = [h for h in set(heads) if heads.count(h) > 1]
    if dup:
        print(u"REFUSE：重号标题 %s" % dup)
        return 1
    bak = HAND + u".bak_56_2113"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(bak and t)
    io.open(HAND, "w", encoding="utf-8", newline="").write(new)
    print(u"已补 五·五十六；行数 %d → %d；五·小节现 %d 节"
          % (t.count(u"\n"), new.count(u"\n"),
             len(re.findall(r"^## 五·", new, re.M))))
    return 0


if __name__ == "__main__":
    sys.exit(main())