# -*- coding: utf-8 -*-
u"""把形状闸接进巡逻第②格：静默过档之后，还要末态判「断在半路」才算真该敲。

为什么（20:11–20:13 六拍现读）：
  19:55 ②列出 0afdb49b 静 51 分／20:08 ②列出 8ac89982 静 46 分、0afdb49b 静 63 分；
  20:11 逐扇回读流水，**这两扇末条都在 1 分前**（一扇跑工具、一扇在思考），板上同刻 idle 0.9／1.1。
  ⇒ "静默过档且未取>0"量到的是**一次长间隔**，不是停摆。原判据只有 idle+unread 两项，看不见末态。

改法（只动这一处，②格的其余分支与①②③④…⑫格一行不碰）：
  在 `if (r.get("unread") or 0) > 0:` 之前插一道 `shape_of(r["id8"])`：
    「断在半路」⇒ 真该敲（照旧进 knock）
    「交活型停着」/ 已经在写 ⇒ 落 `waiting`（那一格是"缺下一件，不是懒也不是卡"）
    读不到判词 ⇒ 落 `undecidable` 单独一格，**不混进 knock 也不混进 waiting**
              （不拿默认值冒充读数——这是判红纪律）
末态判词来自 `_lane_tailform_r1.py`（末态尺），本补丁只调它，不复制形态识别逻辑。

为什么要有 undecidable 那一格：形状闸自测第 ④ 臂就是"判词读不到⇒不可判"。
若把它塞进 waiting，那一格说的是"缺下一件"，语义就错了；塞进 knock 更糟（会去敲）。

跑法：python _patch_patrol_shape_gate_r1.py
"""
import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "_bb_patrol_once_r1.py")
TAILFORM = os.path.join(HERE, "_lane_tailform_r1.py")

OLD = u'''        if (r.get("unread") or 0) > 0:
            knock.append(r)
        else:
            waiting.append(r)
'''

NEW = u'''        if (r.get("unread") or 0) <= 0:
            waiting.append(r)
            continue
        # 形状闸（20:13 装）：静默过档 **且** 末态判「断在半路」才算真该敲。
        # 原判据只有 idle+unread，看不见末态 ⇒ 19:55/20:08 两拍把"静完自己走回来的车"
        # 列成该敲（20:11 回读：两扇末条都在 1 分前）。判词由 _lane_tailform_r1.py 给，不另写一套。
        _v = shape_of(r["id8"])
        if _v == u"\\u65ad\\u5728\\u534a\\u8def" or u"断在半路" in _v:
            knock.append(r)
        elif _v.startswith(u"（读不到"):
            undecidable.append((r, _v))
        else:
            waiting.append(r)
'''


def main():
    t = io.open(SRC, encoding="utf-8", newline="").read()
    if u"形状闸" in t and u"undecidable" in t:
        print(u"已在 ⇒ 不重复改")
        return 0
    if t.count(OLD) != 1:
        print(u"REFUSE：锚命中 %d 次（应为 1），未写盘" % t.count(OLD))
        print(u"现读那段：")
        i = t.find(u"knock, waiting = [], []")
        print(t[i:i + 700])
        return 1
    new = t.replace(OLD, NEW, 1)

    # 声明两个新容器 + 形状闸调用（放在那一段之前）
    old_decl = u"    knock, waiting = [], []\n"
    new_decl = (u"    knock, waiting, undecidable = [], [], []\n"
                u"    # 末态尺：每拍起一次子进程读那一扇的 jsonl 末三条（只读，0 发送）\n"
                u"    _shape_cache = {}\n"
                u"\n"
                u"    def shape_of(id8):\n"
                u"        if id8 in _shape_cache:\n"
                u"            return _shape_cache[id8]\n"
                u"        try:\n"
                u"            p = subprocess.run([sys.executable, TAILFORM, id8],\n"
                u"                             capture_output=True, cwd=HERE, timeout=60,\n"
                u"                             env=dict(os.environ, PYTHONIOENCODING=\"utf-8\"))\n"
                u"            out = (p.stdout or b\"\").decode(\"utf-8\", \"replace\")\n"
                u"            v = u\"（读不到判词）\"\n"
                u"            for _l in out.splitlines():\n"
                u"                if _l.strip().startswith(u\"\\u21d2\"):\n"
                u"                    v = _l.strip()[1:].strip()\n"
                u"                    break\n"
                u"        except Exception:\n"
                u"            v = u\"（读不到判词：%s）\" % \"子支起不来\"\n"
                u"        _shape_cache[id8] = v\n"
                u"        return v\n")
    if new.count(old_decl) != 1:
        print(u"REFUSE：声明锚命中 %d 次，未写盘" % new.count(old_decl))
        return 1
    new = new.replace(old_decl, new_decl, 1)

    # 打印第四格
    old_p = u'''    print(u"③ 不该敲（缺下一件，不是懒也不是卡）%d 扇：%s"'''
    new_p = u'''    if undecidable:
        print(u"②b 末态不可判 %d 扇（形状闸读不到判词，**不列该敲也不列不该敲**）：%s"
              % (len(undecidable),
                 u"、".join(u"%s %s（%s）" % (x[0]["id8"], x[0]["name"], x[1]) for x in undecidable)))
    print(u"③ 不该敲（缺下一件，不是懒也不是卡）%d 扇：%s"'''
    if new.count(old_p) != 1:
        print(u"REFUSE：③格打印锚命中 %d 次，未写盘" % new.count(old_p))
        return 1
    new = new.replace(old_p, new_p, 1)

    # 常量
    old_c = u'CMDR = u"qoder:494abfd7"\n'
    new_c = (u'CMDR = u"qoder:494abfd7"\n'
             u'TAILFORM = u"_lane_tailform_r1.py"   # 末态尺（20:13 形状闸的唯一判词来源）\n')
    if new.count(old_c) != 1:
        print(u"REFUSE：常量锚命中 %d 次，未写盘" % new.count(old_c))
        return 1
    new = new.replace(old_c, new_c, 1)

    try:
        ast.parse(new)
    except SyntaxError as e:
        print(u"REFUSE：SyntaxError，未写盘：%s" % e)
        return 1

    bak = SRC + u".bak_shapegate_1213"
    if not os.path.exists(bak):
        io.open(bak, "w", encoding="utf-8", newline="").write(t)
    io.open(SRC, "w", encoding="utf-8", newline="").write(new)
    print(u"已接形状闸（备份 %s）" % os.path.basename(bak))
    print(u"新段：")
    for l in new.splitlines():
        if u"形状闸" in l or u"undecidable" in l or u"shape_of" in l:
            print(u"  " + l.rstrip()[:96])
    return 0


if __name__ == "__main__":
    sys.exit(main())