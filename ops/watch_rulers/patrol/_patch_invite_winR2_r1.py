# -*- coding: utf-8 -*-
u"""接入件两处收口：①「那两扇」改成「那一扇」（现读未接的只有 Window R 一扇）；
② join 的示例 id 直接填成 codex:winR，省掉那扇窗自己想名字这一步。

顺带把 join 的**真实用法**抄进去：20:30 现读 `bus.py join --help` 的形制是
`join --id ID [--name NAME] [--kind KIND]`——件里原本没写 `--kind`，补上，
免得那扇窗以为只能注册不能声明 kind。

安全：只改这份纯文本接入件；不碰 bus.py／board.py／任何腿；不注册任何身份
（注册是那扇窗或人自己执行的动作，我不起）。
"""
import io
import os
import sys

INV = u"D:/moodle/agent_bus/INVITE_CODEX.txt"


def main():
    t = io.open(INV, encoding="utf-8", newline="").read()
    orig = t

    a_old = u"""用途：Codex 那两扇正在干活的窗口（近六小时有轮次，现读 `~/.codex/thread_history_1.sqlite` 只读副本）
还没进 BB 机名册。谁在 Codex 那边粘下面这一行都行，粘完值守这侧的巡逻就能逐扇盯它的静默与未取。
不需要改任何配置，也不需要重启那两扇。"""
    a_new = u"""用途：**CityNexus Codex Window R**（近 90 分活跃窗 `01a10cd0…`，派生自父窗 `01a0c796…`）
还没进 BB 机名册。在那扇窗里粘下面这一行就行，粘完值守这侧的巡逻就能逐扇盯它的静默与未取。
不需要改任何配置，也不需要重启那扇窗。名册里已有的 `codex:bbfix1` 是**另一扇**（早接上），别重复注册。"""
    if a_old in t:
        t = t.replace(a_old, a_new, 1)
        print(u"① 用途段已改准（两扇→那一扇，并点名不是 bbfix1）")
    else:
        print(u"① 用途段锚没命中（可能已改过）⇒ 跳过，现读：")
        i = t.find(u"用途：")
        print(u"   %s" % t[i:i + 200].replace(chr(10), u" / "))

    b_old = u"""```
python D:/moodle/agent_bus/bus.py join --id codex:<花名短码>
```

把 `<花名短码>` 换成这扇窗口的活名，只用字母数字与连字符，例如 `codex:census-r1`。
同一条命令重跑是幂等的；带 `--name 花名·姓名` 才会改花名，不带 name 的重注册不会把已有花名顶回 id。"""
    b_new = u"""```
python D:/moodle/agent_bus/bus.py join --id codex:winR --name "CityNexus·Window R"
```

`--id` 用这枚（窗名 R 缩写的短码）；`--name` 是给人看的花名，可省。
想声明 kind 就加 `--kind <字母>`（现读 `bus.py join --help` 的形制就是
`join --id ID [--name NAME] [--kind KIND]`）。
同一条命令重跑是幂等的；带 `--name` 才会改花名，不带 name 的重注册不会把已有花名顶回 id。
**若你其实是 bbfix1 那扇**：它 10-04 就接上了，别再注册，直接 `read --all` 就行。"""
    if b_old in t:
        t = t.replace(b_old, b_new, 1)
        print(u"② join 段已填实 id（codex:winR）并补 --kind")
    else:
        print(u"② join 段锚没命中 ⇒ 跳过，现读：")
        i = t.find(u"bus.py join")
        print(u"   %s" % t[max(0, i - 120):i + 320].replace(chr(10), u" / "))

    if t == orig:
        print(u"REFUSE：两处都没改 ⇒ 不写盘")
        return 1
    bak = INV + u".bak_winR2_2030"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(orig)
    io.open(INV, "w", encoding="utf-8", newline="").write(t)
    back = io.open(INV, encoding="utf-8", errors="replace").read()
    print(u"已写｜%d → %d 字节（备份 %s）" % (len(orig), len(back), os.path.basename(bak)))
    for k in (u"codex:winR", u"--kind", u"CityNexus·Window R", u"是**另一扇**"):
        print(u"  回读含「%s」：%s" % (k, k in back))
    print(u"  旧「那两扇」还在：%s（应为 False）" % (u"那两扇" in back))
    return 0


if __name__ == "__main__":
    sys.exit(main())